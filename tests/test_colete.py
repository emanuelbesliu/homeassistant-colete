"""Tests for the Colete (Romanian Parcel Tracking) integration."""

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("homeassistant")

from custom_components.colete.api import ColeteAPI  # noqa: E402
from custom_components.colete.const import (  # noqa: E402
    COURIER_SAMEDAY,
    COURIER_FAN,
    SAMEDAY_STATE_DELIVERED,
    SAMEDAY_STATE_IN_TRANSIT,
    SAMEDAY_STATE_OUT_FOR_DELIVERY,
    SAMEDAY_STATE_PICKED_UP,
    SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
    SAMEDAY_STATE_CENTRAL_DEPOT,
    SAMEDAY_STATE_REGISTERED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_UNKNOWN,
    STATUS_PICKED_UP,
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
# FAN Courier fixtures
# ============================================================

MOCK_FAN_RESPONSE = {
    "awbNumber": "2150000000001",
    "date": "2026-03-15",
    "confirmation": {},
    "events": [
        {
            "id": "C0",
            "name": "Ridicat de la expeditor",
            "location": "Bucuresti",
            "date": "2026-03-15 10:00:00",
        },
        {
            "id": "H4",
            "name": "In sortare",
            "location": "Hub Bucuresti",
            "date": "2026-03-15 14:30:00",
        },
    ],
}


MOCK_FAN_FANBOX_RESPONSE = {
    "awbNumber": "2150000000002",
    "date": "2026-03-16",
    "confirmation": {},
    "events": [
        {
            "id": "C0",
            "name": "Ridicat de la expeditor",
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
    """Test parsing a FAN Courier in-transit response."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_RESPONSE, "2150000000001")

    assert result["courier"] == COURIER_FAN
    assert result["awb"] == "2150000000001"
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["location"] == "Hub Bucuresti"
    assert result["delivered"] is False
    assert len(result["events"]) == 2
    api.close()


def test_parse_fan_fanbox():
    """Test parsing a FAN Courier FANbox (locker) response."""
    api = ColeteAPI()
    result = api._parse_fan(MOCK_FAN_FANBOX_RESPONSE, "2150000000002")

    assert result["courier"] == COURIER_FAN
    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    api.close()


def test_parse_fan_empty_events():
    """Test parsing a FAN response with no events."""
    api = ColeteAPI()
    result = api._parse_fan(
        {"awbNumber": "000", "events": [], "confirmation": {}},
        "000",
    )

    assert result["status"] == STATUS_UNKNOWN
    assert result["delivered"] is False
    assert result["events"] == []
    api.close()


# ============================================================
# Utility tests
# ============================================================


def test_matches_locker_keywords():
    """Test the locker keyword matching helper."""
    assert ColeteAPI._matches_locker_keywords("Disponibil in easybox", ["easybox"])
    assert ColeteAPI._matches_locker_keywords("Coletul a fost depus in FANbox", ["fanbox"])
    assert ColeteAPI._matches_locker_keywords("EASYBOX Mega Image", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords("In tranzit", ["easybox", "fanbox"])
    assert not ColeteAPI._matches_locker_keywords("", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords(None, ["easybox"])
