"""Data update coordinator for the Colete (Romanian Parcel Tracking) integration."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

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
    DEFAULT_UPDATE_INTERVAL,
    AUTO_ARCHIVE_DAYS,
    STATUS_DELIVERED,
    STATUS_RETURNED,
    STATUS_CANCELED,
)

_LOGGER = logging.getLogger(__name__)

# Terminal statuses that trigger auto-archive countdown
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
        self._archived_at: datetime | None = None

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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch parcel tracking data.

        Returns:
            dict with normalized parcel tracking data.

        Raises:
            UpdateFailed: If the API request fails.
        """
        # Check auto-archive
        if self._archived_at is not None:
            days_since = (
                datetime.now(timezone.utc) - self._archived_at
            ).days
            if days_since >= AUTO_ARCHIVE_DAYS:
                _LOGGER.info(
                    "Auto-archiving parcel %s (delivered %d days ago)",
                    self._awb,
                    days_since,
                )
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
            raise UpdateFailed(
                f"API returned empty data for {self._awb}"
            )

        # Track when parcel reaches a terminal status
        status = data.get("status")
        if status in TERMINAL_STATUSES:
            if self._archived_at is None:
                self._archived_at = datetime.now(timezone.utc)
                _LOGGER.info(
                    "Parcel %s reached terminal status '%s', "
                    "will auto-archive in %d days",
                    self._awb,
                    status,
                    AUTO_ARCHIVE_DAYS,
                )
        else:
            # Reset if status reverts (unlikely but defensive)
            self._archived_at = None

        _LOGGER.debug("Parcel %s data updated: %s", self._awb, data)
        return data
