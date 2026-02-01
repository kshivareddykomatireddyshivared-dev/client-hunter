import os
import imaplib
import email
import requests
from email.header import decode_header
from groq import Groq

# --- CONFIGURATION ---
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/1SIbyVhHF9RuasqP0zcYMjX6DeFypSPvg"
WHATSAPP_LINK = "https://wa.me/919391577137?text=Hello"
MY_NAME = "Shiva"

# Load Secrets
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# Initialize Brain
client = Groq(api_key=GROQ_API_KEY)

# --- PRIVACY SHIELD ---
SENSITIVE_WORDS = ["otp", "verification code", "password reset", "bank", "debit", "credit card", "login alert", "security code"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Sending plain text to ensure delivery even if AI uses weird symbols
    payload = {"chat_id": CHAT_ID, "text": message}
    
    try:
        response = requests.post(url, data=payload)
        print(f"📨 Telegram Sent. Server Reply: {response.text}")
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")

def ask_brain(email_body, sender_name):
    system_prompt = f"""
    You are the AI Secretary for {MY_NAME}, a professional Scriptwriter.
    Your goal is to convert leads into WhatsApp conversations.
    
    RULES:
    1. If they ask for Price/Cost -> Say: "Let's discuss the package on WhatsApp for a custom deal."
    2. If they ask for Samples -> Share this Portfolio: {PORTFOLIO_LINK}
    3. If they ask for Phone Number -> Do NOT give it. Ask {MY_NAME} (Boss) for permission.
    4. NEVER promise delivery dates or specific results.
    5. Keep the tone professional, short, and persuasive.
    
    Output Format:
    Write a short draft reply that {MY_NAME} can copy-paste.
    """
    
    try:
        completion = client.chat.completions.create(
            # --- UPDATED MODEL HERE ---
            model="llama-3.3-70b-versatile",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Client Email: {email_body}"}
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
        # Check last 5 emails to be safe
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

                        if any(s.lower() in body.lower() for s in SENSITIVE_WORDS):
                            print(f"🔒 Sensitive email detected ({subject}). Ignoring.")
                            continue 

                        sender = msg.get("From")
                        print(f"Analyzing email from: {sender}")
                        
                        ai_draft = ask_brain(body, sender)
                        
                        report = (
                            f"🕵️ SECRETARY REPORT\n"
                            f"From: {sender}\n"
                            f"Subject: {subject}\n\n"
                            f"🧠 AI Suggested Reply:\n"
                            f"{ai_draft}\n\n"
                            f"-- End Report --"
                        )
                        send_telegram(report)
            except Exception as e:
                print(f"Skipping email due to error: {e}")
                continue

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    check_mail()
    
