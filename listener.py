import os
import imaplib
import email
import requests
from email.header import decode_header

# Load Secrets from GitHub
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # We use data dict to handle special characters better
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def check_mail():
    print("Connecting to Gmail...")
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search for UNREAD emails
        status, messages = mail.search(None, '(UNREAD)')
        
        # If no emails found, messages is usually [b'']
        if not messages[0]:
            print("No new emails.")
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new emails!")

        for e_id in email_ids:
            # Fetch the email headers
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
                    
                    # Send Alert to Telegram
                    alert_text = f"🔔 <b>NEW EMAIL!</b>\n\n<b>From:</b> {sender}\n<b>Subject:</b> {subject}"
                    send_telegram(alert_text)
                    print(f"Alert sent: {subject}")

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Error: {e}")
        # Optional: Send error to Telegram so you know if it crashes
        # send_telegram(f"⚠️ Bot Error: {str(e)}")

if __name__ == "__main__":
    check_mail()
  
