"""Base entity class shared by all Kobold platforms."""

from __future__ import annotations

import logging

from pybotvac import Robot
from pybotvac.exceptions import NeatoException

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    KOBOLD_HUB,
    KOBOLD_MAP_DATA,
    KOBOLD_MODEL_NAMES,
    KOBOLD_PERSISTENT_MAPS,
    KOBOLD_ROBOTS,
)

_LOGGER = logging.getLogger(__name__)


class KoboldEntity(Entity):
    """Representation of a single Kobold robot as a HA entity.

    All platform-specific entities (vacuum, sensor, camera, switch, button)
    inherit from this base class to share:
      - device_info  (ties entities to one device card)
      - hub / data accessors
      - common update helpers
    """

    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(self, robot: Robot, entry: ConfigEntry) -> None:
        """Initialise the entity."""
        self._robot = robot
        self._entry = entry
        self._robot_serial: str = robot.serial
        self._robot_state: dict | None = None
        self._available: bool = False

    # ------------------------------------------------------------------
    # HA entity plumbing
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True if the robot is reachable."""
        return self._available

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info so all entities share the same device card."""
        meta = {}
        if self._robot_state:
            meta = self._robot_state.get("meta", {})

        return DeviceInfo(
            identifiers={(DOMAIN, self._robot_serial)},
            name=self._robot.name,
            manufacturer="Vorwerk",
            model=KOBOLD_MODEL_NAMES.get(meta.get("modelName", ""), meta.get("modelName", "Kobold VR300")),
            sw_version=meta.get("firmware"),
        )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def _get_hub(self):
        """Return the KoboldHub for this config entry."""
        return self.hass.data[DOMAIN][self._entry.entry_id][KOBOLD_HUB]

    def _get_map_data(self) -> dict:
        return self.hass.data[DOMAIN][self._entry.entry_id].get(KOBOLD_MAP_DATA, {})

    def _get_persistent_maps(self) -> dict:
        return self.hass.data[DOMAIN][self._entry.entry_id].get(KOBOLD_PERSISTENT_MAPS, {})

    # ------------------------------------------------------------------
    # Shared update helper
    # ------------------------------------------------------------------

    def _update_robot_state(self) -> None:
        """Fetch robot state and update the hub; sets _available flag.

        Subclasses call this inside their ``update()`` method, then use
        ``self._robot_state`` to populate entity-specific attributes.

        State fields (state, action, details, cleaning, availableCommands,
        availableServices, meta) are returned at the top level of the
        response dict by pybotvac – no nested "data" key.
        """
        try:
            # Throttled hub refresh (fetches robots list + maps)
            self._get_hub().update_robots()
            # Fetch this robot's current operational state.
            # robot.state is a property that calls get_robot_state() and
            # returns the top-level response dict (or a cached version).
            self._robot_state = self._robot.state
            if self._robot_state is None:
                raise NeatoException("Empty state response")
            self._available = True
        except NeatoException as exc:
            if self._available:
                _LOGGER.warning(
                    "Could not reach Kobold robot %s (%s): %s",
                    self._robot.name,
                    self._robot_serial,
                    exc,
                )
            self._available = False
            self._robot_state = None
