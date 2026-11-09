"""Organisation enquiry form -> email to Priya.

Vercel Python function at /api/enquiry. Sends through the same free Gmail SMTP
account the review emails use (an app password), so it costs nothing. Settings
are Vercel environment variables, never committed:

    SMTP_USER           Gmail address that sends (e.g. horizon.esg@gmail.com)
    SMTP_APP_PASSWORD   its app password
    ENQUIRY_TO          where enquiries land (hello@mindfullypriya.com)

Nothing is stored. A hidden honeypot field drops most bots silently.
"""
import json
import os
import re
import smtplib
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TYPES = {"A workshop or wellbeing session", "Individual coaching",
         "Leadership or team development", "Not sure yet"}


def clean(v, limit):
    return re.sub(r"[\r\n]+", " ", (v or "").strip())[:limit]


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = min(int(self.headers.get("Content-Length") or 0), 20000)
        raw = self.rfile.read(length).decode("utf-8", "replace")
        if "json" in (self.headers.get("Content-Type") or ""):
            try:
                data = json.loads(raw or "{}")
            except ValueError:
                return self._reply(400, {"ok": False, "error": "Bad request."})
        else:
            data = {k: v[0] for k, v in parse_qs(raw).items()}

        if data.get("company_website"):          # honeypot: pretend success
            return self._reply(200, {"ok": True})

        name = clean(data.get("name"), 120)
        email = clean(data.get("email"), 200)
        org = clean(data.get("organisation"), 200)
        kind = clean(data.get("type"), 80)
        kind = kind if kind in TYPES else "Not sure yet"
        message = (data.get("message") or "").strip()[:4000]
        if not name or not EMAIL_RE.match(email):
            return self._reply(422, {"ok": False,
                                     "error": "Please add your name and a valid email address."})

        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_APP_PASSWORD", "").replace(" ", "")
        to = os.environ.get("ENQUIRY_TO", "hello@mindfullypriya.com")
        if not (user and password):
            return self._reply(503, {"ok": False, "error": "unconfigured"})

        msg = EmailMessage()
        msg["From"] = f"Mindfully Priya website <{user}>"
        msg["To"] = to
        msg["Reply-To"] = email
        msg["Subject"] = f"Organisation enquiry: {kind} - {org or name}"
        msg.set_content(
            f"New enquiry from the Organisations page.\n\n"
            f"Name: {name}\nEmail: {email}\nOrganisation: {org or '-'}\n"
            f"Interested in: {kind}\n\n{message or '(no message)'}\n\n"
            f"Reply to this email to answer {name} directly.\n")
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
                s.starttls()
                s.login(user, password)
                s.send_message(msg)
        except Exception:
            return self._reply(502, {"ok": False, "error": "send-failed"})
        return self._reply(200, {"ok": True})

    def do_GET(self):
        self._reply(405, {"ok": False, "error": "POST only"})
