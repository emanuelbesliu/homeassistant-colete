"""Config flow for the Colete (Romanian Parcel Tracking) integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import ColeteAPI, ColeteApiError, ColeteNotFoundError
from .const import (
    DOMAIN,
    CONF_COURIER,
    CONF_AWB,
    CONF_FRIENDLY_NAME,
    CONF_UPDATE_INTERVAL,
    COURIERS,
    COURIER_AUTO,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ColeteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Colete parcel tracking."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step - add a new parcel to track.

        User provides: courier (or auto-detect), AWB number, optional name.
        We validate the AWB exists, then create the entry.
        """
        errors = {}

        if user_input is not None:
            awb = user_input[CONF_AWB].strip()
            courier = user_input.get(CONF_COURIER, COURIER_AUTO)
            friendly_name = user_input.get(CONF_FRIENDLY_NAME, "").strip()

            # Prevent duplicate AWB tracking
            unique_id = f"{awb}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            api = ColeteAPI()
            detected_courier = courier
            try:
                result = await self.hass.async_add_executor_job(
                    api.validate_awb, courier, awb
                )
                # If auto-detect was used, store the detected courier
                detected_courier = result.get("courier", courier)
            except ColeteNotFoundError:
                errors["base"] = "awb_not_found"
            except ColeteApiError:
                errors["base"] = "cannot_connect"
            finally:
                api.close()

            if not errors:
                # Build entry title
                courier_name = COURIERS.get(detected_courier, detected_courier)
                title = friendly_name if friendly_name else f"{courier_name} {awb}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_COURIER: detected_courier,
                        CONF_AWB: awb,
                        CONF_FRIENDLY_NAME: friendly_name,
                        CONF_UPDATE_INTERVAL: user_input.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    },
                )

        courier_options = {k: v for k, v in COURIERS.items()}

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AWB): str,
                vol.Optional(
                    CONF_COURIER, default=COURIER_AUTO
                ): vol.In(courier_options),
                vol.Optional(CONF_FRIENDLY_NAME, default=""): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_service(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle config flow initiated by the colete.track_parcel service.

        Data is pre-validated by the service handler — create the entry directly.
        """
        if user_input is None:
            return self.async_abort(reason="unknown_error")

        awb = user_input[CONF_AWB]
        courier = user_input.get(CONF_COURIER, COURIER_AUTO)
        friendly_name = user_input.get(CONF_FRIENDLY_NAME, "")

        # Prevent duplicate AWB tracking
        await self.async_set_unique_id(f"{awb}")
        self._abort_if_unique_id_configured()

        courier_name = COURIERS.get(courier, courier)
        title = friendly_name if friendly_name else f"{courier_name} {awb}"

        return self.async_create_entry(
            title=title,
            data={
                CONF_COURIER: courier,
                CONF_AWB: awb,
                CONF_FRIENDLY_NAME: friendly_name,
                CONF_UPDATE_INTERVAL: user_input.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ColeteOptionsFlowHandler(config_entry)


class ColeteOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Colete parcel tracking."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - update friendly name and interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_name = self.config_entry.options.get(
            CONF_FRIENDLY_NAME,
            self.config_entry.data.get(CONF_FRIENDLY_NAME, ""),
        )
        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            ),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FRIENDLY_NAME,
                    default=current_name,
                ): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
