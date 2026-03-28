"""KoboldHub – thin wrapper around pybotvac.Account with throttled updates."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

from pybotvac import Account, PasswordlessSession, Vorwerk
from pybotvac.exceptions import NeatoException

from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    KOBOLD_MAP_DATA,
    KOBOLD_PERSISTENT_MAPS,
    KOBOLD_ROBOTS,
    SCAN_INTERVAL_MINUTES,
    VORWERK_CLIENT_ID,
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=SCAN_INTERVAL_MINUTES)


class KoboldHub:
    """Central hub that owns the pybotvac Account and refreshes robot data.

    Data is scoped to ``hass.data[DOMAIN][entry_id]`` to support multiple
    simultaneous Kobold accounts without cross-contamination.
    """

    def __init__(
        self, hass: HomeAssistant, account: Account, entry_id: str
    ) -> None:
        """Initialise the hub."""
        self._hass = hass
        self._account = account
        self._entry_id = entry_id

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def download_map(self, url: str) -> bytes | None:
        """Download a cleaning-map image and return raw bytes (blocking)."""
        try:
            response = self._account.get_map_image(url)
            if response is not None:
                return response.content  # type: ignore[union-attr]
        except NeatoException as exc:
            _LOGGER.warning("Could not download map image: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Throttled refresh – called by entities during their update cycle
    # ------------------------------------------------------------------

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_robots(self) -> None:
        """Fetch robots, maps, and persistent maps from the Kobold cloud.

        Throttled to at most once per SCAN_INTERVAL_MINUTES to avoid
        hammering the cloud API when multiple entities update together.
        All data is stored scoped to this hub's entry_id.
        """
        entry_data: dict = self._hass.data[DOMAIN][self._entry_id]

        try:
            self._account.refresh_robots()
            entry_data[KOBOLD_ROBOTS] = self._account.robots
        except NeatoException as exc:
            _LOGGER.error("Error refreshing robots for entry %s: %s", self._entry_id, exc)
            raise

        # Maps and persistent maps are best-effort; a failure here should not
        # mark all entities unavailable.
        try:
            self._account.refresh_maps()
            entry_data[KOBOLD_MAP_DATA] = self._account.maps
        except NeatoException as exc:
            _LOGGER.warning("Could not refresh map data: %s", exc)

        try:
            self._account.refresh_persistent_maps()
            entry_data[KOBOLD_PERSISTENT_MAPS] = self._account.persistent_maps
        except NeatoException as exc:
            _LOGGER.warning("Could not refresh persistent maps: %s", exc)


def build_session_from_token(
    token: dict,
    token_updater: Callable[[dict], None] | None = None,
) -> PasswordlessSession:
    """Re-hydrate a PasswordlessSession from a stored token dict.

    Pass a ``token_updater`` callback so that automatic token refreshes
    (Auth0 silent refresh) are persisted back into the config entry.
    """
    session = PasswordlessSession(
        client_id=VORWERK_CLIENT_ID,
        vendor=Vorwerk(),
        token=token,
        token_updater=token_updater or (lambda _t: None),
    )
    return session
