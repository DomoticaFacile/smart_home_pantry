# Creato da domoticafacile.it

import asyncio
import logging
import time

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=product_name,brands"

USER_AGENT = "SmartHomePantry-HomeAssistant/0.2.2"

CACHE_TTL_SECONDS = 60 * 60 * 24 * 30

async def lookup_openfoodfacts(barcode, cache=None):

    barcode = str(barcode or "").strip()
    if not barcode:
        return None

    if cache is not None:
        entry = cache.get(barcode)
        if entry:
            ts = entry.get("ts", 0)
            if (time.time() - ts) < CACHE_TTL_SECONDS:
                result = entry.get("result")

                return dict(result) if result else None

            cache.pop(barcode, None)

    url = BASE_URL.format(barcode=barcode)
    headers = {"User-Agent": USER_AGENT}
    result = None
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    if payload.get("status") == 1:
                        product = payload.get("product", {}) or {}
                        result = {
                            "barcode": barcode,
                            "name": product.get("product_name") or "Unknown",
                            "brand": product.get("brands") or "",
                        }
                    else:

                        result = None
                else:
                    _LOGGER.debug(
                        "Open Food Facts ha risposto %s per il barcode %s",
                        resp.status, barcode,
                    )

                    return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.debug("Errore lookup Open Food Facts per %s: %s", barcode, err)

        return None
    except Exception as err:
        _LOGGER.debug("Errore inatteso lookup %s: %s", barcode, err)
        return None

    if cache is not None:
        cache[barcode] = {"ts": time.time(), "result": result}

    return dict(result) if result else None
