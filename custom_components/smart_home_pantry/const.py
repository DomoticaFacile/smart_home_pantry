# Creato da domoticafacile.it

DOMAIN="smart_home_pantry"
STORAGE_KEY="smart_home_pantry"
CACHE_STORAGE_KEY="smart_home_pantry_cache"

CARD_FILENAME = "smart-home-pantry-card.js"
URL_BASE = "/smart_home_pantry"
CARD_URL = f"{URL_BASE}/{CARD_FILENAME}"
EXPORT_URL = f"{URL_BASE}/export_expired.xlsx"

PANEL_FILENAME = "smart-home-pantry-panel.js"
PANEL_URL = f"{URL_BASE}/{PANEL_FILENAME}"
PANEL_URL_PATH = "smart-home-pantry"
PANEL_COMPONENT_NAME = "smart-home-pantry-panel"
PANEL_ICON = "mdi:fridge"

CONF_DAYS_BEFORE = "days_before"
CONF_NOTIFY_TIME = "notify_time"
CONF_NOTIFY_SERVICES = "notify_services"
CONF_PERSISTENT_ENABLED = "persistent_enabled"
CONF_PUSH_ENABLED = "push_enabled"

# Opzioni di visualizzazione della card
CONF_DATE_FORMAT = "date_format"
CONF_DAYS_CRITICAL = "days_critical"
CONF_SIDEBAR_ENABLED = "sidebar_enabled"
CONF_SIDEBAR_TITLE = "sidebar_title"
CONF_NEXT_EXPIRY_WITHIN = "next_expiry_within"
CONF_EXPIRED_WITHIN = "expired_within"
CONF_SORT_ORDER = "sort_order"

DEFAULT_DAYS_BEFORE = 7
DEFAULT_NOTIFY_TIME = "09:00:00"
DEFAULT_NOTIFY_SERVICES = ""
DEFAULT_PERSISTENT_ENABLED = True
DEFAULT_PUSH_ENABLED = True

DEFAULT_DATE_FORMAT = "dd/mm/yyyy"
DEFAULT_DAYS_CRITICAL = 2
DEFAULT_SIDEBAR_ENABLED = False
DEFAULT_SIDEBAR_TITLE = "Smart Home Pantry"
DEFAULT_NEXT_EXPIRY_WITHIN = 30
DEFAULT_EXPIRED_WITHIN = 30
DEFAULT_SORT_ORDER = "expiry"

DATE_FORMATS = ["dd/mm/yyyy", "yyyy-mm-dd", "mm/dd/yyyy", "relative"]


SORT_ORDERS = [
    "expiry",
    "expiry_valid",
    "alphabetical",
    "quantity_asc",
    "quantity_desc",
]

LEGACY_CONF_CARD_TITLE = "card_title"

PERSISTENT_NOTIFICATION_ID = "smart_home_pantry_expiring"
