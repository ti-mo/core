"""The comfo integration."""
import asyncio
from datetime import timedelta
import logging

import async_timeout
from comfo import Comfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    Debouncer,
    UpdateFailed,
)

from .const import (
    CACHE_BOOTINFO,
    CACHE_BYPASS,
    CACHE_ERRORS,
    CACHE_FANPROFILES,
    CACHE_FANS,
    CACHE_TEMPS,
    DOMAIN,
)
from .exceptions import twirp_exception_handler

PLATFORMS = ["binary_sensor", "climate", "sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the comfo component."""
    hass.data[DOMAIN] = {}
    return True


@twirp_exception_handler
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Set up comfo from a config entry.

    Since we need to set up multiple platforms that rely on a coordinator
    to pull sensor data, we create a single coordinator that can serve all
    platforms.
    """
    # Instantiate an API client.
    api = Comfo(entry.data[CONF_HOST])

    async def async_comfo_update_cache():
        """
        Update callback executed periodically by the coordinator.

        This is supposed to fetch all temperature and speed information from the unit.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Store this dict in the coordinator's data section.
                return {
                    CACHE_BOOTINFO: await api.async_get_bootinfo(),
                    CACHE_ERRORS: await api.async_get_errors(),
                    CACHE_FANS: await api.async_get_fans(),
                    CACHE_FANPROFILES: await api.async_get_fan_profiles(),
                    CACHE_TEMPS: await api.async_get_temps(),
                    CACHE_BYPASS: await api.async_get_bypass(),
                }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with Comfo API: {err}")

    # The coordinator is responsible for gathering data in a single API call
    # for all entities and exposing the results from a single location.
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="sensor",
        update_method=async_comfo_update_cache,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
        # Use a debouncer with a custom interval to allow the unit's state to be updated
        # more than once every 10 seconds (the default). Since all state is handled by
        # the update coordinator, this provides a more snappy user experience when changing
        # settings on the unit.
        request_refresh_debouncer=Debouncer(
            hass,
            _LOGGER,
            # Fetch the unit's state at most once every 2 seconds.
            # Batch all state refresh requests until this cooldown expires.
            cooldown=2,
            immediate=True,
        ),
    )

    # Store the API client and coordinator in hass.
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
