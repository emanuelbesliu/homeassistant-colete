"""Data update coordinator for IMAP email scanning.

Periodically scans an IMAP mailbox for shipping notification emails,
extracts AWB numbers, and creates tracked parcels via the existing
colete.track_parcel service flow.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_AWB,
    CONF_IMAP_EMAIL,
    CONF_IMAP_FOLDER,
    CONF_IMAP_LOOKBACK_DAYS,
    CONF_IMAP_PASSWORD,
    CONF_IMAP_PORT,
    CONF_IMAP_SCAN_INTERVAL,
    CONF_IMAP_SERVER,
    COURIER_AUTO,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_IMAP_LOOKBACK_DAYS,
    DEFAULT_IMAP_SCAN_INTERVAL,
    DOMAIN,
    IMAP_STORAGE_KEY,
    IMAP_STORAGE_VERSION,
)
from .imap_scanner import ExtractedAwb, ImapAwbScanner, ScanResult

_LOGGER = logging.getLogger(__name__)


class ImapDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls IMAP for AWBs and creates parcel entries."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the IMAP coordinator."""
        self.entry = entry
        self._email = entry.data[CONF_IMAP_EMAIL]

        scan_interval = entry.options.get(
            CONF_IMAP_SCAN_INTERVAL,
            entry.data.get(CONF_IMAP_SCAN_INTERVAL, DEFAULT_IMAP_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_imap_{self._email}",
            update_interval=timedelta(seconds=scan_interval),
        )

        # Persistent storage for seen AWBs (survives restarts)
        self._store: Store = Store(
            hass,
            IMAP_STORAGE_VERSION,
            f"{IMAP_STORAGE_KEY}_{entry.entry_id}",
        )
        # {awb: {"status": "tracked"|"invalid"|"dismissed", "first_seen": iso_ts}}
        self._seen_awbs: dict[str, dict[str, str]] = {}
        # Set of IMAP UIDs already processed in this session
        self._processed_uids: set[str] = set()
        # Scan statistics
        self._total_awbs_found: int = 0
        self._last_scan_time: str | None = None
        self._last_error: str | None = None

    async def async_load_seen_awbs(self) -> None:
        """Load previously seen AWBs from persistent storage."""
        data = await self._store.async_load()
        if data and isinstance(data, dict):
            self._seen_awbs = data.get("seen_awbs", {})
            self._processed_uids = set(data.get("processed_uids", []))
            self._total_awbs_found = data.get("total_awbs_found", 0)
            _LOGGER.debug(
                "Loaded %d seen AWBs, %d processed UIDs from storage",
                len(self._seen_awbs),
                len(self._processed_uids),
            )

    async def _async_save(self) -> None:
        """Save seen AWBs to persistent storage."""
        await self._store.async_save(
            {
                "seen_awbs": self._seen_awbs,
                "processed_uids": list(self._processed_uids),
                "total_awbs_found": self._total_awbs_found,
            }
        )

    def _get_currently_tracked_awbs(self) -> set[str]:
        """Get AWBs currently tracked as parcel config entries."""
        tracked = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            awb = entry.data.get(CONF_AWB)
            if awb:
                tracked.add(awb)
        return tracked

    def _create_scanner(self) -> ImapAwbScanner:
        """Create an IMAP scanner from current config."""
        return ImapAwbScanner(
            server=self.entry.data[CONF_IMAP_SERVER],
            port=self.entry.data.get(CONF_IMAP_PORT, 993),
            email_address=self.entry.data[CONF_IMAP_EMAIL],
            password=self.entry.data[CONF_IMAP_PASSWORD],
            folder=self.entry.options.get(
                CONF_IMAP_FOLDER,
                self.entry.data.get(CONF_IMAP_FOLDER, DEFAULT_IMAP_FOLDER),
            ),
            lookback_days=self.entry.options.get(
                CONF_IMAP_LOOKBACK_DAYS,
                self.entry.data.get(
                    CONF_IMAP_LOOKBACK_DAYS, DEFAULT_IMAP_LOOKBACK_DAYS
                ),
            ),
        )

    async def _async_track_awb(self, extracted: ExtractedAwb) -> bool:
        """Attempt to track a newly discovered AWB.

        Returns True if tracking was initiated, False if AWB was invalid.
        """
        awb = extracted.awb
        courier = extracted.courier_hint if extracted.courier_hint != "auto" else "auto"

        _LOGGER.info(
            "IMAP scanner found new AWB %s (courier hint: %s, from: %s, subject: %s)",
            awb,
            courier,
            extracted.sender,
            extracted.subject[:60],
        )

        # Use the track_parcel service to create the entry
        # This handles validation, auto-detect, and config entry creation
        try:
            await self.hass.services.async_call(
                DOMAIN,
                "track_parcel",
                {
                    "awb": awb,
                    "courier": courier,
                    "friendly_name": "",
                },
                blocking=True,
            )
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "AWB %s could not be tracked (invalid or API error): %s",
                awb,
                err,
            )
            return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Scan IMAP and process any new AWBs found."""
        now = datetime.now(timezone.utc)
        self._last_scan_time = now.isoformat()
        self._last_error = None

        scanner = self._create_scanner()
        try:
            scan_result: ScanResult = await self.hass.async_add_executor_job(
                scanner.scan, self._processed_uids
            )
        except Exception as err:
            self._last_error = str(err)
            raise UpdateFailed(f"IMAP scan failed: {err}") from err

        if scan_result.errors:
            # Log errors but don't fail — partial results are still useful
            for error in scan_result.errors:
                _LOGGER.warning("IMAP scan error: %s", error)
            if not scan_result.awbs and scan_result.emails_scanned == 0:
                self._last_error = scan_result.errors[0]
                raise UpdateFailed(f"IMAP scan failed: {scan_result.errors[0]}")

        # Track ALL scanned UIDs (not just AWB-containing ones)
        # This prevents re-downloading non-AWB emails on the next scan cycle
        for uid in scan_result.scanned_uids:
            self._processed_uids.add(uid)

        # Filter out AWBs we've already seen or are already tracked
        currently_tracked = self._get_currently_tracked_awbs()
        new_awbs: list[ExtractedAwb] = []
        for extracted in scan_result.awbs:
            awb = extracted.awb
            if awb in self._seen_awbs:
                continue
            if awb in currently_tracked:
                # Already tracked by manual entry — mark as seen
                self._seen_awbs[awb] = {
                    "status": "tracked",
                    "first_seen": now.isoformat(),
                }
                continue
            new_awbs.append(extracted)

        # Try to track each new AWB
        newly_tracked = 0
        for extracted in new_awbs:
            success = await self._async_track_awb(extracted)
            self._seen_awbs[extracted.awb] = {
                "status": "tracked" if success else "invalid",
                "first_seen": now.isoformat(),
            }
            if success:
                newly_tracked += 1
                self._total_awbs_found += 1

        # Persist state (save if we processed any new UIDs or found new AWBs)
        if scan_result.scanned_uids or new_awbs:
            await self._async_save()

        if newly_tracked > 0:
            _LOGGER.info(
                "IMAP scan complete: %d new AWBs tracked out of %d candidates",
                newly_tracked,
                len(new_awbs),
            )

        return {
            "status": "idle",
            "last_scan": self._last_scan_time,
            "emails_scanned": scan_result.emails_scanned,
            "awbs_found_this_scan": len(scan_result.awbs),
            "new_awbs_tracked": newly_tracked,
            "total_awbs_found": self._total_awbs_found,
            "last_error": self._last_error,
            "email": self._email,
        }
