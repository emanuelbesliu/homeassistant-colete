"""Constants for the Colete (Romanian Parcel Tracking) integration."""

DOMAIN = "colete"
PLATFORMS = ["sensor"]

# Configuration keys
CONF_COURIER = "courier"
CONF_AWB = "awb"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_UPDATE_INTERVAL = "update_interval"

# Defaults
DEFAULT_UPDATE_INTERVAL = 900  # 15 minutes in seconds
MIN_UPDATE_INTERVAL = 300  # 5 minutes
MAX_UPDATE_INTERVAL = 3600  # 1 hour

# Auto-archive: delivered parcels are removed after this many days
AUTO_ARCHIVE_DAYS = 30

# Supported couriers
COURIER_AUTO = "auto"
COURIER_SAMEDAY = "sameday"
COURIER_FAN = "fan_courier"

COURIERS = {
    COURIER_AUTO: "Auto-detect",
    COURIER_SAMEDAY: "Sameday",
    COURIER_FAN: "FAN Courier",
}

# Courier detection order (tried sequentially when auto-detect is used)
COURIER_DETECT_ORDER = [COURIER_SAMEDAY, COURIER_FAN]

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

# FAN Courier status codes
# C0 = picked up, H4 = sorting/in transit, C1 = out for delivery,
# S1 = delivering, S2 = delivered
FAN_STATUS_PICKED_UP = "C0"
FAN_STATUS_IN_TRANSIT = "H4"
FAN_STATUS_OUT_FOR_DELIVERY = "C1"
FAN_STATUS_DELIVERING = "S1"
FAN_STATUS_DELIVERED = "S2"

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
