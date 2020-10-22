"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
import logging

from homeassistant.components.binary_sensor import DEVICE_CLASS_PROBLEM
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    CONF_SENSORS,
    DEVICE_CLASS_TEMPERATURE,
    PERCENTAGE,
    TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_OPTIONAL,
    CACHE_BOOTINFO,
    CACHE_FANS,
    CACHE_TEMPS,
    DEVICE_CLASS_FANDUTY,
    DEVICE_CLASS_FANSPEED,
    DOMAIN,
    RPM,
)

_LOGGER = logging.getLogger(__name__)

# Sensors are named after their field names in Comfo's protobuf definition.
# Since protobuf fields names are global, there can be no overlapping fields.
SENSORS = {
    # TODO: Rename to InsideAir.
    "OutAir": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Inside Air Temperature",
    },
    "OutsideAir": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Outside Air Temperature",
    },
    "SupplyAir": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Supply Air Temperature",
    },
    "ExhaustAir": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Exhaust Air Temperature",
    },
    "GeoHeat": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Ground Loop Temperature",
        ATTR_OPTIONAL: True,
    },
    "Reheating": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Reheater Air Temperature",
        ATTR_OPTIONAL: True,
    },
    "KitchenHood": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_FRIENDLY_NAME: "Kitchen Hood Air Temperature",
        ATTR_OPTIONAL: True,
    },
    "InPercent": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_FANDUTY,
        ATTR_FRIENDLY_NAME: "Supply Fan Duty",
    },
    "OutPercent": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_FANDUTY,
        ATTR_FRIENDLY_NAME: "Exhaust Fan Duty",
    },
    "InSpeed": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_FANSPEED,
        ATTR_FRIENDLY_NAME: "Supply Fan Speed",
    },
    "OutSpeed": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_FANSPEED,
        ATTR_FRIENDLY_NAME: "Exhaust Fan Speed",
    },
}


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    """Set up Comfo based on the config entry received from the user."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Fetch initial data before registering entities to avoid inserting None values.
    await coordinator.async_refresh()

    # Enable all sensors by default unless a list of wanted sensors is configured.
    wanted_sensors = config_entry.data.get(CONF_SENSORS, [])
    enabled_sensors = (
        {k: v for k, v in SENSORS.items() if k in wanted_sensors}
        if wanted_sensors
        else SENSORS
    )

    # Generate sensor entities and register them with hass.
    async_add_entities(
        s
        for s in (
            ComfoSensor(
                coordinator=coordinator,
                name=f"{coordinator.data[CACHE_BOOTINFO].DeviceName} {sensor[ATTR_FRIENDLY_NAME]}",
                cache_key=name,
                sensor_class=sensor[ATTR_DEVICE_CLASS],
                entry_id=config_entry.entry_id,
                optional=sensor.get(ATTR_OPTIONAL, False),
            )
            for name, sensor in enabled_sensors.items()
        )
        # Skip sensors that are marked as optional and have a reading of 0.
        # These are sensor values written by optional hardware on the unit.
        # Since these are mostly indoor/heater accessories, they are safe to
        # skip if they have a reading of 0 or lower.
        if not (s.optional and s.state <= 0)
    )

    return True


class ComfoSensor(CoordinatorEntity, Entity):
    """
    Representation of a sensor in a Comfo unit.

    This class is inherited by ComfoBinarySensor and must implement some of its functionality.
    """

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        name: str,
        cache_key: str,
        sensor_class: str,
        entry_id: str,
        optional: bool = False,
    ) -> None:
        """Initialize a Comfo sensor."""
        super().__init__(coordinator)

        self._name = name
        self._cache_key = cache_key
        self._class = sensor_class
        self._entry_id = entry_id
        self._optional = optional

    @property
    def state(self) -> int:
        """Return the state of the entity."""
        # Select the cache type to fetch the cache key from based on the device class.
        cache = {
            DEVICE_CLASS_FANDUTY: CACHE_FANS,
            DEVICE_CLASS_FANSPEED: CACHE_FANS,
            DEVICE_CLASS_TEMPERATURE: CACHE_TEMPS,
        }[self._class]

        return getattr(self.coordinator.data[cache], self._cache_key)

    @property
    def unique_id(self) -> str:
        """Return a unique_id for this entity."""
        return f"{self._entry_id}_{self._name}"

    @property
    def name(self) -> str:
        """Return the (friendly) name of the sensor."""
        return self._name

    @property
    def device_class(self) -> str:
        """Return the sensor's class: temp, speed, etc."""
        return self._class

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return {
            DEVICE_CLASS_TEMPERATURE: "mdi:thermometer",
            DEVICE_CLASS_FANDUTY: "mdi:fan",
            DEVICE_CLASS_FANSPEED: "mdi:fan",
            DEVICE_CLASS_PROBLEM: "mdi:exclamation",  # Used by ComfoBinarySensor.
        }[self._class]

    @property
    def optional(self) -> bool:
        """Return whether or not the sensor is an option/add-on to the unit."""
        return self._optional

    @property
    def unit_of_measurement(self) -> str:
        """
        Return the unit of measurement of this entity.

        Sensor classes with an unknown unit (like ComfoBinarySensor)
        default to a unit of None.
        """
        return {
            DEVICE_CLASS_TEMPERATURE: TEMP_CELSIUS,
            DEVICE_CLASS_FANDUTY: PERCENTAGE,
            DEVICE_CLASS_FANSPEED: RPM,
        }.get(self._class, None)
