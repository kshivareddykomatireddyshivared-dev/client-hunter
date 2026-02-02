import os
import imaplib
import email
import requests
import html
import time
from email.header import decode_header
from groq import Groq

# --- CONFIGURATION ---
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/1SIbyVhHF9RuasqP0zcYMjX6DeFypSPvg"
MY_NAME = "Shiva"

# --- JUNK FILTER ---
IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice", 
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions", 
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking"
]

# --- 🧠 HYBRID ENGINE ---
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
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

def ask_brain_smart(email_body, sender_name, subject_line):
    short_body = email_body[:1500]
    
    system_prompt = f"""
    You are the AI Secretary for {MY_NAME}, a professional Scriptwriter.
    RULES:
    1. If this is a REPLY (Subject has 'Re:'), draft a polite response.
    2. If it's Spam/Automated -> Reply exactly: "IGNORE"
    3. If asking Price -> Say: "Let's discuss on WhatsApp."
    4. If asking Samples -> Share Portfolio: {PORTFOLIO_LINK}
    Output: Only the draft reply.
    """
    
    # --- FAILOVER LOOP ---
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
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                print(f"⚠️ {model_name} limit reached! Switching...")
                continue 
            else:
                return f"Brain Error: {error_msg}"
    
    return "❌ All AI Models are busy."

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
        recent_email_ids = email_ids[-20:] # Check last 20
        
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

                        # Get Body
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
                        ai_draft = ask_brain_smart(body, sender, subject)
                        
                        if "IGNORE" in ai_draft: continue

                        report = (
                            f"🔔 NEW CLIENT REPLY!\n"
                            f"From: {sender}\n"
                            f"Subject: {subject}\n\n"
                            f"📝 Draft Reply:\n{ai_draft}"
                        )
                        send_telegram(report)
                        
            except Exception as e:
                print(f"Skipping email error: {e}")
                continue

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    check_mail()
    
