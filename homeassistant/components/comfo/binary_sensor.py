"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, CONF_SENSORS

from .const import CACHE_BOOTINFO, CACHE_ERRORS, DOMAIN
from .sensor import ComfoSensor

SENSORS = {
    "Filter": {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_PROBLEM,
        ATTR_FRIENDLY_NAME: "Replace Filter",
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
        ComfoBinarySensor(
            coordinator=coordinator,
            name=f"{coordinator.data[CACHE_BOOTINFO].DeviceName} {sensor[ATTR_FRIENDLY_NAME]}",
            cache_key=name,
            sensor_class=sensor[ATTR_DEVICE_CLASS],
            entry_id=config_entry.entry_id,
        )
        for name, sensor in enabled_sensors.items()
    )

    return True


class ComfoBinarySensor(BinarySensorEntity, ComfoSensor):
    """
    Representation of a binary sensor in a Comfo unit.

    Inherits from BinarySensorEntity first, since we want to inherit its 'state' property
    that on the 'is_on' property. The 'is_on' property is then overridden.
    """

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        cache = {
            DEVICE_CLASS_PROBLEM: CACHE_ERRORS,
        }[self._class]

        v = getattr(self.coordinator.data[cache], self._cache_key)
        assert bool(v)

        return v
