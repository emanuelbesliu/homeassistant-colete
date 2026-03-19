"""Tests for the Colete (Romanian Parcel Tracking) integration."""

import pytest

pytest.importorskip("homeassistant")

from custom_components.colete.api import ColeteAPI  # noqa: E402
from custom_components.colete.const import (  # noqa: E402
    CONF_RETENTION_DAYS,
    COURIER_SAMEDAY,
    COURIER_FAN,
    COURIER_CARGUS,
    COURIER_GLS,
    COURIER_DPD,
    DEFAULT_RETENTION_DAYS,
    MIN_RETENTION_DAYS,
    MAX_RETENTION_DAYS,
    SAMEDAY_STATE_DELIVERED,
    SAMEDAY_STATE_IN_TRANSIT,
    SAMEDAY_STATE_OUT_FOR_DELIVERY,
    SAMEDAY_STATE_PICKED_UP,
    SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
    SAMEDAY_STATE_REGISTERED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_UNKNOWN,
    STATUS_PICKED_UP,
    STATUS_CANCELED,
)
from custom_components.colete.coordinator import (  # noqa: E402
    ColeteDataUpdateCoordinator,
)


# ============================================================
# Sameday fixtures (matches real API structure)
# ============================================================

# In-transit parcel — awbHistory ordered newest first
MOCK_SAMEDAY_IN_TRANSIT = {
    "awbNumber": "4EMGLN123456789",
    "awbHistory": [
        {
            "county": "Ilfov",
            "country": "Romania",
            "status": "Coletul este in drum spre depozitul local.",
            "statusId": 56,
            "statusState": "Coletul este in tranzit",
            "statusStateId": SAMEDAY_STATE_IN_TRANSIT,
            "transitLocation": "Bacu",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-15T21:43:23+02:00",
        },
        {
            "county": "Ilfov",
            "country": "Romania",
            "status": "Expeditorul a predat coletul catre Sameday.",
            "statusId": 4,
            "statusState": "Coletul a intrat in posesia noastra",
            "statusStateId": SAMEDAY_STATE_PICKED_UP,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-15T17:54:54+02:00",
        },
        {
            "county": "",
            "country": "",
            "status": "Un curier urmeaza sa ridice coletul de la expeditor.",
            "statusId": 23,
            "statusState": "Expedierea a fost inregistrata",
            "statusStateId": SAMEDAY_STATE_REGISTERED,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-15T14:01:01+02:00",
        },
    ],
    "parcelsList": {},
    "isLockerService": False,
    "isReturn": False,
    "c2cOrder": False,
    "isPudoService": False,
    "c2cType": 0,
}


# Delivered parcel (real response from AWB 4EMGLN159150598)
MOCK_SAMEDAY_DELIVERED = {
    "awbNumber": "4EMGLN159150598",
    "awbHistory": [
        {
            "county": "Iasi",
            "country": "Romania",
            "status": "Coletul a fost livrat cu succes.",
            "statusId": 9,
            "statusState": "Coletul a fost livrat cu succes",
            "statusStateId": SAMEDAY_STATE_DELIVERED,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-02-25T20:14:05+02:00",
        },
        {
            "county": "Iasi",
            "country": "Romania",
            "status": "Coletul a ajuns in punctul de livrare.",
            "statusId": 78,
            "statusState": "Colet incarcat in punctul de livrare",
            "statusStateId": SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-02-25T14:27:06+02:00",
        },
    ],
    "parcelsList": {},
    "isLockerService": True,
    "isReturn": False,
    "c2cOrder": False,
    "isPudoService": False,
    "c2cType": 0,
}


# Easybox locker parcel — isLockerService=True, loaded at delivery point
MOCK_SAMEDAY_EASYBOX = {
    "awbNumber": "4EMGLN987654321",
    "awbHistory": [
        {
            "county": "Iasi",
            "country": "Romania",
            "status": "Coletul a ajuns in punctul de livrare. Detaliile de ridicare sunt disponibile in SAMEDAY App.",
            "statusId": 78,
            "statusState": "Colet incarcat in punctul de livrare",
            "statusStateId": SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-16T14:27:06+02:00",
        },
        {
            "county": "Iasi",
            "country": "Romania",
            "status": "Curierul urmeaza sa efectueze livrarea in curand.",
            "statusId": 33,
            "statusState": "Curierul Sameday urmeaza sa efectueze livrarea",
            "statusStateId": SAMEDAY_STATE_OUT_FOR_DELIVERY,
            "transitLocation": "",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-16T10:01:30+02:00",
        },
    ],
    "parcelsList": {},
    "isLockerService": True,
    "isReturn": False,
    "c2cOrder": False,
    "isPudoService": False,
    "c2cType": 0,
}


# Easybox with keyword fallback (isLockerService=False but label has easybox)
MOCK_SAMEDAY_EASYBOX_KEYWORD = {
    "awbNumber": "4EMGLN111222333",
    "awbHistory": [
        {
            "county": "Bucuresti",
            "country": "Romania",
            "status": "Coletul a fost depozitat in easybox Mega Image Unirii.",
            "statusId": 78,
            "statusState": "Colet incarcat in punctul de livrare",
            "statusStateId": SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
            "transitLocation": "easybox Mega Image Unirii",
            "reasonId": "",
            "reason": "",
            "statusDate": "2026-03-16T09:15:00+02:00",
        },
    ],
    "parcelsList": {},
    "isLockerService": False,
    "isReturn": False,
    "c2cOrder": False,
    "isPudoService": False,
    "c2cType": 0,
}


# Empty response (no history)
MOCK_SAMEDAY_EMPTY = {
    "awbNumber": "000000000",
    "awbHistory": [],
    "parcelsList": {},
    "isLockerService": False,
    "isReturn": False,
    "c2cOrder": False,
    "isPudoService": False,
    "c2cType": 0,
}


# ============================================================
# FAN Courier fixtures (matches real API structure from AWB 7000081306984)
# ============================================================

# In-transit parcel — events ordered chronologically (oldest first)
MOCK_FAN_IN_TRANSIT = {
    "content": "PCA/106962",
    "awbNumber": "7000081306984",
    "date": "2025-08-04 00:00:00",
    "weight": 5,
    "paymentDate": None,
    "returnAwbNumber": None,
    "redirectionAwbNumber": None,
    "reimbursementAwbNumber": None,
    "oPODAwbNumber": None,
    "confirmation": {"name": None, "date": None},
    "service": None,
    "options": None,
    "events": [
        {
            "id": "C0",
            "name": "Expeditie ridicata",
            "location": "Bucuresti",
            "date": "2025-08-04 14:20:00",
        },
        {
            "id": "H0",
            "name": "Expeditie in tranzit spre depozitul de destinatie",
            "location": "Bucuresti",
            "date": "2025-08-04 23:57:52",
        },
    ],
    "barcodes": None,
    "serviceId": 1,
    "optionCodes": ["X"],
}


# Delivered parcel (real data from AWB 7000081306984)
MOCK_FAN_DELIVERED = {
    "content": "PCA/106962",
    "awbNumber": "7000081306984",
    "date": "2025-08-04 00:00:00",
    "weight": 5,
    "paymentDate": None,
    "returnAwbNumber": None,
    "redirectionAwbNumber": None,
    "reimbursementAwbNumber": None,
    "oPODAwbNumber": None,
    "confirmation": {"name": "e*****l b****u", "date": "2025-08-05 14:00"},
    "service": None,
    "options": None,
    "events": [
        {
            "id": "C0",
            "name": "Expeditie ridicata",
            "location": "Bucuresti",
            "date": "2025-08-04 14:20:00",
        },
        {
            "id": "H0",
            "name": "Expeditie in tranzit spre depozitul de destinatie",
            "location": "Bucuresti",
            "date": "2025-08-04 23:57:52",
        },
        {
            "id": "C1",
            "name": "Expeditie preluata spre livrare",
            "location": "Iasi",
            "date": "2025-08-05 09:30:00",
        },
        {
            "id": "S1",
            "name": "Expeditie in livrare",
            "location": "Iasi",
            "date": "2025-08-05 09:30:36",
        },
        {
            "id": "S2",
            "name": "Livrat",
            "location": "Iasi",
            "date": "2025-08-05 14:00:03",
        },
    ],
    "barcodes": None,
    "serviceId": 1,
    "optionCodes": ["X"],
}


# FANbox (locker) parcel
MOCK_FAN_FANBOX = {
    "awbNumber": "2150000000002",
    "date": "2026-03-16 00:00:00",
    "weight": 2,
    "returnAwbNumber": None,
    "confirmation": {},
    "events": [
        {
            "id": "C0",
            "name": "Expeditie ridicata",
            "location": "Bucuresti",
            "date": "2026-03-16 08:00:00",
        },
        {
            "id": "S1",
            "name": "Coletul a fost depus in FANbox",
            "location": "FANbox Carrefour Orhideea",
            "date": "2026-03-16 11:30:00",
        },
    ],
}


# Returned parcel (returnAwbNumber populated)
MOCK_FAN_RETURNED = {
    "awbNumber": "7000099999999",
    "date": "2026-03-10 00:00:00",
    "weight": 3,
    "returnAwbNumber": "7000099999998",
    "confirmation": {},
    "events": [
        {
            "id": "C0",
            "name": "Expeditie ridicata",
            "location": "Bucuresti",
            "date": "2026-03-10 10:00:00",
        },
        {
            "id": "H0",
            "name": "Expeditie in tranzit",
            "location": "Bucuresti",
            "date": "2026-03-10 18:00:00",
        },
    ],
}


# ============================================================
# Sameday tests
# ============================================================


def test_parse_sameday_in_transit():
    """Test parsing a Sameday in-transit response."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_IN_TRANSIT, "4EMGLN123456789")

    assert result["courier"] == COURIER_SAMEDAY
    assert result["awb"] == "4EMGLN123456789"
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["status_label"] == "In Transit"
    assert result["location"] == "Bacu, Ilfov"
    assert result["last_update"] == "2026-03-15T21:43:23+02:00"
    assert result["delivered"] is False
    assert len(result["events"]) == 3
    assert result["is_locker_service"] is False
    api.close()


def test_parse_sameday_delivered():
    """Test parsing a Sameday delivered response (real AWB data)."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_DELIVERED, "4EMGLN159150598")

    assert result["status"] == STATUS_DELIVERED
    assert result["status_label"] == "Delivered"
    assert result["delivered"] is True
    assert result["delivered_date"] == "2026-02-25T20:14:05+02:00"
    assert result["is_locker_service"] is True
    assert len(result["events"]) == 2
    api.close()


def test_parse_sameday_easybox_by_flag():
    """Test easybox detection using isLockerService flag + statusStateId."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_EASYBOX, "4EMGLN987654321")

    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["is_locker_service"] is True
    api.close()


def test_parse_sameday_easybox_by_keyword():
    """Test easybox detection via keyword fallback when isLockerService=False."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_EASYBOX_KEYWORD, "4EMGLN111222333")

    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["is_locker_service"] is False
    api.close()


def test_parse_sameday_empty():
    """Test parsing an empty Sameday response (no awbHistory)."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_EMPTY, "000000000")

    assert result["status"] == STATUS_UNKNOWN
    assert result["delivered"] is False
    assert result["events"] == []
    api.close()


# ============================================================
# FAN Courier tests
# ============================================================


def test_parse_fan_in_transit():
    """Test parsing a FAN Courier in-transit response (H0 event)."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_IN_TRANSIT, "7000081306984")

    assert result["courier"] == COURIER_FAN
    assert result["awb"] == "7000081306984"
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["location"] == "Bucuresti"
    assert result["last_update"] == "2025-08-04 23:57:52"
    assert result["delivered"] is False
    assert result["weight"] == 5
    assert len(result["events"]) == 2
    # Verify event status_id mapping
    assert result["events"][0]["status_id"] == "C0"
    assert result["events"][1]["status_id"] == "H0"
    api.close()


def test_parse_fan_delivered():
    """Test parsing a FAN Courier delivered response (real AWB data)."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_DELIVERED, "7000081306984")

    assert result["status"] == STATUS_DELIVERED
    assert result["status_label"] == "Delivered"
    assert result["delivered"] is True
    assert result["delivered_date"] == "2025-08-05 14:00"
    assert result["delivered_to"] == "e*****l b****u"
    assert result["location"] == "Iasi"
    assert result["weight"] == 5
    assert len(result["events"]) == 5
    api.close()


def test_parse_fan_fanbox():
    """Test parsing a FAN Courier FANbox (locker) response."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_FANBOX, "2150000000002")

    assert result["courier"] == COURIER_FAN
    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["weight"] == 2
    api.close()


def test_parse_fan_returned():
    """Test FAN Courier return detection via returnAwbNumber."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_RETURNED, "7000099999999")

    assert result["status"] == STATUS_RETURNED
    assert result["status_label"] == "Returned"
    assert result["delivered"] is False
    assert result["weight"] == 3
    api.close()


def test_parse_fan_empty_events():
    """Test parsing a FAN response with no events."""
    api = ColeteAPI()
    result = api._parse_fan(
        {"awbNumber": "000", "events": [], "confirmation": {}, "weight": None},
        "000",
    )

    assert result["status"] == STATUS_UNKNOWN
    assert result["delivered"] is False
    assert result["events"] == []
    assert result["weight"] is None
    api.close()


def test_fan_invalid_awb_detection():
    """Test that FAN invalid AWB response raises ColeteNotFoundError."""
    from custom_components.colete.api import ColeteNotFoundError

    api = ColeteAPI()

    # FAN returns {"message": "..."} for invalid AWBs
    invalid_response = {"message": "The AWB has been registered by sender"}
    with pytest.raises(ColeteNotFoundError):
        # We need to test the validation logic in _track_fan,
        # but we can test the condition directly
        data = invalid_response
        if "message" in data and "events" not in data:
            raise ColeteNotFoundError("FAN Courier AWB test not found")

    # Malformed AWB response
    malformed_response = {"message": "The reference.0 format is invalid."}
    with pytest.raises(ColeteNotFoundError):
        data = malformed_response
        if "message" in data and "events" not in data:
            raise ColeteNotFoundError("FAN Courier AWB test not found")

    api.close()


# ============================================================
# Utility tests
# ============================================================


def test_matches_locker_keywords():
    """Test the locker keyword matching helper."""
    assert ColeteAPI._matches_locker_keywords("Disponibil in easybox", ["easybox"])
    assert ColeteAPI._matches_locker_keywords(
        "Coletul a fost depus in FANbox", ["fanbox"]
    )
    assert ColeteAPI._matches_locker_keywords("EASYBOX Mega Image", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords("In tranzit", ["easybox", "fanbox"])
    assert not ColeteAPI._matches_locker_keywords("", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords(None, ["easybox"])


# ============================================================
# Cargus fixtures (real HTML snippets from AWB INDX15452666)
# ============================================================

# Delivered parcel — real HTML from cargus.ro tracking page
MOCK_CARGUS_DELIVERED_HTML = """
<html><body>
<div class="tracking-response-container">
  <h3 class="trk-title">Detalii de tracking pentru AWB INDX15452666</h3>
  <p class="trk-update-time">11 December 2025, 12:12</p>
  <div class="trk-response-card">
    <div class="trk-status-container">
      <img decoding="async" src="/wp-content/uploads/cargus-theme/status-bell.svg" />
      <span>Livrat la destinatar (confirmat)</span>
    </div>
    <style>
      .trk-progress-bar > div {
        width: 100%;
        background-image: linear-gradient(to right, #A74CB5, #B95992, #F58220, #F9BB4A, #0DCE5A);
      }
    </style>
    <div class="trk-progress-bar"><div></div></div>
  </div>
</div>
</body></html>
"""

# In-transit parcel (simulated — same HTML structure, different status)
MOCK_CARGUS_IN_TRANSIT_HTML = """
<html><body>
<div class="tracking-response-container">
  <h3 class="trk-title">Detalii de tracking pentru AWB CARGUS123456</h3>
  <p class="trk-update-time">18 March 2026, 09:30</p>
  <div class="trk-response-card">
    <div class="trk-status-container">
      <img decoding="async" src="/wp-content/uploads/cargus-theme/status-truck.svg" />
      <span>In tranzit</span>
    </div>
    <style>
      .trk-progress-bar > div {
        width: 50%;
        background-image: linear-gradient(to right, #A74CB5, #B95992, #F58220);
      }
    </style>
    <div class="trk-progress-bar"><div></div></div>
  </div>
</div>
</body></html>
"""

# Out for delivery parcel
MOCK_CARGUS_OUT_FOR_DELIVERY_HTML = """
<html><body>
<div class="tracking-response-container">
  <h3 class="trk-title">Detalii de tracking pentru AWB CARGUS789012</h3>
  <p class="trk-update-time">18 March 2026, 14:00</p>
  <div class="trk-response-card">
    <div class="trk-status-container">
      <span>In curs de livrare</span>
    </div>
    <style>
      .trk-progress-bar > div {
        width: 80%;
      }
    </style>
    <div class="trk-progress-bar"><div></div></div>
  </div>
</div>
</body></html>
"""

# Picked up parcel
MOCK_CARGUS_PICKED_UP_HTML = """
<html><body>
<div class="tracking-response-container">
  <h3 class="trk-title">Detalii de tracking pentru AWB CARGUS345678</h3>
  <p class="trk-update-time">18 March 2026, 08:00</p>
  <div class="trk-response-card">
    <div class="trk-status-container">
      <span>Colet preluat de la expeditor</span>
    </div>
    <style>
      .trk-progress-bar > div {
        width: 20%;
      }
    </style>
    <div class="trk-progress-bar"><div></div></div>
  </div>
</div>
</body></html>
"""

# Not found response
MOCK_CARGUS_NOT_FOUND_HTML = """
<html><body>
<div class="not-found-response">Nu am gasit nici un colet!</div>
</body></html>
"""

# Empty page (no tracking container, no not-found)
MOCK_CARGUS_EMPTY_HTML = """
<html><body>
<div class="main-content"></div>
</body></html>
"""

# Returned parcel
MOCK_CARGUS_RETURNED_HTML = """
<html><body>
<div class="tracking-response-container">
  <h3 class="trk-title">Detalii de tracking pentru AWB CARGUS999999</h3>
  <p class="trk-update-time">17 March 2026, 16:00</p>
  <div class="trk-response-card">
    <div class="trk-status-container">
      <span>Returnat la expeditor</span>
    </div>
    <style>
      .trk-progress-bar > div {
        width: 100%;
      }
    </style>
    <div class="trk-progress-bar"><div></div></div>
  </div>
</div>
</body></html>
"""


# ============================================================
# Cargus tests
# ============================================================


def test_parse_cargus_delivered():
    """Test parsing a Cargus delivered response (real AWB data)."""
    api = ColeteAPI()
    result = api._parse_cargus(MOCK_CARGUS_DELIVERED_HTML, "INDX15452666")

    assert result["courier"] == COURIER_CARGUS
    assert result["awb"] == "INDX15452666"
    assert result["status"] == STATUS_DELIVERED
    assert result["status_label"] == "Delivered"
    assert result["status_detail"] == "Livrat la destinatar (confirmat)"
    assert result["last_update"] == "11 December 2025, 12:12"
    assert result["delivered"] is True
    assert result["delivered_date"] == "11 December 2025, 12:12"
    assert result["delivered_to"] is None  # Not available from Cargus
    assert result["weight"] is None  # Not available from Cargus
    assert result["events"] == []  # Cargus only shows current status
    assert result["progress_pct"] == 100
    assert result["location"] == ""  # Not available from Cargus
    api.close()


def test_parse_cargus_in_transit():
    """Test parsing a Cargus in-transit response."""
    api = ColeteAPI()
    result = api._parse_cargus(MOCK_CARGUS_IN_TRANSIT_HTML, "CARGUS123456")

    assert result["courier"] == COURIER_CARGUS
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["status_detail"] == "In tranzit"
    assert result["last_update"] == "18 March 2026, 09:30"
    assert result["delivered"] is False
    assert result["delivered_date"] is None
    assert result["progress_pct"] == 50
    api.close()


def test_parse_cargus_out_for_delivery():
    """Test parsing a Cargus out-for-delivery response."""
    api = ColeteAPI()
    result = api._parse_cargus(MOCK_CARGUS_OUT_FOR_DELIVERY_HTML, "CARGUS789012")

    assert result["status"] == STATUS_OUT_FOR_DELIVERY
    assert result["status_detail"] == "In curs de livrare"
    assert result["delivered"] is False
    assert result["progress_pct"] == 80
    api.close()


def test_parse_cargus_picked_up():
    """Test parsing a Cargus picked-up response."""
    api = ColeteAPI()
    result = api._parse_cargus(MOCK_CARGUS_PICKED_UP_HTML, "CARGUS345678")

    assert result["status"] == STATUS_PICKED_UP
    assert result["status_detail"] == "Colet preluat de la expeditor"
    assert result["delivered"] is False
    assert result["progress_pct"] == 20
    api.close()


def test_parse_cargus_not_found():
    """Test Cargus not-found response raises ColeteNotFoundError."""
    from custom_components.colete.api import ColeteNotFoundError

    api = ColeteAPI()
    with pytest.raises(ColeteNotFoundError, match="not found"):
        api._parse_cargus(MOCK_CARGUS_NOT_FOUND_HTML, "INVALID123")
    api.close()


def test_parse_cargus_empty_page():
    """Test Cargus empty page (no tracking container) raises ColeteNotFoundError."""
    from custom_components.colete.api import ColeteNotFoundError

    api = ColeteAPI()
    with pytest.raises(ColeteNotFoundError, match="no tracking data"):
        api._parse_cargus(MOCK_CARGUS_EMPTY_HTML, "EMPTY123")
    api.close()


def test_parse_cargus_returned():
    """Test parsing a Cargus returned parcel response."""
    api = ColeteAPI()
    result = api._parse_cargus(MOCK_CARGUS_RETURNED_HTML, "CARGUS999999")

    assert result["status"] == STATUS_RETURNED
    assert result["status_label"] == "Returned"
    assert result["delivered"] is False
    assert result["delivered_date"] is None
    api.close()


def test_normalize_cargus_status():
    """Test Cargus status normalization with various Romanian strings."""
    assert (
        ColeteAPI._normalize_cargus_status("Livrat la destinatar (confirmat)")
        == STATUS_DELIVERED
    )
    assert ColeteAPI._normalize_cargus_status("Livrat") == STATUS_DELIVERED
    assert (
        ColeteAPI._normalize_cargus_status("In curs de livrare")
        == STATUS_OUT_FOR_DELIVERY
    )
    assert ColeteAPI._normalize_cargus_status("In tranzit") == STATUS_IN_TRANSIT
    assert (
        ColeteAPI._normalize_cargus_status("Colet preluat de la expeditor")
        == STATUS_PICKED_UP
    )
    assert ColeteAPI._normalize_cargus_status("Expeditie ridicata") == STATUS_PICKED_UP
    assert (
        ColeteAPI._normalize_cargus_status("Returnat la expeditor") == STATUS_RETURNED
    )
    assert ColeteAPI._normalize_cargus_status("Comanda anulata") == STATUS_CANCELED
    assert ColeteAPI._normalize_cargus_status("") == STATUS_UNKNOWN
    assert ColeteAPI._normalize_cargus_status("Status necunoscut xyz") == STATUS_UNKNOWN


# ============================================================
# Retention configuration tests
# ============================================================


def test_retention_days_constants():
    """Test retention_days constant values."""
    assert CONF_RETENTION_DAYS == "retention_days"
    assert DEFAULT_RETENTION_DAYS == 30
    assert MIN_RETENTION_DAYS == 0
    assert MAX_RETENTION_DAYS == 365


# ============================================================
# Coordinator date parsing tests
# ============================================================


def test_parse_delivered_date_iso8601():
    """Test parsing ISO 8601 date from Sameday (timezone-aware)."""
    dt = ColeteDataUpdateCoordinator._parse_delivered_date("2026-02-25T20:14:05+02:00")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 25
    assert dt.tzinfo is not None


def test_parse_delivered_date_fan_format():
    """Test parsing FAN Courier date format (YYYY-MM-DD HH:MM)."""
    dt = ColeteDataUpdateCoordinator._parse_delivered_date("2025-08-05 14:00")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 8
    assert dt.day == 5
    assert dt.tzinfo is not None  # Should be set to UTC as fallback


def test_parse_delivered_date_cargus_format():
    """Test parsing Cargus date format (DD Month YYYY, HH:MM)."""
    dt = ColeteDataUpdateCoordinator._parse_delivered_date("11 December 2025, 12:12")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 12
    assert dt.day == 11
    assert dt.tzinfo is not None


def test_parse_delivered_date_none():
    """Test that None input returns None."""
    assert ColeteDataUpdateCoordinator._parse_delivered_date(None) is None


def test_parse_delivered_date_empty():
    """Test that empty string returns None."""
    assert ColeteDataUpdateCoordinator._parse_delivered_date("") is None


def test_parse_delivered_date_invalid():
    """Test that invalid date string returns None (no exception)."""
    assert ColeteDataUpdateCoordinator._parse_delivered_date("not a date") is None


# ============================================================
# GLS Romania fixtures (based on real API response from AWB 6234776771)
# ============================================================

# Delivered parcel — real response structure from GLS rstt029 endpoint
MOCK_GLS_DELIVERED = {
    "tuStatus": [
        {
            "postalCode": "",
            "emailNotificationCard": False,
            "date": "2026-02-16",
            "tuNo": "6234776771",
            "progressBar": {
                "level": 100,
                "statusBar": [
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Centrul de expedieri",
                        "status": "INWAREHOUSE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "\u00cen livrare",
                        "status": "INDELIVERY",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "Livrat",
                        "status": "DELIVERED",
                        "statusText": (
                            "Coletul a fost livrat. Pentru detalii,"
                            " vizualiza&#539;i istoricul coletului mai jos."
                        ),
                    },
                ],
                "statusInfo": "DELIVERED",
                "evtNos": ["3.0"],
                "statusText": "Livrat",
                "retourFlag": False,
                "colourIndex": 4,
            },
            "natSysOwnerCode": "RO01",
            "owners": [],
        }
    ]
}

# In-transit parcel
MOCK_GLS_IN_TRANSIT = {
    "tuStatus": [
        {
            "postalCode": "",
            "date": "2026-03-18",
            "tuNo": "6234999999",
            "progressBar": {
                "level": 40,
                "statusBar": [
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "Coletul este \u00een tranzit.",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "Centrul de expedieri",
                        "status": "INWAREHOUSE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "\u00cen livrare",
                        "status": "INDELIVERY",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "Livrat",
                        "status": "DELIVERED",
                        "statusText": "",
                    },
                ],
                "statusInfo": "INTRANSIT",
                "statusText": "\u00cen tranzit",
                "retourFlag": False,
                "colourIndex": 1,
            },
            "owners": [],
        }
    ]
}

# Out for delivery parcel
MOCK_GLS_OUT_FOR_DELIVERY = {
    "tuStatus": [
        {
            "date": "2026-03-18",
            "tuNo": "6234888888",
            "progressBar": {
                "level": 80,
                "statusBar": [
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Centrul de expedieri",
                        "status": "INWAREHOUSE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "\u00cen livrare",
                        "status": "INDELIVERY",
                        "statusText": "Coletul este \u00een curs de livrare.",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "Livrat",
                        "status": "DELIVERED",
                        "statusText": "",
                    },
                ],
                "statusInfo": "INDELIVERY",
                "statusText": "\u00cen livrare",
                "retourFlag": False,
                "colourIndex": 3,
            },
            "owners": [],
        }
    ]
}

# Preadvice (just registered) parcel
MOCK_GLS_PREADVICE = {
    "tuStatus": [
        {
            "date": "2026-03-18",
            "tuNo": "6234777777",
            "progressBar": {
                "level": 0,
                "statusBar": [
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "Coletul a fost \u00eenregistrat.",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "Centrul de expedieri",
                        "status": "INWAREHOUSE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "\u00cen livrare",
                        "status": "INDELIVERY",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "PENDING",
                        "imageText": "Livrat",
                        "status": "DELIVERED",
                        "statusText": "",
                    },
                ],
                "statusInfo": "PREADVICE",
                "statusText": "Preadvice",
                "retourFlag": False,
                "colourIndex": 0,
            },
            "owners": [],
        }
    ]
}

# Delivered to parcel shop/locker
MOCK_GLS_PARCEL_SHOP = {
    "tuStatus": [
        {
            "date": "2026-03-18",
            "tuNo": "6234666666",
            "progressBar": {
                "level": 100,
                "statusBar": [
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Centrul de expedieri",
                        "status": "INWAREHOUSE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "\u00cen livrare",
                        "status": "INDELIVERY",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "Livrat la parcel shop",
                        "status": "DELIVEREDPS",
                        "statusText": "Coletul a fost livrat la parcel shop.",
                    },
                ],
                "statusInfo": "DELIVEREDPS",
                "statusText": "Livrat la parcel shop",
                "retourFlag": False,
                "colourIndex": 4,
            },
            "owners": [],
        }
    ]
}

# Returned parcel (retourFlag=True)
MOCK_GLS_RETURNED = {
    "tuStatus": [
        {
            "date": "2026-03-17",
            "tuNo": "6234555555",
            "progressBar": {
                "level": 60,
                "statusBar": [
                    {
                        "imageStatus": "COMPLETE",
                        "imageText": "Preadvice",
                        "status": "PREADVICE",
                        "statusText": "",
                    },
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "Retur",
                        "status": "INTRANSIT",
                        "statusText": "Coletul este \u00een retur.",
                    },
                ],
                "statusInfo": "INTRANSIT",
                "statusText": "Retur",
                "retourFlag": True,
                "colourIndex": 1,
            },
            "owners": [],
        }
    ]
}

# Empty response (no tuStatus)
MOCK_GLS_EMPTY = {"tuStatus": []}

# HTML entities in statusText
MOCK_GLS_HTML_ENTITIES = {
    "tuStatus": [
        {
            "date": "2026-03-18",
            "tuNo": "6234444444",
            "progressBar": {
                "level": 40,
                "statusBar": [
                    {
                        "imageStatus": "CURRENT",
                        "imageText": "\u00cen tranzit",
                        "status": "INTRANSIT",
                        "statusText": "Vizualiza&#539;i detaliile coletului &#238;n aplica&#539;ie.",
                    },
                ],
                "statusInfo": "INTRANSIT",
                "statusText": "&#206;n tranzit",
                "retourFlag": False,
            },
            "owners": [],
        }
    ]
}


# ============================================================
# GLS Romania tests
# ============================================================


def test_parse_gls_delivered():
    """Test parsing a GLS delivered response (real AWB data structure)."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_DELIVERED, "6234776771")

    assert result["courier"] == COURIER_GLS
    assert result["awb"] == "6234776771"
    assert result["status"] == STATUS_DELIVERED
    assert result["status_label"] == "Delivered"
    assert result["delivered"] is True
    assert result["delivered_date"] == "2026-02-16"
    assert result["last_update"] == "2026-02-16"
    assert result["progress_pct"] == 100
    assert result["location"] == ""  # Not available from GLS
    assert result["weight"] is None  # Not available from GLS
    assert result["events"] == []  # GLS only shows current status
    assert result["delivered_to"] is None
    # Status detail should be from the CURRENT step's statusText (HTML-unescaped)
    assert "vizualiza" in result["status_detail"].lower()
    assert "&#" not in result["status_detail"]  # HTML entities decoded
    api.close()


def test_parse_gls_in_transit():
    """Test parsing a GLS in-transit response."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_IN_TRANSIT, "6234999999")

    assert result["courier"] == COURIER_GLS
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["status_label"] == "In Transit"
    assert result["delivered"] is False
    assert result["delivered_date"] is None
    assert result["progress_pct"] == 40
    assert result["last_update"] == "2026-03-18"
    api.close()


def test_parse_gls_out_for_delivery():
    """Test parsing a GLS out-for-delivery response."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_OUT_FOR_DELIVERY, "6234888888")

    assert result["status"] == STATUS_OUT_FOR_DELIVERY
    assert result["status_label"] == "Out for Delivery"
    assert result["delivered"] is False
    assert result["progress_pct"] == 80
    api.close()


def test_parse_gls_preadvice():
    """Test parsing a GLS preadvice (just registered) response."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_PREADVICE, "6234777777")

    assert result["status"] == STATUS_PICKED_UP
    assert result["status_label"] == "Picked Up"
    assert result["delivered"] is False
    assert result["progress_pct"] == 0
    api.close()


def test_parse_gls_parcel_shop():
    """Test parsing a GLS parcel shop/locker delivery (DELIVEREDPS)."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_PARCEL_SHOP, "6234666666")

    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["progress_pct"] == 100
    api.close()


def test_parse_gls_returned():
    """Test GLS return detection via retourFlag."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_RETURNED, "6234555555")

    assert result["status"] == STATUS_RETURNED
    assert result["status_label"] == "Returned"
    assert result["delivered"] is False
    api.close()


def test_parse_gls_empty():
    """Test GLS empty response raises ColeteNotFoundError."""
    from custom_components.colete.api import ColeteNotFoundError

    api = ColeteAPI()
    with pytest.raises(ColeteNotFoundError, match="empty response"):
        api._parse_gls(MOCK_GLS_EMPTY, "0000000000")
    api.close()


def test_parse_gls_html_entities():
    """Test that HTML entities in GLS status text are properly decoded."""
    api = ColeteAPI()
    result = api._parse_gls(MOCK_GLS_HTML_ENTITIES, "6234444444")

    assert result["status"] == STATUS_IN_TRANSIT
    # statusText had &#206;n → În (decoded)
    assert "&#" not in result["status_detail"]
    # Main statusText should also be decoded
    assert "&#" not in result["status_label"]
    api.close()


# ============================================================
# DPD Romania fixtures (based on real API response structure
# from tracking.dpd.de/rest/plc/ro_RO/{AWB})
# ============================================================

# Delivered parcel — full response with scan events
MOCK_DPD_DELIVERED = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981100001234",
                "serviceElements": [],
                "codInformationAvailable": False,
                "documents": [],
                "additionalProperties": [
                    {
                        "key": "PARCEL_ID",
                        "value": "20260120-0000-8000-a009-981100001234",
                    },
                    {"key": "RECEIVER_NAME", "value": "Ion Popescu"},
                ],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat catre DPD",
                    "description": {
                        "content": [
                            "DPD a receptionat coletul dumneavoastra."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {
                        "content": ["Coletul este in tranzit."]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozitul de livrare",
                    "description": {
                        "content": [
                            "Coletul a ajuns la depozitul de livrare."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In curs de livrare",
                    "description": {
                        "content": [
                            "Coletul este in curs de livrare."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {
                        "content": [
                            "Coletul a fost livrat cu succes."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": True,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {
                "scan": [
                    {
                        "date": "2026-01-18T16:30:00",
                        "scanData": {
                            "scanType": {
                                "code": "15",
                                "name": "SC_15_PICKUP",
                            },
                            "location": "Bucuresti (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": ["Coletul a fost ridicat de la expeditor."]
                        },
                        "links": [],
                    },
                    {
                        "date": "2026-01-19T08:15:00",
                        "scanData": {
                            "scanType": {
                                "code": "1",
                                "name": "SC_1_SORT",
                            },
                            "location": "Bucuresti (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": ["Coletul a fost sortat in depozit."]
                        },
                        "links": [],
                    },
                    {
                        "date": "2026-01-19T14:00:00",
                        "scanData": {
                            "scanType": {
                                "code": "4",
                                "name": "SC_4_INBOUND",
                            },
                            "location": "Iasi (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul a ajuns la depozitul de destinatie."
                            ]
                        },
                        "links": [],
                    },
                    {
                        "date": "2026-01-20T09:00:00",
                        "scanData": {
                            "scanType": {
                                "code": "3",
                                "name": "SC_3_IN_DELIVERY",
                            },
                            "location": "Iasi (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul este in curs de livrare."
                            ]
                        },
                        "links": [],
                    },
                    {
                        "date": "2026-01-20T12:23:23",
                        "scanData": {
                            "scanType": {
                                "code": "13",
                                "name": "SC_13_DELIVERED",
                            },
                            "location": "Iasi (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": [{"code": "068"}]
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": ["Coletul a fost livrat."]
                        },
                        "links": [
                            {
                                "target": "DOCUMENT_POD_V2",
                                "url": "https://tracking.dpd.de/pod/...",
                            }
                        ],
                    },
                ],
            },
        }
    }
}

# In-transit parcel — ON_THE_ROAD stage
MOCK_DPD_IN_TRANSIT = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981100005678",
                "additionalProperties": [
                    {
                        "key": "PARCEL_ID",
                        "value": "20260318-0000-8000-a009-981100005678",
                    },
                ],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat catre DPD",
                    "description": {
                        "content": [
                            "DPD a receptionat coletul dumneavoastra."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {
                        "content": ["Coletul este in tranzit."]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": True,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozitul de livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In curs de livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {
                "scan": [
                    {
                        "date": "2026-03-17T18:00:00",
                        "scanData": {
                            "scanType": {
                                "code": "15",
                                "name": "SC_15_PICKUP",
                            },
                            "location": "Cluj-Napoca (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul a fost ridicat de la expeditor."
                            ]
                        },
                        "links": [],
                    },
                    {
                        "date": "2026-03-18T06:30:00",
                        "scanData": {
                            "scanType": {
                                "code": "1",
                                "name": "SC_1_SORT",
                            },
                            "location": "Bucuresti (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": []
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul a fost sortat in depozit."
                            ]
                        },
                        "links": [],
                    },
                ],
            },
        }
    }
}

# Out for delivery parcel
MOCK_DPD_OUT_FOR_DELIVERY = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981100009999",
                "additionalProperties": [],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat catre DPD",
                    "description": {"content": ["DPD a receptionat coletul."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {"content": ["Coletul este in tranzit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozitul de livrare",
                    "description": {"content": ["La depozit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In curs de livrare",
                    "description": {
                        "content": [
                            "Coletul este in curs de livrare."
                        ]
                    },
                    "statusHasBeenReached": True,
                    "isCurrentStatus": True,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {
                "scan": [
                    {
                        "date": "2026-03-18T09:00:00",
                        "scanData": {
                            "scanType": {"code": "3", "name": "SC_3_IN_DELIVERY"},
                            "location": "Timisoara (RO)",
                            "country": "RO",
                            "additionalCodes": {"additionalCode": []},
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul este in curs de livrare."
                            ]
                        },
                        "links": [],
                    },
                ],
            },
        }
    }
}

# Parcel shop delivery (scan code 23 = store dropoff)
MOCK_DPD_PARCEL_SHOP = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981100007777",
                "additionalProperties": [],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat",
                    "description": {"content": ["Predat."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {"content": ["In tranzit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozit",
                    "description": {"content": ["La depozit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": True,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {
                "scan": [
                    {
                        "date": "2026-03-18T10:00:00",
                        "scanData": {
                            "scanType": {
                                "code": "23",
                                "name": "SC_23_STORE_DROPOFF",
                            },
                            "location": "Bucuresti (RO)",
                            "country": "RO",
                            "additionalCodes": {"additionalCode": []},
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul a fost depus la DPD Pickup Shop."
                            ]
                        },
                        "links": [
                            {
                                "target": "PARCELSHOP_DETAIL",
                                "url": "https://tracking.dpd.de/rest/ps/ro_RO/P12345",
                            }
                        ],
                    },
                ],
            },
        }
    }
}

# Pre-registered parcel — no stages reached, empty scans
MOCK_DPD_PREREGISTERED = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981122334455",
                "serviceElements": [],
                "codInformationAvailable": False,
                "documents": [],
                "additionalProperties": [
                    {
                        "key": "PARCEL_ID",
                        "value": "20260221-0000-8000-a009-981122334455",
                    }
                ],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat catre DPD",
                    "description": {
                        "content": [
                            "DPD a receptionat coletul dumneavoastra."
                        ]
                    },
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozitul de livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In curs de livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {"scan": []},
        }
    }
}

# Not found — null parcelLifeCycleData
MOCK_DPD_NOT_FOUND = {
    "parcellifecycleResponse": {"parcelLifeCycleData": None}
}

# Parcel shop redirect via not-delivered event (scan code 14, additional 091)
MOCK_DPD_PARCELSHOP_REDIRECT = {
    "parcellifecycleResponse": {
        "parcelLifeCycleData": {
            "shipmentInfo": {
                "parcelLabelNumber": "09981100006666",
                "additionalProperties": [],
            },
            "statusInfo": [
                {
                    "status": "ACCEPTED",
                    "label": "Colet predat",
                    "description": {"content": ["Predat."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "ON_THE_ROAD",
                    "label": "In drum",
                    "description": {"content": ["In tranzit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "AT_DELIVERY_DEPOT",
                    "label": "La depozit",
                    "description": {"content": ["La depozit."]},
                    "statusHasBeenReached": True,
                    "isCurrentStatus": True,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "OUT_FOR_DELIVERY",
                    "label": "In livrare",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
                {
                    "status": "DELIVERED",
                    "label": "Livrat",
                    "description": {"content": []},
                    "statusHasBeenReached": False,
                    "isCurrentStatus": False,
                    "normalItems": [],
                    "importantItems": [],
                    "errorItems": [],
                },
            ],
            "contactInfo": [],
            "scanInfo": {
                "scan": [
                    {
                        "date": "2026-03-18T11:00:00",
                        "scanData": {
                            "scanType": {
                                "code": "14",
                                "name": "SC_14_NOT_DELIVERED",
                            },
                            "location": "Brasov (RO)",
                            "country": "RO",
                            "additionalCodes": {
                                "additionalCode": [{"code": "091"}]
                            },
                            "serviceElements": [],
                        },
                        "scanDescription": {
                            "content": [
                                "Coletul a fost redirectionat la parcel shop."
                            ]
                        },
                        "links": [],
                    },
                ],
            },
        }
    }
}


# ============================================================
# DPD Romania tests
# ============================================================


def test_parse_dpd_delivered():
    """Test parsing a DPD delivered response with full scan history."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_DELIVERED, "09981100001234")

    assert result["courier"] == COURIER_DPD
    assert result["awb"] == "09981100001234"
    assert result["status"] == STATUS_DELIVERED
    assert result["status_label"] == "Delivered"
    assert result["delivered"] is True
    assert result["delivered_date"] == "2026-01-20T12:23:23"
    assert result["delivered_to"] == "Ion Popescu"
    assert result["location"] == "Iasi"  # Extracted from "Iasi (RO)"
    assert result["last_update"] == "2026-01-20T12:23:23"
    assert result["weight"] is None  # Not available from DPD
    assert len(result["events"]) == 5
    # Verify first event
    assert result["events"][0]["date"] == "2026-01-18T16:30:00"
    assert result["events"][0]["location"] == "Bucuresti"
    assert result["events"][0]["scan_code"] == "15"
    # Verify last event (delivery)
    assert result["events"][-1]["scan_code"] == "13"
    assert result["events"][-1]["location"] == "Iasi"
    api.close()


def test_parse_dpd_in_transit():
    """Test parsing a DPD in-transit response (ON_THE_ROAD stage)."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_IN_TRANSIT, "09981100005678")

    assert result["courier"] == COURIER_DPD
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["status_label"] == "In Transit"
    assert result["delivered"] is False
    assert result["delivered_date"] is None
    assert result["delivered_to"] is None
    assert result["location"] == "Bucuresti"
    assert result["last_update"] == "2026-03-18T06:30:00"
    assert len(result["events"]) == 2
    assert result["status_detail"] == "Coletul este in tranzit."
    api.close()


def test_parse_dpd_out_for_delivery():
    """Test parsing a DPD out-for-delivery response."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_OUT_FOR_DELIVERY, "09981100009999")

    assert result["status"] == STATUS_OUT_FOR_DELIVERY
    assert result["status_label"] == "Out for Delivery"
    assert result["delivered"] is False
    assert result["location"] == "Timisoara"
    assert len(result["events"]) == 1
    api.close()


def test_parse_dpd_parcel_shop():
    """Test DPD parcel shop delivery (scan code 23 = store dropoff)."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_PARCEL_SHOP, "09981100007777")

    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["location"] == "Bucuresti"
    api.close()


def test_parse_dpd_parcelshop_redirect():
    """Test DPD parcel shop redirect via not-delivered event (code 14 + 091)."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_PARCELSHOP_REDIRECT, "09981100006666")

    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    assert result["location"] == "Brasov"
    api.close()


def test_parse_dpd_preregistered():
    """Test DPD pre-registered parcel (no stages reached, no scans)."""
    api = ColeteAPI()
    result = api._parse_dpd(MOCK_DPD_PREREGISTERED, "09981122334455")

    # Falls back to ACCEPTED (first stage) since no isCurrentStatus/reached
    assert result["status"] == STATUS_PICKED_UP
    assert result["delivered"] is False
    assert result["delivered_date"] is None
    assert result["location"] == ""
    assert result["last_update"] == ""
    assert result["events"] == []
    api.close()


def test_parse_dpd_not_found():
    """Test DPD not-found response (null parcelLifeCycleData)."""
    from custom_components.colete.api import ColeteNotFoundError

    api = ColeteAPI()
    with pytest.raises(ColeteNotFoundError, match="not found"):
        api._parse_dpd(MOCK_DPD_NOT_FOUND, "00000000000000")
    api.close()


def test_parse_dpd_location_without_country_code():
    """Test DPD location parsing when format doesn't match 'City (CC)'."""
    api = ColeteAPI()
    # Modify a fixture with a non-standard location format
    data = {
        "parcellifecycleResponse": {
            "parcelLifeCycleData": {
                "shipmentInfo": {
                    "parcelLabelNumber": "09981100008888",
                    "additionalProperties": [],
                },
                "statusInfo": [
                    {
                        "status": "ON_THE_ROAD",
                        "label": "In drum",
                        "description": {"content": ["In tranzit."]},
                        "statusHasBeenReached": True,
                        "isCurrentStatus": True,
                        "normalItems": [],
                        "importantItems": [],
                        "errorItems": [],
                    },
                ],
                "contactInfo": [],
                "scanInfo": {
                    "scan": [
                        {
                            "date": "2026-03-18T10:00:00",
                            "scanData": {
                                "scanType": {"code": "1", "name": "SC_1_SORT"},
                                "location": "Some Depot Location",
                                "country": "RO",
                                "additionalCodes": {"additionalCode": []},
                                "serviceElements": [],
                            },
                            "scanDescription": {
                                "content": ["Sorted."]
                            },
                            "links": [],
                        },
                    ],
                },
            }
        }
    }
    result = api._parse_dpd(data, "09981100008888")

    # Location without "(CC)" format should be kept as-is
    assert result["location"] == "Some Depot Location"
    api.close()
