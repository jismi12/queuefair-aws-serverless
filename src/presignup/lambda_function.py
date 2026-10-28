import os

DOMAINS = [d.strip().lower() for d in os.environ.get("ALLOWED_DOMAINS", "").split(",") if d.strip()]
EMAILS = [e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()]

def handler(event, context):
    email = event["request"]["userAttributes"].get("email", "").strip().lower()
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    if email in EMAILS or domain in DOMAINS:
        return event
    raise Exception("Only college email addresses can register.")
