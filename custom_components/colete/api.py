"""API clients for Romanian parcel tracking couriers."""

import logging
from typing import Any

import requests

from .const import (
    COURIER_AUTO,
    COURIER_SAMEDAY,
    COURIER_FAN,
    COURIER_DETECT_ORDER,
    SAMEDAY_API_URL,
    FAN_API_URL,
    SAMEDAY_STATE_DELIVERED,
    SAMEDAY_STATE_OUT_FOR_DELIVERY,
    SAMEDAY_STATE_PICKED_UP,
    SAMEDAY_STATE_IN_TRANSIT,
    SAMEDAY_STATE_REGISTERED,
    SAMEDAY_STATE_CENTRAL_DEPOT,
    SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
    SAMEDAY_LOCKER_KEYWORDS,
    FAN_STATUS_DELIVERED,
    FAN_STATUS_OUT_FOR_DELIVERY,
    FAN_STATUS_DELIVERING,
    FAN_STATUS_PICKED_UP,
    FAN_IN_TRANSIT_CODES,
    FAN_LOCKER_KEYWORDS,
    STATUS_UNKNOWN,
    STATUS_PICKED_UP,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_DELIVERED,
    STATUS_RETURNED,
    STATUS_CANCELED,
    STATUS_LABELS,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for API requests in seconds
REQUEST_TIMEOUT = 15

# User-Agent header
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class ColeteApiError(Exception):
    """Exception for parcel tracking API errors."""


class ColeteNotFoundError(ColeteApiError):
    """Exception when an AWB is not found."""


class ColeteAPI:
    """Client for Romanian parcel tracking APIs."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
            }
        )

    def track_parcel(self, courier: str, awb: str) -> dict[str, Any]:
        """Track a parcel by courier and AWB number.

        Returns a normalized dict with parcel tracking data.
        If courier is "auto", tries each supported courier in sequence.

        Args:
            courier: The courier identifier (auto, sameday, fan_courier).
            awb: The AWB/tracking number.

        Returns:
            dict with normalized tracking data.

        Raises:
            ColeteApiError: If the API request fails.
            ColeteNotFoundError: If the AWB is not found.
        """
        if courier == COURIER_AUTO:
            return self._auto_detect_and_track(awb)
        elif courier == COURIER_SAMEDAY:
            return self._track_sameday(awb)
        elif courier == COURIER_FAN:
            return self._track_fan(awb)
        else:
            raise ColeteApiError(f"Unsupported courier: {courier}")

    def _auto_detect_and_track(self, awb: str) -> dict[str, Any]:
        """Try each courier in sequence until one returns data.

        Args:
            awb: The AWB/tracking number.

        Returns:
            dict with normalized tracking data (includes detected courier).

        Raises:
            ColeteNotFoundError: If no courier recognized the AWB.
        """
        last_error = None
        for courier in COURIER_DETECT_ORDER:
            try:
                result = self.track_parcel(courier, awb)
                _LOGGER.debug(
                    "Auto-detected courier %s for AWB %s", courier, awb
                )
                return result
            except ColeteNotFoundError:
                _LOGGER.debug(
                    "AWB %s not found with %s, trying next courier",
                    awb,
                    courier,
                )
                continue
            except ColeteApiError as err:
                _LOGGER.debug(
                    "Error checking %s for AWB %s: %s", courier, awb, err
                )
                last_error = err
                continue

        if last_error:
            raise ColeteNotFoundError(
                f"AWB {awb} not found with any courier (last error: {last_error})"
            )
        raise ColeteNotFoundError(
            f"AWB {awb} not found with any supported courier"
        )

    def validate_awb(self, courier: str, awb: str) -> dict[str, Any]:
        """Validate that an AWB exists and return tracking data.

        Returns:
            dict with tracking data (includes detected courier if auto).

        Raises:
            ColeteApiError: If the API request fails.
            ColeteNotFoundError: If the AWB is not found.
        """
        return self.track_parcel(courier, awb)

    def _track_sameday(self, awb: str) -> dict[str, Any]:
        """Track a Sameday parcel.

        API: GET https://api.sameday.ro/api/public/awb/{AWB}/awb-history?_locale=ro
        Returns JSON with awbNumber, awbHistory, parcelsList, isLockerService.
        """
        url = SAMEDAY_API_URL.format(awb=awb)
        params = {"_locale": "ro"}

        try:
            response = self._session.get(
                url, params=params, timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout as err:
            raise ColeteApiError(
                f"Timeout connecting to Sameday API: {err}"
            ) from err
        except requests.exceptions.ConnectionError as err:
            raise ColeteApiError(
                f"Connection error to Sameday API: {err}"
            ) from err
        except requests.exceptions.RequestException as err:
            raise ColeteApiError(
                f"Error fetching Sameday data: {err}"
            ) from err

        if response.status_code == 404:
            raise ColeteNotFoundError(f"Sameday AWB {awb} not found")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise ColeteApiError(
                f"HTTP error from Sameday API: {err}"
            ) from err

        try:
            data = response.json()
        except ValueError as err:
            raise ColeteApiError(
                f"Invalid JSON from Sameday API: {err}"
            ) from err

        return self._parse_sameday(data, awb)

    @staticmethod
    def _matches_locker_keywords(label: str, keywords: list[str]) -> bool:
        """Check if a status label contains any locker/easybox keywords.

        Args:
            label: The status label string to check.
            keywords: List of keywords to match (case-insensitive).

        Returns:
            True if any keyword is found in the label.
        """
        if not label:
            return False
        label_lower = label.lower()
        return any(keyword in label_lower for keyword in keywords)

    def _parse_sameday(self, data: dict[str, Any], awb: str) -> dict[str, Any]:
        """Parse Sameday API response into normalized format.

        Real API structure:
        {
            "awbNumber": "...",
            "awbHistory": [ { statusStateId, statusState, status, statusId,
                              county, country, transitLocation, statusDate, ... } ],
            "parcelsList": { "<parcelAwb>": [...] },
            "isLockerService": bool,
            "isReturn": bool,
            ...
        }
        """
        history = data.get("awbHistory", [])
        is_locker_service = data.get("isLockerService", False)
        is_return = data.get("isReturn", False)

        # Latest event is first in the awbHistory array
        latest_event = history[0] if history else {}
        latest_state_id = latest_event.get("statusStateId")

        # Map statusStateId to normalized status
        if latest_state_id == SAMEDAY_STATE_DELIVERED:
            normalized_status = STATUS_DELIVERED
        elif latest_state_id == SAMEDAY_STATE_OUT_FOR_DELIVERY:
            normalized_status = STATUS_OUT_FOR_DELIVERY
        elif latest_state_id == SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT:
            normalized_status = STATUS_OUT_FOR_DELIVERY
        elif latest_state_id == SAMEDAY_STATE_PICKED_UP:
            normalized_status = STATUS_PICKED_UP
        elif latest_state_id == SAMEDAY_STATE_IN_TRANSIT:
            normalized_status = STATUS_IN_TRANSIT
        elif latest_state_id == SAMEDAY_STATE_CENTRAL_DEPOT:
            normalized_status = STATUS_IN_TRANSIT
        elif latest_state_id == SAMEDAY_STATE_REGISTERED:
            normalized_status = STATUS_PICKED_UP
        elif latest_state_id is not None:
            normalized_status = STATUS_IN_TRANSIT
        else:
            normalized_status = STATUS_UNKNOWN

        # Check for returned parcels (isReturn flag or status text)
        if is_return:
            normalized_status = STATUS_RETURNED
        else:
            # Check status text for return/cancel keywords
            latest_status_text = (
                latest_event.get("status", "") or ""
            ).lower()
            latest_state_text = (
                latest_event.get("statusState", "") or ""
            ).lower()
            combined_text = f"{latest_status_text} {latest_state_text}"
            if "retur" in combined_text or "returnat" in combined_text:
                normalized_status = STATUS_RETURNED
            elif "anulat" in combined_text:
                normalized_status = STATUS_CANCELED

        # Locker/easybox detection:
        # 1. Use the isLockerService flag from the API response
        # 2. Also check status labels for locker keywords
        # If parcel is at a locker and not yet delivered, set ready_for_pickup
        if normalized_status != STATUS_DELIVERED and normalized_status != STATUS_RETURNED:
            if is_locker_service and latest_state_id in (
                SAMEDAY_STATE_LOADED_AT_DELIVERY_POINT,
                SAMEDAY_STATE_OUT_FOR_DELIVERY,
            ):
                normalized_status = STATUS_READY_FOR_PICKUP
            else:
                # Fallback: check status text for locker keywords
                current_label = (
                    latest_event.get("status", "")
                    or latest_event.get("statusState", "")
                    or ""
                )
                if self._matches_locker_keywords(
                    current_label, SAMEDAY_LOCKER_KEYWORDS
                ):
                    normalized_status = STATUS_READY_FOR_PICKUP

        # Extract location from latest event
        location = latest_event.get("transitLocation", "")
        county = latest_event.get("county", "")
        if county and location:
            location = f"{location}, {county}"
        elif county:
            location = county

        last_update = latest_event.get("statusDate", "")

        # Delivery info
        is_delivered = normalized_status == STATUS_DELIVERED
        delivered_to = None
        delivered_date = None
        if is_delivered:
            for event in history:
                if event.get("statusStateId") == SAMEDAY_STATE_DELIVERED:
                    delivered_date = event.get("statusDate", "")
                    break

        # Build normalized events list
        events = []
        for event in history:
            events.append(
                {
                    "date": event.get("statusDate", ""),
                    "status": event.get("status", event.get("statusState", "")),
                    "location": event.get("transitLocation", ""),
                    "county": event.get("county", ""),
                }
            )

        # Status detail from the latest event
        status_detail = latest_event.get(
            "status", latest_event.get("statusState", "")
        )

        return {
            "courier": COURIER_SAMEDAY,
            "awb": awb,
            "status": normalized_status,
            "status_label": STATUS_LABELS.get(normalized_status, "Unknown"),
            "status_detail": status_detail,
            "location": location,
            "last_update": last_update,
            "delivered": is_delivered,
            "delivered_date": delivered_date,
            "delivered_to": delivered_to,
            "weight": None,  # Not available in current API response
            "events": events,
            "is_locker_service": is_locker_service,
        }

    def _track_fan(self, awb: str) -> dict[str, Any]:
        """Track a FAN Courier parcel.

        API: POST https://www.fancourier.ro/limit-tracking.php
        Form data: action=get_awb, awb=<number>, lang=romana
        Returns JSON with awbNumber, date, confirmation, events.
        """
        form_data = {
            "action": "get_awb",
            "awb": awb,
            "lang": "romana",
        }

        try:
            response = self._session.post(
                FAN_API_URL, data=form_data, timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout as err:
            raise ColeteApiError(
                f"Timeout connecting to FAN Courier API: {err}"
            ) from err
        except requests.exceptions.ConnectionError as err:
            raise ColeteApiError(
                f"Connection error to FAN Courier API: {err}"
            ) from err
        except requests.exceptions.RequestException as err:
            raise ColeteApiError(
                f"Error fetching FAN Courier data: {err}"
            ) from err

        if response.status_code == 429:
            raise ColeteApiError("FAN Courier API rate limit exceeded")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise ColeteApiError(
                f"HTTP error from FAN Courier API: {err}"
            ) from err

        try:
            data = response.json()
        except ValueError as err:
            raise ColeteApiError(
                f"Invalid JSON from FAN Courier API: {err}"
            ) from err

        # FAN returns empty or error structure for invalid AWBs
        # Real invalid responses: {"message": "..."} with no events/awbNumber
        if not data or (isinstance(data, dict) and data.get("error")):
            raise ColeteNotFoundError(f"FAN Courier AWB {awb} not found")

        # FAN may return a list with one item or a dict directly
        if isinstance(data, list):
            if len(data) == 0:
                raise ColeteNotFoundError(f"FAN Courier AWB {awb} not found")
            data = data[0]

        # Detect invalid AWB: response has "message" but no "events" or "awbNumber"
        if "message" in data and "events" not in data:
            raise ColeteNotFoundError(
                f"FAN Courier AWB {awb} not found: {data.get('message', '')}"
            )

        return self._parse_fan(data, awb)

    def _parse_fan(self, data: dict[str, Any], awb: str) -> dict[str, Any]:
        """Parse FAN Courier API response into normalized format.

        Real API structure:
        {
            "content": "PCA/...",
            "awbNumber": "...",
            "date": "2025-08-04 00:00:00",
            "weight": 5,
            "confirmation": { "name": "...", "date": "..." },
            "returnAwbNumber": null,
            "events": [
                { "id": "C0", "name": "Expeditie ridicata",
                  "location": "Bucuresti", "date": "..." },
                ...
            ],
            "serviceId": 1,
            "optionCodes": ["X"]
        }
        Events are ordered chronologically (oldest first, newest last).
        """
        events_raw = data.get("events", [])
        confirmation = data.get("confirmation", {}) or {}

        # Determine status from events
        normalized_status = STATUS_UNKNOWN
        if events_raw:
            # Events are ordered chronologically, last event is most recent
            last_event = events_raw[-1]
            last_status_id = str(last_event.get("id", ""))
            last_event_name = last_event.get("name", "") or ""

            if last_status_id == FAN_STATUS_DELIVERED:
                normalized_status = STATUS_DELIVERED
            elif last_status_id == FAN_STATUS_DELIVERING:
                normalized_status = STATUS_OUT_FOR_DELIVERY
            elif last_status_id == FAN_STATUS_OUT_FOR_DELIVERY:
                normalized_status = STATUS_OUT_FOR_DELIVERY
            elif last_status_id == FAN_STATUS_PICKED_UP:
                normalized_status = STATUS_PICKED_UP
            elif last_status_id in FAN_IN_TRANSIT_CODES:
                normalized_status = STATUS_IN_TRANSIT
            else:
                # Check if any event is S2 (delivered)
                for event in events_raw:
                    if str(event.get("id", "")) == FAN_STATUS_DELIVERED:
                        normalized_status = STATUS_DELIVERED
                        break
                else:
                    normalized_status = STATUS_IN_TRANSIT

            # Check for locker/fanbox status — parcel deposited in a locker
            # awaiting customer pickup. Override unless already delivered.
            if normalized_status != STATUS_DELIVERED:
                if self._matches_locker_keywords(
                    last_event_name, FAN_LOCKER_KEYWORDS
                ):
                    normalized_status = STATUS_READY_FOR_PICKUP

        # Check for returned parcels (returnAwbNumber populated)
        return_awb = data.get("returnAwbNumber")
        if return_awb and normalized_status != STATUS_DELIVERED:
            normalized_status = STATUS_RETURNED

        # Extract location from latest event
        last_event = events_raw[-1] if events_raw else {}
        location = last_event.get("location", "")
        last_update = last_event.get("date", "")

        # Delivery info
        is_delivered = normalized_status == STATUS_DELIVERED
        delivered_to = confirmation.get("name") if is_delivered else None
        delivered_date = confirmation.get("date") if is_delivered else None

        # Weight is available from FAN API
        weight = data.get("weight")

        # Build normalized events list
        events = []
        for event in events_raw:
            events.append(
                {
                    "date": event.get("date", ""),
                    "status": event.get("name", ""),
                    "location": event.get("location", ""),
                    "status_id": str(event.get("id", "")),
                }
            )

        return {
            "courier": COURIER_FAN,
            "awb": awb,
            "status": normalized_status,
            "status_label": STATUS_LABELS.get(normalized_status, "Unknown"),
            "status_detail": last_event.get("name", ""),
            "location": location,
            "last_update": last_update,
            "delivered": is_delivered,
            "delivered_date": delivered_date,
            "delivered_to": delivered_to,
            "weight": weight,
            "events": events,
        }

    def close(self) -> None:
        """Close the API session."""
        self._session.close()
