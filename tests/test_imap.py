"""Tests for the IMAP scanner AWB extraction and utilities.

These tests verify pure functions from imap_scanner.py without requiring
homeassistant to be installed. We mock the import chain to isolate the scanner.

The local Python is 3.9 but the integration targets HA (Python 3.12+).
Some modules use `str | None` union syntax (PEP 604) which fails at parse-time
on 3.9. We mock those modules before they're imported.
"""

import importlib
import re
import sys
import types
from unittest.mock import MagicMock

import pytest

# ── Mock homeassistant and problematic modules before any colete import ────
_ha_mock = MagicMock()
for mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.data_entry_flow",
    "homeassistant.exceptions",
    "voluptuous",
]:
    sys.modules.setdefault(mod, _ha_mock)

# Create the custom_components.colete package namespace without running __init__
# This avoids loading coordinator.py (which uses PEP 604 on Python 3.9)
_cc = types.ModuleType("custom_components")
_cc.__path__ = ["custom_components"]
sys.modules.setdefault("custom_components", _cc)

_colete = types.ModuleType("custom_components.colete")
_colete.__path__ = ["custom_components/colete"]
sys.modules.setdefault("custom_components.colete", _colete)

# Load const.py directly (pure Python, no HA deps, no PEP 604 issues)
_const_spec = importlib.util.spec_from_file_location(
    "custom_components.colete.const",
    "custom_components/colete/const.py",
)
_const_mod = importlib.util.module_from_spec(_const_spec)
sys.modules["custom_components.colete.const"] = _const_mod
_const_spec.loader.exec_module(_const_mod)
_colete.const = _const_mod

# Load imap_scanner.py (depends only on const + stdlib)
_scanner_spec = importlib.util.spec_from_file_location(
    "custom_components.colete.imap_scanner",
    "custom_components/colete/imap_scanner.py",
)
_scanner_mod = importlib.util.module_from_spec(_scanner_spec)
sys.modules["custom_components.colete.imap_scanner"] = _scanner_mod
_scanner_spec.loader.exec_module(_scanner_mod)
_colete.imap_scanner = _scanner_mod

from custom_components.colete.imap_scanner import (  # noqa: E402
    ImapAwbScanner,
    ExtractedAwb,
    ScanResult,
    _html_to_text,
)
from custom_components.colete.const import (  # noqa: E402
    AWB_KEYWORD_PATTERNS,
    COURIER_SENDER_HINTS,
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_IMAP_LOOKBACK_DAYS,
    DEFAULT_IMAP_SCAN_INTERVAL,
    IMAP_SENSOR_TYPES,
    SENSOR_TYPE_IMAP_STATUS,
    SENSOR_TYPE_IMAP_LAST_SCAN,
    SENSOR_TYPE_IMAP_AWBS_FOUND,
    CONF_ENTRY_TYPE,
    ENTRY_TYPE_PARCEL,
    ENTRY_TYPE_IMAP,
)


# ============================================================
# AWB regex extraction tests
# ============================================================


class TestAwbExtraction:
    """Test AWB number extraction from email text."""

    def test_awb_keyword_basic(self):
        """Test 'AWB: 1234567890' pattern."""
        awbs = ImapAwbScanner._extract_awbs(
            "Comanda dvs. AWB: 1234567890 a fost expediata."
        )
        assert awbs == ["1234567890"]

    def test_awb_keyword_hash(self):
        """Test 'AWB #1234567890' pattern."""
        awbs = ImapAwbScanner._extract_awbs("AWB #9876543210")
        assert awbs == ["9876543210"]

    def test_awb_keyword_no_separator(self):
        """Test 'AWB1234567890' — digits immediately after AWB."""
        awbs = ImapAwbScanner._extract_awbs("Numarul AWB1234567890 este valid.")
        assert awbs == ["1234567890"]

    def test_numar_urmarire(self):
        """Test Romanian 'numar de urmarire: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs(
            "Numarul de urmarire: 5566778899 pentru coletul tau."
        )
        assert awbs == ["5566778899"]

    def test_numar_urmarire_without_de(self):
        """Test 'numar urmarire: ...' pattern (without 'de')."""
        awbs = ImapAwbScanner._extract_awbs("Numar urmarire: 1122334455")
        assert awbs == ["1122334455"]

    def test_tracking_number(self):
        """Test English 'tracking number: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs(
            "Your tracking number: 9988776655 for order #123"
        )
        assert awbs == ["9988776655"]

    def test_tracking_plain(self):
        """Test 'tracking: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs("Tracking: 1122334455")
        assert awbs == ["1122334455"]

    def test_colet_keyword(self):
        """Test 'colet: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs(
            "Coletul dvs cu numarul colet: 5544332211"
        )
        assert awbs == ["5544332211"]

    def test_coletul_keyword(self):
        """Test 'coletul ...' pattern (with suffix)."""
        awbs = ImapAwbScanner._extract_awbs("Coletul 5544332211 a fost expediat.")
        assert awbs == ["5544332211"]

    def test_expediere_keyword(self):
        """Test 'expediere: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs("Numar expediere: 6677889900")
        assert awbs == ["6677889900"]

    def test_expedierea_keyword(self):
        """Test 'expedierea ...' variant."""
        awbs = ImapAwbScanner._extract_awbs("Expedierea 6677889900 in curs")
        assert awbs == ["6677889900"]

    def test_livrare_keyword(self):
        """Test 'livrare: ...' pattern."""
        awbs = ImapAwbScanner._extract_awbs("Numar livrare: 1122334455")
        assert awbs == ["1122334455"]

    def test_livrarea_keyword(self):
        """Test 'livrarea ...' variant."""
        awbs = ImapAwbScanner._extract_awbs("Livrarea 1122334455 confirmata")
        assert awbs == ["1122334455"]

    def test_multiple_awbs_deduplicated(self):
        """Test that duplicate AWBs from different patterns are deduplicated."""
        text = "AWB: 1234567890 -- tracking: 1234567890 -- colet: 1234567890"
        awbs = ImapAwbScanner._extract_awbs(text)
        assert awbs == ["1234567890"]

    def test_multiple_distinct_awbs(self):
        """Test extraction of multiple distinct AWBs from one text."""
        text = (
            "Comanda 1: AWB: 1111111111\n"
            "Comanda 2: AWB: 2222222222\n"
            "Comanda 3: tracking: 3333333333"
        )
        awbs = ImapAwbScanner._extract_awbs(text)
        assert awbs == ["1111111111", "2222222222", "3333333333"]

    def test_awb_too_short_ignored(self):
        """Test that numbers shorter than 8 digits are rejected."""
        awbs = ImapAwbScanner._extract_awbs("AWB: 1234567")  # 7 digits
        assert awbs == []

    def test_awb_min_length_accepted(self):
        """Test that exactly 8-digit AWBs are accepted."""
        awbs = ImapAwbScanner._extract_awbs("AWB: 12345678")
        assert awbs == ["12345678"]

    def test_awb_max_length_accepted(self):
        """Test that 20-digit AWBs are accepted."""
        awb20 = "1" * 20
        awbs = ImapAwbScanner._extract_awbs(f"AWB: {awb20}")
        assert awbs == [awb20]

    def test_awb_all_zeros_ignored(self):
        """Test that AWBs starting with 00000 are rejected (sanity check)."""
        awbs = ImapAwbScanner._extract_awbs("AWB: 00000123456789")
        assert awbs == []

    def test_no_awb_in_text(self):
        """Test that irrelevant text returns no AWBs."""
        awbs = ImapAwbScanner._extract_awbs(
            "Buna ziua, comanda dvs. a fost procesata. Va multumim!"
        )
        assert awbs == []

    def test_case_insensitive(self):
        """Test that patterns match case-insensitively."""
        awbs = ImapAwbScanner._extract_awbs("awb: 1234567890")
        assert awbs == ["1234567890"]
        awbs2 = ImapAwbScanner._extract_awbs("TRACKING NUMBER: 9876543210")
        assert awbs2 == ["9876543210"]

    def test_real_sameday_email_pattern(self):
        """Test AWB extraction from a realistic Sameday shipping email."""
        text = (
            "Comanda ta de pe emag.ro a fost expediata!\n\n"
            "Detalii expediere:\n"
            "Curier: Sameday\n"
            "AWB: 4EMGLN159150598\n\n"  # Note: has alphanumeric prefix
            "Numarul de urmarire: 159150598\n"
            "Poti urmari coletul pe sameday.ro"
        )
        awbs = ImapAwbScanner._extract_awbs(text)
        # 4EMGLN159150598 won't match because AWB patterns only capture \d{8,20}
        # But 159150598 (9 digits) from "urmarire" will match
        assert "159150598" in awbs

    def test_real_fan_courier_pattern(self):
        """Test AWB extraction from a FAN Courier style notification."""
        text = (
            "Coletul dumneavoastra a fost expediat prin FAN Courier.\n"
            "AWB: 2166050860023\n"
            "Puteti urmari coletul pe fancourier.ro"
        )
        awbs = ImapAwbScanner._extract_awbs(text)
        assert awbs == ["2166050860023"]

    def test_awb_in_subject_and_body(self):
        """Test that AWBs are found in combined subject+body text."""
        combined = "Colet expediat AWB: 1234567890\nMultumim pentru comanda!"
        awbs = ImapAwbScanner._extract_awbs(combined)
        assert awbs == ["1234567890"]


# ============================================================
# HTML to text conversion tests
# ============================================================


class TestHtmlToText:
    """Test HTML-to-text conversion used for email body parsing."""

    def test_simple_html(self):
        """Test basic HTML tag stripping."""
        html = "<p>Hello <b>world</b></p>"
        text = _html_to_text(html)
        assert "Hello" in text
        assert "world" in text
        assert "<p>" not in text
        assert "<b>" not in text

    def test_script_and_style_excluded(self):
        """Test that script and style content is excluded."""
        html = (
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert('hi')</script>"
            "<p>AWB: 1234567890</p></body></html>"
        )
        text = _html_to_text(html)
        assert "AWB" in text
        assert "1234567890" in text
        assert "alert" not in text
        assert "color:red" not in text

    def test_empty_html(self):
        """Test empty HTML returns empty text."""
        text = _html_to_text("")
        assert text.strip() == ""

    def test_plain_text_passthrough(self):
        """Test that non-HTML text passes through unchanged."""
        text = _html_to_text("Just plain text with AWB: 1234567890")
        assert "AWB: 1234567890" in text


# ============================================================
# Email header decoding tests
# ============================================================


class TestDecodeHeader:
    """Test email header decoding."""

    def test_plain_ascii(self):
        """Test plain ASCII header is returned as-is."""
        result = ImapAwbScanner._decode_header("Hello World")
        assert result == "Hello World"

    def test_empty_header(self):
        """Test empty header returns empty string."""
        result = ImapAwbScanner._decode_header("")
        assert result == ""

    def test_encoded_utf8(self):
        """Test RFC2047 encoded UTF-8 header."""
        encoded = "=?utf-8?Q?Coletul_t=C4=83u?="
        result = ImapAwbScanner._decode_header(encoded)
        assert "Coletul" in result

    def test_encoded_base64(self):
        """Test RFC2047 base64 encoded header."""
        import base64

        text = "Test Subject"
        encoded = f"=?utf-8?B?{base64.b64encode(text.encode()).decode()}?="
        result = ImapAwbScanner._decode_header(encoded)
        assert result == text


# ============================================================
# Email body extraction tests
# ============================================================


class TestGetBodyText:
    """Test email body text extraction from email.message.Message objects."""

    @staticmethod
    def _make_html_email(html: str):
        """Create a simple HTML email message."""
        from email.mime.text import MIMEText

        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = "Test HTML"
        msg["From"] = "test@example.com"
        return msg

    @staticmethod
    def _make_multipart_email(plain: str, html: str):
        """Create a multipart email with both plain and HTML parts."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Test Multipart"
        msg["From"] = "test@example.com"
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        return msg

    def test_html_body(self):
        """Test extraction from HTML-only email (converts to text)."""
        msg = self._make_html_email(
            "<html><body><p>AWB: 9876543210</p></body></html>"
        )
        body = ImapAwbScanner._get_body_text(msg)
        assert "9876543210" in body
        assert "<p>" not in body

    def test_multipart_prefers_plain(self):
        """Test that multipart email prefers plain text over HTML."""
        msg = self._make_multipart_email(
            "AWB plain: 1111111111",
            "<p>AWB html: 2222222222</p>",
        )
        body = ImapAwbScanner._get_body_text(msg)
        assert "1111111111" in body


# ============================================================
# Data classes tests
# ============================================================


class TestDataClasses:
    """Test IMAP scanner data classes."""

    def test_scan_result_defaults(self):
        """Test ScanResult default values."""
        result = ScanResult()
        assert result.awbs == []
        assert result.emails_scanned == 0
        assert result.errors == []

    def test_extracted_awb_creation(self):
        """Test ExtractedAwb creation and fields."""
        awb = ExtractedAwb(
            awb="1234567890",
            courier_hint="sameday",
            subject="Your order shipped",
            sender="shop@emag.ro",
            date="Thu, 20 Mar 2026 10:00:00 +0200",
            email_uid="123",
        )
        assert awb.awb == "1234567890"
        assert awb.courier_hint == "sameday"
        assert awb.email_uid == "123"

    def test_scan_result_accumulation(self):
        """Test adding AWBs to ScanResult."""
        result = ScanResult()
        result.emails_scanned = 5
        result.awbs.append(
            ExtractedAwb(
                awb="1111111111",
                courier_hint="auto",
                subject="Test",
                sender="test@test.com",
                date="",
                email_uid="1",
            )
        )
        assert len(result.awbs) == 1
        assert result.emails_scanned == 5


# ============================================================
# Courier sender hint detection tests
# ============================================================


class TestCourierSenderHints:
    """Test courier detection from sender domain hints."""

    def test_sameday_domain(self):
        """Test sameday.ro sender hint."""
        assert COURIER_SENDER_HINTS.get("sameday.ro") == "sameday"
        assert COURIER_SENDER_HINTS.get("sameday.com") == "sameday"

    def test_fan_courier_domain(self):
        """Test fancourier.ro sender hint."""
        assert COURIER_SENDER_HINTS.get("fancourier.ro") == "fan_courier"
        assert COURIER_SENDER_HINTS.get("fan-courier.ro") == "fan_courier"

    def test_cargus_domain(self):
        """Test cargus.ro sender hint."""
        assert COURIER_SENDER_HINTS.get("cargus.ro") == "cargus"

    def test_gls_domain(self):
        """Test GLS sender hints."""
        assert COURIER_SENDER_HINTS.get("gls-romania.ro") == "gls"
        assert COURIER_SENDER_HINTS.get("gls-group.eu") == "gls"

    def test_dpd_domain(self):
        """Test DPD sender hints."""
        assert COURIER_SENDER_HINTS.get("dpd.ro") == "dpd"
        assert COURIER_SENDER_HINTS.get("dpd.com") == "dpd"

    def test_unknown_domain_returns_none(self):
        """Test that unknown domains return None (auto-detect)."""
        assert COURIER_SENDER_HINTS.get("emag.ro") is None
        assert COURIER_SENDER_HINTS.get("altex.ro") is None
        assert COURIER_SENDER_HINTS.get("gmail.com") is None


# ============================================================
# IMAP Constants tests
# ============================================================


class TestImapConstants:
    """Test IMAP-related constants are properly defined."""

    def test_imap_defaults(self):
        """Test IMAP default values."""
        assert DEFAULT_IMAP_PORT == 993
        assert DEFAULT_IMAP_FOLDER == "INBOX"
        assert DEFAULT_IMAP_LOOKBACK_DAYS == 7
        assert DEFAULT_IMAP_SCAN_INTERVAL == 300

    def test_imap_sensor_types(self):
        """Test IMAP sensor type definitions."""
        assert SENSOR_TYPE_IMAP_STATUS in IMAP_SENSOR_TYPES
        assert SENSOR_TYPE_IMAP_LAST_SCAN in IMAP_SENSOR_TYPES
        assert SENSOR_TYPE_IMAP_AWBS_FOUND in IMAP_SENSOR_TYPES
        # Each should have name and icon
        for key, info in IMAP_SENSOR_TYPES.items():
            assert "name" in info, f"Missing 'name' for {key}"
            assert "icon" in info, f"Missing 'icon' for {key}"

    def test_entry_type_constants(self):
        """Test entry type discriminator constants."""
        assert CONF_ENTRY_TYPE == "entry_type"
        assert ENTRY_TYPE_PARCEL == "parcel"
        assert ENTRY_TYPE_IMAP == "imap"

    def test_awb_patterns_count(self):
        """Test that all 6 AWB patterns are defined."""
        assert len(AWB_KEYWORD_PATTERNS) == 6

    def test_awb_patterns_have_named_group(self):
        """Test that all AWB patterns have a named 'awb' capture group."""
        for i, pattern in enumerate(AWB_KEYWORD_PATTERNS):
            compiled = re.compile(pattern)
            assert "awb" in compiled.groupindex, (
                f"Pattern {i} missing named group 'awb': {pattern}"
            )
