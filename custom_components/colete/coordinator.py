"""Data update coordinator for the Colete (Romanian Parcel Tracking) integration."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as dateutil_parser

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ColeteAPI, ColeteApiError
from .const import (
    DOMAIN,
    CONF_COURIER,
    CONF_AWB,
    CONF_UPDATE_INTERVAL,
    CONF_RETENTION_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_RETENTION_DAYS,
    STATUS_DELIVERED,
    STATUS_RETURNED,
    STATUS_CANCELED,
)

_LOGGER = logging.getLogger(__name__)

# Terminal statuses that trigger retention countdown
TERMINAL_STATUSES = {STATUS_DELIVERED, STATUS_RETURNED, STATUS_CANCELED}


class ColeteDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch parcel tracking data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ColeteAPI,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.entry = entry
        self._courier = entry.data[CONF_COURIER]
        self._awb = entry.data[CONF_AWB]

        update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._awb}",
            update_interval=timedelta(seconds=update_interval),
        )

    def _get_retention_days(self) -> int:
        """Get the configured retention days (0 = keep forever)."""
        return self.entry.options.get(
            CONF_RETENTION_DAYS,
            self.entry.data.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS),
        )

    @staticmethod
    def _parse_delivered_date(date_str: str | None) -> datetime | None:
        """Parse a delivery date string into a timezone-aware datetime.

        Handles ISO 8601 (Sameday), 'YYYY-MM-DD HH:MM' (FAN Courier),
        and 'DD Month YYYY, HH:MM' (Cargus) formats.
        Returns None if parsing fails.
        """
        if not date_str:
            return None
        try:
            dt = dateutil_parser.parse(date_str)
            # Ensure timezone-aware (assume UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            _LOGGER.debug("Could not parse delivered_date '%s'", date_str)
            return None

    def _check_retention(self) -> bool:
        """Check if parcel should be auto-removed based on retention policy.

        Returns True if the entry should be removed, False otherwise.
        """
        retention_days = self._get_retention_days()
        if retention_days == 0:
            return False  # Keep forever

        if not self.data:
            return False

        status = self.data.get("status")
        if status not in TERMINAL_STATUSES:
            return False

        # Use delivered_date from API data (actual delivery timestamp)
        delivered_date = self._parse_delivered_date(self.data.get("delivered_date"))
        if delivered_date is None:
            # Fallback: use last_update if delivered_date is unavailable
            delivered_date = self._parse_delivered_date(self.data.get("last_update"))
        if delivered_date is None:
            return False  # Can't determine age, keep it

        now = datetime.now(timezone.utc)
        days_since = (now - delivered_date).days
        if days_since >= retention_days:
            _LOGGER.info(
                "Auto-removing parcel %s (delivered %d days ago, " "retention=%d days)",
                self._awb,
                days_since,
                retention_days,
            )
            return True
        return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch parcel tracking data.

        Returns:
            dict with normalized parcel tracking data.

        Raises:
            UpdateFailed: If the API request fails.
        """
        # Check retention on existing data before fetching
        if self._check_retention():
            # Schedule removal (can't do it during update)
            self.hass.async_create_task(
                self.hass.config_entries.async_remove(self.entry.entry_id)
            )
            # Return last known data
            if self.data:
                return self.data
            return {}

        try:
            data = await self.hass.async_add_executor_job(
                self.api.track_parcel, self._courier, self._awb
            )
        except ColeteApiError as err:
            raise UpdateFailed(
                f"Error fetching tracking data for {self._awb}: {err}"
            ) from err

        if not data:
            raise UpdateFailed(f"API returned empty data for {self._awb}")

        # Log terminal status transitions
        status = data.get("status")
        old_status = self.data.get("status") if self.data else None
        if status in TERMINAL_STATUSES and old_status != status:
            retention_days = self._get_retention_days()
            if retention_days > 0:
                _LOGGER.info(
                    "Parcel %s reached terminal status '%s', "
                    "will auto-remove %d days after delivery",
                    self._awb,
                    status,
                    retention_days,
                )
            else:
                _LOGGER.info(
                    "Parcel %s reached terminal status '%s' "
                    "(retention disabled, keeping forever)",
                    self._awb,
                    status,
                )

        _LOGGER.debug("Parcel %s data updated: %s", self._awb, data)
        return data
