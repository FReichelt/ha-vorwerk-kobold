"""Kobold VR300 vacuum entity."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from pybotvac import Robot
from pybotvac.exceptions import NeatoRobotException

from homeassistant.components.vacuum import (
    VacuumActivity,
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.entity_platform as entity_platform

from .const import (
    ATTR_BOUNDARY_ID,
    ATTR_CATEGORY,
    ATTR_CLEANING_MODE,
    ATTR_MAP_ID,
    ATTR_NAVIGATION_MODE,
    CLEANING_CATEGORY_NON_PERSISTENT_MAP,
    CLEANING_CATEGORY_PERSISTENT_MAP,
    CLEANING_MODE_FROM_NAME,
    CLEANING_MODE_TO_NAME,
    CLEANING_MODE_TURBO,
    DOMAIN,
    KOBOLD_ROBOTS,
    NAVIGATION_MODE_FROM_NAME,
    NAVIGATION_MODE_NORMAL,
    NAVIGATION_MODE_TO_NAME,
    ROBOT_ACTIONS,
    ROBOT_ALERTS,
    ROBOT_ERRORS,
    ROBOT_STATE_BUSY,
    ROBOT_STATE_ERROR,
    ROBOT_STATE_IDLE,
    ROBOT_STATE_PAUSED,
    SERVICE_CUSTOM_CLEANING,
)
from .entity import KoboldEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

# ---------------------------------------------------------------------------
# Supported features bitmap
# ---------------------------------------------------------------------------
SUPPORT_KOBOLD = (
    VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.START
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.STATE
    | VacuumEntityFeature.MAP
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.SEND_COMMAND
)

# ---------------------------------------------------------------------------
# Custom service schema
# ---------------------------------------------------------------------------
CUSTOM_CLEANING_SCHEMA = {
    vol.Optional(ATTR_CLEANING_MODE, default="Turbo"): vol.In(
        list(CLEANING_MODE_FROM_NAME)
    ),
    vol.Optional(ATTR_NAVIGATION_MODE, default="Normal"): vol.In(
        list(NAVIGATION_MODE_FROM_NAME)
    ),
    vol.Optional(ATTR_CATEGORY): vol.In(
        [CLEANING_CATEGORY_NON_PERSISTENT_MAP, CLEANING_CATEGORY_PERSISTENT_MAP]
    ),
    vol.Optional(ATTR_BOUNDARY_ID): cv.string,
    vol.Optional(ATTR_MAP_ID): cv.string,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kobold vacuum entities from a config entry."""
    robots: set[Robot] = hass.data[DOMAIN][entry.entry_id][KOBOLD_ROBOTS]

    entities = [KoboldVacuum(robot, entry) for robot in robots]
    async_add_entities(entities, update_before_add=True)

    # ------------------------------------------------------------------ #
    # Register platform-level custom services                             #
    # ------------------------------------------------------------------ #
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_CUSTOM_CLEANING,
        CUSTOM_CLEANING_SCHEMA,
        "async_custom_cleaning",
    )


class KoboldVacuum(KoboldEntity, StateVacuumEntity):
    """Representation of a Kobold VR300 vacuum robot."""

    _attr_name = None  # uses the device name directly
    _attr_supported_features = SUPPORT_KOBOLD

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        """Initialise the vacuum entity."""
        super().__init__(robot, entry)
        self._attr_unique_id = robot.serial
        self._attr_activity: VacuumActivity = VacuumActivity.IDLE
        self._activity: str | None = None
        self._status_message: str = "Initialising"
        self._available_commands: dict = {}

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Poll the robot and refresh all state."""
        self._update_robot_state()

        if not self._available or self._robot_state is None:
            return

        state_num: int = self._robot_state.get("state", ROBOT_STATE_IDLE)
        action_num: int = self._robot_state.get("action", 0)
        details: dict = self._robot_state.get("details", {})
        error: str | None = self._robot_state.get("error")
        alert: str | None = self._robot_state.get("alert")
        self._available_commands = self._robot_state.get("availableCommands", {})

        # ---- Map pybotvac state number → HA vacuum activity ----
        if state_num == ROBOT_STATE_IDLE:
            if details.get("isCharging") or details.get("isDocked"):
                self._attr_activity = VacuumActivity.DOCKED
            else:
                self._attr_activity = VacuumActivity.IDLE
        elif state_num == ROBOT_STATE_BUSY:
            if alert:
                self._attr_activity = VacuumActivity.ERROR
            else:
                self._attr_activity = VacuumActivity.CLEANING
        elif state_num == ROBOT_STATE_PAUSED:
            self._attr_activity = VacuumActivity.PAUSED
        elif state_num == ROBOT_STATE_ERROR:
            self._attr_activity = VacuumActivity.ERROR
        else:
            self._attr_activity = VacuumActivity.IDLE

        # ---- Human-readable status message ----
        if error:
            self._status_message = ROBOT_ERRORS.get(error, f"Error: {error}")
        elif alert:
            self._status_message = ROBOT_ALERTS.get(alert, f"Alert: {alert}")
        else:
            self._status_message = ROBOT_ACTIONS.get(action_num, "Unknown")

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        """Return a human-readable status string."""
        return self._status_message

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Kobold-specific attributes for the state card."""
        if not self._robot_state:
            return {}

        details: dict = self._robot_state.get("details", {})
        cleaning: dict = self._robot_state.get("cleaning", {})
        meta: dict = self._robot_state.get("meta", {})
        services: dict = self._robot_state.get("availableServices", {})

        mode_num = cleaning.get("mode")
        nav_num = cleaning.get("navigationMode")

        attrs: dict[str, Any] = {
            # Robot details
            "status": self._status_message,
            "dock_has_been_seen": details.get("dockHasBeenSeen"),
            "is_docked": details.get("isDocked"),
            "is_charging": details.get("isCharging"),
            "schedule_enabled": details.get("isScheduleEnabled"),
            # Cleaning parameters
            "cleaning_mode": CLEANING_MODE_TO_NAME.get(mode_num, mode_num),
            "navigation_mode": NAVIGATION_MODE_TO_NAME.get(nav_num, nav_num),
            "cleaning_category": cleaning.get("category"),
            "spot_width": cleaning.get("spotWidth"),
            "spot_height": cleaning.get("spotHeight"),
            # Robot metadata
            "model": meta.get("modelName"),
            "firmware": meta.get("firmware"),
            # Available commands (useful for automations)
            "available_commands": self._available_commands,
            # Available services (for advanced users)
            "available_services": services,
        }

        # Include error/alert if present
        error = self._robot_state.get("error")
        alert = self._robot_state.get("alert")
        if error:
            attrs["error"] = ROBOT_ERRORS.get(error, error)
        if alert:
            attrs["alert"] = ROBOT_ALERTS.get(alert, alert)

        return attrs

    # ------------------------------------------------------------------
    # Standard vacuum services
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start or resume cleaning."""
        try:
            if self._attr_activity == VacuumActivity.PAUSED:
                self._robot.resume_cleaning()
            else:
                # Determine best cleaning category
                persistent_maps = self._get_persistent_maps()
                has_persistent = bool(
                    persistent_maps.get(self._robot_serial)
                )
                category = (
                    CLEANING_CATEGORY_PERSISTENT_MAP
                    if has_persistent
                    else CLEANING_CATEGORY_NON_PERSISTENT_MAP
                )
                self._robot.start_cleaning(
                    mode=CLEANING_MODE_TURBO,
                    navigation_mode=NAVIGATION_MODE_NORMAL,
                    category=category,
                )
        except NeatoRobotException as exc:
            _LOGGER.error("Could not start cleaning %s: %s", self._robot.name, exc)

    def pause(self) -> None:
        """Pause the current cleaning session."""
        try:
            self._robot.pause_cleaning()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not pause %s: %s", self._robot.name, exc)

    def stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        try:
            self._robot.stop_cleaning()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not stop %s: %s", self._robot.name, exc)

    def return_to_base(self, **kwargs: Any) -> None:
        """Send the robot home."""
        try:
            if self._attr_activity == VacuumActivity.CLEANING:
                self._robot.pause_cleaning()
            self._robot.send_to_base()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not send %s to base: %s", self._robot.name, exc)

    def locate(self, **kwargs: Any) -> None:
        """Play a sound to help the user find the robot."""
        try:
            self._robot.locate()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not locate %s: %s", self._robot.name, exc)

    def clean_spot(self, **kwargs: Any) -> None:
        """Perform a spot clean at the current position."""
        try:
            self._robot.start_spot_cleaning()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not start spot clean on %s: %s", self._robot.name, exc)

    async def async_send_command(
        self, command: str, params: dict[str, Any] | list[Any] | None = None, **kwargs: Any
    ) -> None:
        """Send a raw command to the robot.

        Supports manual driving and any other robot command not exposed
        as a dedicated HA service. Commands are sent directly via the
        pybotvac _message() low-level API.

        Example commands:
          - startManualCleaning  (no params)
          - driveManual          params: velocity (-0.3..0.3 m/s), twist (-1..1 rad/s), brakeOnStop (bool)
          - stopCleaning         (no params)
          - getGeneralInfo       (no params)
        """
        payload: dict[str, Any] = {"reqId": "1", "cmd": command}
        if params:
            payload["params"] = params

        _LOGGER.debug("send_command %s: %s", self._robot.name, payload)

        # Accept any response shape — the caller is doing exploratory/manual control
        any_response = vol.Schema({}, extra=vol.ALLOW_EXTRA)
        try:
            await self.hass.async_add_executor_job(
                self._robot._message, payload, any_response  # noqa: SLF001
            )
        except NeatoRobotException as exc:
            _LOGGER.error(
                "send_command '%s' failed for %s: %s", command, self._robot.name, exc
            )

    # ------------------------------------------------------------------
    # Custom service: kobold.custom_cleaning
    # ------------------------------------------------------------------

    async def async_custom_cleaning(
        self,
        cleaning_mode: str = "Turbo",
        navigation_mode: str = "Normal",
        category: int | None = None,
        boundary_id: str | None = None,
        map_id: str | None = None,
    ) -> None:
        """Start cleaning with explicit mode, navigation, and map options.

        Called by HA entity platform service with schema-validated kwargs.
        This service exposes all parameters of pybotvac's start_cleaning().
        """
        mode = CLEANING_MODE_FROM_NAME.get(cleaning_mode, CLEANING_MODE_TURBO)
        nav = NAVIGATION_MODE_FROM_NAME.get(navigation_mode, NAVIGATION_MODE_NORMAL)

        if category is None:
            persistent_maps = self._get_persistent_maps()
            has_persistent = bool(persistent_maps.get(self._robot_serial))
            category = (
                CLEANING_CATEGORY_PERSISTENT_MAP
                if has_persistent
                else CLEANING_CATEGORY_NON_PERSISTENT_MAP
            )

        _LOGGER.debug(
            "Custom cleaning %s: mode=%s nav=%s category=%s boundary=%s map=%s",
            self._robot.name,
            mode,
            nav,
            category,
            boundary_id,
            map_id,
        )

        try:
            await self.hass.async_add_executor_job(
                self._robot.start_cleaning,
                mode,
                nav,
                category,
                boundary_id,
                map_id,
            )
        except NeatoRobotException as exc:
            _LOGGER.error(
                "Custom cleaning failed for %s: %s", self._robot.name, exc
            )
