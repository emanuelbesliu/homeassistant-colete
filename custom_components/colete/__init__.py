"""The Colete (Romanian Parcel Tracking) integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import ColeteAPI, ColeteApiError, ColeteNotFoundError
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_COURIER,
    CONF_AWB,
    CONF_FRIENDLY_NAME,
    CONF_UPDATE_INTERVAL,
    COURIER_AUTO,
    COURIERS,
    DEFAULT_UPDATE_INTERVAL,
)
from .coordinator import ColeteDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schema for colete.track_parcel
SERVICE_TRACK_PARCEL = "track_parcel"
SERVICE_TRACK_PARCEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AWB): cv.string,
        vol.Optional(CONF_COURIER, default=COURIER_AUTO): vol.In(
            list(COURIERS.keys())
        ),
        vol.Optional(CONF_FRIENDLY_NAME, default=""): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Colete parcel tracking from a config entry."""
    api = ColeteAPI()

    coordinator = ColeteDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register the track_parcel service (only once, on first entry)
    if not hass.services.has_service(DOMAIN, SERVICE_TRACK_PARCEL):
        async def handle_track_parcel(call: ServiceCall) -> None:
            """Handle the colete.track_parcel service call."""
            awb = call.data[CONF_AWB].strip()
            courier = call.data.get(CONF_COURIER, COURIER_AUTO)
            friendly_name = call.data.get(CONF_FRIENDLY_NAME, "").strip()

            # Check if already tracked
            for existing_entry in hass.config_entries.async_entries(DOMAIN):
                if existing_entry.data.get(CONF_AWB) == awb:
                    _LOGGER.warning(
                        "AWB %s is already being tracked", awb
                    )
                    return

            # Validate AWB before creating config entry
            api = ColeteAPI()
            try:
                result = await hass.async_add_executor_job(
                    api.validate_awb, courier, awb
                )
                detected_courier = result.get("courier", courier)
            except (ColeteNotFoundError, ColeteApiError) as err:
                _LOGGER.error(
                    "Failed to track AWB %s: %s", awb, err
                )
                return
            finally:
                api.close()

            # Create a new config entry programmatically
            courier_name = COURIERS.get(detected_courier, detected_courier)
            title = friendly_name if friendly_name else f"{courier_name} {awb}"

            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "service"},
                data={
                    CONF_COURIER: detected_courier,
                    CONF_AWB: awb,
                    CONF_FRIENDLY_NAME: friendly_name,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                },
            )

        hass.services.async_register(
            DOMAIN,
            SERVICE_TRACK_PARCEL,
            handle_track_parcel,
            schema=SERVICE_TRACK_PARCEL_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Colete parcel tracking config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        api = data["api"]
        await hass.async_add_executor_job(api.close)

    # Unregister service if no entries remain
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_TRACK_PARCEL)

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
