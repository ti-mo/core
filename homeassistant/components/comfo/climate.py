"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
import logging
from typing import List

from comfo import Comfo
from comfo.types import FanProfiles
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CACHE_BOOTINFO, CACHE_BYPASS, CACHE_FANPROFILES, CACHE_TEMPS, DOMAIN
from .exceptions import HVACModeError, TemperatureError, twirp_exception_handler

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
            ComfoUnit(
                coordinator=coordinator,
                api=api,
                name=f"{coordinator.data[CACHE_BOOTINFO].DeviceName} Ventilation Unit",
                entry_id=config_entry.entry_id,
            )
        ]
    )

    # Register service calls for modifying various parameters of the unit.
    platform = entity_platform.current_platform.get()

    # Set off, low, ... fan profiles to duty levels expressed in percent.
    platform.async_register_entity_service(
        "configure_fan_profile",
        {
            vol.Required("profile"): vol.In(
                ComfoUnit.SPEED_MAPPING_TO_COMFO.keys(),
                msg=f"Profile must be one of '{', '.join(ComfoUnit.SPEED_MAPPING_TO_COMFO.keys())}'",
            ),
            vol.Required("percent"): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            ),
        },
        "async_configure_fan_profile",
    )

    return True


class ComfoUnit(CoordinatorEntity, ClimateEntity):
    """Representation of the ComfoConnect fan platform."""

    SPEED_MAPPING_TO_HASS = {
        FanProfiles.SPEED_OFF: FAN_OFF,
        FanProfiles.SPEED_LOW: FAN_LOW,
        FanProfiles.SPEED_MEDIUM: FAN_MEDIUM,
        FanProfiles.SPEED_HIGH: FAN_HIGH,
    }

    SPEED_MAPPING_TO_COMFO = {
        FAN_OFF: FanProfiles.SPEED_OFF,
        FAN_LOW: FanProfiles.SPEED_LOW,
        FAN_MEDIUM: FanProfiles.SPEED_MEDIUM,
        FAN_HIGH: FanProfiles.SPEED_HIGH,
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

    @twirp_exception_handler
    async def async_configure_fan_profile(self, profile: int, percent: int) -> None:
        """
        Set the fan duty percentage of a profile.

        Exposed as the 'configure_fan_profile' service.
        """
        _LOGGER.debug("Changing profile %s to %d percent", profile, percent)

        modified = await self._api.async_configure_fan_profile(
            profile=self.SPEED_MAPPING_TO_COMFO[profile],
            percent=percent,
        )

        if modified:
            _LOGGER.debug("Profile '%s' was changed on the unit", profile)

            # Pull in the new state information from the unit.
            await self.async_update_ha_state(force_refresh=True)
        else:
            _LOGGER.debug("Profile '%s' unmodified", profile)

    @property
    def target_temperature(self) -> int:
        """Return the current comfort temperature of the unit."""
        return self.coordinator.data[CACHE_TEMPS].Comfort

    @property
    def target_temperature_step(self) -> float:
        """Return the comfort temperature step the unit supports."""
        return self.precision

    @twirp_exception_handler
    async def async_set_temperature(
        self, entity_id: int = None, temperature: int = None
    ) -> None:
        """
        Set the comfort temperature of the unit.

        The comfort temperature is the maximum temperature of air inbound to the house.

        When it's colder on the outside than on the inside, the unit will try to
        reclaim the heat from outbound air by exchanging it to the inbound air.
        The comfort temperature sets the cut-off point of the heat exchanger.

        For example, if the house is at 25°C and the outside is at 15°C, setting
        a comfort temperature of 21°C will ensure the unit pushes air into the
        house that's no hotter than 21°C.
        """
        _LOGGER.debug("Changing comfort temperature to %d", temperature)

        if temperature is None:
            raise TemperatureError

        temperature = int(temperature)

        modified = await self._api.async_set_comfort_temperature(
            temperature=temperature
        )

        if modified:
            _LOGGER.debug("Comfort temperature was changed on the unit")

            # Pull in the new state information from the unit.
            await self.async_update_ha_state(force_refresh=True)
        else:
            _LOGGER.debug("Comfort temperature unmodified")

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode.

        Converts Comfo's integer speed representation (1-4)
        to hass' string-based representation.
        """
        mode = self.coordinator.data[CACHE_FANPROFILES].CurrentMode
        return self.SPEED_MAPPING_TO_HASS.get(mode, None)

    @twirp_exception_handler
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        _LOGGER.debug("Changing fan speed to %s", fan_mode)

        modified = await self._api.async_set_fan_speed(
            self.SPEED_MAPPING_TO_COMFO.get(fan_mode, None)
        )

        if modified:
            _LOGGER.debug("Fan speed was changed on the unit")

        # Pull in the new state information from the unit.
        await self.async_update_ha_state(force_refresh=True)

    @property
    def hvac_mode(self) -> str:
        """Return the currently-active HVAC mode.

        The unit is autonomous in activating its heat exchanger based on
        the configured comfort temperature.
        If the outdoor temperature is lower than the indoor temperature,
        heat recovery will automatically occur up to the comfort temperature.
        """
        # Bypass is deactivated, so heat exchanger is active.
        if self.coordinator.data[CACHE_BYPASS].Level == 0:
            return HVAC_MODE_HEAT

        # Bypass is activated, no heat is recovered.
        return HVAC_MODE_FAN_ONLY

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Return an exception when the user attempts to modify the HVAC mode.

        The unit doesn't allow the mode to be changed, but does use the 'hvac_mode'
        to communicate whether or not the heat exchanger is active.
        """
        raise HVACModeError("HVAC mode cannot be modified")

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
    def temperature_unit(self) -> int:
        """Return degrees Celsius."""
        return TEMP_CELSIUS

    @property
    def precision(self) -> float:
        """Return the precision of expected temperature values."""
        return PRECISION_WHOLE

    @property
    def hvac_modes(self) -> List[str]:
        """Return list of supported HVAC modes."""
        return [HVAC_MODE_HEAT, HVAC_MODE_FAN_ONLY]

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_FAN_MODE | SUPPORT_TARGET_TEMPERATURE

    @property
    def fan_modes(self) -> List[str]:
        """Return a list of supported fan profiles."""
        return [FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
