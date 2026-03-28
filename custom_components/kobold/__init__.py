"""The Vorwerk Kobold integration."""

from __future__ import annotations

import logging

from pybotvac import Account
from pybotvac.exceptions import NeatoException, NeatoLoginException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    CONF_TOKEN,
    DOMAIN,
    KOBOLD_HUB,
    KOBOLD_MAP_DATA,
    KOBOLD_PERSISTENT_MAPS,
    KOBOLD_ROBOTS,
    PLATFORMS,
)
from .hub import KoboldHub, build_session_from_token

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kobold from a config entry."""

    token: dict = entry.data[CONF_TOKEN]
    email: str = entry.data[CONF_EMAIL]

    # ------------------------------------------------------------------ #
    # Token-updater: when pybotvac refreshes the token, persist it back   #
    # into the config entry so it survives restarts.                       #
    # ------------------------------------------------------------------ #
    def _token_updater(new_token: dict) -> None:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_TOKEN: new_token},
        )

    # Build a session from the stored token, passing the updater at
    # construction time so no private-attribute patching is needed.
    session = build_session_from_token(token, token_updater=_token_updater)

    # Build the pybotvac Account object (wraps the session)
    account = Account(session)

    # Do an initial robot fetch inside the executor (blocking HTTP call)
    try:
        await hass.async_add_executor_job(account.refresh_robots)
    except NeatoLoginException as exc:
        raise ConfigEntryAuthFailed(
            f"Authentication failed for {email}. Please re-authenticate."
        ) from exc
    except NeatoException as exc:
        raise ConfigEntryNotReady(
            f"Could not connect to Kobold cloud for {email}: {exc}"
        ) from exc

    # Seed hass.data for this domain
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        KOBOLD_HUB: KoboldHub(hass, account, entry.entry_id),
        KOBOLD_ROBOTS: account.robots,
        KOBOLD_MAP_DATA: {},
        KOBOLD_PERSISTENT_MAPS: {},
    }

    # Forward to all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
