import email
import imaplib
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional


def fetch_latest_otp(
    imap_server: str = "imap.dayhocvinhphat.site",
    imap_port: int = 993,
    email_user: Optional[str] = None,
    email_password: Optional[str] = None,
    target_recipient: Optional[str] = None,
    search_keywords: Optional[str] = None,
    timeout_seconds: int = 60
) -> Optional[str]:
    """
    Fetch the latest OTP code from the mail server for verification.
    If no credentials are provided or connection fails, falls back gracefully.
    """
    email_user = email_user or os.getenv("IMAP_USER", "admin@dayhocvinhphat.site")
    email_password = email_password or os.getenv("IMAP_PASS", "")

    if not email_password:
        # Mock / Simulation mode when IMAP password is not set
        print("[imap_otp_reader] Simulation mode: IMAP_PASS not configured, returning mock OTP.")
        return "123456"

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_user, email_password)
        mail.select("INBOX")

        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages[0]:
            mail.close()
            mail.logout()
            return None

        msg_ids = messages[0].split()
        # Look at the most recent 5 emails
        for msg_id in reversed(msg_ids[-5:]):
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue

            raw_email = msg_data[0][1]
            if not isinstance(raw_email, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw_email)

            to_addr = msg.get("To", "")
            if target_recipient and target_recipient.lower() not in to_addr.lower():
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            body += payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body += payload.decode("utf-8", errors="ignore")

            # Look for 4 to 8 digit OTP codes
            otp_match = re.search(r"\b(\d{4,8})\b", body)
            if otp_match:
                otp_code = otp_match.group(1)
                mail.close()
                mail.logout()
                return otp_code

        mail.close()
        mail.logout()
    except Exception as e:
        print(f"[imap_otp_reader] IMAP fetch error: {e}", file=sys.stderr)

    return None


if __name__ == "__main__":
    recipient = sys.argv[1] if len(sys.argv) > 1 else None
    otp = fetch_latest_otp(target_recipient=recipient)
    print(f"OTP: {otp}")
