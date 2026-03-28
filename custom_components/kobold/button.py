"""Kobold button entities."""

from __future__ import annotations

import logging

from pybotvac import Robot
from pybotvac.exceptions import NeatoRobotException

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KOBOLD_ROBOTS
from .entity import KoboldEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kobold button entities from a config entry."""
    robots: set[Robot] = hass.data[DOMAIN][entry.entry_id][KOBOLD_ROBOTS]
    entities = []
    for robot in robots:
        entities.append(KoboldDismissAlertButton(robot, entry))
        entities.append(KoboldFindMeButton(robot, entry))
    async_add_entities(entities)


class KoboldDismissAlertButton(KoboldEntity, ButtonEntity):
    """Button to dismiss the current robot alert."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "dismiss_alert"
    # Buttons don't need polling
    _attr_should_poll = False

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        super().__init__(robot, entry)
        self._attr_unique_id = f"{robot.serial}_dismiss_alert"
        self._available = True  # always show; availability follows vacuum entity

    async def async_press(self) -> None:
        """Dismiss the current alert on the robot."""
        try:
            await self.hass.async_add_executor_job(
                self._robot.dismiss_current_alert
            )
        except NeatoRobotException as exc:
            _LOGGER.error(
                "Could not dismiss alert for %s: %s", self._robot.name, exc
            )


class KoboldFindMeButton(KoboldEntity, ButtonEntity):
    """Button to trigger the robot's locate/find-me sound."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "find_me"
    _attr_should_poll = False

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        super().__init__(robot, entry)
        self._attr_unique_id = f"{robot.serial}_find_me"
        self._available = True

    async def async_press(self) -> None:
        """Make the robot emit a locator beep."""
        try:
            await self.hass.async_add_executor_job(self._robot.locate)
        except NeatoRobotException as exc:
            _LOGGER.error(
                "Could not locate %s: %s", self._robot.name, exc
            )
