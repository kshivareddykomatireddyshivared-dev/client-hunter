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

# --- 🧠 SMART FILTERS ---
# The bot will ONLY alert you if the subject contains these words
# "Re:" is the most important one for replies.
KEYWORDS = ["Re:", "Project", "Script", "Proposal", "Collab", "Inquiry", "Payment"]

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

        # Search for UNREAD emails only
        status, messages = mail.search(None, 'UNREAD')
        
        if not messages or messages[0] == b'':
            print("No new unread emails.")
            return

        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} unread emails. Filtering for clients...")

        for e_id in email_ids:
            try:
                # Fetch headers
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode Subject
                        subject_raw = msg["Subject"]
                        subject = "No Subject"
                        if subject_raw:
                            decoded_list = decode_header(subject_raw)
                            subject, encoding = decoded_list[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8")
                        
                        sender = msg.get("From")
                        
                        # --- 🧠 FILTER LOGIC ---
                        # Check if any keyword matches the subject
                        is_important = any(word.lower() in subject.lower() for word in KEYWORDS)
                        
                        if is_important:
                            print(f"✅ MATCH FOUND: {subject}")
                            alert_text = (
                                f"🚨 <b>CLIENT REPLY DETECTED!</b>\n\n"
                                f"👤 <b>From:</b> {sender}\n"
                                f"📝 <b>Subject:</b> {subject}\n"
                                f"👉 <i>Check your Gmail now!</i>"
                            )
                            send_telegram(alert_text)
                        else:
                            print(f"🗑️ Ignored (Spam/Not Important): {subject}")

            except Exception as e:
                print(f"Error reading email {e_id}: {e}")

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    check_mail()
    
