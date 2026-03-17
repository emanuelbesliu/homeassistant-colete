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
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_UNKNOWN,
)


# Sample Sameday API response (normal delivery)
MOCK_SAMEDAY_RESPONSE = {
    "expeditionSummary": {
        "delivered": False,
        "canceled": False,
        "weight": 1.5,
    },
    "expeditionHistory": [
        {
            "statusState": SAMEDAY_STATE_IN_TRANSIT,
            "status": "InTransit",
            "statusLabel": "In tranzit",
            "statusDate": "2026-03-15 14:30:00",
            "transitLocation": "Bucuresti - Hub",
            "county": "Bucuresti",
        },
        {
            "statusState": 1,
            "status": "PickedUp",
            "statusLabel": "Ridicat",
            "statusDate": "2026-03-15 10:00:00",
            "transitLocation": "Depozit Expeditor",
            "county": "Ilfov",
        },
    ],
    "expeditionStatus": {
        "statusState": SAMEDAY_STATE_IN_TRANSIT,
        "status": "InTransit",
        "statusLabel": "In tranzit",
    },
}


# Sample Sameday easybox response (parcel waiting at locker)
MOCK_SAMEDAY_EASYBOX_RESPONSE = {
    "expeditionSummary": {
        "delivered": False,
        "canceled": False,
        "weight": 0.8,
    },
    "expeditionHistory": [
        {
            "statusState": SAMEDAY_STATE_OUT_FOR_DELIVERY,
            "status": "OutForDelivery",
            "statusLabel": "Coletul a fost depozitat in easybox",
            "statusDate": "2026-03-16 09:15:00",
            "transitLocation": "easybox Mega Image Unirii",
            "county": "Bucuresti",
        },
    ],
    "expeditionStatus": {
        "statusState": SAMEDAY_STATE_OUT_FOR_DELIVERY,
        "status": "OutForDelivery",
        "statusLabel": "Disponibil in easybox",
    },
}


# Sample Sameday delivered response
MOCK_SAMEDAY_DELIVERED_RESPONSE = {
    "expeditionSummary": {
        "delivered": True,
        "canceled": False,
        "weight": 2.0,
    },
    "expeditionHistory": [
        {
            "statusState": SAMEDAY_STATE_DELIVERED,
            "status": "Delivered",
            "statusLabel": "Livrat",
            "statusDate": "2026-03-16 12:00:00",
            "transitLocation": "Bucuresti",
            "county": "Bucuresti",
        },
    ],
    "expeditionStatus": {
        "statusState": SAMEDAY_STATE_DELIVERED,
        "status": "Delivered",
        "statusLabel": "Livrat",
    },
}


# Sample FAN Courier response
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


# Sample FAN Courier FANbox response (parcel at locker)
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


def test_parse_sameday_in_transit():
    """Test parsing a Sameday in-transit response."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_RESPONSE, "123456789")

    assert result["courier"] == COURIER_SAMEDAY
    assert result["awb"] == "123456789"
    assert result["status"] == STATUS_IN_TRANSIT
    assert result["status_label"] == "In Transit"
    assert result["location"] == "Bucuresti - Hub, Bucuresti"
    assert result["last_update"] == "2026-03-15 14:30:00"
    assert result["delivered"] is False
    assert result["weight"] == 1.5
    assert len(result["events"]) == 2
    api.close()


def test_parse_sameday_easybox():
    """Test parsing a Sameday easybox (locker) response."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_EASYBOX_RESPONSE, "987654321")

    assert result["courier"] == COURIER_SAMEDAY
    assert result["status"] == STATUS_READY_FOR_PICKUP
    assert result["status_label"] == "Ready for Pickup"
    assert result["delivered"] is False
    api.close()


def test_parse_sameday_delivered():
    """Test parsing a Sameday delivered response."""
    api = ColeteAPI()
    result = api._parse_sameday(MOCK_SAMEDAY_DELIVERED_RESPONSE, "111222333")

    assert result["status"] == STATUS_DELIVERED
    assert result["delivered"] is True
    assert result["delivered_date"] == "2026-03-16 12:00:00"
    api.close()


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


def test_parse_sameday_empty():
    """Test parsing an empty Sameday response."""
    api = ColeteAPI()
    result = api._parse_sameday(
        {"expeditionSummary": {}, "expeditionHistory": [], "expeditionStatus": {}},
        "000000000",
    )

    assert result["status"] == STATUS_UNKNOWN
    assert result["delivered"] is False
    assert result["events"] == []
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


def test_matches_locker_keywords():
    """Test the locker keyword matching helper."""
    assert ColeteAPI._matches_locker_keywords("Disponibil in easybox", ["easybox"])
    assert ColeteAPI._matches_locker_keywords("Coletul a fost depus in FANbox", ["fanbox"])
    assert ColeteAPI._matches_locker_keywords("EASYBOX Mega Image", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords("In tranzit", ["easybox", "fanbox"])
    assert not ColeteAPI._matches_locker_keywords("", ["easybox"])
    assert not ColeteAPI._matches_locker_keywords(None, ["easybox"])
