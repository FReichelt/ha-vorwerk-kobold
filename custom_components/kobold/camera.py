"""Kobold cleaning map camera entity.

Displays the most recent cleaning map image retrieved from the Kobold cloud.
The image URL is compared against the cached URL to avoid redundant downloads.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from pybotvac import Robot
from pybotvac.exceptions import NeatoException

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KOBOLD_MAP_DATA, KOBOLD_ROBOTS
from .entity import KoboldEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)  # Maps update less frequently


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kobold camera entities from a config entry."""
    robots: set[Robot] = hass.data[DOMAIN][entry.entry_id][KOBOLD_ROBOTS]
    async_add_entities(
        [KoboldCleaningMap(robot, entry) for robot in robots],
        update_before_add=False,  # Don't block startup on map fetch
    )


class KoboldCleaningMap(KoboldEntity, Camera):
    """Camera entity that shows the latest cleaning map."""

    _attr_translation_key = "cleaning_map"
    _attr_is_on = True  # Camera is always "on" (streaming = False, snapshot only)
    _attr_is_streaming = False

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        """Initialise the map camera."""
        KoboldEntity.__init__(self, robot, entry)
        Camera.__init__(self)
        self._attr_unique_id = f"{robot.serial}_map"
        self._image: bytes | None = None
        self._image_url: str | None = None
        self._generated_at: str | None = None
        self._available = False

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Refresh the hub and download a new map image if the URL changed."""
        try:
            hub = self._get_hub()
            hub.update_robots()

            map_data: dict = self._get_map_data()
            robot_maps: list = map_data.get(self._robot_serial, {}).get("maps", [])

            if not robot_maps:
                _LOGGER.debug("No map available yet for %s", self._robot.name)
                self._available = False
                return

            latest_map: dict = robot_maps[0]
            new_url: str | None = latest_map.get("url")
            self._generated_at = latest_map.get("generated_at")

            if new_url and new_url != self._image_url:
                _LOGGER.debug(
                    "New map URL for %s, downloading…", self._robot.name
                )
                image_bytes = hub.download_map(new_url)
                if image_bytes:
                    self._image = image_bytes
                    self._image_url = new_url
                    self._available = True
                else:
                    self._available = False
            else:
                # URL unchanged – reuse cached image
                self._available = self._image is not None

        except NeatoException as exc:
            if self._available:
                _LOGGER.warning(
                    "Could not update map for %s: %s", self._robot.name, exc
                )
            self._available = False

    # ------------------------------------------------------------------
    # Camera interface
    # ------------------------------------------------------------------

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest map image bytes."""
        return self._image

    # ------------------------------------------------------------------
    # Extra attributes
    # ------------------------------------------------------------------

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the map generation timestamp."""
        attrs: dict[str, Any] = {}
        if self._generated_at:
            attrs["generated_at"] = self._generated_at
        if self._image_url:
            attrs["map_url"] = self._image_url
        return attrs
