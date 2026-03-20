"""Sensor platform for the Colete (Romanian Parcel Tracking) integration."""

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AWB,
    CONF_COURIER,
    CONF_ENTRY_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_IMAP_EMAIL,
    CONF_IMAP_SERVER,
    COURIERS,
    DOMAIN,
    ENTRY_TYPE_IMAP,
    IMAP_SENSOR_TYPES,
    SENSOR_TYPE_DELIVERY,
    SENSOR_TYPE_IMAP_AWBS_FOUND,
    SENSOR_TYPE_IMAP_LAST_SCAN,
    SENSOR_TYPE_IMAP_STATUS,
    SENSOR_TYPE_LAST_UPDATE,
    SENSOR_TYPE_LOCATION,
    SENSOR_TYPE_STATUS,
    SENSOR_TYPES,
    STATUS_LABELS,
    STATUS_READY_FOR_PICKUP,
)
from .coordinator import ColeteDataUpdateCoordinator
from .imap_coordinator import ImapDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _is_imap_entry(entry: ConfigEntry) -> bool:
    """Check if a config entry is an IMAP scanner entry."""
    return (
        entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_IMAP
        or CONF_IMAP_SERVER in entry.data
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry (parcel or IMAP)."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    if _is_imap_entry(entry):
        # IMAP scanner sensors
        entities = []
        for sensor_type, sensor_config in IMAP_SENSOR_TYPES.items():
            entities.append(
                ColeteImapSensor(
                    coordinator=coordinator,
                    entry=entry,
                    sensor_type=sensor_type,
                    sensor_config=sensor_config,
                )
            )
        async_add_entities(entities)
    else:
        # Parcel tracking sensors
        entities = []
        for sensor_type, sensor_config in SENSOR_TYPES.items():
            entities.append(
                ColeteSensor(
                    coordinator=coordinator,
                    entry=entry,
                    sensor_type=sensor_type,
                    sensor_config=sensor_config,
                )
            )
        async_add_entities(entities)


class ColeteSensor(CoordinatorEntity[ColeteDataUpdateCoordinator], SensorEntity):
    """Representation of a parcel tracking sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ColeteDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config
        self._entry = entry
        self._awb = entry.data[CONF_AWB]
        self._courier = entry.data[CONF_COURIER]

        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]

    @property
    def icon(self) -> str:
        """Return dynamic icon based on parcel status."""
        if (
            self.coordinator.data
            and self._sensor_type == SENSOR_TYPE_STATUS
            and self.coordinator.data.get("status") == STATUS_READY_FOR_PICKUP
        ):
            return "mdi:package-variant-closed-check"
        return self._attr_icon

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info - one device per tracked parcel."""
        friendly_name = self._entry.options.get(
            CONF_FRIENDLY_NAME,
            self._entry.data.get(CONF_FRIENDLY_NAME, ""),
        )
        courier_name = COURIERS.get(self._courier, self._courier)
        device_name = friendly_name if friendly_name else f"{courier_name} {self._awb}"

        return {
            "identifiers": {(DOMAIN, self._awb)},
            "name": device_name,
            "manufacturer": courier_name,
            "model": "Parcel Tracking",
            "entry_type": "service",
            "sw_version": self._awb,
        }

    @property
    def native_value(self) -> str | None:
        """Return the sensor value based on sensor type."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data

        if self._sensor_type == SENSOR_TYPE_STATUS:
            return data.get("status_label", data.get("status"))

        elif self._sensor_type == SENSOR_TYPE_LOCATION:
            return data.get("location") or None

        elif self._sensor_type == SENSOR_TYPE_LAST_UPDATE:
            return data.get("last_update") or None

        elif self._sensor_type == SENSOR_TYPE_DELIVERY:
            if data.get("delivered"):
                return "Delivered"
            status = data.get("status", "")
            if status == STATUS_READY_FOR_PICKUP:
                return "Ready for Pickup"
            label = STATUS_LABELS.get(status, "Pending")
            return label

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if self.coordinator.data is None:
            return attrs

        data = self.coordinator.data

        # Common attributes for all sensor types
        attrs["awb"] = self._awb
        attrs["courier"] = COURIERS.get(self._courier, self._courier)

        if self._sensor_type == SENSOR_TYPE_STATUS:
            # Status sensor gets the full event history and details
            attrs["status_detail"] = data.get("status_detail", "")
            attrs["status_normalized"] = data.get("status", "")
            events = data.get("events", [])
            if events:
                attrs["events"] = events
                attrs["event_count"] = len(events)
            weight = data.get("weight")
            if weight is not None:
                attrs["weight"] = weight

        elif self._sensor_type == SENSOR_TYPE_DELIVERY:
            # Delivery sensor gets confirmation details
            attrs["delivered"] = data.get("delivered", False)
            delivered_to = data.get("delivered_to")
            if delivered_to:
                attrs["delivered_to"] = delivered_to
            delivered_date = data.get("delivered_date")
            if delivered_date:
                attrs["delivered_date"] = delivered_date

        return attrs


class ColeteImapSensor(CoordinatorEntity[ImapDataUpdateCoordinator], SensorEntity):
    """Representation of an IMAP email scanner sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ImapDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the IMAP sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config
        self._entry = entry
        self._email = entry.data[CONF_IMAP_EMAIL]

        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the email scanner."""
        return {
            "identifiers": {(DOMAIN, f"imap_{self._email}")},
            "name": f"Email Scanner ({self._email})",
            "manufacturer": "Colete",
            "model": "IMAP Email Scanner",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | int | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data

        if self._sensor_type == SENSOR_TYPE_IMAP_STATUS:
            if data.get("last_error"):
                return "error"
            return data.get("status", "idle")

        elif self._sensor_type == SENSOR_TYPE_IMAP_LAST_SCAN:
            return data.get("last_scan")

        elif self._sensor_type == SENSOR_TYPE_IMAP_AWBS_FOUND:
            return data.get("total_awbs_found", 0)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {"email": self._email}

        if self.coordinator.data is None:
            return attrs

        data = self.coordinator.data

        if self._sensor_type == SENSOR_TYPE_IMAP_STATUS:
            attrs["emails_scanned"] = data.get("emails_scanned", 0)
            attrs["awbs_found_this_scan"] = data.get("awbs_found_this_scan", 0)
            attrs["new_awbs_tracked"] = data.get("new_awbs_tracked", 0)
            last_error = data.get("last_error")
            if last_error:
                attrs["last_error"] = last_error

        elif self._sensor_type == SENSOR_TYPE_IMAP_AWBS_FOUND:
            attrs["total_awbs_found"] = data.get("total_awbs_found", 0)

        return attrs
