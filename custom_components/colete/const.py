"""Constants for the Colete (Romanian Parcel Tracking) integration."""

DOMAIN = "colete"
PLATFORMS = ["sensor"]

# ── Entry type discriminator ──────────────────────────────────────────────────
# Existing parcel entries don't have this key (implicitly "parcel").
# IMAP scanner entries store CONF_ENTRY_TYPE = ENTRY_TYPE_IMAP.
CONF_ENTRY_TYPE = "entry_type"
ENTRY_TYPE_PARCEL = "parcel"
ENTRY_TYPE_IMAP = "imap"

# ── Parcel configuration keys ────────────────────────────────────────────────
CONF_COURIER = "courier"
CONF_AWB = "awb"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_RETENTION_DAYS = "retention_days"

# Defaults
DEFAULT_UPDATE_INTERVAL = 900  # 15 minutes in seconds
MIN_UPDATE_INTERVAL = 300  # 5 minutes
MAX_UPDATE_INTERVAL = 3600  # 1 hour

# Retention: delivered parcels are removed after this many days (0 = keep forever)
DEFAULT_RETENTION_DAYS = 30
MIN_RETENTION_DAYS = 0
MAX_RETENTION_DAYS = 365

# ── IMAP configuration keys ─────────────────────────────────────────────────
CONF_IMAP_SERVER = "imap_server"
CONF_IMAP_PORT = "imap_port"
CONF_IMAP_EMAIL = "imap_email"
CONF_IMAP_PASSWORD = "imap_password"
CONF_IMAP_FOLDER = "imap_folder"
CONF_IMAP_LOOKBACK_DAYS = "imap_lookback_days"
CONF_IMAP_SCAN_INTERVAL = "imap_scan_interval"

# IMAP defaults
DEFAULT_IMAP_PORT = 993
DEFAULT_IMAP_FOLDER = "INBOX"
DEFAULT_IMAP_LOOKBACK_DAYS = 7
MIN_IMAP_LOOKBACK_DAYS = 1
MAX_IMAP_LOOKBACK_DAYS = 90
DEFAULT_IMAP_SCAN_INTERVAL = 300  # 5 minutes
MIN_IMAP_SCAN_INTERVAL = 60  # 1 minute
MAX_IMAP_SCAN_INTERVAL = 3600  # 1 hour

# IMAP persistent storage (for dedup — remember AWBs we already processed)
IMAP_STORAGE_KEY = "colete_imap_seen_awbs"
IMAP_STORAGE_VERSION = 1

# ── AWB extraction patterns ──────────────────────────────────────────────────
# Primary strategy: look for numeric sequences near Romanian shipping keywords.
# These patterns work regardless of sender (shop emails, courier emails, etc.).
#
# AWB_KEYWORD_PATTERNS: compiled against email body text. Each pattern should
# have a named group "awb" capturing the tracking number.
# Checked in order; first match wins per region of text.
AWB_KEYWORD_PATTERNS = [
    # "AWB: 1234567890" / "AWB 1234567890" / "AWB #1234567890" / "AWB:1234567890"
    r"(?i)\bAWB[\s:#]*(?P<awb>\d{8,20})\b",
    # "numar de urmarire: 1234567890" / "numar urmarire 1234567890"
    r"(?i)\bnuma[a-z]*\s+(?:de\s+)?urmarire[\s:#]*(?P<awb>\d{8,20})\b",
    # "tracking: 1234567890" / "tracking number: 1234567890"
    r"(?i)\btracking[\s\w]*[\s:#]*(?P<awb>\d{8,20})\b",
    # "colet: 1234567890" / "coletul 1234567890"
    r"(?i)\bcolet(?:ul)?[\s:#]*(?P<awb>\d{8,20})\b",
    # "expediere: 1234567890" / "expedierea: 1234567890"
    r"(?i)\bexpediere(?:a)?[\s:#]*(?P<awb>\d{8,20})\b",
    # "livrare: 1234567890" / "livrarea: 1234567890"
    r"(?i)\blivrare(?:a)?[\s:#]*(?P<awb>\d{8,20})\b",
]

# Courier sender domain hints — if the email comes from one of these domains,
# we can skip auto-detect and go straight to the right courier.
# This is an optimization only; AWB extraction does NOT depend on sender.
COURIER_SENDER_HINTS: dict[str, str] = {
    "sameday.ro": "sameday",
    "sameday.com": "sameday",
    "fancourier.ro": "fan_courier",
    "fan-courier.ro": "fan_courier",
    "cargus.ro": "cargus",
    "gls-romania.ro": "gls",
    "gls-group.eu": "gls",
    "dpd.ro": "dpd",
    "dpd.com": "dpd",
}

# IMAP sensor types
SENSOR_TYPE_IMAP_STATUS = "imap_status"
SENSOR_TYPE_IMAP_LAST_SCAN = "imap_last_scan"
SENSOR_TYPE_IMAP_AWBS_FOUND = "imap_awbs_found"

IMAP_SENSOR_TYPES = {
    SENSOR_TYPE_IMAP_STATUS: {
        "name": "Scanner Status",
        "icon": "mdi:email-search-outline",
    },
    SENSOR_TYPE_IMAP_LAST_SCAN: {
        "name": "Last Scan",
        "icon": "mdi:clock-outline",
    },
    SENSOR_TYPE_IMAP_AWBS_FOUND: {
        "name": "AWBs Found",
        "icon": "mdi:package-variant-closed-plus",
    },
}

# Supported couriers
COURIER_AUTO = "auto"
COURIER_SAMEDAY = "sameday"
COURIER_FAN = "fan_courier"
COURIER_CARGUS = "cargus"
COURIER_GLS = "gls"
COURIER_DPD = "dpd"

COURIERS = {
    COURIER_AUTO: "Auto-detect",
    COURIER_SAMEDAY: "Sameday",
    COURIER_FAN: "FAN Courier",
    COURIER_CARGUS: "Cargus",
    COURIER_GLS: "GLS",
    COURIER_DPD: "DPD",
}

# Courier detection order (tried sequentially when auto-detect is used)
COURIER_DETECT_ORDER = [
    COURIER_SAMEDAY,
    COURIER_FAN,
    COURIER_CARGUS,
    COURIER_GLS,
    COURIER_DPD,
]

# Sameday API
SAMEDAY_API_URL = "https://api.sameday.ro/api/public/awb/{awb}/awb-history"

# Sameday statusStateId values (from real API response awbHistory[].statusStateId)
# These are integers used to determine normalized parcel status.
SAMEDAY_STATE_REGISTERED = 1
SAMEDAY_STATE_PICKED_UP = 2
SAMEDAY_STATE_OUT_FOR_DELIVERY = 4
SAMEDAY_STATE_DELIVERED = 5
SAMEDAY_STATE_IN_TRANSIT = 7
SAMEDAY_STATE_CENTRAL_DEPOT = 17
SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT = 18

# Returned/canceled are inferred from statusId or status text (no dedicated statusStateId)
# Common statusId values:
# 1 = awaiting pickup, 4 = picked up, 9 = delivered, 23 = registered,
# 33 = out for delivery, 56 = in transit, 78 = loaded at delivery point,
# 84 = central depot

# FAN Courier API
FAN_API_URL = "https://www.fancourier.ro/limit-tracking.php"

# FAN Courier status codes (from real API event id values)
# C0 = picked up, H0 = in transit to destination depot, H4 = sorting/in transit,
# C1 = out for delivery, S1 = delivering, S2 = delivered
FAN_STATUS_PICKED_UP = "C0"
FAN_STATUS_IN_TRANSIT = "H0"
FAN_STATUS_IN_TRANSIT_SORTING = "H4"
FAN_STATUS_OUT_FOR_DELIVERY = "C1"
FAN_STATUS_DELIVERING = "S1"
FAN_STATUS_DELIVERED = "S2"

# All FAN status codes that indicate in-transit state
FAN_IN_TRANSIT_CODES = {FAN_STATUS_IN_TRANSIT, FAN_STATUS_IN_TRANSIT_SORTING}

# Cargus tracking (HTML scraping — no public JSON API exists)
CARGUS_TRACKING_URL = (
    "https://www.cargus.ro/personal/urmareste-coletul/?tracking_number={awb}"
)

# Cargus status string mappings are defined below (after STATUS_* constants)

# GLS Romania API (public endpoint, no authentication required)
GLS_API_URL = (
    "https://gls-group.eu/app/service/open/rest/RO/ro/rstt029"
    "?match={awb}&type=&caller=witt002&millis={millis}"
)

# DPD Romania API (via DPD Germany tracking REST API — works for Romanian parcels)
# No authentication required. Supports locale parameter for Romanian translations.
DPD_API_URL = "https://tracking.dpd.de/rest/plc/ro_RO/{awb}"

# Normalized parcel statuses (courier-agnostic)
STATUS_UNKNOWN = "unknown"
STATUS_PICKED_UP = "picked_up"
STATUS_IN_TRANSIT = "in_transit"
STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
STATUS_READY_FOR_PICKUP = "ready_for_pickup"
STATUS_DELIVERED = "delivered"
STATUS_RETURNED = "returned"
STATUS_CANCELED = "canceled"

# Human-readable status labels
STATUS_LABELS = {
    STATUS_UNKNOWN: "Unknown",
    STATUS_PICKED_UP: "Picked Up",
    STATUS_IN_TRANSIT: "In Transit",
    STATUS_OUT_FOR_DELIVERY: "Out for Delivery",
    STATUS_READY_FOR_PICKUP: "Ready for Pickup",
    STATUS_DELIVERED: "Delivered",
    STATUS_RETURNED: "Returned",
    STATUS_CANCELED: "Canceled",
}

# Cargus status string mappings (Romanian status text from HTML → normalized status)
# The tracking page returns a single current status string in Romanian.
# Keys are lowercase substrings matched against the status text (checked in order,
# longer/more specific strings first to avoid false matches).
CARGUS_STATUS_MAP = [
    ("livrat la destinatar", STATUS_DELIVERED),
    ("livrat", STATUS_DELIVERED),
    ("in curs de livrare", STATUS_OUT_FOR_DELIVERY),
    ("disponibil pentru ridicare", STATUS_READY_FOR_PICKUP),
    ("easybox", STATUS_READY_FOR_PICKUP),
    ("locker", STATUS_READY_FOR_PICKUP),
    ("in tranzit", STATUS_IN_TRANSIT),
    ("depozitat", STATUS_IN_TRANSIT),
    ("preluat", STATUS_PICKED_UP),
    ("ridicat", STATUS_PICKED_UP),
    ("inregistrat", STATUS_PICKED_UP),
    ("returnat", STATUS_RETURNED),
    ("retur", STATUS_RETURNED),
    ("anulat", STATUS_CANCELED),
]

# GLS progressBar.statusInfo → normalized status mapping
# These values come from the GLS tracking widget JavaScript source.
GLS_STATUS_MAP = {
    "PREADVICE": STATUS_PICKED_UP,
    "INTRANSIT": STATUS_IN_TRANSIT,
    "INWAREHOUSE": STATUS_IN_TRANSIT,
    "INDELIVERY": STATUS_OUT_FOR_DELIVERY,
    "DELIVERED": STATUS_DELIVERED,
    "DELIVEREDPS": STATUS_READY_FOR_PICKUP,
    "NOTDELIVERED": STATUS_IN_TRANSIT,
    "CANCELLED": STATUS_CANCELED,
}

# DPD statusInfo[].status → normalized status mapping
# The API returns 5 stages as a progress bar (ACCEPTED → DELIVERED).
# The entry with isCurrentStatus=True indicates the current stage.
DPD_STATUS_MAP = {
    "ACCEPTED": STATUS_PICKED_UP,
    "ON_THE_ROAD": STATUS_IN_TRANSIT,
    "AT_DELIVERY_DEPOT": STATUS_IN_TRANSIT,
    "OUT_FOR_DELIVERY": STATUS_OUT_FOR_DELIVERY,
    "DELIVERED": STATUS_DELIVERED,
}

# DPD scan type codes (from scanInfo.scan[].scanData.scanType.code)
# Used to extract detailed event info from scan history.
DPD_SCAN_DELIVERED = "13"  # Delivery event
DPD_SCAN_NOT_DELIVERED = "14"  # Not delivered / exception
DPD_SCAN_PICKUP = "15"  # Pickup event
DPD_SCAN_STORE_DROPOFF = "23"  # Parcel shop / locker delivery

# DPD additional codes for scan events
DPD_ADDITIONAL_PARCELSHOP = "091"  # Redirected to parcel shop

# Locker/Easybox detection keywords (case-insensitive matching on status text)
# Sameday uses "easybox" in status labels when parcel is deposited in a locker
SAMEDAY_LOCKER_KEYWORDS = [
    "easybox",
    "locker",
    "disponibil in easybox",
    "disponibil pentru ridicare",
    "depozitat in easybox",
]

# FAN Courier locker detection keywords (in event name field)
FAN_LOCKER_KEYWORDS = [
    "fanbox",
    "easybox",
    "locker",
    "automat de colete",
    "disponibil pentru ridicare",
]

# Sensor type definitions
SENSOR_TYPE_STATUS = "status"
SENSOR_TYPE_LOCATION = "location"
SENSOR_TYPE_LAST_UPDATE = "last_update"
SENSOR_TYPE_DELIVERY = "delivery"

SENSOR_TYPES = {
    SENSOR_TYPE_STATUS: {
        "name": "Status",
        "icon": "mdi:package-variant",
    },
    SENSOR_TYPE_LOCATION: {
        "name": "Location",
        "icon": "mdi:map-marker",
    },
    SENSOR_TYPE_LAST_UPDATE: {
        "name": "Last Update",
        "icon": "mdi:clock-outline",
    },
    SENSOR_TYPE_DELIVERY: {
        "name": "Delivery",
        "icon": "mdi:package-check",
    },
}
