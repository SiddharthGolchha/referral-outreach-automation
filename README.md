# Referral Outreach Automation

Sends personalized referral-request emails from a CSV, tracks each one,
and automatically sends a threaded follow-up after N days if there's no reply.

## Folder contents

```
referral_automation/
├── recruiters_sample.csv        # Your contact list (edit this)
├── templates/
│   ├── referral_template.txt    # Initial outreach message
│   └── followup_template.txt    # Follow-up message
├── resume/
│   └── Siddharth_Golchha.pdf    # Attached to every referral email
├── send_referrals.py            # Step 1: send initial emails
├── send_followups.py            # Step 2: run daily, sends follow-ups
├── .env.example                 # Copy to .env and fill in
├── requirements.txt
└── tracking.json                # Auto-created — log of everything sent
```

## 1. One-time setup

### a) Install dependencies
```bash
pip install -r requirements.txt 
or
python3 -m pip install -r requirements.txt
```

### b) Turn on 2-Step Verification on your Google account (if not already on)
https://myaccount.google.com/security

### c) Create a Gmail App Password
1. Go to https://myaccount.google.com/apppasswords
2. Create a new app password (name it anything, e.g. "referral-script")
3. Google gives you a 16-character password — copy it

### d) Configure your credentials
```bash
cp .env.example .env
```
Open `.env` and fill in:
- `GMAIL_ADDRESS` — your Gmail address
- `GMAIL_APP_PASSWORD` — the 16-character app password from step (c)
- Your name, phone, email, LinkedIn (used to personalize templates)

**Never commit `.env` to git or share it — it contains your login credentials.**

## 2. Edit your contact list

Open `recruiters_sample.csv` and replace the sample rows with real contacts.
Columns:

| column     | example                                      |
|------------|-----------------------------------------------|
| email      | priya.sharma@google.com                       |
| name       | Priya Sharma                                   |
| company    | Google                                         |
| job_title  | Backend Software Engineer                      |
| job_id     | REQ12345                                       |
| job_link   | https://careers.google.com/jobs/REQ12345       |

You can rename the file, just update `CSV_PATH` in `send_referrals.py` if you do.

## 3. Edit the templates (optional)

`templates/referral_template.txt` and `templates/followup_template.txt`
use these placeholders, filled in automatically per row:
`{name} {company} {job_title} {job_id} {job_link} {my_name} {my_phone} {my_email} {my_linkedin}`

Feel free to rewrite the wording — just keep the `{...}` placeholders intact.

## 4. Send the initial referral requests

```bash
python3 send_referrals.py
```
- Sends one email per row (with your resume attached)
- Waits 20–45 seconds between sends so it doesn't look like a mass blast
- Logs every send to `tracking.json`
- Safe to re-run — it skips anyone already in `tracking.json`

## 5. Send follow-ups (run this daily)

```bash
python3 send_followups.py
```
For anyone who:
- was emailed 2+ days ago (change via `FOLLOWUP_WAIT_DAYS` in `.env`)
- hasn't replied (checked via IMAP — see note below)
- hasn't already been followed up

...it sends the follow-up template **in the same email thread**.

### Automate it with cron (Linux/Mac)
```bash
crontab -e
```
Add a line to run it every day at 10am:
```
0 10 * * * cd /full/path/to/referral_automation && /usr/bin/python3 send_followups.py >> followup_log.txt 2>&1
```

On Windows, use **Task Scheduler** to run `send_followups.py` daily instead.

## Notes & limitations

- **Reply detection is a practical approximation**, not exact thread-matching:
  it checks whether *any* email arrived in your inbox from that recruiter's
  address after you first emailed them. For a one-person outreach campaign
  this is reliable in practice.
- **Gmail sending limits:** personal Gmail accounts can send ~500 emails/day,
  so this comfortably supports normal job-search volumes.
- **Keep your list personalized and reasonably small** (dozens, not
  hundreds, at once) — this is meant for genuine 1:1 outreach, not bulk
  spam, and un-personalized mass email is more likely to get flagged by
  Gmail's own spam filters anyway.
- All state lives in `tracking.json` — delete an entry (or the whole file)
  to reset and resend to someone.
