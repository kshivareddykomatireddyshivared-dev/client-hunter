import os
import imaplib
import smtplib
import email
import email.utils
import requests
import html
import re
import time
from email.header import decode_header
from email.mime.text import MIMEText
from groq import Groq

# --- CONFIGURATION ---

MY_NAME = "Shiva"
WHATSAPP_LINK = "https://wa.me/"
PORTFOLIO_LINK = "https://drive.google.com/drive/folder/#####"

# --- 🛡️ JUNK FILTER ---

IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice",
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions",
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking",
    "amazon", "adobe", "wordpress", "flipkart", "zomato", "swiggy", "bank",
    "report", "snapcalorie", "wemakescholars", "info", "contact", "hello",
    "donotreply", "automated", "bounced", "mailer-daemon", "postmaster"
]

# --- 🧠 HYBRID ENGINE ---

MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "moonshotai/kimi-k2-instruct-0905",
    "qwen-2.5-32b",
    "llama-3.1-8b-instant"
]

# --- Load Secrets with Validation ---

required_env_vars = ["GMAIL_USER", "GMAIL_PASSWORD", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "GROQ_API_KEY"]
missing_vars = [var for var in required_env_vars if var not in os.environ]

if missing_vars:
    raise ValueError(f"❌ Missing environment variables: {', '.join(missing_vars)}")

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

client = Groq(api_key=GROQ_API_KEY)


def safe_html(text, max_len=60):
    """Escape HTML special chars for Telegram — fixes the 400 error"""
    return html.escape(str(text))[:max_len]


def send_telegram(message):
    """Send notification to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Telegram returned: {response.status_code} | {response.text[:200]}")
            # Retry without parse_mode if HTML caused the error
            payload_plain = {"chat_id": CHAT_ID, "text": message}
            response2 = requests.post(url, data=payload_plain, timeout=10)
            if response2.status_code != 200:
                print(f"❌ Telegram retry also failed: {response2.status_code}")
        else:
            print("📲 Telegram notified successfully.")
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")


def send_gmail_reply(to_email, subject, body):
    """Send email reply via Gmail SMTP"""
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        return str(e)


def ask_brain_autopilot(email_body, sender_name, subject_line):
    """AI analyzes email and decides response"""
    short_body = email_body[:2500]

    system_prompt = f"""You are Shiva's AI Assistant analyzing email replies.

OUTPUT FORMAT — always start with ONE of these exact codes on its own line:
NEGATIVE_ABORT - They said: stop, unsubscribe, not interested, remove me, angry tone
IGNORE - Automated email (Amazon, tracking, bills, newsletters, receipts, OTPs)
INTERESTED - They asked questions, want pricing, said "tell me more", positive tone
NEUTRAL - Polite but non-committal ("thanks for reaching out", "I'll think about it")
HUMAN_HELP - You are confused and cannot classify this email

FOR INTERESTED and NEUTRAL: After the code on a new line, write a professional reply (2-3 sentences) that:
- Answers their question briefly and warmly
- Shares WhatsApp for quick discussion: {WHATSAPP_LINK}
- Shares portfolio if they seem interested: {PORTFOLIO_LINK}
- Ends with a friendly sign-off from Shiva

EXAMPLE:
INTERESTED
Thank you for reaching out! I specialize in Telugu and English scriptwriting for YouTube channels. Let's discuss your project on WhatsApp for a quick chat: {WHATSAPP_LINK} — you can also check my portfolio here: {PORTFOLIO_LINK}

Best regards,
Shiva

Now analyze:
Sender: {sender_name}
Subject: {subject_line}
Body: {short_body}"""

    for model_name in MODELS:
        try:
            print(f"🧠 Thinking with {model_name}...")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Analyze this email and respond."}
                ],
                temperature=0.6,
                max_tokens=350
            )
            return completion.choices[0].message.content.strip()

        except Exception as e:
            print(f"⚠️ {model_name} failed: {str(e)[:100]}")
            continue

    return "HUMAN_HELP"


def parse_ai_response(ai_response):
    """
    Robustly parse AI response into (code, reply_text).
    Handles cases where code and reply are on the same line or split by newline.
    """
    CODES = ["NEGATIVE_ABORT", "IGNORE", "INTERESTED", "NEUTRAL", "HUMAN_HELP"]

    lines = ai_response.strip().splitlines()
    detected_code = None
    reply_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        matched = next((c for c in CODES if stripped.startswith(c)), None)
        if matched and detected_code is None:
            detected_code = matched
            # If there's text after the code on the same line, keep it
            remainder = stripped[len(matched):].strip().lstrip(":").strip()
            if remainder:
                reply_lines.append(remainder)
        elif detected_code:
            reply_lines.append(line)

    reply_text = "\n".join(reply_lines).strip()
    return detected_code, reply_text


def extract_email_body(msg):
    """Extract body text from email (supports HTML and plain text)"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                        break
                except:
                    continue

            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = payload.decode("utf-8", errors="ignore")
                        body = re.sub('<[^<]+?>', '', html_body)
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        except:
            pass

    return body.strip()


def is_junk_email(sender, subject):
    """Check if email is junk/automated"""
    combined = (sender + " " + subject).lower()

    for word in IGNORE_LIST:
        if word in combined:
            return True

    if "@" not in sender:
        return True

    return False


def check_mail():
    """Main function to check and process emails"""
    print("🔍 Connecting to Gmail...")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, 'UNSEEN')
        if not messages or messages[0] == b'':
            print("✅ No new mail.")
            return

        email_ids = messages[0].split()
        recent_email_ids = email_ids[-15:]

        print(f"📬 Found {len(recent_email_ids)} unread emails")

        for e_id in recent_email_ids:
            try:
                _, msg_data = mail.fetch(e_id, "(RFC822)")

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Decode subject
                        subject_parts = decode_header(msg["Subject"] or "No Subject")
                        subject = ""
                        for part, encoding in subject_parts:
                            if isinstance(part, bytes):
                                subject += part.decode(encoding or "utf-8", errors="ignore")
                            else:
                                subject += str(part)

                        sender = msg.get("From") or "Unknown"

                        # --- JUNK FILTER ---
                        if is_junk_email(sender, subject):
                            print(f"🗑️ Junk: {sender[:50]}")
                            continue

                        # Extract email address
                        reply_to = email.utils.parseaddr(sender)[1]
                        if not reply_to or "@" not in reply_to:
                            print(f"⚠️ Invalid email: {sender}")
                            continue

                        body = extract_email_body(msg)

                        if not body or len(body) < 10:
                            print(f"⚠️ Empty email from {sender[:30]}")
                            continue

                        print(f"\n{'='*60}")
                        print(f"✅ Analyzing: {sender[:80]}")
                        print(f"📧 Subject: {subject[:60]}")
                        print(f"{'='*60}\n")

                        # --- AI ANALYSIS ---
                        ai_response = ask_brain_autopilot(body, sender, subject)
                        print(f"🤖 Raw AI: {ai_response[:150]}")

                        # --- ROBUST PARSING ---
                        code, reply_text = parse_ai_response(ai_response)

                        if not code:
                            # Fallback: no recognized code found
                            code = "HUMAN_HELP"

                        # --- DECISION MATRIX ---

                        if code == "IGNORE":
                            print("🤖 AI: Spam/Automated. Skipping.\n")
                            continue

                        elif code == "NEGATIVE_ABORT":
                            report = (
                                f"🛑 <b>CLIENT SAID NO</b>\n\n"
                                f"<b>From:</b> {safe_html(sender)}\n"
                                f"<b>Subject:</b> {safe_html(subject)}\n\n"
                                f"⚠️ Client is NOT interested. I did NOT reply."
                            )
                            send_telegram(report)
                            print("🛑 Negative response. Alert sent.\n")

                        elif code == "HUMAN_HELP":
                            report = (
                                f"⚠️ <b>I NEED YOUR HELP</b>\n\n"
                                f"<b>From:</b> {safe_html(sender)}\n"
                                f"<b>Subject:</b> {safe_html(subject)}\n\n"
                                f"🤔 AI is confused. Please check manually."
                            )
                            send_telegram(report)
                            print("🤔 AI needs help. Alert sent.\n")

                        else:
                            # INTERESTED or NEUTRAL -> SEND REPLY
                            if len(reply_text) < 20:
                                # AI didn't generate a usable reply — use fallback
                                print("⚠️ AI reply too short — using fallback template.\n")
                                reply_text = (
                                    f"Thank you for reaching out!\n\n"
                                    f"I'd love to discuss this further. "
                                    f"Please connect with me on WhatsApp for a quick chat: {WHATSAPP_LINK}\n\n"
                                    f"You can also check my portfolio here: {PORTFOLIO_LINK}\n\n"
                                    f"Best regards,\nShiva"
                                )

                            print(f"🚀 Sending reply to {reply_to}...")
                            success = send_gmail_reply(reply_to, subject, reply_text)

                            if success is True:
                                emoji = "🔥" if code == "INTERESTED" else "📧"
                                report = (
                                    f"{emoji} <b>AUTO-REPLY SENT!</b>\n\n"
                                    f"<b>To:</b> {safe_html(sender)}\n"
                                    f"<b>Subject:</b> {safe_html(subject)}\n\n"
                                    f"<b>My Reply:</b>\n{safe_html(reply_text, max_len=400)}"
                                )
                                send_telegram(report)
                                print(f"✅ Reply sent!\n")
                            else:
                                report = (
                                    f"❌ <b>Reply Failed</b>\n\n"
                                    f"<b>To:</b> {safe_html(sender)}\n"
                                    f"<b>Error:</b> {safe_html(str(success), max_len=200)}"
                                )
                                send_telegram(report)
                                print(f"❌ Send failed: {success}\n")

            except Exception as e:
                print(f"❌ Error processing email: {str(e)[:100]}")
                continue

        mail.close()
        mail.logout()
        print("\n✅ Finished checking emails")

    except imaplib.IMAP4.error as e:
        error_msg = f"❌ Gmail IMAP Error: {safe_html(str(e), max_len=200)}"
        print(error_msg)
        send_telegram(error_msg)

    except Exception as e:
        error_msg = f"❌ Critical Error: {safe_html(str(e), max_len=200)}"
        print(error_msg)
        send_telegram(error_msg)


if __name__ == "__main__":
    check_mail()
        
