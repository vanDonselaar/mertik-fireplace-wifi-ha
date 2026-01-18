import logging

from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN, CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD

from .mertik import Mertik

_LOGGER = logging.getLogger(__name__)


class MertikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mertik config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, device_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if device_input is not None:
            self.data = device_input

            return self.async_create_entry(title="Mertik Maxitrol", data=self.data)

        DEVICE_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_FLAME_HEIGHT_THRESHOLD, default=DEFAULT_FLAME_HEIGHT_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=254,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle reconfiguration of an existing entry."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, **user_input},
            )

        RECONFIGURE_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_NAME, default=entry.data.get(CONF_NAME)): str,
                vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST)): str,
                vol.Optional(
                    CONF_FLAME_HEIGHT_THRESHOLD,
                    default=entry.data.get(CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=254,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure", data_schema=RECONFIGURE_SCHEMA
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MertikOptionsFlow(config_entry)


class MertikOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Mertik."""

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    CONF_FLAME_HEIGHT_THRESHOLD,
                    default=self.config_entry.options.get(
                        CONF_FLAME_HEIGHT_THRESHOLD,
                        self.config_entry.data.get(CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD)
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=254,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)
