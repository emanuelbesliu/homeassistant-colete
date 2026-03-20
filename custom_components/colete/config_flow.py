"""Config flow for the Colete (Romanian Parcel Tracking) integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import ColeteAPI, ColeteApiError, ColeteNotFoundError
from .const import (
    CONF_AWB,
    CONF_COURIER,
    CONF_ENTRY_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_IMAP_EMAIL,
    CONF_IMAP_FOLDER,
    CONF_IMAP_LOOKBACK_DAYS,
    CONF_IMAP_PASSWORD,
    CONF_IMAP_PORT,
    CONF_IMAP_SCAN_INTERVAL,
    CONF_IMAP_SERVER,
    CONF_RETENTION_DAYS,
    CONF_UPDATE_INTERVAL,
    COURIER_AUTO,
    COURIERS,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_IMAP_LOOKBACK_DAYS,
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_SCAN_INTERVAL,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ENTRY_TYPE_IMAP,
    MAX_IMAP_LOOKBACK_DAYS,
    MAX_IMAP_SCAN_INTERVAL,
    MAX_RETENTION_DAYS,
    MAX_UPDATE_INTERVAL,
    MIN_IMAP_LOOKBACK_DAYS,
    MIN_IMAP_SCAN_INTERVAL,
    MIN_RETENTION_DAYS,
    MIN_UPDATE_INTERVAL,
)
from .imap_scanner import ImapAwbScanner, ImapScannerError

_LOGGER = logging.getLogger(__name__)

# Menu choices
MENU_TRACK_PARCEL = "track_parcel"
MENU_IMAP_SCANNER = "imap_scanner"


class ColeteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Colete parcel tracking."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the initial menu: track a parcel or set up email scanner."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[MENU_TRACK_PARCEL, MENU_IMAP_SCANNER],
        )

    async def async_step_track_parcel(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the parcel tracking step - add a new parcel to track.

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
                        CONF_RETENTION_DAYS: user_input.get(
                            CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
                        ),
                    },
                )

        courier_options = {k: v for k, v in COURIERS.items()}

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AWB): str,
                vol.Optional(CONF_COURIER, default=COURIER_AUTO): vol.In(
                    courier_options
                ),
                vol.Optional(CONF_FRIENDLY_NAME, default=""): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
                vol.Optional(
                    CONF_RETENTION_DAYS,
                    default=DEFAULT_RETENTION_DAYS,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_RETENTION_DAYS, max=MAX_RETENTION_DAYS),
                ),
            }
        )

        return self.async_show_form(
            step_id="track_parcel",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_imap_scanner(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle IMAP email scanner setup."""
        errors = {}

        if user_input is not None:
            imap_server = user_input[CONF_IMAP_SERVER].strip()
            imap_port = user_input.get(CONF_IMAP_PORT, DEFAULT_IMAP_PORT)
            imap_email = user_input[CONF_IMAP_EMAIL].strip().lower()
            imap_password = user_input[CONF_IMAP_PASSWORD]
            imap_folder = user_input.get(CONF_IMAP_FOLDER, DEFAULT_IMAP_FOLDER).strip()

            # Prevent duplicate IMAP scanner for same email
            unique_id = f"imap_{imap_email}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Validate IMAP connection
            scanner = ImapAwbScanner(
                server=imap_server,
                port=imap_port,
                email_address=imap_email,
                password=imap_password,
                folder=imap_folder,
            )
            try:
                valid = await self.hass.async_add_executor_job(
                    scanner.validate_connection
                )
                if not valid:
                    errors["base"] = "imap_cannot_connect"
            except ImapScannerError as err:
                _LOGGER.error("IMAP validation error: %s", err)
                errors["base"] = "imap_invalid_folder"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("IMAP connection error: %s", err)
                errors["base"] = "imap_cannot_connect"

            if not errors:
                title = f"Email Scanner ({imap_email})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_IMAP,
                        CONF_IMAP_SERVER: imap_server,
                        CONF_IMAP_PORT: imap_port,
                        CONF_IMAP_EMAIL: imap_email,
                        CONF_IMAP_PASSWORD: imap_password,
                        CONF_IMAP_FOLDER: imap_folder,
                        CONF_IMAP_LOOKBACK_DAYS: user_input.get(
                            CONF_IMAP_LOOKBACK_DAYS, DEFAULT_IMAP_LOOKBACK_DAYS
                        ),
                        CONF_IMAP_SCAN_INTERVAL: user_input.get(
                            CONF_IMAP_SCAN_INTERVAL, DEFAULT_IMAP_SCAN_INTERVAL
                        ),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_IMAP_SERVER): str,
                vol.Optional(CONF_IMAP_PORT, default=DEFAULT_IMAP_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_IMAP_EMAIL): str,
                vol.Required(CONF_IMAP_PASSWORD): str,
                vol.Optional(
                    CONF_IMAP_FOLDER, default=DEFAULT_IMAP_FOLDER
                ): str,
                vol.Optional(
                    CONF_IMAP_LOOKBACK_DAYS, default=DEFAULT_IMAP_LOOKBACK_DAYS
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_IMAP_LOOKBACK_DAYS, max=MAX_IMAP_LOOKBACK_DAYS
                    ),
                ),
                vol.Optional(
                    CONF_IMAP_SCAN_INTERVAL, default=DEFAULT_IMAP_SCAN_INTERVAL
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_IMAP_SCAN_INTERVAL, max=MAX_IMAP_SCAN_INTERVAL
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="imap_scanner",
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
                CONF_RETENTION_DAYS: user_input.get(
                    CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
                ),
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow (routes to parcel or IMAP options)."""
        if config_entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_IMAP:
            return ColeteImapOptionsFlowHandler()
        return ColeteOptionsFlowHandler()


class ColeteOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Colete parcel tracking."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - update friendly name, interval, and retention."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_name = self.config_entry.options.get(
            CONF_FRIENDLY_NAME,
            self.config_entry.data.get(CONF_FRIENDLY_NAME, ""),
        )
        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        current_retention = self.config_entry.options.get(
            CONF_RETENTION_DAYS,
            self.config_entry.data.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS),
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
                vol.Optional(
                    CONF_RETENTION_DAYS,
                    default=current_retention,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_RETENTION_DAYS, max=MAX_RETENTION_DAYS),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )


class ColeteImapOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for IMAP email scanner."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage IMAP options - folder, lookback days, scan interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_folder = self.config_entry.options.get(
            CONF_IMAP_FOLDER,
            self.config_entry.data.get(CONF_IMAP_FOLDER, DEFAULT_IMAP_FOLDER),
        )
        current_lookback = self.config_entry.options.get(
            CONF_IMAP_LOOKBACK_DAYS,
            self.config_entry.data.get(
                CONF_IMAP_LOOKBACK_DAYS, DEFAULT_IMAP_LOOKBACK_DAYS
            ),
        )
        current_interval = self.config_entry.options.get(
            CONF_IMAP_SCAN_INTERVAL,
            self.config_entry.data.get(
                CONF_IMAP_SCAN_INTERVAL, DEFAULT_IMAP_SCAN_INTERVAL
            ),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_IMAP_FOLDER,
                    default=current_folder,
                ): str,
                vol.Optional(
                    CONF_IMAP_LOOKBACK_DAYS,
                    default=current_lookback,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_IMAP_LOOKBACK_DAYS, max=MAX_IMAP_LOOKBACK_DAYS
                    ),
                ),
                vol.Optional(
                    CONF_IMAP_SCAN_INTERVAL,
                    default=current_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_IMAP_SCAN_INTERVAL, max=MAX_IMAP_SCAN_INTERVAL
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
