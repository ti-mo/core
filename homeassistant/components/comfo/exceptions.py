"""Exceptions handling of the Comfo API."""

from twirp.errors import Errors
from twirp.exceptions import TwirpServerException

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class RequestTimeout(HomeAssistantError):
    """Error to indicate the connection timeout was exceeded."""


def twirp_caller(func):
    """
    Decorate Home Assistant functions that call into Twirp-based libraries.

    Converts TwirpServerExceptions into exceptions known to Home Assistant.
    """

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TwirpServerException as e:
            if e.code == Errors.Unavailable:
                raise CannotConnect
            elif e.code == Errors.DeadlineExceeded:
                raise RequestTimeout
            else:
                raise e

    return wrapper
