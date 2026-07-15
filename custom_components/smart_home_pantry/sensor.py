# Creato da domoticafacile.it

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from .const import DOMAIN

UPDATE_EVENT = "smart_home_pantry_updated"

SENSORS = [
("last_barcode","Last Barcode"),
("last_product","Last Product"),
("last_brand","Last Brand"),
("products_count","Products Count"),
("unique_products","Unique Products"),
("pantry","Smart Home Pantry"),
("expiring","Expiring Products"),
("expired","Expired Products"),
("next_expiry","Next Expiry"),
]

async def async_setup_entry(hass, entry, async_add_entities):
    entities=[PantrySensor(hass,k,n) for k,n in SENSORS]
    hass.data[DOMAIN]["entities"] = list(entities)
    async_add_entities(entities)

class PantrySensor(SensorEntity):

    _attr_should_poll = False

    def __init__(self,hass,key,name):
        self.hass=hass
        self._key=key
        self._attr_name=name
        self._attr_unique_id=f"smart_home_pantry_{key}"

    async def async_added_to_hass(self):

        self.async_on_remove(
            self.hass.bus.async_listen(UPDATE_EVENT, self._handle_update)
        )

    @callback
    def _handle_update(self, event):
        self.async_write_ha_state()

    @property
    def native_value(self):
        if self._key == "pantry":
            return self.hass.data[DOMAIN]["data"].get("products_count",0)

        if self._key=="expiring":
            return self.hass.data[DOMAIN]["data"].get("expiring_count",0)

        if self._key=="expired":
            return self.hass.data[DOMAIN]["data"].get("expired_count",0)

        return self.hass.data[DOMAIN]["data"].get(self._key)

    @property
    def extra_state_attributes(self):
        data = self.hass.data[DOMAIN]["data"]

        def copy_products(items):
            return [dict(p) for p in items]

        if self._key == "pantry":
            return {
                "unique_products": data.get("unique_products", 0),
                "products": copy_products(data.get("products", [])),
                "lookup": dict(data["last_lookup"]) if data.get("last_lookup") else None,
                "settings": dict(data.get("card_settings", {}))
            }

        if self._key == "expiring":
            return {
                "products": copy_products(data.get("expiring_products", []))
            }

        if self._key == "expired":
            return {
                "products": copy_products(data.get("expired_products", []))
            }

        if self._key == "next_expiry":
            return {
                "next_expiry_date": data.get("next_expiry_date")
            }

        return None
