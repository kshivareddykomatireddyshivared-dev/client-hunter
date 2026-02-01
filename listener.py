import os
import imaplib
import email
import requests
import html
from email.header import decode_header
from groq import Groq

# --- CONFIGURATION ---
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/1SIbyVhHF9RuasqP0zcYMjX6DeFypSPvg"
MY_NAME = "Shiva"

# --- JUNK FILTER (Save CPU & Money) ---
IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice", 
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions", 
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking"
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

def ask_brain(email_body, sender_name):
    short_body = email_body[:1000]
    
    system_prompt = f"""
    You are the AI Secretary for {MY_NAME}, a professional Scriptwriter.
    
    RULES:
    1. If it's a Client/Job -> Write a draft reply.
    2. If it's Spam/Newsletter -> Reply exactly: "IGNORE"
    3. If asking Price -> Say: "Let's discuss on WhatsApp."
    4. If asking Samples -> Share Portfolio: {PORTFOLIO_LINK}
    5. Keep it short.
    
    Output: Only the draft reply.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Sender: {sender_name}\nEmail: {short_body}..."}
            ],
            temperature=0.6,
            max_tokens=200
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Brain Error: {str(e)}"

def check_mail():
    print("Connecting to Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search UNSEEN (Unread) emails only
        status, messages = mail.search(None, 'UNSEEN')
        
        if not messages or messages[0] == b'':
            print("No new mail.")
            return

        email_ids = messages[0].split()
        
        # --- ⚡ THE SPEED FIX ⚡ ---
        # Only take the last 10 emails (The most recent ones).
        # This prevents it from reading 1000s of old unread emails.
        recent_email_ids = email_ids[-10:] 
        
        print(f"Checking {len(recent_email_ids)} recent unread emails...")

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

                        # --- 1. JUNK FILTER ---
                        is_junk = False
                        for word in IGNORE_LIST:
                            if word.lower() in sender.lower() or word.lower() in subject.lower():
                                print(f"🗑️ Junk detected ({word}): {subject}")
                                is_junk = True
                                break
                        
                        if is_junk: continue

                        # --- 2. GET BODY ---
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
                        
                        # --- 3. ASK BRAIN ---
                        ai_draft = ask_brain(body, sender)
                        
                        if "IGNORE" in ai_draft:
                            print("🤖 AI said IGNORE.")
                            continue

                        # --- 4. SEND ALERT ---
                        report = (
                            f"🔔 NEW CLIENT EMAIL!\n"
                            f"From: {sender}\n"
                            f"Subject: {subject}\n\n"
                            f"📝 Suggested Reply:\n{ai_draft}"
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
    
