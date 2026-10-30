"""Configure Mertik connectivity and fireplace-specific flame calibration."""

import socket

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN, CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD


def _threshold_selector():
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=254, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )


def _device_schema(data=None, threshold=DEFAULT_FLAME_HEIGHT_THRESHOLD):
    data = data or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, **({"default": data[CONF_NAME]} if CONF_NAME in data else {})
            ): str,
            vol.Required(
                CONF_HOST, **({"default": data[CONF_HOST]} if CONF_HOST in data else {})
            ): str,
            vol.Optional(
                CONF_FLAME_HEIGHT_THRESHOLD, default=threshold
            ): _threshold_selector(),
        }
    )


DEVICE_SCHEMA = _device_schema()


class MertikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mertik config flow."""

    async def async_step_user(self, device_input=None):
        errors = {}
        if device_input is not None:
            host = device_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            # Vincent's older entries predate host-based unique IDs.
            if any(
                entry.data.get(CONF_HOST) == host
                for entry in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            if not await self.hass.async_add_executor_job(_test_connection, host):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Mertik Maxitrol", data=device_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        threshold = entry.options.get(
            CONF_FLAME_HEIGHT_THRESHOLD,
            entry.data.get(CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD),
        )
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            if any(
                other.entry_id != entry.entry_id
                and (other.data.get(CONF_HOST) == host or other.unique_id == host)
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            if not await self.hass.async_add_executor_job(_test_connection, host):
                errors["base"] = "cannot_connect"
            else:
                options = dict(entry.options)
                # An old option must not silently mask an explicit reconfigure edit.
                if CONF_FLAME_HEIGHT_THRESHOLD in options:
                    options[CONF_FLAME_HEIGHT_THRESHOLD] = user_input[
                        CONF_FLAME_HEIGHT_THRESHOLD
                    ]
                data = {**entry.data, **user_input}
                changed = (
                    entry.unique_id != host
                    or entry.data != data
                    or entry.options != options
                )
                # Loaded entries reload through their update listener. Preserve
                # the helper's reload for unloaded entries and unchanged input.
                reload_needed = not entry.update_listeners or not changed
                result = self.async_update_and_abort(
                    entry,
                    unique_id=host,
                    data=data,
                    options=options,
                )
                if reload_needed:
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return result
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_device_schema(entry.data, threshold),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MertikOptionsFlow()


class MertikOptionsFlow(config_entries.OptionsFlow):
    """Edit flame calibration without changing connection settings."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        threshold = self.config_entry.options.get(
            CONF_FLAME_HEIGHT_THRESHOLD,
            self.config_entry.data.get(
                CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD
            ),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FLAME_HEIGHT_THRESHOLD, default=threshold
                    ): _threshold_selector(),
                }
            ),
        )


def _test_connection(host: str) -> bool:
    """Test if the fireplace is reachable on TCP port 2000."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, 2000))
        sock.close()
        return True
    except OSError:
        return False
