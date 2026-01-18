from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    dataservice = hass.data[DOMAIN].get(entry.entry_id)

    entities = []

    entities.append(
        MertikOnOffSwitchEntity(hass, dataservice, entry.entry_id, entry.data["name"])
    )

    entities.append(
        MertikPilotLightSwitchEntity(hass, dataservice, entry.entry_id, entry.data["name"])
    )

    entities.append(
        MertikAuxOnOffSwitchEntity(
            hass, dataservice, entry.entry_id, entry.data["name"] + " Aux"
        )
    )

    async_add_entities(entities)


class MertikOnOffSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, hass, dataservice, entry_id, name):
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._attr_name = name
        self._attr_unique_id = entry_id + "-OnOff"
        self._attr_device_class = "switch"  # Enables color when ON
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "Mertik Maxitrol",
        }

    @property
    def is_on(self):
        """Return true if the device is on."""
        return bool(self._dataservice.is_on)

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "igniting": self._dataservice.mertik.is_igniting,
            "shutting_down": self._dataservice.mertik.is_shutting_down,
        }

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.set_flame_height, 12)
        self.coordinator.async_set_updated_data(None)

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.standBy)
        self.coordinator.async_set_updated_data(None)

    @property
    def icon(self) -> str:
        if self._dataservice.mertik.is_igniting:
            return "mdi:fire-alert" # Or a pulsing icon
        return "mdi:fireplace" if self.is_on else "mdi:fireplace-off"

class MertikPilotLightSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, hass, dataservice, entry_id, name):
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._attr_name = name + ' Pilot Light'
        self._attr_unique_id = entry_id + "-PilotLightOnOff"
        self._attr_device_class = "switch"  # Enables color when ON
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "Mertik Maxitrol",
        }

    @property
    def is_on(self):
        """Return true if the pilot is on."""
        return bool(self._dataservice.is_guard_flame_on)

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.ignite_fireplace)
        self.coordinator.async_set_updated_data(None)

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.guard_flame_off)
        self.coordinator.async_set_updated_data(None)

    @property
    def icon(self) -> str:
        """Icon of the entity."""
        return "mdi:fire" if self.is_on else "mdi:fire-off"


class MertikAuxOnOffSwitchEntity(CoordinatorEntity, SwitchEntity):
    def __init__(self, hass, dataservice, entry_id, name):
        super().__init__(dataservice)
        self._dataservice = dataservice
        self._attr_name = name
        self._attr_unique_id = entry_id + "-AuxOnOff"
        self._attr_device_class = "switch"  # Enables color when ON
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name.replace(" Aux", ""),
            "manufacturer": "Mertik Maxitrol",
        }

    @property
    def is_on(self):
        """Return true if the device is on."""
        return bool(self._dataservice.is_aux_on)

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.aux_on)
        self.coordinator.async_set_updated_data(None)

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._dataservice.aux_off)
        self.coordinator.async_set_updated_data(None)

    @property
    def icon(self) -> str:
        """Icon of the entity."""
        return "mdi:numeric-2-box-multiple" if self.is_on else "mdi:numeric-1-box-outline"
