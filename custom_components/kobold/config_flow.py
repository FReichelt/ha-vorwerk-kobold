"""Config flow for the Vorwerk Kobold integration.

Authentication uses the Vorwerk/MyKobold passwordless (email OTP) flow:
  Step 1 – user enters email  → OTP sent to their inbox
  Step 2 – user enters code   → token exchanged and stored
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pybotvac import PasswordlessSession, Vorwerk
from pybotvac.exceptions import NeatoLoginException

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_TOKEN,
    DOMAIN,
    VORWERK_CLIENT_ID,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
    }
)

STEP_CODE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("code"): cv.string,
    }
)


def _build_session() -> PasswordlessSession:
    """Create a new PasswordlessSession for Vorwerk."""
    return PasswordlessSession(
        client_id=VORWERK_CLIENT_ID,
        vendor=Vorwerk(),
    )


async def _async_send_otp(hass: HomeAssistant, session: PasswordlessSession, email: str) -> None:
    """Send OTP email using executor (pybotvac is blocking)."""
    await hass.async_add_executor_job(session.send_email_otp, email)


async def _async_fetch_token(
    hass: HomeAssistant,
    session: PasswordlessSession,
    email: str,
    code: str,
) -> dict:
    """Exchange email + OTP for a token dict."""
    await hass.async_add_executor_job(
        session.fetch_token_passwordless, email, code
    )
    # The token is stored internally; retrieve it for persistence
    return session._token  # pybotvac stores the token as a private attribute


class KoboldConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vorwerk Kobold."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._session: PasswordlessSession | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step – collect the user's email."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()

            # Prevent duplicate entries for the same account
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            self._email = email
            self._session = _build_session()

            try:
                await _async_send_otp(self.hass, self._session, email)
            except NeatoLoginException:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while sending OTP")
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_code()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the OTP code step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            code = user_input["code"].strip()

            try:
                token = await _async_fetch_token(
                    self.hass, self._session, self._email, code
                )
            except NeatoLoginException:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while fetching token")
                errors["base"] = "cannot_connect"
            else:
                new_data = {CONF_EMAIL: self._email, CONF_TOKEN: token}
                # Reauth: update the existing entry instead of creating a new one
                existing_entries = self._async_current_entries()
                for existing in existing_entries:
                    if existing.unique_id == self.unique_id:
                        self.hass.config_entries.async_update_entry(
                            existing, data=new_data
                        )
                        await self.hass.config_entries.async_reload(existing.entry_id)
                        return self.async_abort(reason="reauth_successful")
                # Normal first-time setup
                return self.async_create_entry(
                    title=self._email,
                    data=new_data,
                )

        return self.async_show_form(
            step_id="code",
            data_schema=STEP_CODE_DATA_SCHEMA,
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication when the stored token is expired/revoked.

        ``entry_data`` is the existing config entry's data dict, passed by HA
        automatically when ConfigEntryAuthFailed is raised.
        """
        self._email = entry_data.get(CONF_EMAIL, "")
        self._session = _build_session()

        try:
            await _async_send_otp(self.hass, self._session, self._email)
        except NeatoLoginException:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Reauth: error sending OTP")
            return self.async_abort(reason="cannot_connect")

        return await self.async_step_code()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm handler that redirects into the code step for reauth."""
        return await self.async_step_code(user_input)
