"""Constants for Govee Ring."""

DOMAIN = "govee_ring"
PORT_CMD = 4003

CONF_MAIN_ENTITY = "main_entity"

ZONES = 20  # DreamView zones on the H60A4: 0-18 are the ring, 19 drives the centre panel
RING_ZONES = ZONES - 1
SERVICE_SET_SEGMENTS = "set_segments"
