import os
import imaplib
import email
import requests
from email.header import decode_header

# Load Secrets
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def check_mail():
    print("Connecting to Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # --- THE FIX IS HERE ---
        # We removed the brackets around 'UNREAD'
        status, messages = mail.search(None, 'UNREAD')
        
        # Check if we got any data back
        if not messages or messages[0] == b'':
            print("No new emails.")
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new emails!")

        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Get Sender
                    sender = msg.get("From")
                    
                    alert_text = f"🔔 <b>NEW EMAIL!</b>\n\n<b>From:</b> {sender}\n<b>Subject:</b> {subject}"
                    send_telegram(alert_text)
                    print(f"Alert sent: {subject}")

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Error: {e}")
        # Only send alert if it's NOT a search error (to avoid spamming you)
        if "SEARCH" not in str(e):
            send_telegram(f"⚠️ Bot Error: {e}")

if __name__ == "__main__":
    check_mail()
    
