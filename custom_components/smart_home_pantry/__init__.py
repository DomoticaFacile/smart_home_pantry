# Creato da domoticafacile.it
import logging
import os
from datetime import datetime, date

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components.persistent_notification import (
    async_create as pn_async_create,
    async_dismiss as pn_async_dismiss,
)

from .const import (
    DOMAIN,
    STORAGE_KEY,
    CACHE_STORAGE_KEY,
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
    PERSISTENT_NOTIFICATION_ID,
)
from .api import lookup_openfoodfacts

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    try:
        from .frontend import async_register_card
        version = "0"
        try:
            version = entry.version and str(entry.version) or "0"
        except Exception:
            pass
        integration = hass.data.get("integrations", {}).get(DOMAIN)
        manifest_version = None
        try:
            from homeassistant.loader import async_get_integration
            integ = await async_get_integration(hass, DOMAIN)
            manifest_version = str(integ.version) if integ.version else None
        except Exception:
            manifest_version = None
        await async_register_card(hass, manifest_version or version)
    except Exception as err:
        _LOGGER.warning("Registrazione card frontend non riuscita: %s", err)

    store = Store(hass, 1, STORAGE_KEY)
    data = await store.async_load() or {}

    cache_store = Store(hass, 1, CACHE_STORAGE_KEY)
    barcode_cache = await cache_store.async_load() or {}

    data.setdefault("last_barcode", "")
    data.setdefault("last_product", "")
    data.setdefault("last_brand", "")
    data.setdefault("products_count", 0)
    data.setdefault("unique_products", 0)
    data.setdefault("products", [])

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["data"] = data
    hass.data[DOMAIN]["entities"] = []

    merged={}
    for p in data["products"]:
        k=(p.get("barcode"), p.get("expiry_date"))
        if k not in merged:
            merged[k]=p.copy()
        else:
            merged[k]["quantity"]=merged[k].get("quantity",1)+p.get("quantity",1)
    data["products"]=list(merged.values())
    data["unique_products"]=len(data["products"])
    for p in data["products"]:
        p.setdefault("expiry_date", None)

    data.setdefault("expiring_count", 0)
    data.setdefault("expired_count", 0)
    data.setdefault("next_expiry", "")
    data.setdefault("next_expiry_date", None)
    data.setdefault("expiring_products", [])
    data.setdefault("expired_products", [])
    data.setdefault("last_notified_keys", [])
    data.setdefault("last_lookup", None)
    data.setdefault("card_settings", {})
	

    def update_expiry_stats():

        today = date.today()

        expiring = []
        expired = []

        for prod in data["products"]:

            expiry = prod.get("expiry_date")

            if not expiry:
                continue

            try:
                exp_date = datetime.strptime(
                    expiry,
                    "%Y-%m-%d"
                ).date()

            except Exception:
                continue

            days = (exp_date - today).days

            days_before = entry.options.get(CONF_DAYS_BEFORE, DEFAULT_DAYS_BEFORE)

            if days < 0:
                expired.append(prod)

            elif days <= days_before:
                expiring.append(prod)

        data["expiring_products"] = expiring
        data["expired_products"] = expired

        data["expiring_count"] = sum(
            int(x.get("quantity", 0))
            for x in expiring
        )

        data["expired_count"] = sum(
            int(x.get("quantity", 0))
            for x in expired
        )

        next_expiry = None

        for prod in data["products"]:

            expiry = prod.get("expiry_date")

            if not expiry:
                continue

            try:
                exp_date = datetime.strptime(
                    expiry,
                    "%Y-%m-%d"
                ).date()

            except Exception:
                continue

            if exp_date < today:
                continue

            if next_expiry is None or exp_date < next_expiry:
                next_expiry = exp_date

        if next_expiry:
            data["next_expiry"] = str(next_expiry)
            data["next_expiry_date"] = str(next_expiry)
        else:
            data["next_expiry"] = ""
            data["next_expiry_date"] = None

    def _format_products(prods):
        lines = []
        today = date.today()
        for p in sorted(prods, key=lambda x: x.get("expiry_date") or "9999-12-31"):
            name = p.get("name") or p.get("barcode") or "Prodotto"
            qty = p.get("quantity", 1)
            expiry = p.get("expiry_date")
            if expiry:
                try:
                    exp_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                    days = (exp_date - today).days
                    if days < 0:
                        when = f"scaduto da {abs(days)} giorni"
                    elif days == 0:
                        when = "scade oggi"
                    else:
                        when = f"scade tra {days} giorni"
                except Exception:
                    when = expiry
            else:
                when = "senza data"
            lines.append(f"- {name} (x{qty}) - {when}")
        return lines

    async def check_and_notify():
        options = entry.options

        persistent_enabled = options.get(CONF_PERSISTENT_ENABLED, DEFAULT_PERSISTENT_ENABLED)
        push_enabled = options.get(CONF_PUSH_ENABLED, DEFAULT_PUSH_ENABLED)

        expiring = data.get("expiring_products", [])
        expired = data.get("expired_products", [])
        relevant = expired + expiring

        if persistent_enabled:
            if relevant:
                lines = []
                if expired:
                    lines.append("Scaduti:")
                    lines.extend(_format_products(expired))
                if expiring:
                    lines.append("In scadenza:")
                    lines.extend(_format_products(expiring))

                message = "\n".join(lines)
                pn_async_create(
                    hass,
                    message,
                    title="Prodotti in scadenza - Smart Home Pantry",
                    notification_id=PERSISTENT_NOTIFICATION_ID,
                )
            else:
                pn_async_dismiss(hass, PERSISTENT_NOTIFICATION_ID)

        current_keys = sorted(
            f"{p.get('barcode')}|{p.get('expiry_date')}" for p in relevant
        )
        last_keys = data.get("last_notified_keys", [])

        if push_enabled and relevant and current_keys != last_keys:
            services_raw = options.get(CONF_NOTIFY_SERVICES, DEFAULT_NOTIFY_SERVICES)
            services_list = [s.strip() for s in services_raw.split(",") if s.strip()]

            if not services_list:
                _LOGGER.debug(
                    "Nessun servizio notify configurato per Smart Home Pantry: "
                    "salto la notifica push (configurala in Opzioni)."
                )
            else:
                lines = []
                if expired:
                    lines.extend(_format_products(expired))
                if expiring:
                    lines.extend(_format_products(expiring))
                message = "\n".join(lines[:10])
                if len(lines) > 10:
                    message += f"\n... e altri {len(lines) - 10}"

                for service_name in services_list:
                    if not hass.services.has_service("notify", service_name):
                        _LOGGER.warning(
                            "Servizio notify.%s non trovato: controlla il nome "
                            "nelle opzioni di Smart Home Pantry.",
                            service_name,
                        )
                        continue
                    try:
                        await hass.services.async_call(
                            "notify",
                            service_name,
                            {
                                "title": "Prodotti in scadenza",
                                "message": message,
                                "data": {"tag": PERSISTENT_NOTIFICATION_ID},
                            },
                            blocking=False,
                        )
                    except Exception as err:
                        _LOGGER.warning(
                            "Invio notifica push a notify.%s fallito: %s",
                            service_name,
                            err,
                        )

        data["last_notified_keys"] = current_keys

    async def save_and_refresh():

        update_expiry_stats()

        await store.async_save(data)

        hass.bus.async_fire(
            "smart_home_pantry_updated",
            {"ts": datetime.now().isoformat()}
        )

        try:
            await check_and_notify()
        except Exception as err:
            _LOGGER.exception("Errore invio notifiche scadenza: %s", err)

    async def handle_scan(call):
        barcode = call.data.get("barcode", "")

        cache_size_before = len(barcode_cache)
        info = await lookup_openfoodfacts(barcode, cache=barcode_cache)
        if info is None:
            info = {"barcode": barcode, "name": f"Product {barcode}", "brand": "Unknown"}

        if len(barcode_cache) != cache_size_before:
            await cache_store.async_save(barcode_cache)

        expiry_date = call.data.get("expiry_date")
        now = datetime.now().isoformat()

        data["last_barcode"] = barcode
        data["last_product"] = info["name"]
        data["last_brand"] = info["brand"]
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])

        found = False
        for p in data["products"]:
            if p["barcode"] == barcode and p.get("expiry_date") == expiry_date:
                p["quantity"] = p.get("quantity", 1) + 1
                p["last_scan"] = now
                if expiry_date:
                    p["expiry_date"] = expiry_date
                found = True
                break

        if not found:
            data["products"].append({
                "barcode": barcode,
                "name": info["name"],
                "brand": info["brand"],
                "quantity": 1,
                "added": now,
                "last_scan": now,
                "expiry_date": expiry_date
            })

        data["unique_products"] = len(data["products"])
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])
        await save_and_refresh()

    async def handle_add(call):
        barcode = call.data.get("barcode", "")
        name = call.data.get("name", "Manual Product")
        brand = call.data.get("brand", "")
        expiry_date = call.data.get("expiry_date")
        now = datetime.now().isoformat()

        data["last_barcode"] = barcode
        data["last_product"] = name
        data["last_brand"] = brand
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])

        found = False
        for p in data["products"]:
            if p["barcode"] == barcode and p.get("expiry_date") == expiry_date:
                p["quantity"] = p.get("quantity",1) + 1
                p["last_scan"] = now
                found = True
                break

        if not found:
            data["products"].append({
                "barcode": barcode,
                "name": name,
                "brand": brand,
                "quantity": 1,
                "added": now,
                "last_scan": now,
                "expiry_date": expiry_date
            })

        data["unique_products"] = len(data["products"])
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])
        await save_and_refresh()

    async def handle_remove(call):
        barcode = call.data.get("barcode", "")
        data["products"] = [p for p in data["products"] if p["barcode"] != barcode]
        data["unique_products"] = len(data["products"])
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])
        await save_and_refresh()

    async def handle_update_quantity(call):
        barcode = call.data.get("barcode", "")
        quantity = int(call.data.get("quantity", 1))
        for p in data["products"]:
            if p["barcode"] == barcode:
                p["quantity"] = quantity
                break
        data["products_count"] = sum(int(x.get("quantity",0)) for x in data["products"])
        data["unique_products"] = len(data["products"])
        await save_and_refresh()

    async def handle_update_lot(call):
        barcode = call.data.get("barcode", "")

        old_expiry = call.data.get("old_expiry_date")
        if old_expiry == "":
            old_expiry = None

        has_new_qty = "quantity" in call.data
        new_qty = call.data.get("quantity")
        has_new_expiry = "new_expiry_date" in call.data
        new_expiry = call.data.get("new_expiry_date")
        if new_expiry == "":
            new_expiry = None

        target = None
        for p in data["products"]:
            if p["barcode"] == barcode and p.get("expiry_date") == old_expiry:
                target = p
                break

        if target is None:
            _LOGGER.warning(
                "update_lot: lotto non trovato (barcode=%s, scadenza=%s)",
                barcode, old_expiry,
            )
            return

        if has_new_qty:
            try:
                q = int(new_qty)
            except (TypeError, ValueError):
                q = target.get("quantity", 1)
            if q <= 0:
                data["products"].remove(target)
                target = None
            else:
                target["quantity"] = q

        if target is not None and has_new_expiry and new_expiry != old_expiry:
            merge_into = None
            for p in data["products"]:
                if p is target:
                    continue
                if p["barcode"] == barcode and p.get("expiry_date") == new_expiry:
                    merge_into = p
                    break

            if merge_into is not None:
                merge_into["quantity"] = int(merge_into.get("quantity", 0)) + int(target.get("quantity", 0))
                data["products"].remove(target)
            else:
                target["expiry_date"] = new_expiry

        data["unique_products"] = len(data["products"])
        data["products_count"] = sum(int(x.get("quantity", 0)) for x in data["products"])
        await save_and_refresh()

    async def handle_remove_quantity(call):

        barcode = call.data.get("barcode", "")
        quantity = int(call.data.get("quantity", 1))

        lots = sorted(
            [
                p for p in data["products"]
                if p["barcode"] == barcode
            ],
            key=lambda x: (
                x.get("expiry_date")
                or "9999-12-31"
            )
        )

        remaining = quantity

        for lot in lots:

            if remaining <= 0:
                break

            lot_qty = int(
                lot.get("quantity", 0)
            )

            if lot_qty <= remaining:

                remaining -= lot_qty

                data["products"].remove(lot)

            else:

                lot["quantity"] = (
                    lot_qty - remaining
                )

                remaining = 0

        data["unique_products"] = len(
            data["products"]
        )

        data["products_count"] = sum(
            int(x.get("quantity", 0))
            for x in data["products"]
        )

        await save_and_refresh()

    async def handle_refresh(call):
        await save_and_refresh()

    async def handle_clear(call):
        data["products"] = []
        data["products_count"] = 0
        data["unique_products"] = 0
        data["last_barcode"] = ""
        data["last_product"] = ""
        data["last_brand"] = ""
        await save_and_refresh()

    async def handle_clear_cache(call):
        barcode_cache.clear()
        await cache_store.async_save(barcode_cache)
        _LOGGER.info("Cache lookup Open Food Facts svuotata")

    async def handle_clear_expired(call):
        today = date.today()
        rimasti = []
        rimossi = 0
        for p in data["products"]:
            expiry = p.get("expiry_date")
            scaduto = False
            if expiry:
                try:
                    if datetime.strptime(expiry, "%Y-%m-%d").date() < today:
                        scaduto = True
                except ValueError:
                    scaduto = False
            if scaduto:
                rimossi += int(p.get("quantity", 0))
            else:
                rimasti.append(p)

        data["products"] = rimasti
        data["unique_products"] = len(rimasti)
        data["products_count"] = sum(int(x.get("quantity", 0)) for x in rimasti)
        _LOGGER.info("Rimossi %s pezzi scaduti dalla dispensa", rimossi)
        await save_and_refresh()

    async def handle_export_expired(call):
        from .export import build_xlsx, expired_rows

        filename = str(call.data.get("filename") or "prodotti_scaduti.xlsx").strip()
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        filename = os.path.basename(filename)

        www_dir = hass.config.path("www")
        target = os.path.join(www_dir, filename)

        products = data.get("expired_products", [])

        def _write():
            os.makedirs(www_dir, exist_ok=True)
            rows = expired_rows(products, date.today())
            content = build_xlsx(rows)
            with open(target, "wb") as f:
                f.write(content)
            return len(products)

        try:
            n = await hass.async_add_executor_job(_write)
            _LOGGER.info(
                "Export scaduti salvato: %s (%s prodotti) - scaricabile da /local/%s",
                target, n, filename,
            )
        except Exception as err:
            _LOGGER.error("Errore durante l'export dei prodotti scaduti: %s", err)

    async def handle_lookup_barcode(call):
        barcode = str(call.data.get("barcode", "")).strip()
        request_id = call.data.get("request_id")

        name = None
        found = False
        if barcode:
            cache_size_before = len(barcode_cache)
            info = await lookup_openfoodfacts(barcode, cache=barcode_cache)
            if len(barcode_cache) != cache_size_before:
                await cache_store.async_save(barcode_cache)
            if info and info.get("name") and info["name"] != "Unknown":
                name = info["name"]
                found = True

        data["last_lookup"] = {
            "request_id": request_id,
            "barcode": barcode,
            "name": name,
            "found": found,
        }

        hass.bus.async_fire(
            "smart_home_pantry_updated",
            {"ts": datetime.now().isoformat()},
        )

    def _parse_notify_time(value):
        parts = value.split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            return h, m, s
        except Exception:
            return 9, 0, 0

    async def _scheduled_check(now):
        try:
            await check_and_notify()
        except Exception as err:
            _LOGGER.exception("Errore controllo scadenze pianificato: %s", err)

    def _schedule_daily_check():
        old_unsub = hass.data[DOMAIN].get("unsub_time_change")
        if old_unsub:
            old_unsub()

        notify_time = entry.options.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME)
        h, m, s = _parse_notify_time(notify_time)

        hass.data[DOMAIN]["unsub_time_change"] = async_track_time_change(
            hass, _scheduled_check, hour=h, minute=m, second=s
        )

    def _sidebar_title():
        opts = entry.options
        titolo = opts.get(CONF_SIDEBAR_TITLE)
        if not titolo:
            titolo = opts.get(LEGACY_CONF_CARD_TITLE)
        titolo = str(titolo or "").strip()
        return titolo or DEFAULT_SIDEBAR_TITLE

    async def _sync_panel():
        from .frontend import async_setup_panel
        abilitato = bool(entry.options.get(CONF_SIDEBAR_ENABLED, DEFAULT_SIDEBAR_ENABLED))
        await async_setup_panel(hass, abilitato, _sidebar_title())

    def _update_card_settings():
        opts = entry.options
        data["card_settings"] = {
            "days_before": int(opts.get(CONF_DAYS_BEFORE, DEFAULT_DAYS_BEFORE)),
            "days_critical": int(opts.get(CONF_DAYS_CRITICAL, DEFAULT_DAYS_CRITICAL)),
            "date_format": opts.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT),
            "next_expiry_within": int(opts.get(CONF_NEXT_EXPIRY_WITHIN, DEFAULT_NEXT_EXPIRY_WITHIN)),
            "expired_within": int(opts.get(CONF_EXPIRED_WITHIN, DEFAULT_EXPIRED_WITHIN)),
            "sort_order": opts.get(CONF_SORT_ORDER, DEFAULT_SORT_ORDER),
        }

    async def _options_updated(hass, updated_entry):
        _update_card_settings()
        await _sync_panel()
        _schedule_daily_check()
        update_expiry_stats()
        await store.async_save(data)
        hass.bus.async_fire(
            "smart_home_pantry_updated",
            {"ts": datetime.now().isoformat()},
        )
        await check_and_notify()

    _update_card_settings()
    await _sync_panel()
    _schedule_daily_check()
    hass.data[DOMAIN]["unsub_options_update"] = entry.add_update_listener(_options_updated)

    update_expiry_stats()
    try:
        await check_and_notify()
    except Exception as err:
        _LOGGER.exception("Errore controllo scadenze all'avvio: %s", err)

    services = hass.services
    if not services.has_service(DOMAIN, "scan_barcode"):
        services.async_register(DOMAIN, "scan_barcode", handle_scan)
    if not services.has_service(DOMAIN, "add_product"):
        services.async_register(DOMAIN, "add_product", handle_add)
    if not services.has_service(DOMAIN, "remove_product"):
        services.async_register(DOMAIN, "remove_product", handle_remove)
    services.async_register(DOMAIN, "refresh", handle_refresh)
    services.async_register(DOMAIN, "remove_quantity", handle_remove_quantity)
    if not services.has_service(DOMAIN, "clear_pantry"):
        services.async_register(DOMAIN, "clear_pantry", handle_clear)
    if not services.has_service(DOMAIN, "update_quantity"):
        services.async_register(DOMAIN, "update_quantity", handle_update_quantity)
    services.async_register(DOMAIN, "update_lot", handle_update_lot)
    services.async_register(DOMAIN, "clear_cache", handle_clear_cache)
    services.async_register(DOMAIN, "lookup_barcode", handle_lookup_barcode)
    services.async_register(DOMAIN, "clear_expired", handle_clear_expired)
    services.async_register(DOMAIN, "export_expired", handle_export_expired)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    domain_data = hass.data.get(DOMAIN, {})

    unsub_time_change = domain_data.pop("unsub_time_change", None)
    if unsub_time_change:
        unsub_time_change()

    unsub_options_update = domain_data.pop("unsub_options_update", None)
    if unsub_options_update:
        unsub_options_update()

    if domain_data.get("panel_registered"):
        from .frontend import async_remove_panel
        await async_remove_panel(hass)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
