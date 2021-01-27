"""Exceptions handling of the Comfo API."""

from twirp.errors import Errors
from twirp.exceptions import TwirpServerException

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TemperatureError(HomeAssistantError):
    """Invalid temperature value provided."""


class HVACModeError(HomeAssistantError):
    """The HVAC mode cannot be controlled on the unit."""


def twirp_exception_handler(func):
    """
    Decorate Home Assistant functions that call into Twirp-based libraries.

    Converts TwirpServerExceptions into exceptions known to Home Assistant.
    """

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TwirpServerException as e:
            if e.code in (Errors.Unavailable, Errors.DeadlineExceeded):
                raise CannotConnect
            else:
                raise e

    return wrapper
