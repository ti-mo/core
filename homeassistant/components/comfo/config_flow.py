"""Config flow for comfo integration."""
import logging

from comfo import Comfo
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST

from .const import DOMAIN  # pylint:disable=unused-import
from .exceptions import CannotConnect, RequestTimeout, twirp_exception_handler

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({CONF_HOST: str})


@twirp_exception_handler
async def validate_input(hass: core.HomeAssistant, data):
    """
    Validate whether the user's input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    Exception handling is done by the @twirp_exception_handler decorator.
    """
    host = data[CONF_HOST]
    client = Comfo(host)

    await client.async_ping()

    bootinfo = await client.async_get_bootinfo()

    # Return the name of the device to use as the title of the config entry.
    return {"title": f"Zehnder {bootinfo.DeviceName} ({host})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for comfo."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except RequestTimeout:
                errors["base"] = "request_timeout"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
