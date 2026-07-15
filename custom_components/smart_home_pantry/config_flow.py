# Creato da domoticafacile.it

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_DAYS_BEFORE,
    CONF_NOTIFY_TIME,
    CONF_NOTIFY_SERVICES,
    CONF_PERSISTENT_ENABLED,
    CONF_PUSH_ENABLED,
    CONF_DATE_FORMAT,
    CONF_DAYS_CRITICAL,
    CONF_SIDEBAR_ENABLED,
    CONF_SIDEBAR_TITLE,
    CONF_NEXT_EXPIRY_WITHIN,
    CONF_EXPIRED_WITHIN,
    CONF_SORT_ORDER,
    DEFAULT_DAYS_BEFORE,
    DEFAULT_NOTIFY_TIME,
    DEFAULT_NOTIFY_SERVICES,
    DEFAULT_PERSISTENT_ENABLED,
    DEFAULT_PUSH_ENABLED,
    DEFAULT_DATE_FORMAT,
    DEFAULT_DAYS_CRITICAL,
    DEFAULT_SIDEBAR_ENABLED,
    DEFAULT_SIDEBAR_TITLE,
    LEGACY_CONF_CARD_TITLE,
    DEFAULT_NEXT_EXPIRY_WITHIN,
    DEFAULT_EXPIRED_WITHIN,
    DEFAULT_SORT_ORDER,
    DATE_FORMATS,
    SORT_ORDERS,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title='Smart Home Pantry', data={})

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:

            notify_time = user_input.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME).strip()
            parts = notify_time.split(":")
            valid_time = False
            if len(parts) in (2, 3) and all(p.isdigit() for p in parts):
                h = int(parts[0])
                m = int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    valid_time = True

            if not valid_time:
                errors[CONF_NOTIFY_TIME] = "invalid_time"

            days_before = int(user_input.get(CONF_DAYS_BEFORE, DEFAULT_DAYS_BEFORE))
            days_critical = int(user_input.get(CONF_DAYS_CRITICAL, DEFAULT_DAYS_CRITICAL))
            if days_critical > days_before:
                errors[CONF_DAYS_CRITICAL] = "critical_above_warning"

            if not errors:
                if len(parts) == 2:
                    notify_time = f"{parts[0]}:{parts[1]}:00"
                user_input[CONF_NOTIFY_TIME] = notify_time

                title = str(user_input.get(CONF_SIDEBAR_TITLE, "")).strip()
                user_input[CONF_SIDEBAR_TITLE] = title or DEFAULT_SIDEBAR_TITLE

                return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema = vol.Schema({
            vol.Optional(
                CONF_PERSISTENT_ENABLED,
                default=options.get(CONF_PERSISTENT_ENABLED, DEFAULT_PERSISTENT_ENABLED),
            ): bool,
            vol.Optional(
                CONF_PUSH_ENABLED,
                default=options.get(CONF_PUSH_ENABLED, DEFAULT_PUSH_ENABLED),
            ): bool,
            vol.Optional(
                CONF_NOTIFY_SERVICES,
                default=options.get(CONF_NOTIFY_SERVICES, DEFAULT_NOTIFY_SERVICES),
            ): str,
            vol.Optional(
                CONF_NOTIFY_TIME,
                default=options.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_DAYS_BEFORE,
                default=options.get(CONF_DAYS_BEFORE, DEFAULT_DAYS_BEFORE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=365, mode="box")
            ),
            vol.Optional(
                CONF_DAYS_CRITICAL,
                default=options.get(CONF_DAYS_CRITICAL, DEFAULT_DAYS_CRITICAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=365, mode="box")
            ),
            vol.Optional(
                CONF_SIDEBAR_ENABLED,
                default=options.get(CONF_SIDEBAR_ENABLED, DEFAULT_SIDEBAR_ENABLED),
            ): bool,
            vol.Optional(
                CONF_SIDEBAR_TITLE,
                default=options.get(
                    CONF_SIDEBAR_TITLE,
                    options.get(LEGACY_CONF_CARD_TITLE, DEFAULT_SIDEBAR_TITLE),
                ),
            ): str,
            vol.Optional(
                CONF_DATE_FORMAT,
                default=options.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DATE_FORMATS,
                    mode="dropdown",
                )
            ),
            vol.Optional(
                CONF_NEXT_EXPIRY_WITHIN,
                default=options.get(CONF_NEXT_EXPIRY_WITHIN, DEFAULT_NEXT_EXPIRY_WITHIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3650, mode="box")
            ),
            vol.Optional(
                CONF_EXPIRED_WITHIN,
                default=options.get(CONF_EXPIRED_WITHIN, DEFAULT_EXPIRED_WITHIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3650, mode="box")
            ),
            vol.Optional(
                CONF_SORT_ORDER,
                default=options.get(CONF_SORT_ORDER, DEFAULT_SORT_ORDER),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SORT_ORDERS,
                    mode="dropdown",
                    translation_key="sort_order",
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
