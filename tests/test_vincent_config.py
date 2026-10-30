"""Calibration setup, options, and reconfigure regression tests."""

from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mertik.const import DOMAIN

THRESHOLD = "flame_height_threshold"


@pytest.fixture(autouse=True)
def mock_setup(enable_custom_integrations):
    with (
        patch("custom_components.mertik.async_setup_entry", return_value=True),
        patch(
            "custom_components.mertik.config_flow._test_connection", return_value=True
        ),
    ):
        yield


def entry_for(hass, *, options=None, host="192.168.1.100"):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=host,
        data={"name": "Fire", "host": host, THRESHOLD: 110},
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


def defaults(result):
    return {
        str(key): key.default()
        for key in result["data_schema"].schema
        if key.default is not vol.UNDEFINED
    }


async def test_threshold_field_defaults_to_116(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert defaults(result)[THRESHOLD] == 116


async def test_user_flow_stores_threshold(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Fire", "host": "192.168.1.100", THRESHOLD: 105},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][THRESHOLD] == 105


@pytest.mark.parametrize("value", [-1, 255])
async def test_threshold_rejects_out_of_range(hass, value):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with pytest.raises(vol.Invalid):
        result["data_schema"](
            {"name": "Fire", "host": "192.168.1.100", THRESHOLD: value}
        )


@pytest.mark.parametrize("options,expected", [({}, 110), ({THRESHOLD: 115}, 115)])
async def test_options_defaults_and_stores_threshold(hass, options, expected):
    entry = entry_for(hass, options=options)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert defaults(result)[THRESHOLD] == expected
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={THRESHOLD: 120}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[THRESHOLD] == 120


async def test_reconfigure_updates_host_threshold_and_reloads(hass):
    entry = entry_for(hass, options={THRESHOLD: 115})
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload", return_value=True
    ) as reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert defaults(result)[THRESHOLD] == 115
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"name": "Renamed", "host": "192.168.1.101", THRESHOLD: 100},
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert entry.data == {
            "name": "Renamed",
            "host": "192.168.1.101",
            THRESHOLD: 100,
        }
        assert entry.options[THRESHOLD] == 100
        assert entry.unique_id == "192.168.1.101"
        reload.assert_called_once_with(entry.entry_id)


async def test_reconfigure_connection_error_preserves_entry(hass):
    entry = entry_for(hass)
    with patch(
        "custom_components.mertik.config_flow._test_connection", return_value=False
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"name": "Other", "host": "192.168.1.101", THRESHOLD: 116},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data["host"] == "192.168.1.100"


async def test_reconfigure_duplicate_host_rejected(hass):
    entry = entry_for(hass)
    entry_for(hass, host="192.168.1.101")
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"name": "Fire", "host": "192.168.1.101", THRESHOLD: 116},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "192.168.1.100"
