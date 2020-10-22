"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
import logging

from comfo import Comfo
from comfo.types import FanProfiles

from homeassistant.components.fan import (
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SUPPORT_SET_SPEED,
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CACHE_BOOTINFO, CACHE_FANPROFILES, DOMAIN
from .exceptions import twirp_exception_handler

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    """Set up Comfo based on the config entry received from the user."""
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Fetch initial data before registering entities to avoid inserting None values.
    await coordinator.async_refresh()

    # Instantiate and register the fan.
    async_add_entities(
        [
            ComfoFan(
                coordinator=coordinator,
                api=api,
                name=f"{coordinator.data[CACHE_BOOTINFO].DeviceName} Ventilation Unit",
                entry_id=config_entry.entry_id,
            )
        ]
    )

    return True


class ComfoFan(CoordinatorEntity, FanEntity):
    """Representation of the ComfoConnect fan platform."""

    SPEED_MAPPING_TO_HASS = {
        FanProfiles.SPEED_OFF: SPEED_OFF,
        FanProfiles.SPEED_LOW: SPEED_LOW,
        FanProfiles.SPEED_MEDIUM: SPEED_MEDIUM,
        FanProfiles.SPEED_HIGH: SPEED_HIGH,
    }

    SPEED_MAPPING_TO_COMFO = {
        SPEED_OFF: FanProfiles.SPEED_OFF,
        SPEED_LOW: FanProfiles.SPEED_LOW,
        SPEED_MEDIUM: FanProfiles.SPEED_MEDIUM,
        SPEED_HIGH: FanProfiles.SPEED_HIGH,
    }

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        api: Comfo,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Comfo fan."""
        super().__init__(coordinator)

        self._name = name
        self._api = api
        self._entry_id = entry_id

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the fan."""
        if speed is None:
            speed = SPEED_LOW

        await self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan (to away)."""
        await self.async_set_speed(SPEED_OFF)

    @twirp_exception_handler
    async def async_set_speed(self, speed: str) -> None:
        """Set fan speed."""
        _LOGGER.debug("Changing fan speed to %s", speed)

        modified = await self._api.async_set_fan_speed(
            self.SPEED_MAPPING_TO_COMFO.get(speed, None)
        )

        if modified:
            _LOGGER.debug("Fan speed was changed on the unit")

        # Pull in the new state information from the unit.
        await self.async_update_ha_state(force_refresh=True)

    @property
    def speed(self) -> str:
        """Return the current fan mode.

        Converts Comfo's integer speed representation (1-4)
        to hass' string-based representation.
        """
        mode = self.coordinator.data[CACHE_FANPROFILES].CurrentMode
        return self.SPEED_MAPPING_TO_HASS.get(mode, None)

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self._entry_id}_{self._name}"

    @property
    def name(self):
        """Return the name of the fan."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:air-conditioner"

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def speed_list(self):
        """List of available fan modes."""
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]
