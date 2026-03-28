"""Kobold schedule switch – enable/disable and edit the cleaning schedule."""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

import voluptuous as vol
from pybotvac import Robot
from pybotvac.exceptions import NeatoRobotException

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.entity_platform as entity_platform

from .const import (
    ATTR_SCHEDULE_DAY,
    ATTR_SCHEDULE_EVENTS,
    ATTR_SCHEDULE_MODE,
    ATTR_SCHEDULE_START_TIME,
    CLEANING_MODE_FROM_NAME,
    CLEANING_MODE_TO_NAME,
    DOMAIN,
    KOBOLD_ROBOTS,
    SERVICE_ADD_SCHEDULE_EVENT,
    SERVICE_REMOVE_SCHEDULE_EVENT,
    SERVICE_SET_SCHEDULE,
)
from .entity import KoboldEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

# day 0=Sunday … 6=Saturday
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Regex for "HH:MM" (00:00–23:59)
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_time(value: str) -> str:
    if not _TIME_RE.match(value):
        raise vol.Invalid(f"Invalid time '{value}', expected HH:MM (e.g. 08:30)")
    return value


# Schema for a single schedule event
_SCHEDULE_EVENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCHEDULE_DAY): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required(ATTR_SCHEDULE_MODE): vol.In(list(CLEANING_MODE_FROM_NAME)),
        vol.Required(ATTR_SCHEDULE_START_TIME): vol.All(cv.string, _validate_time),
    }
)

# Entity service schemas
SET_SCHEDULE_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_EVENTS): vol.All(
        list,
        [_SCHEDULE_EVENT_SCHEMA],
        vol.Length(min=0, max=7),
    ),
}

ADD_SCHEDULE_EVENT_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_DAY): vol.All(int, vol.Range(min=0, max=6)),
    vol.Required(ATTR_SCHEDULE_MODE): vol.In(list(CLEANING_MODE_FROM_NAME)),
    vol.Required(ATTR_SCHEDULE_START_TIME): vol.All(cv.string, _validate_time),
}

REMOVE_SCHEDULE_EVENT_SCHEMA = {
    vol.Required(ATTR_SCHEDULE_DAY): vol.All(int, vol.Range(min=0, max=6)),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kobold switch entities from a config entry."""
    robots: set[Robot] = hass.data[DOMAIN][entry.entry_id][KOBOLD_ROBOTS]
    async_add_entities(
        [KoboldScheduleSwitch(robot, entry) for robot in robots],
        update_before_add=True,
    )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SET_SCHEDULE,
        SET_SCHEDULE_SCHEMA,
        "async_set_schedule",
    )
    platform.async_register_entity_service(
        SERVICE_ADD_SCHEDULE_EVENT,
        ADD_SCHEDULE_EVENT_SCHEMA,
        "async_add_schedule_event",
    )
    platform.async_register_entity_service(
        SERVICE_REMOVE_SCHEDULE_EVENT,
        REMOVE_SCHEDULE_EVENT_SCHEMA,
        "async_remove_schedule_event",
    )


class KoboldScheduleSwitch(KoboldEntity, SwitchEntity):
    """Toggle the robot's cleaning schedule on/off and manage its events."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "schedule"

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        super().__init__(robot, entry)
        self._attr_unique_id = f"{robot.serial}_schedule"
        self._schedule_enabled: bool = False
        self._schedule_events: list[dict] = []

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Fetch robot state and full schedule."""
        self._update_robot_state()
        if not self._robot_state:
            return

        self._schedule_enabled = bool(
            self._robot_state.get("details", {}).get("isScheduleEnabled", False)
        )

        try:
            resp = self._robot.get_schedule()
            data = resp.json().get("data", {})
            self._schedule_events = data.get("events", [])
        except NeatoRobotException as exc:
            _LOGGER.warning("Could not fetch schedule for %s: %s", self._robot.name, exc)
            self._schedule_events = []

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        return self._schedule_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose schedule events as state attributes for automations/UI."""
        readable = []
        for ev in self._schedule_events:
            day_num = ev.get("day", 0)
            mode_num = ev.get("mode", 1)
            readable.append({
                "day": DAY_NAMES[day_num] if 0 <= day_num <= 6 else day_num,
                "day_number": day_num,
                "mode": CLEANING_MODE_TO_NAME.get(mode_num, mode_num),
                "start_time": ev.get("startTime", ""),
            })
        return {"schedule_events": readable}

    # ------------------------------------------------------------------
    # Switch on/off
    # ------------------------------------------------------------------

    def turn_on(self, **kwargs: Any) -> None:
        try:
            self._robot.enable_schedule()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not enable schedule for %s: %s", self._robot.name, exc)

    def turn_off(self, **kwargs: Any) -> None:
        try:
            self._robot.disable_schedule()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not disable schedule for %s: %s", self._robot.name, exc)

    # ------------------------------------------------------------------
    # Schedule services
    # ------------------------------------------------------------------

    def _push_schedule(self, events: list[dict]) -> None:
        """Send a full schedule replacement to the robot (blocking)."""
        payload = {
            "reqId": "1",
            "cmd": "setSchedule",
            "params": {
                "type": 1,
                "enabled": self._schedule_enabled,
                "events": events,
            },
        }
        any_schema = vol.Schema({}, extra=vol.ALLOW_EXTRA)
        self._robot._message(payload, any_schema)  # noqa: SLF001

    async def async_set_schedule(self, events: list[dict]) -> None:
        """Replace the entire schedule.

        Each event: {day: 0-6, mode: "Eco"|"Turbo", start_time: "HH:MM"}
        Day 0 = Sunday, 1 = Monday … 6 = Saturday.
        Pass an empty list to clear all events.
        """
        api_events = [
            {
                "day": ev[ATTR_SCHEDULE_DAY],
                "mode": CLEANING_MODE_FROM_NAME[ev[ATTR_SCHEDULE_MODE]],
                "startTime": ev[ATTR_SCHEDULE_START_TIME],
            }
            for ev in events
        ]
        try:
            await self.hass.async_add_executor_job(self._push_schedule, api_events)
            self._schedule_events = [
                {"day": e["day"], "mode": e["mode"], "startTime": e["startTime"]}
                for e in api_events
            ]
            self.async_write_ha_state()
        except NeatoRobotException as exc:
            _LOGGER.error("Could not set schedule for %s: %s", self._robot.name, exc)

    async def async_add_schedule_event(
        self,
        day: int,
        mode: str,
        start_time: str,
    ) -> None:
        """Add or replace a single day's event in the current schedule.

        If an event already exists for that day it is overwritten.
        """
        # Remove any existing event for this day, then append the new one
        existing = [ev for ev in self._schedule_events if ev.get("day") != day]
        new_event = {
            "day": day,
            "mode": CLEANING_MODE_FROM_NAME[mode],
            "startTime": start_time,
        }
        merged = existing + [new_event]
        try:
            await self.hass.async_add_executor_job(self._push_schedule, merged)
            self._schedule_events = merged
            self.async_write_ha_state()
        except NeatoRobotException as exc:
            _LOGGER.error(
                "Could not add schedule event for %s: %s", self._robot.name, exc
            )

    async def async_remove_schedule_event(self, day: int) -> None:
        """Remove the event for the given day (0=Sunday … 6=Saturday).

        No-op if no event exists for that day.
        """
        filtered = [ev for ev in self._schedule_events if ev.get("day") != day]
        try:
            await self.hass.async_add_executor_job(self._push_schedule, filtered)
            self._schedule_events = filtered
            self.async_write_ha_state()
        except NeatoRobotException as exc:
            _LOGGER.error(
                "Could not remove schedule event for %s: %s", self._robot.name, exc
            )
