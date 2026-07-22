"""
send_referrals.py

Reads recruiter contacts from a CSV, sends each one a personalized referral
request email (with your resume attached), and logs every send to
tracking.json so send_followups.py knows what to follow up on later.

Run:
    python3 send_referrals.py
"""

import csv
import json
import os
import random
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MY_NAME = os.getenv("MY_NAME")
MY_PHONE = os.getenv("MY_PHONE")
MY_EMAIL = os.getenv("MY_EMAIL")
MY_LINKEDIN = os.getenv("MY_LINKEDIN")
RESUME_PATH = os.getenv("RESUME_PATH")

CSV_PATH = "recruiters_sample.csv"
TEMPLATE_PATH = "templates/ref_template.txt"
TRACKING_PATH = "tracking.json"


def load_tracking():
    if Path(TRACKING_PATH).exists():
        with open(TRACKING_PATH) as f:
            return json.load(f)
    return []


def save_tracking(records):
    with open(TRACKING_PATH, "w") as f:
        json.dump(records, f, indent=2, default=str)


def build_message(template_text, row):
    return template_text.format(
        name=row.get("name", "there"),
        company=row.get("company", "the company"),
        job_title=row.get("job_title", "the role"),
        job_id=row.get("job_id", "N/A"),
        job_link=row.get("job_link", ""),
        my_name=MY_NAME,
        my_phone=MY_PHONE,
        my_email=MY_EMAIL,
        my_linkedin=MY_LINKEDIN,
    )


def send_email(to_email, subject, body, attach_path=None):
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg_id = make_msgid(domain="gmail.com")
    msg["Message-ID"] = msg_id
    msg.set_content(body)

    if attach_path and Path(attach_path).exists():
        with open(attach_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=Path(attach_path).name,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    return msg_id


def main():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise SystemExit(
            "Missing GMAIL_ADDRESS / GMAIL_APP_PASSWORD. "
            "Copy .env.example to .env and fill it in first."
        )

    template_text = Path(TEMPLATE_PATH).read_text()
    tracking = load_tracking()
    already_sent = {r["email"] for r in tracking}

    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No rows found in the CSV.")
        return

    for row in rows:
        email = row["email"].strip()
        if email in already_sent:
            print(f"Skipping {email} (already sent).")
            continue

        body = build_message(template_text, row)
        subject_line = (
            f"Referral request for {row.get('job_title', 'the role')} "
            f"({row.get('job_id', 'N/A')}) at {row.get('company', '')}"
        )

        try:
            msg_id = send_email(email, subject_line, body, attach_path=RESUME_PATH)
            print(f"Sent to {email}")
        except Exception as e:
            print(f"FAILED to send to {email}: {e}")
            continue

        tracking.append(
            {
                "email": email,
                "name": row.get("name", ""),
                "company": row.get("company", ""),
                "job_title": row.get("job_title", ""),
                "job_id": row.get("job_id", ""),
                "job_link": row.get("job_link", ""),
                "subject": subject_line,
                "message_id": msg_id,
                "sent_date": datetime.now().isoformat(),
                "followed_up": False,
                "replied": False,
            }
        )
        save_tracking(tracking)

        # Small randomized delay between sends so this doesn't look like a blast
        time.sleep(random.randint(20, 45))

    print("\nDone. See tracking.json for the log of everything sent.")


if __name__ == "__main__":
    main()
