"""Exercise config flows with Mertik's real entry update listener."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mertik import async_reload_entry
from custom_components.mertik.const import DOMAIN

THRESHOLD = "flame_height_threshold"


@pytest.fixture(autouse=True)
def mock_device(enable_custom_integrations):
    """Mock hardware/platform boundaries, not integration setup or its listener."""
    with (
        patch("custom_components.mertik.Mertik") as device,
        patch("custom_components.mertik.MertikDataCoordinator"),
        patch("custom_components.mertik.config_flow._test_connection", return_value=True),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ),
    ):
        yield device


@pytest.mark.parametrize("loaded", [True, False])
@pytest.mark.parametrize("changed", [True, False])
async def test_reconfigure_reloads_once(hass, mock_device, loaded, changed):
    """The real setup listener must not compete with the flow's reload helper."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100",
        data={
            "name": "Fire",
            "host": "192.168.1.100",
            THRESHOLD: 110 if changed else 115,
        },
        options={THRESHOLD: 115},
    )
    entry.add_to_hass(hass)
    if loaded:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert entry.update_listeners == [async_reload_entry]

    user_input = (
        {"name": "Renamed", "host": "192.168.1.101", THRESHOLD: 100}
        if changed
        else dict(entry.data)
    )

    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == user_input
    assert entry.options[THRESHOLD] == user_input[THRESHOLD]
    assert entry.unique_id == user_input["host"]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.update_listeners == [async_reload_entry]
    mock_device.assert_called_with(user_input["host"], user_input[THRESHOLD])
    reload.assert_awaited_once_with(entry.entry_id)


async def test_user_setup_and_options_reload_once(hass, mock_device):
    """Initial setup registers the listener; options survive a real reload."""
    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"name": "Fire", "host": "192.168.1.100", THRESHOLD: 105},
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY
        entry = result["result"]
        assert entry.state is ConfigEntryState.LOADED
        assert entry.update_listeners == [async_reload_entry]
        mock_device.assert_called_once_with("192.168.1.100", 105)
        reload.assert_not_awaited()

        # A second edit also catches lost or duplicate listeners after reload.
        for threshold in (120, 125):
            reload.reset_mock()
            result = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], user_input={THRESHOLD: threshold}
            )
            await hass.async_block_till_done()
            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert entry.options[THRESHOLD] == threshold
            assert entry.state is ConfigEntryState.LOADED
            assert entry.update_listeners == [async_reload_entry]
            mock_device.assert_called_with("192.168.1.100", threshold)
            reload.assert_awaited_once_with(entry.entry_id)
