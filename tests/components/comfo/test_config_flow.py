"""Test the comfo config flow."""
from comfo import comfo_pb2
from comfo.types import BootInfo

from homeassistant import config_entries, setup
from homeassistant.components.comfo.config_flow import CannotConnect
from homeassistant.components.comfo.const import DOMAIN

from tests.async_mock import patch


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.comfo.config_flow.Comfo.async_ping",
        return_value=True,
    ) as mock_ping, patch(
        "homeassistant.components.comfo.config_flow.Comfo.async_get_bootinfo",
        return_value=BootInfo(comfo_pb2.BootInfo(DeviceName="Mock Device")),
    ) as mock_bootinfo, patch(
        "homeassistant.components.comfo.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.comfo.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Zehnder Mock Device (1.1.1.1)"
    assert result2["data"] == {
        "host": "1.1.1.1",
    }
    await hass.async_block_till_done()
    assert len(mock_ping.mock_calls) == 1
    assert len(mock_bootinfo.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass):
    """Test whether we handle CannotConnect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.comfo.config_flow.Comfo.async_ping",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
