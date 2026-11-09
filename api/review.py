"""Draft-page review form -> email to the reviewer.

Vercel Python function at /api/review. The "Ask for changes" and "Approve"
buttons on draft pages post here, so a request arrives even when the device
has no mail app set up (a mailto link silently does nothing then). Same free
Gmail SMTP settings as /api/enquiry, plus:

    REVIEW_PAGE_TO   who gets page reviews (default azim.khan@ais-consulting.co.uk)
"""
import json
import os
import re
import smtplib
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler


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
        length = min(int(self.headers.get("Content-Length") or 0), 60000)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8", "replace") or "{}")
        except ValueError:
            return self._reply(400, {"ok": False, "error": "Bad request."})
        if data.get("company_website"):          # honeypot
            return self._reply(200, {"ok": True})

        page = re.sub(r"[^a-z0-9-]", "", (data.get("page") or "").lower())[:80]
        verdict = "APPROVED" if data.get("verdict") == "approve" else "Changes to"
        message = (data.get("message") or "").strip()[:20000]
        sender = clean(data.get("from"), 120) or "Priya"
        if not page or (verdict != "APPROVED" and not message):
            return self._reply(422, {"ok": False, "error": "Please write what you'd like changed."})

        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_APP_PASSWORD", "").replace(" ", "")
        to = os.environ.get("REVIEW_PAGE_TO", "azim.khan@ais-consulting.co.uk")
        if not (user and password):
            return self._reply(503, {"ok": False, "error": "unconfigured"})

        msg = EmailMessage()
        msg["From"] = f"Mindfully Priya website <{user}>"
        msg["To"] = to
        msg["Subject"] = f"{verdict} page {page}"
        msg.set_content(
            f"From: {sender}\nPage: /{page}\n\n"
            + (message or "Please make this page live.") + "\n")
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
