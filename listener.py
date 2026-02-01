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
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def ask_brain(email_body, sender_name):
    """
    Sends the email content to DeepSeek to generate a smart strategy.
    """
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
            model="deepseek-r1-distill-llama-70b",  # <--- Fixed comma here
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

        # Search UNREAD only
        status, messages = mail.search(None, 'UNREAD')
        if not messages or messages[0] == b'':
            print("No new mail.")
            return

        email_ids = messages[0].split()
        
        for e_id in email_ids:
            # Fetch Email
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Get Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Get Body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # --- 🛡️ PRIVACY CHECK ---
                    if any(s.lower() in body.lower() for s in SENSITIVE_WORDS):
                        print(f"🔒 Sensitive email detected ({subject}). Ignoring.")
                        continue 

                    # --- 🧠 AI ANALYSIS ---
                    sender = msg.get("From")
                    print(f"Analyzing email from: {sender}")
                    
                    ai_draft = ask_brain(body, sender)
                    
                    report = (
                        f"🕵️ <b>SECRETARY REPORT</b>\n"
                        f"<b>From:</b> {sender}\n"
                        f"<b>Subject:</b> {subject}\n\n"
                        f"🧠 <b>AI Suggested Reply:</b>\n"
                        f"<pre>{ai_draft}</pre>\n\n"
                        f"<i>Copy the text above and send it!</i>"
                    )
                    send_telegram(report)

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_mail()
    
