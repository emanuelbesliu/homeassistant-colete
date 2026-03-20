"""IMAP email scanner for automatic AWB extraction.

Connects to an IMAP mailbox, searches for shipping notification emails,
and extracts AWB/tracking numbers using keyword-based regex patterns.
All methods are synchronous (designed to be wrapped in async_add_executor_job).
"""

from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any

from .const import AWB_KEYWORD_PATTERNS, COURIER_SENDER_HINTS

_LOGGER = logging.getLogger(__name__)

# Pre-compile AWB regex patterns
_COMPILED_AWB_PATTERNS = [re.compile(p) for p in AWB_KEYWORD_PATTERNS]


class _HtmlTextExtractor(HTMLParser):
    """Simple HTML-to-text converter (strips tags, keeps text content)."""

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._text_parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._text_parts)


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text."""
    parser = _HtmlTextExtractor()
    try:
        parser.feed(html)
        return parser.get_text()
    except Exception:  # noqa: BLE001
        # If HTML parsing fails, return raw HTML (regex will still work)
        return html


@dataclass
class ExtractedAwb:
    """An AWB number extracted from an email."""

    awb: str
    courier_hint: str  # Courier slug from sender hint, or "auto"
    subject: str
    sender: str
    date: str
    email_uid: str  # IMAP UID for dedup


@dataclass
class ScanResult:
    """Result of an IMAP scan."""

    awbs: list[ExtractedAwb] = field(default_factory=list)
    emails_scanned: int = 0
    errors: list[str] = field(default_factory=list)


class ImapAwbScanner:
    """Scans an IMAP mailbox for shipping notification emails and extracts AWBs.

    All methods are synchronous — call from async_add_executor_job.
    """

    def __init__(
        self,
        server: str,
        port: int,
        email_address: str,
        password: str,
        folder: str = "INBOX",
        lookback_days: int = 7,
    ) -> None:
        self._server = server
        self._port = port
        self._email = email_address
        self._password = password
        self._folder = folder
        self._lookback_days = lookback_days
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        """Connect and authenticate to the IMAP server."""
        _LOGGER.debug("Connecting to IMAP server %s:%s", self._server, self._port)
        self._conn = imaplib.IMAP4_SSL(self._server, self._port)
        self._conn.login(self._email, self._password)
        _LOGGER.debug("IMAP login successful for %s", self._email)

    def close(self) -> None:
        """Close the IMAP connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                self._conn.logout()
            except Exception:  # noqa: BLE001
                pass
            self._conn = None

    def validate_connection(self) -> bool:
        """Test IMAP connection and login. Returns True on success.

        Used during config flow to validate credentials.
        """
        try:
            self.connect()
            # Try selecting the folder to verify it exists
            if self._conn:
                status, _ = self._conn.select(self._folder, readonly=True)
                if status != "OK":
                    raise ImapScannerError(
                        f"Cannot select folder '{self._folder}'"
                    )
            return True
        finally:
            self.close()

    def scan(self, seen_uids: set[str] | None = None) -> ScanResult:
        """Scan the mailbox for emails containing AWB numbers.

        Args:
            seen_uids: Set of IMAP UIDs already processed (skip these).

        Returns:
            ScanResult with extracted AWBs and scan metadata.
        """
        result = ScanResult()
        if seen_uids is None:
            seen_uids = set()

        try:
            self.connect()
            assert self._conn is not None

            # Select folder (read-only — we never modify emails)
            status, data = self._conn.select(self._folder, readonly=True)
            if status != "OK":
                result.errors.append(f"Cannot select folder '{self._folder}'")
                return result

            # Build IMAP search criteria: emails from the last N days
            since_date = datetime.now(timezone.utc) - timedelta(
                days=self._lookback_days
            )
            since_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f"(SINCE {since_str})"

            _LOGGER.debug(
                "IMAP search: %s in folder %s", search_criteria, self._folder
            )
            status, msg_nums = self._conn.uid("search", None, search_criteria)
            if status != "OK" or not msg_nums or not msg_nums[0]:
                _LOGGER.debug("No emails found matching criteria")
                return result

            uids = msg_nums[0].split()
            _LOGGER.debug("Found %d emails to scan", len(uids))

            for uid_bytes in uids:
                uid = uid_bytes.decode("utf-8", errors="replace")

                # Skip already-processed emails
                if uid in seen_uids:
                    continue

                try:
                    awbs = self._process_email(uid)
                    result.emails_scanned += 1
                    result.awbs.extend(awbs)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Error processing email UID %s: %s", uid, err)
                    result.errors.append(f"UID {uid}: {err}")

            _LOGGER.debug(
                "Scan complete: %d emails scanned, %d AWBs found",
                result.emails_scanned,
                len(result.awbs),
            )

        except imaplib.IMAP4.error as err:
            error_msg = f"IMAP error: {err}"
            _LOGGER.error(error_msg)
            result.errors.append(error_msg)
        except Exception as err:  # noqa: BLE001
            error_msg = f"Unexpected error: {err}"
            _LOGGER.error(error_msg)
            result.errors.append(error_msg)
        finally:
            self.close()

        return result

    def _process_email(self, uid: str) -> list[ExtractedAwb]:
        """Fetch and parse a single email, extracting any AWB numbers."""
        assert self._conn is not None

        status, msg_data = self._conn.uid("fetch", uid, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            return []

        raw_email = msg_data[0]
        if isinstance(raw_email, tuple):
            raw_bytes = raw_email[1]
        else:
            return []

        msg = email.message_from_bytes(raw_bytes)

        # Extract metadata
        subject = self._decode_header(msg.get("Subject", ""))
        sender = self._decode_header(msg.get("From", ""))
        date_str = msg.get("Date", "")

        # Get sender domain for courier hint
        sender_email = email.utils.parseaddr(sender)[1].lower()
        sender_domain = sender_email.split("@")[1] if "@" in sender_email else ""
        courier_hint = COURIER_SENDER_HINTS.get(sender_domain, "auto")

        # Extract email body text
        body_text = self._get_body_text(msg)

        # Also check subject line for AWBs
        full_text = f"{subject}\n{body_text}"

        # Extract AWB numbers
        awb_numbers = self._extract_awbs(full_text)

        results = []
        for awb in awb_numbers:
            results.append(
                ExtractedAwb(
                    awb=awb,
                    courier_hint=courier_hint,
                    subject=subject[:200],  # Truncate long subjects
                    sender=sender_email,
                    date=date_str,
                    email_uid=uid,
                )
            )

        if results:
            _LOGGER.debug(
                "Email UID %s (%s): found AWBs %s",
                uid,
                subject[:60],
                [r.awb for r in results],
            )

        return results

    @staticmethod
    def _decode_header(value: str) -> str:
        """Decode an email header value (handles encoded words)."""
        if not value:
            return ""
        decoded_parts = email.header.decode_header(value)
        parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                parts.append(
                    part.decode(charset or "utf-8", errors="replace")
                )
            else:
                parts.append(part)
        return " ".join(parts)

    @staticmethod
    def _get_body_text(msg: email.message.Message) -> str:
        """Extract plain text from an email message (handles multipart)."""
        text_parts: list[str] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_parts.append(
                            payload.decode(charset, errors="replace")
                        )
                elif content_type == "text/html" and not text_parts:
                    # Only use HTML if no plain text found yet
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html = payload.decode(charset, errors="replace")
                        text_parts.append(_html_to_text(html))
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    text = _html_to_text(text)
                text_parts.append(text)

        return "\n".join(text_parts)

    @staticmethod
    def _extract_awbs(text: str) -> list[str]:
        """Extract AWB numbers from text using keyword-based patterns.

        Returns deduplicated list of AWB strings found in the text.
        """
        found: dict[str, None] = {}  # Ordered set (preserve discovery order)

        for pattern in _COMPILED_AWB_PATTERNS:
            for match in pattern.finditer(text):
                awb = match.group("awb")
                # Basic sanity: AWBs should be 8-20 digits, not all zeros
                if awb and not awb.startswith("00000") and len(awb) >= 8:
                    found[awb] = None

        return list(found.keys())


class ImapScannerError(Exception):
    """Error from the IMAP scanner."""
