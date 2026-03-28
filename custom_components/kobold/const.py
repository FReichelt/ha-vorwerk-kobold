"""Constants for the Vorwerk Kobold integration."""

from homeassistant.const import Platform

DOMAIN = "kobold"

# Vorwerk Auth0 client_id (known working client_id for MyKobold app)
VORWERK_CLIENT_ID = "KY4YbVAvtgB7lp8vIbWQ7zLk3hssZlhR"

# Config entry data keys
CONF_TOKEN = "token"
CONF_EMAIL = "email"

# hass.data keys
KOBOLD_HUB = "hub"
KOBOLD_ROBOTS = "robots"
KOBOLD_MAP_DATA = "map_data"
KOBOLD_PERSISTENT_MAPS = "persistent_maps"

# Platforms
PLATFORMS = [
    Platform.VACUUM,
    Platform.SENSOR,
    Platform.CAMERA,
    Platform.SWITCH,
    Platform.BUTTON,
]

# Update interval (minutes)
SCAN_INTERVAL_MINUTES = 1

# ---------------------------------------------------------------------------
# Robot state values (robot.state["state"])
# ---------------------------------------------------------------------------
ROBOT_STATE_IDLE = 1
ROBOT_STATE_BUSY = 2
ROBOT_STATE_PAUSED = 3
ROBOT_STATE_ERROR = 4

# ---------------------------------------------------------------------------
# Robot action values (robot.state["action"])
# ---------------------------------------------------------------------------
ROBOT_ACTIONS = {
    0: "Invalid",
    1: "House Cleaning",
    2: "Spot Cleaning",
    3: "Manual Cleaning",
    4: "Docking",
    5: "User Menu Active",
    6: "Suspended Cleaning",
    7: "Updating",
    8: "Copying logs",
    9: "Recovering Location",
    10: "IEC test",
    11: "Map cleaning",
    12: "Exploring map (creating a persistent map)",
    13: "Acquiring Persistent Home Map IDs",
    14: "Creating & Uploading Map",
    15: "Suspended Exploration",
}

# ---------------------------------------------------------------------------
# Cleaning modes
# ---------------------------------------------------------------------------
CLEANING_MODE_ECO = 1
CLEANING_MODE_TURBO = 2

CLEANING_MODE_TO_NAME = {
    CLEANING_MODE_ECO: "Eco",
    CLEANING_MODE_TURBO: "Turbo",
}

CLEANING_MODE_FROM_NAME = {v: k for k, v in CLEANING_MODE_TO_NAME.items()}

# ---------------------------------------------------------------------------
# Navigation modes
# ---------------------------------------------------------------------------
NAVIGATION_MODE_NORMAL = 1
NAVIGATION_MODE_EXTRA_CARE = 2
NAVIGATION_MODE_DEEP = 3

NAVIGATION_MODE_TO_NAME = {
    NAVIGATION_MODE_NORMAL: "Normal",
    NAVIGATION_MODE_EXTRA_CARE: "Extra Care",
    NAVIGATION_MODE_DEEP: "Deep",
}

NAVIGATION_MODE_FROM_NAME = {v: k for k, v in NAVIGATION_MODE_TO_NAME.items()}

# ---------------------------------------------------------------------------
# Cleaning categories
# ---------------------------------------------------------------------------
CLEANING_CATEGORY_NON_PERSISTENT_MAP = 2
CLEANING_CATEGORY_SPOT = 3
CLEANING_CATEGORY_PERSISTENT_MAP = 4

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------
ROBOT_ERRORS = {
    "ui_error_invalid_robot": "Invalid robot",
    "ui_error_unable_to_return_to_base": "Unable to return to base. Check if path is clear",
    "ui_error_brush_stuck": "Brush stuck. Clean the brush",
    "ui_error_brush_overloaded": "Brush overloaded. Clean the brush",
    "ui_error_bumper_stuck": "Bumper stuck. Clean and check the bumper",
    "ui_error_over_temperature": "Robot temperature too high. Let the robot cool down",
    "ui_error_dust_bin_missing": "Dust bin missing. Reinstall the dust bin",
    "ui_error_dust_bin_full": "Dust bin full. Empty the dust bin",
    "ui_error_hardware_failure": "Hardware failure. Reboot the robot",
    "ui_error_laser_sensor_failure": "Laser sensor failure. Reboot the robot",
    "ui_error_laser_blocked": "Laser blocked. Clean the robot",
    "ui_error_laser_communication_failure": "Laser communication failure. Reboot the robot",
    "ui_error_left_drop_sensor": "Left drop sensor error. Clean and check the sensor",
    "ui_error_right_drop_sensor": "Right drop sensor error. Clean and check the sensor",
    "ui_error_left_wheel_stuck": "Left wheel stuck",
    "ui_error_right_wheel_stuck": "Right wheel stuck",
    "ui_error_left_wheel_overloaded": "Left wheel overloaded",
    "ui_error_right_wheel_overloaded": "Right wheel overloaded",
    "ui_error_battery_low": "Battery low. Place the robot on the charging dock",
    "ui_error_battery_critical_low": "Battery critically low. Place the robot on the charging dock",
    "ui_error_unable_to_see": "Unable to see. Clean the sensors",
    "ui_error_path_blocked": "Path blocked. Remove obstacles",
    "ui_error_not_on_charge_base": "Robot not on charge base",
    "ui_error_no_wifi": "No WiFi connection",
    "ui_error_insufficient_memory": "Insufficient memory",
    "ui_error_bmp_communication_failure": "BMP communication failure",
    "ui_error_ui_board_failure": "UI board failure",
    "ui_error_unrecognized_map": "Unrecognized map",
    "ui_error_cannot_load_map_quick": "Cannot load map (quick)",
    "ui_error_not_docked": "Robot not docked",
    "ui_error_charge_communication_failure": "Charge communication failure",
}

# ---------------------------------------------------------------------------
# Alert codes
# ---------------------------------------------------------------------------
ROBOT_ALERTS = {
    "ui_alert_dust_bin_full": "Dust bin full. Empty the dust bin",
    "ui_alert_recovering_location": "Recovering location",
    "ui_alert_insufficient_memory": "Insufficient memory",
    "ui_alert_change_brush": "Change the brush",
    "ui_alert_change_filter": "Change the filter",
    "ui_alert_maint_brush": "Clean the brush",
    "ui_alert_maint_filter": "Clean the filter",
    "ui_alert_maint_brush_and_filter": "Clean the brush and filter",
    "ui_alert_task_completed": "Task completed",
    "ui_alert_rejecting_floorplan": "Rejecting floorplan",
    "ui_alert_unable_to_load_floorplan": "Unable to load floorplan",
    "ui_alert_unable_to_load_floorplan_no_map": "Unable to load floorplan (no map)",
    "ui_alert_floorplan_not_found": "Floorplan not found",
    "ui_alert_charging_now": "Charging now",
    "ui_alert_schedule_updated": "Schedule updated",
    "ui_alert_schedule_enabled": "Schedule enabled",
    "ui_alert_schedule_disabled": "Schedule disabled",
    "ui_alert_nav_draining_to_base": "Returning to base to charge",
    "ui_alert_front_camera_exposure": "Front camera exposure issue",
}

# ---------------------------------------------------------------------------
# Model name mapping (API model code → display name)
# ---------------------------------------------------------------------------
KOBOLD_MODEL_NAMES: dict[str, str] = {
    "VR100": "Kobold VR100",
    "VR200": "Kobold VR200",
    "VR220": "Kobold VR300",
    "VR300": "Kobold VR300",
}

# ---------------------------------------------------------------------------
# Service names (custom HA services)
# ---------------------------------------------------------------------------
SERVICE_CUSTOM_CLEANING = "custom_cleaning"
SERVICE_FIND_ME = "find_me"
SERVICE_DISMISS_ALERT = "dismiss_alert"
SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_ADD_SCHEDULE_EVENT = "add_schedule_event"
SERVICE_REMOVE_SCHEDULE_EVENT = "remove_schedule_event"

# Schedule field names
ATTR_SCHEDULE_EVENTS = "events"
ATTR_SCHEDULE_DAY = "day"
ATTR_SCHEDULE_MODE = "mode"
ATTR_SCHEDULE_START_TIME = "start_time"

# Service schema field names
ATTR_CLEANING_MODE = "cleaning_mode"
ATTR_NAVIGATION_MODE = "navigation_mode"
ATTR_CATEGORY = "category"
ATTR_BOUNDARY_ID = "boundary_id"
ATTR_MAP_ID = "map_id"
ATTR_SPOT_WIDTH = "spot_width"
ATTR_SPOT_HEIGHT = "spot_height"
