"""Constants for the comfo integration."""

DOMAIN = "comfo"

# Custom device classes.
DEVICE_CLASS_FANSPEED = "fanspeed"
DEVICE_CLASS_FANDUTY = "fanduty"
DEVICE_CLASS_ERROR = "boolean"

# List of caches the coordinator maintains for internal use.
CACHE_BOOTINFO = 0
CACHE_BYPASS = 1
CACHE_ERRORS = 2
CACHE_FANS = 3
CACHE_FANPROFILES = 4
CACHE_TEMPS = 5

RPM = "rpm"

ATTR_OPTIONAL = "optional"
