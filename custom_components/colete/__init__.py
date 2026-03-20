"""The Colete (Romanian Parcel Tracking) integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import ColeteAPI, ColeteApiError, ColeteNotFoundError
from .const import (
    CONF_AWB,
    CONF_COURIER,
    CONF_ENTRY_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_IMAP_EMAIL,
    CONF_IMAP_SERVER,
    CONF_UPDATE_INTERVAL,
    COURIER_AUTO,
    COURIERS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ENTRY_TYPE_IMAP,
    PLATFORMS,
)
from .coordinator import ColeteDataUpdateCoordinator
from .imap_coordinator import ImapDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schema for colete.track_parcel
SERVICE_TRACK_PARCEL = "track_parcel"
SERVICE_TRACK_PARCEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AWB): cv.string,
        vol.Optional(CONF_COURIER, default=COURIER_AUTO): vol.In(list(COURIERS.keys())),
        vol.Optional(CONF_FRIENDLY_NAME, default=""): cv.string,
    }
)


def _is_imap_entry(entry: ConfigEntry) -> bool:
    """Check if a config entry is an IMAP scanner entry."""
    return (
        entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_IMAP
        or CONF_IMAP_SERVER in entry.data
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Colete from a config entry (parcel or IMAP scanner)."""
    hass.data.setdefault(DOMAIN, {})

    # Register the track_parcel service on the first entry of ANY type.
    # This must happen before IMAP setup because the IMAP coordinator
    # calls this service to create parcel entries from discovered AWBs.
    _async_register_track_parcel_service(hass)

    if _is_imap_entry(entry):
        return await _async_setup_imap_entry(hass, entry)
    return await _async_setup_parcel_entry(hass, entry)


async def _async_setup_imap_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an IMAP email scanner entry.

    Unlike parcel entries, the first IMAP scan is deferred (not run during
    HA startup) to avoid blocking startup with IMAP connections and AWB
    validation API calls.  The coordinator is set up immediately so that
    sensors are created, and the first actual scan is scheduled after a
    short delay once HA is fully loaded.
    """
    coordinator = ImapDataUpdateCoordinator(hass, entry)
    await coordinator.async_load_seen_awbs()

    # Do NOT call async_config_entry_first_refresh() here.
    # That would run a full IMAP scan (connect, download, extract, validate
    # each AWB against courier APIs) synchronously during HA startup.
    # Instead, provide initial data for sensors and schedule the first scan
    # to run after HA has finished starting up.
    coordinator.async_set_updated_data(
        {
            "status": "waiting",
            "last_scan": coordinator._last_scan_time,
            "emails_scanned": 0,
            "awbs_found_this_scan": 0,
            "new_awbs_tracked": 0,
            "total_awbs_found": coordinator._total_awbs_found,
            "last_error": None,
            "email": entry.data.get(CONF_IMAP_EMAIL, ""),
        }
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "type": "imap",
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_setup_parcel_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a parcel tracking entry."""
    api = ColeteAPI()

    coordinator = ColeteDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "type": "parcel",
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


def _async_register_track_parcel_service(hass: HomeAssistant) -> None:
    """Register the colete.track_parcel service (idempotent — skips if already registered)."""
    if hass.services.has_service(DOMAIN, SERVICE_TRACK_PARCEL):
        return

    async def handle_track_parcel(call: ServiceCall) -> None:
        """Handle the colete.track_parcel service call."""
        awb = call.data[CONF_AWB].strip()
        courier = call.data.get(CONF_COURIER, COURIER_AUTO)
        friendly_name = call.data.get(CONF_FRIENDLY_NAME, "").strip()

        # Check if already tracked
        for existing_entry in hass.config_entries.async_entries(DOMAIN):
            if existing_entry.data.get(CONF_AWB) == awb:
                _LOGGER.warning("AWB %s is already being tracked", awb)
                return

        # Validate AWB before creating config entry
        api = ColeteAPI()
        try:
            result = await hass.async_add_executor_job(
                api.validate_awb, courier, awb
            )
            detected_courier = result.get("courier", courier)
        except (ColeteNotFoundError, ColeteApiError) as err:
            _LOGGER.error("Failed to track AWB %s: %s", awb, err)
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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Colete config entry (parcel or IMAP)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the API session for parcel entries
        api = data.get("api")
        if api:
            await hass.async_add_executor_job(api.close)

    # Unregister service if no entries remain
    if not hass.data.get(DOMAIN):
        if hass.services.has_service(DOMAIN, SERVICE_TRACK_PARCEL):
            hass.services.async_remove(DOMAIN, SERVICE_TRACK_PARCEL)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
