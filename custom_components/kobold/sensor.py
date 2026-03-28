"""Kobold battery sensor."""

from __future__ import annotations

import logging
from datetime import timedelta

from pybotvac import Robot

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KOBOLD_ROBOTS
from .entity import KoboldEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kobold sensor entities from a config entry."""
    robots: set[Robot] = hass.data[DOMAIN][entry.entry_id][KOBOLD_ROBOTS]
    async_add_entities(
        [KoboldBatterySensor(robot, entry) for robot in robots],
        update_before_add=True,
    )


class KoboldBatterySensor(KoboldEntity, SensorEntity):
    """Reports the robot's battery charge level."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery"

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        super().__init__(robot, entry)
        self._attr_unique_id = f"{robot.serial}_battery"

    def update(self) -> None:
        """Fetch state and extract battery level."""
        self._update_robot_state()

    @property
    def native_value(self) -> int | None:
        """Return battery charge percentage."""
        if self._robot_state:
            return self._robot_state.get("details", {}).get("charge")
        return None
