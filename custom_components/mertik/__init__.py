from homeassistant import config_entries, core

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.exceptions import ConfigEntryAuthFailed, Unauthorized

from .const import DOMAIN, CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD

from homeassistant.const import CONF_HOST

from .mertik import Mertik

from .mertikdatacoordinator import MertikDataCoordinator


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up the Mertik component."""
    # Get threshold from options, fallback to data, then to default
    threshold = entry.options.get(
        CONF_FLAME_HEIGHT_THRESHOLD,
        entry.data.get(CONF_FLAME_HEIGHT_THRESHOLD, DEFAULT_FLAME_HEIGHT_THRESHOLD)
    )

    mertik = Mertik(entry.data[CONF_HOST], threshold)

    coordinator = MertikDataCoordinator(hass, mertik)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward to all platforms at once
    await hass.config_entries.async_forward_entry_setups(
        entry, ["switch", "sensor", "light", "number"]
    )

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    return True
