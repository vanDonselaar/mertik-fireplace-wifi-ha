"""Regression coverage for Vincent's calibrated, pilot-preserving controls."""

from unittest.mock import Mock, call

import pytest

from custom_components.mertik.light import MertikLightEntity
from custom_components.mertik.mertik import COMMAND_PREFIX, Mertik
from custom_components.mertik.mertikdatacoordinator import MertikDataCoordinator
from custom_components.mertik.number import MertikFlameHeightEntity
from custom_components.mertik.sensor import MertikAmbientTemperatureSensorEntity
from custom_components.mertik.switch import (
    MertikAuxOnOffSwitchEntity,
    MertikOnOffSwitchEntity,
    MertikPilotLightSwitchEntity,
)
from tests.conftest import _build_status_bytes


def test_flame_zero_sends_standby_not_maximum(mertik_device, mock_socket):
    """Zero must retain the pilot, never index the last (maximum) flame step."""
    mock_socket.send.reset_mock()
    mertik_device.set_flame_height(0)
    assert mock_socket.send.call_args_list[0] == call(
        bytearray.fromhex(COMMAND_PREFIX + "3136303003")
    )
    assert (
        call(bytearray.fromhex(COMMAND_PREFIX + "3136464603"))
        not in mock_socket.send.call_args_list
    )


@pytest.mark.parametrize(
    "raw,level,on",
    [
        (0, 0, False),
        (116, 0, False),
        (117, 1, True),
        (123, 1, True),
        (128, 2, True),
        (255, 12, True),
    ],
)
def test_default_low_flame_calibration(mock_socket, raw, level, on):
    mock_socket.recv.return_value = _build_status_bytes(flame_height=raw)
    device = Mertik("192.168.1.100")
    assert device.is_on is on
    assert device.get_flame_height() == level


@pytest.mark.parametrize(
    "threshold,raw,level",
    [(100, 100, 0), (100, 101, 1), (100, 255, 12), (254, 254, 0), (254, 255, 1)],
)
def test_custom_threshold_calibration(mock_socket, threshold, raw, level):
    mock_socket.recv.return_value = _build_status_bytes(flame_height=raw)
    device = Mertik("192.168.1.100", threshold)
    assert device.get_flame_height() == level
    assert device.raw_flame_height == raw


def test_raw_flame_tracks_reported_status(mertik_device, mock_socket):
    mock_socket.recv.return_value = _build_status_bytes(flame_height=117)
    mertik_device.refresh_status()
    assert mertik_device.raw_flame_height == 117
    mock_socket.recv.return_value = _build_status_bytes(flame_height=116)
    mertik_device.refresh_status()
    assert mertik_device.raw_flame_height == 116
    assert mertik_device.get_flame_height() == 0


@pytest.mark.parametrize(
    "method,args",
    [
        ("standBy", ()),
        ("ignite_fireplace", ()),
        ("guard_flame_off", ()),
        ("aux_on", ()),
        ("aux_off", ()),
        ("light_on", ()),
        ("light_off", ()),
        ("set_light_brightness", (128,)),
        ("set_flame_height", (0,)),
        ("set_flame_height", (12,)),
    ],
)
def test_commands_refresh_reported_state_once(mertik_device, mock_socket, method, args):
    mock_socket.send.reset_mock()
    mock_socket.recv.return_value = _build_status_bytes(
        flame_height=117, status_bits="808C"
    )
    getattr(mertik_device, method)(*args)
    refresh = call(bytearray.fromhex(COMMAND_PREFIX + "303303"))
    assert mock_socket.send.call_args_list[-1] == refresh
    assert mock_socket.send.call_args_list.count(refresh) == 1
    assert mertik_device.raw_flame_height == 117
    assert mertik_device.is_guard_flame_on is True
    assert mertik_device.is_aux_on is True
    assert mertik_device.is_light_on is True


@pytest.mark.parametrize(
    "entity_type,action,expected",
    [
        (MertikOnOffSwitchEntity, "async_turn_on", "3136464603"),
        (MertikOnOffSwitchEntity, "async_turn_off", "3136303003"),
        (MertikPilotLightSwitchEntity, "async_turn_on", "314103"),
        (MertikPilotLightSwitchEntity, "async_turn_off", "313003"),
        (MertikAuxOnOffSwitchEntity, "async_turn_on", "32303031030a"),
        (MertikAuxOnOffSwitchEntity, "async_turn_off", "32303030030a"),
        (MertikLightEntity, "async_turn_on", "3330303103"),
        (MertikLightEntity, "async_turn_off", "3330303003"),
    ],
)
async def test_controls_notify_after_status_refresh(
    hass, mertik_device, mock_socket, entity_type, action, expected
):
    coordinator = MertikDataCoordinator(hass, mertik_device)
    entity = entity_type(coordinator, "entry", "Fire")
    entity.hass = hass
    mock_socket.send.reset_mock()
    # Command ACK has no status. Only the follow-up query provides fresh state.
    mock_socket.recv.side_effect = [
        b"\x02OK",
        _build_status_bytes(flame_height=117, status_bits="808C"),
    ]
    notified = []
    coordinator.async_set_updated_data = Mock(
        side_effect=lambda data: notified.append(
            (mertik_device.raw_flame_height, mertik_device.is_guard_flame_on)
        )
    )
    await getattr(entity, action)()
    assert mock_socket.send.call_args_list == [
        call(bytearray.fromhex(COMMAND_PREFIX + expected)),
        call(bytearray.fromhex(COMMAND_PREFIX + "303303")),
    ]
    assert notified == [(117, True)]
    assert (
        coordinator.is_on is True
    )  # Reported low flame, not optimistic command tracking.
    assert coordinator.is_aux_on is True
    assert coordinator.is_light_on is True


def test_pilot_identity_and_status_icons(mock_coordinator):
    entity = MertikPilotLightSwitchEntity(mock_coordinator, "entry", "Fire")
    assert entity.unique_id == "entry-PilotLightOnOff"
    assert entity.name == "Pilot Light"
    assert entity.is_on is False
    assert entity.icon == "mdi:fire-off"
    mock_coordinator.is_guard_flame_on = True
    assert entity.is_on is True
    assert entity.icon == "mdi:fire"


def test_main_reports_igniting_shutting_down_and_dynamic_icons(mock_coordinator):
    entity = MertikOnOffSwitchEntity(mock_coordinator, "entry", "Fire")
    assert entity.extra_state_attributes == {"igniting": False, "shutting_down": False}
    assert entity.icon == "mdi:fireplace-off"
    mock_coordinator.is_on = True
    assert entity.icon == "mdi:fireplace"
    mock_coordinator.mertik.is_igniting = True
    mock_coordinator.mertik.is_shutting_down = True
    assert entity.extra_state_attributes == {"igniting": True, "shutting_down": True}
    assert entity.icon == "mdi:fire-alert"


def test_all_entities_share_modern_device_grouping(mock_coordinator):
    types = [
        MertikOnOffSwitchEntity,
        MertikPilotLightSwitchEntity,
        MertikAuxOnOffSwitchEntity,
        MertikLightEntity,
        MertikFlameHeightEntity,
        MertikAmbientTemperatureSensorEntity,
    ]
    entities = [cls(mock_coordinator, "entry", "Fire") for cls in types]
    for entity in entities:
        assert entity.has_entity_name is True
        assert entity.device_info["identifiers"] == {("mertik", "entry")}
        assert entity.device_info["name"] == "Fire"
    assert len({entity.unique_id for entity in entities}) == 6
    assert entities[-1].icon == "mdi:thermometer-lines"
    for entity in entities[:3]:
        assert entity.device_class == "switch"
