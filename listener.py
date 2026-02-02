import os
import imaplib
import smtplib
import email
import requests
import html
import time
from email.header import decode_header
from email.mime.text import MIMEText
from groq import Groq

# --- CONFIGURATION ---
MY_NAME = "Shiva"
WHATSAPP_LINK = "https://wa.me/919391577137?text=Hi%20Shiva,%20I%20am%20interested%20in%20scriptwriting"
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/1SIbyVhHF9RuasqP0zcYMjX6DeFypSPvg"

# --- JUNK FILTER ---
IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice", 
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions", 
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking"
]

# --- 🧠 HYBRID ENGINE (Updated with 120B Model) ---
MODELS = [
    "openai/gpt-oss-120b",            # 1. HUGE LIMIT (250k tokens)
    "llama-3.3-70b-versatile",        # 2. High Quality
    "moonshotai/kimi-k2-instruct-0905", 
    "qwen-2.5-32b",                   
    "llama-3.1-8b-instant"            
]

# Load Secrets
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

client = Groq(api_key=GROQ_API_KEY)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")

def send_gmail_reply(to_email, subject, body):
    # Ensure subject has "Re:"
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject
        
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        return str(e)

def ask_brain_autopilot(email_body, sender_name, subject_line):
    short_body = email_body[:2000]
    
    system_prompt = f"""
    You are Shiva's AI Personal Assistant.
    YOUR GOAL: Get the client to message Shiva on WhatsApp: {WHATSAPP_LINK}
    
    STRATEGY:
    1. If they ask for PRICE/COST -> Reply: "Pricing depends on the project scope. Let's discuss it quickly on WhatsApp here: {WHATSAPP_LINK}"
    2. If they ask for CONTACT -> Reply: "You can reach me directly on WhatsApp: {WHATSAPP_LINK}"
    3. If they say "INTERESTED" -> Reply: "Great! Let's finalize the details. Please message me on WhatsApp: {WHATSAPP_LINK}"
    4. If they ask for SAMPLES -> Reply: "Here is my portfolio: {PORTFOLIO_LINK} . Let me know on WhatsApp what you think!"
    
    CRITICAL RULES:
    - Keep it SHORT (under 50 words).
    - Be professional but direct.
    - If the email is confusing, angry, or requires complex human thought, output EXACTLY: "HUMAN_HELP"
    - Do NOT output "Subject:" or any other text, just the email body.
    """
    
    for model_name in MODELS:
        try:
            print(f"🧠 Thinking with {model_name}...")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Sender: {sender_name}\nSubject: {subject_line}\nEmail: {short_body}..."}
                ],
                temperature=0.6,
                max_tokens=200
            )
            return completion.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ {model_name} failed. Switching...")
            continue 
    
    return "HUMAN_HELP"

def check_mail():
    print("Connecting to Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, 'UNSEEN')
        if not messages or messages[0] == b'':
            print("No new mail.")
            return

        email_ids = messages[0].split()
        recent_email_ids = email_ids[-10:] # Check last 10
        
        print(f"Checking {len(recent_email_ids)} emails...")

        for e_id in recent_email_ids:
            try:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        sender = msg.get("From") or ""

                        # --- VIP RULE ---
                        is_reply = "re:" in subject.lower()
                        is_junk = False
                        if not is_reply:
                            for word in IGNORE_LIST:
                                if word.lower() in sender.lower() or word.lower() in subject.lower():
                                    print(f"🗑️ Junk: {subject}")
                                    is_junk = True
                                    break
                        if is_junk: continue
                        
                        # Extract Email Address for Replying
                        reply_to = email.utils.parseaddr(sender)[1]

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload: body = payload.decode("utf-8", errors="ignore")
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload: body = payload.decode("utf-8", errors="ignore")

                        print(f"✅ Analyzing: {sender}")
                        ai_response = ask_brain_autopilot(body, sender, subject)
                        
                        # --- AUTO-PILOT DECISION ---
                        if "HUMAN_HELP" in ai_response or "IGNORE" in ai_response:
                            # Too complex? Alert Shiva.
                            report = (
                                f"⚠️ <b>I NEED YOUR HELP</b>\n"
                                f"From: {sender}\n"
                                f"Subject: {subject}\n\n"
                                f"I didn't auto-reply because the client seems confused or angry. Please check."
                            )
                            send_telegram(report)
                        else:
                            # CONFIDENT? AUTO-SEND! 🚀
                            print(f"🚀 Auto-Replying to {reply_to}...")
                            success = send_gmail_reply(reply_to, subject, ai_response)
                            
                            if success is True:
                                report = (
                                    f"✅ <b>AUTO-REPLY SENT!</b>\n"
                                    f"To: {sender}\n"
                                    f"Subject: {subject}\n\n"
                                    f"<b>I said:</b>\n{ai_response}"
                                )
                                send_telegram(report)
                            else:
                                send_telegram(f"❌ Failed to Auto-Reply: {success}")
                        
            except Exception as e:
                print(f"Error: {e}")
                continue

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    check_mail()
    
