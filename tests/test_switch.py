"""Tests for switch entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.mertik.switch import (
    MertikOnOffSwitchEntity,
    MertikAuxOnOffSwitchEntity,
    MertikPilotLightSwitchEntity,
    async_setup_entry,
)
from custom_components.mertik.const import DOMAIN


class TestOnOffSwitch:
    """Test the main on/off switch entity."""

    @pytest.fixture
    def switch(self, hass, mock_coordinator):
        entity = MertikOnOffSwitchEntity(mock_coordinator, "test_entry", "My Fireplace")
        entity.hass = hass
        return entity

    def test_unique_id(self, switch):
        assert switch.unique_id == "test_entry-OnOff"

    def test_name(self, switch):
        """Primary entity has name=None (uses device name)."""
        assert switch.name is None

    def test_has_entity_name(self, switch):
        assert switch.has_entity_name is True

    def test_icon(self, switch):
        assert switch.icon == "mdi:fireplace-off"

    def test_device_info(self, switch):
        info = switch.device_info
        assert info["identifiers"] == {(DOMAIN, "test_entry")}
        assert info["name"] == "My Fireplace"
        assert info["manufacturer"] == "Mertik Maxitrol"

    def test_is_on_false(self, switch, mock_coordinator):
        mock_coordinator.is_on = False
        assert switch.is_on is False

    def test_is_on_true(self, switch, mock_coordinator):
        mock_coordinator.is_on = True
        assert switch.is_on is True

    async def test_turn_on(self, switch, mock_coordinator):
        await switch.async_turn_on()
        mock_coordinator.set_flame_height.assert_called_once_with(12)
        mock_coordinator.ignite_fireplace.assert_not_called()
        mock_coordinator.mark_optimistic_on.assert_not_called()
        mock_coordinator.async_set_updated_data.assert_called_once_with(None)

    async def test_turn_off(self, switch, mock_coordinator):
        await switch.async_turn_off()
        mock_coordinator.standBy.assert_called_once()
        mock_coordinator.guard_flame_off.assert_not_called()
        mock_coordinator.mark_optimistic_off.assert_not_called()
        mock_coordinator.async_set_updated_data.assert_called_once_with(None)


class TestAuxSwitch:
    """Test the aux on/off switch entity."""

    @pytest.fixture
    def switch(self, hass, mock_coordinator):
        entity = MertikAuxOnOffSwitchEntity(
            mock_coordinator, "test_entry", "My Fireplace"
        )
        entity.hass = hass
        return entity

    def test_unique_id(self, switch):
        assert switch.unique_id == "test_entry-AuxOnOff"

    def test_name(self, switch):
        assert switch.name == "Aux"

    def test_has_entity_name(self, switch):
        assert switch.has_entity_name is True

    def test_icon(self, switch):
        assert switch.icon == "mdi:numeric-1-box-outline"

    def test_device_info(self, switch):
        info = switch.device_info
        assert info["identifiers"] == {(DOMAIN, "test_entry")}
        assert info["name"] == "My Fireplace"
        assert info["manufacturer"] == "Mertik Maxitrol"

    def test_is_on_false(self, switch, mock_coordinator):
        mock_coordinator.is_aux_on = False
        assert switch.is_on is False

    def test_is_on_true(self, switch, mock_coordinator):
        mock_coordinator.is_aux_on = True
        assert switch.is_on is True

    async def test_turn_on(self, switch, mock_coordinator):
        await switch.async_turn_on()
        mock_coordinator.aux_on.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once_with(None)

    async def test_turn_off(self, switch, mock_coordinator):
        await switch.async_turn_off()
        mock_coordinator.aux_off.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once_with(None)


class TestSwitchPlatformSetup:
    """Test switch platform async_setup_entry."""

    async def test_creates_three_entities(self, hass, mock_coordinator, mock_config_entry):
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
        added = []

        await async_setup_entry(hass, mock_config_entry, lambda e: added.extend(e))

        assert len(added) == 3
        assert isinstance(added[0], MertikOnOffSwitchEntity)
        assert isinstance(added[1], MertikPilotLightSwitchEntity)
        assert isinstance(added[2], MertikAuxOnOffSwitchEntity)

    async def test_entity_names(self, hass, mock_coordinator, mock_config_entry):
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
        added = []
        await async_setup_entry(hass, mock_config_entry, lambda e: added.extend(e))

        assert added[0].name is None
        assert added[1].name == "Pilot Light"
        assert added[2].name == "Aux"

    async def test_all_entities_share_device(self, hass, mock_coordinator, mock_config_entry):
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
        added = []
        await async_setup_entry(hass, mock_config_entry, lambda e: added.extend(e))

        assert added[0].device_info["identifiers"] == added[1].device_info["identifiers"]
