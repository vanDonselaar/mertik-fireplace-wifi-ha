"""Regression coverage for Vincent's calibrated, pilot-preserving controls."""
from unittest.mock import call

from custom_components.mertik.mertik import COMMAND_PREFIX


def test_flame_zero_sends_standby_not_maximum(mertik_device, mock_socket):
    """Zero must retain the pilot, never index the last (maximum) flame step."""
    mock_socket.send.reset_mock()
    mertik_device.set_flame_height(0)
    assert mock_socket.send.call_args_list[0] == call(
        bytearray.fromhex(COMMAND_PREFIX + "3136303003")
    )
    assert call(bytearray.fromhex(COMMAND_PREFIX + "3136464603")) not in mock_socket.send.call_args_list
