import os
import imaplib
import email
import requests
import time
from email.header import decode_header
from groq import Groq

# --- CONFIGURATION ---
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/1SIbyVhHF9RuasqP0zcYMjX6DeFypSPvg"
WHATSAPP_LINK = "https://wa.me/919391577137?text=Hello"
MY_NAME = "Shiva"

# --- THE BOUNCER (Junk Filter) ---
# If the Sender or Subject contains these words, we IGNORE them.
IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice", 
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions", 
    "marketing", "team", "support", "notifications"
]

# Load Secrets
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# Initialize Brain
client = Groq(api_key=GROQ_API_KEY)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")

def ask_brain(email_body, sender_name):
    # --- CRASH FIX: THE HAIRCUT ---
    # We truncate the email to 1000 characters max. 
    # This prevents the "Request too large" error completely.
    short_body = email_body[:1000] 
    
    system_prompt = f"""
    You are the AI Secretary for {MY_NAME}, a professional Scriptwriter.
    Your goal is to convert leads into WhatsApp conversations.
    
    RULES:
    1. If the email is a Job Offer or Client Lead -> Write a draft reply.
    2. If it is Spam/Newsletter/Automated -> Reply exactly: "IGNORE"
    3. If asking for Price -> Say: "Let's discuss on WhatsApp."
    4. If asking for Samples -> Share Portfolio: {PORTFOLIO_LINK}
    5. Keep it short (under 50 words).
    
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

        status, messages = mail.search(None, 'UNSEEN')
        if not messages or messages[0] == b'':
            print("No new mail.")
            return

        email_ids = messages[0].split()
        # Check last 5 emails
        recent_email_ids = email_ids[-5:] 
        
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

                        # --- 🚫 THE BOUNCER (Junk Check) ---
                        is_junk = False
                        for word in IGNORE_LIST:
                            if word.lower() in sender.lower() or word.lower() in subject.lower():
                                print(f"🗑️ Junk detected ({word}): {subject}")
                                is_junk = True
                                break
                        
                        if is_junk:
                            continue # Skip to next email

                        # Get Body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode("utf-8", errors="ignore")
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="ignore")

                        print(f"✅ Analyzing potential client: {sender}")
                        
                        # Get AI Draft
                        ai_reply = ask_brain(body, sender)
                        
                        # Double Check: If AI says "IGNORE", we don't message you
                        if "IGNORE" in ai_reply:
                            print("🤖 AI said this is spam. Skipping.")
                            continue

                        report = (
                            f"🕵️ SECRETARY REPORT\n"
                            f"From: {sender}\n"
                            f"Subject: {subject}\n\n"
                            f"🧠 Suggested Reply:\n{ai_reply}\n"
                        )
                        send_telegram(report)
                        time.sleep(2) # Avoid rate limits
                        
            except Exception as e:
                print(f"Skipping email error: {e}")
                continue

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    check_mail()
    
