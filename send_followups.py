"""
send_followups.py

Checks tracking.json for referral requests that:
  1. Were sent FOLLOWUP_WAIT_DAYS or more days ago
  2. Haven't been followed up on yet
  3. Haven't received a reply (checked via IMAP)

For any that qualify, sends the follow-up template IN THE SAME THREAD
(using In-Reply-To / References headers).

Run this once a day, e.g. via cron:
    python3 send_followups.py

Note on reply detection: this does a simple IMAP check for any inbox
message FROM the recruiter's email address received after you emailed
them. It isn't a perfect thread-match, but it's a solid practical proxy —
if they replied at all, this will almost always catch it.
"""

import imaplib
import json
import os
import random
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MY_NAME = os.getenv("MY_NAME")
MY_PHONE = os.getenv("MY_PHONE")
MY_EMAIL = os.getenv("MY_EMAIL")
MY_LINKEDIN = os.getenv("MY_LINKEDIN")
FOLLOWUP_WAIT_DAYS = int(os.getenv("FOLLOWUP_WAIT_DAYS", "2"))

TRACKING_PATH = "tracking.json"
TEMPLATE_PATH = "templates/followup_template.txt"


def load_tracking():
    with open(TRACKING_PATH) as f:
        return json.load(f)


def save_tracking(records):
    with open(TRACKING_PATH, "w") as f:
        json.dump(records, f, indent=2, default=str)


def has_replied(recruiter_email, since_date):
    """Rough check: any inbox message FROM this recruiter since we emailed them."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    imap.select("INBOX")

    date_str = since_date.strftime("%d-%b-%Y")
    typ, data = imap.search(None, f'(FROM "{recruiter_email}" SINCE {date_str})')
    imap.logout()

    return typ == "OK" and len(data[0].split()) > 0


def build_followup(template_text, record):
    return template_text.format(
        name=record.get("name", "there"),
        company=record.get("company", "the company"),
        job_title=record.get("job_title", "the role"),
        job_id=record.get("job_id", "N/A"),
        job_link=record.get("job_link", ""),
        my_name=MY_NAME,
        my_phone=MY_PHONE,
        my_email=MY_EMAIL,
        my_linkedin=MY_LINKEDIN,
    )


def send_followup_email(to_email, subject, body, in_reply_to, references):
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg["In-Reply-To"] = in_reply_to
    msg["References"] = references or in_reply_to
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def main():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise SystemExit(
            "Missing GMAIL_ADDRESS / GMAIL_APP_PASSWORD. "
            "Copy .env.example to .env and fill it in first."
        )

    if not Path(TRACKING_PATH).exists():
        print("No tracking.json found yet. Run send_referrals.py first.")
        return

    tracking = load_tracking()
    template_text = Path(TEMPLATE_PATH).read_text()
    now = datetime.now()
    updated = False

    for record in tracking:
        if record.get("followed_up") or record.get("replied"):
            continue

        sent_date = datetime.fromisoformat(record["sent_date"])
        if now - sent_date < timedelta(days=FOLLOWUP_WAIT_DAYS):
            continue

        print(f"Checking replies from {record['email']}...")
        try:
            if has_replied(record["email"], sent_date):
                print("  -> Reply found. Marking as replied, no follow-up needed.")
                record["replied"] = True
                updated = True
                continue
        except Exception as e:
            print(f"  -> Couldn't check inbox ({e}); sending follow-up anyway.")

        body = build_followup(template_text, record)
        try:
            send_followup_email(
                record["email"],
                record["subject"],
                body,
                in_reply_to=record["message_id"],
                references=record["message_id"],
            )
            print(f"  -> Follow-up sent to {record['email']}")
            record["followed_up"] = True
            updated = True
        except Exception as e:
            print(f"  -> FAILED to send follow-up: {e}")

        time.sleep(random.randint(20, 45))

    if updated:
        save_tracking(tracking)

    print("\nDone.")


if __name__ == "__main__":
    main()
