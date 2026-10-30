import logging

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD, DOMAIN
from .mertik import Mertik
from .mertikdatacoordinator import MertikDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "number", "sensor", "light"]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up the Mertik component."""
    threshold = entry.options.get(
        CONF_FLAME_HEIGHT_THRESHOLD,
        entry.data.get(CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD),
    )
    try:
        mertik = await hass.async_add_executor_job(Mertik, entry.data[CONF_HOST], threshold)
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to fireplace at {entry.data[CONF_HOST]}"
        ) from err

    coordinator = MertikDataCoordinator(hass, mertik)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass, entry):
    """Apply calibration options by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
