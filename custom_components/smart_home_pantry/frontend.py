# Creato da domoticafacile.it

import logging
import os
from datetime import date

from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig, HomeAssistantView
from homeassistant.components import frontend, panel_custom

from .const import (
    CARD_FILENAME, CARD_URL, URL_BASE, EXPORT_URL, DOMAIN,
    PANEL_FILENAME, PANEL_URL, PANEL_URL_PATH, PANEL_COMPONENT_NAME, PANEL_ICON,
)
from .export import build_xlsx, expired_rows

_LOGGER = logging.getLogger(__name__)


class ExpiredExportView(HomeAssistantView):

    url = EXPORT_URL
    name = "smart_home_pantry:export_expired"
    requires_auth = True

    async def get(self, request):
        from aiohttp import web

        hass = request.app["hass"]
        data = hass.data.get(DOMAIN, {}).get("data", {})
        products = data.get("expired_products", [])

        rows = await hass.async_add_executor_job(expired_rows, products, date.today())
        content = await hass.async_add_executor_job(build_xlsx, rows)

        filename = "prodotti_scaduti_" + date.today().isoformat() + ".xlsx"
        return web.Response(
            body=content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": 'attachment; filename="' + filename + '"'
            },
        )


async def async_register_card(hass: HomeAssistant, version: str) -> None:

    base = os.path.dirname(__file__)
    card_path = os.path.join(base, CARD_FILENAME)
    panel_path = os.path.join(base, PANEL_FILENAME)

    if not hass.data.get(DOMAIN, {}).get("export_view_registered"):
        try:
            hass.http.register_view(ExpiredExportView())
            hass.data.setdefault(DOMAIN, {})["export_view_registered"] = True
            _LOGGER.debug("Endpoint export scaduti registrato: %s", EXPORT_URL)
        except Exception as err:
            _LOGGER.warning("Impossibile registrare l'export: %s", err)

    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_URL, card_path, False),
            StaticPathConfig(PANEL_URL, panel_path, False),
        ])
        _LOGGER.debug("Card e pannello Smart Home Pantry serviti (%s, %s)", CARD_URL, PANEL_URL)
    except RuntimeError:

        _LOGGER.debug("Percorsi statici gia' registrati")
    except Exception as err:
        _LOGGER.warning("Impossibile servire la card: %s", err)
        return

    await _async_register_lovelace_resource(hass, version)


async def _async_register_lovelace_resource(hass: HomeAssistant, version: str) -> None:
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return

    mode = getattr(lovelace, "mode", getattr(lovelace, "resource_mode", "yaml"))
    if mode != "storage":
        _LOGGER.info(
            "Lovelace in modalita' '%s': aggiungi manualmente la risorsa %s "
            "(tipo: module) tra le risorse del dashboard.",
            mode, CARD_URL,
        )
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
    except Exception:
        pass

    url_with_version = f"{CARD_URL}?v={version}"

    existing = None
    for item in resources.async_items():
        item_url = item.get("url", "")
        if item_url.split("?")[0] == CARD_URL:
            existing = item
            break

    try:
        if existing is None:
            await resources.async_create_item({"res_type": "module", "url": url_with_version})
            _LOGGER.info("Risorsa Lovelace della card registrata: %s", url_with_version)
        elif existing.get("url") != url_with_version:

            await resources.async_update_item(existing["id"], {"res_type": "module", "url": url_with_version})
            _LOGGER.info("Risorsa Lovelace della card aggiornata: %s", url_with_version)
    except Exception as err:
        _LOGGER.warning("Impossibile registrare la risorsa Lovelace: %s", err)


async def async_setup_panel(hass: HomeAssistant, enabled: bool, title: str) -> None:

    registered = hass.data.get(DOMAIN, {}).get("panel_registered")
    current_title = hass.data.get(DOMAIN, {}).get("panel_title")

    if not enabled:
        if registered:
            await async_remove_panel(hass)
        return

    if registered and current_title == title:
        return

    if registered:
        await async_remove_panel(hass)

    try:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_COMPONENT_NAME,
            module_url=PANEL_URL,
            sidebar_title=title,
            sidebar_icon=PANEL_ICON,
            require_admin=False,
            embed_iframe=False,
        )
        hass.data.setdefault(DOMAIN, {})["panel_registered"] = True
        hass.data[DOMAIN]["panel_title"] = title
        _LOGGER.info("Pannello laterale registrato: %s", title)
    except ValueError:

        hass.data.setdefault(DOMAIN, {})["panel_registered"] = True
        hass.data[DOMAIN]["panel_title"] = title
    except Exception as err:
        _LOGGER.warning("Impossibile registrare il pannello laterale: %s", err)


async def async_remove_panel(hass: HomeAssistant) -> None:

    try:
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
        _LOGGER.info("Pannello laterale rimosso")
    except Exception as err:
        _LOGGER.debug("Rimozione pannello: %s", err)
    if DOMAIN in hass.data:
        hass.data[DOMAIN]["panel_registered"] = False
        hass.data[DOMAIN]["panel_title"] = None
