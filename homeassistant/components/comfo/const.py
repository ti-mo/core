"""Constants for the comfo integration."""

DOMAIN = "comfo"

# Custom device classes.
DEVICE_CLASS_FANSPEED = "fanspeed"
DEVICE_CLASS_FANDUTY = "fanduty"
DEVICE_CLASS_ERROR = "boolean"

# List of caches the coordinator maintains for internal use.
CACHE_BOOTINFO = 0
CACHE_TEMPS = 1
CACHE_FANS = 2
CACHE_FANPROFILES = 3
CACHE_ERRORS = 4

RPM = "rpm"

ATTR_OPTIONAL = "optional"
