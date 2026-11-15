"""Constants for Govee Ring."""

DOMAIN = "govee_ring"
PORT_CMD = 4003

CONF_MAIN_ENTITY = "main_entity"

CONF_MODEL = "model"

# DreamView zones per model. The last zone drives the centre panel; the rest are the ring.
#   H60A4: 20 zones, 0-18 ring, 19 panel
#   H60A6: 12 zones, 0-10 side ring (halo), 11 the whole front face (found by camera test)
MODEL_ZONES = {"H60A4": 20, "H60A6": 12}
DEFAULT_MODEL = "H60A4"

# kept for backwards compatibility (H60A4 values)
ZONES = MODEL_ZONES[DEFAULT_MODEL]
RING_ZONES = ZONES - 1
SERVICE_SET_SEGMENTS = "set_segments"
