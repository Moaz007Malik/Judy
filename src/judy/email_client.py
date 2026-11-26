from __future__ import annotations
import smtplib, urllib.parse, webbrowser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .config import Settings, get_smtp_password

EMAIL_TEMPLATES = {
    "Web Design & Digital Upgrade": {
        "subject": "Quick question regarding {company}'s digital presence",
        "body": """Hi {name},

I came across {company} while researching top {niche} businesses in {location}, and I was really impressed with your track record.

I noticed a few high-impact opportunities on your website and online funnels that could significantly increase conversions and bring in more qualified client inquiries every week.

We recently helped a similar company in your space revamp their web experience, resulting in a 40% increase in inbound leads within 30 days.

Would you be open to a brief 5-minute chat this Thursday to see what this could look like for {company}?

Best regards,
{sender_name}
"""
    },
    "AI Automation & Operations": {
        "subject": "Automating client inquiries for {company}",
        "body": """Hi {name},

I hope this finds you well.

I'm reaching out because we help growing companies in the {niche} space automate repetitive administrative tasks, customer follow-ups, and inbound lead qualification using smart AI workflows.

For {company}, this typically saves 15+ hours per week per team member while ensuring zero leads slip through the cracks.

Do you have 10 minutes next week to explore if this could help streamline your operations?

Best,
{sender_name}
"""
    },
    "Client Acquisition & Growth": {
        "subject": "Partnership idea for {company} — New client pipeline",
        "body": """Hi {name},

I hope you're having a productive week.

I specialize in B2B client acquisition for {niche} firms in {location}. We build outbound client pipelines that consistently generate booked appointments with decision-makers on your calendar.

Given {company}'s reputation, I'm confident we could help you bring on 3–5 new high-ticket clients every month on a performance-driven basis.

Let me know if you're open to seeing a quick breakdown of how this works.

Warm regards,
{sender_name}
"""
    },
    "Quick Follow-Up": {
        "subject": "Following up: {company} growth strategy",
        "body": """Hi {name},

Just following up on my previous note. I know you're busy running {company}, so I'll keep this short.

If expanding your client base or modernizing your systems is on your radar this quarter, I'd love to share two quick actionable ideas tailored to {company}.

Would a quick call this Friday work for you?

Best,
{sender_name}
"""
    }
}

class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_draft(self, template_key: str, lead: dict, custom_offer: str = "", ai_client=None) -> tuple[str, str]:
        name = lead.get("name") or "there"
        company = lead.get("company") or "your company"
        niche = lead.get("niche") or "industry"
        location = lead.get("location") or "your area"
        sender = self.settings.sender_name or "Judy Partner"

        if ai_client and custom_offer:
            prompt = f"""Write a compelling, concise, high-converting cold outreach email to a potential client.
Recipient Name: {name}
Company Name: {company}
Industry/Niche: {niche}
Location: {location}
Service Offered: {custom_offer}
Sender Name: {sender}

Guidelines:
- Keep it under 130 words.
- Professional, friendly, value-focused, zero spammy buzzwords.
- Clear low-friction call to action (e.g. 5-minute chat).
- Format output as:
SUBJECT: <subject line>
BODY:
<body text>"""
            try:
                reply = ai_client.reply([{"role": "user", "content": prompt}])
                if "SUBJECT:" in reply and "BODY:" in reply:
                    parts = reply.split("BODY:")
                    subject = parts[0].replace("SUBJECT:", "").strip()
                    body = parts[1].strip()
                    return subject, body
            except Exception:
                pass

        tmpl = EMAIL_TEMPLATES.get(template_key) or EMAIL_TEMPLATES["Web Design & Digital Upgrade"]
        subject = tmpl["subject"].format(name=name, company=company, niche=niche, location=location, sender_name=sender)
        body = tmpl["body"].format(name=name, company=company, niche=niche, location=location, sender_name=sender)
        return subject, body

    def send_via_smtp(self, to_email: str, subject: str, body: str) -> tuple[bool, str]:
        s = self.settings
        if not s.smtp_username or not s.sender_email:
            return False, "SMTP username and Sender Email are not configured. Open Settings -> Email to configure your SMTP credentials."

        password = get_smtp_password(s)
        if not password:
            return False, "SMTP Password is not set. Please save your email password in Settings."

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{s.sender_name} <{s.sender_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15)
            server.starttls()
            server.login(s.smtp_username, password)
            server.send_message(msg)
            server.quit()
            return True, f"Successfully sent email to {to_email}!"
        except Exception as e:
            return False, f"Failed to send email via SMTP: {e}"

    def open_in_mail_app(self, to_email: str, subject: str, body: str) -> tuple[bool, str]:
        try:
            params = {
                "subject": subject,
                "body": body
            }
            query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            mailto_url = f"mailto:{to_email}?{query}"
            webbrowser.open(mailto_url)
            return True, f"Opened {to_email} in your default email application."
        except Exception as e:
            return False, f"Could not launch mail application: {e}"
