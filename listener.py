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

# --- 🛡️ EXPANDED JUNK FILTER ---
IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice", 
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions", 
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking",
    "amazon", "adobe", "wordpress", "flipkart", "zomato", "swiggy", "bank", 
    "report", "snapcalorie", "wemakescholars", "info", "contact", "hello"
]

# --- 🧠 HYBRID ENGINE ---
MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
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
    You are Shiva's AI Assistant.
    
    CRITICAL RULE:
    - ONLY write a reply if this is a REAL HUMAN CLIENT interested in scriptwriting.
    - If this is a Newsletter, Receipt, Spam, Automated Notification, or from Amazon/Adobe/etc -> Output EXACTLY: "IGNORE"
    
    GOAL:
    - If it's a real client, get them to WhatsApp: {WHATSAPP_LINK}
    - Keep it under 50 words. Professional tone.
    
    SCENARIOS:
    1. Asking Price/Samples -> "Let's discuss on WhatsApp: {WHATSAPP_LINK}"
    2. "Interested" -> "Great! Message me here: {WHATSAPP_LINK}"
    3. Confusing/Angry -> "HUMAN_HELP"
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

                        # --- 🛡️ STRICT FILTERING ---
                        
                        # 1. MUST BE A REPLY (Contain "Re:" or "RE:")
                        # If it's not a reply, we assume it's a newsletter/spam and ignore it.
                        if "re:" not in subject.lower():
                            print(f"🚫 Ignoring (Not a reply): {subject}")
                            continue

                        # 2. CHECK BLACKLIST
                        is_junk = False
                        for word in IGNORE_LIST:
                            if word.lower() in sender.lower() or word.lower() in subject.lower():
                                print(f"🗑️ Junk detected: {sender}")
                                is_junk = True
                                break
                        if is_junk: continue
                        
                        # Extract Email Address
                        reply_to = email.utils.parseaddr(sender)[1]

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

                        print(f"✅ Analyzing Client: {sender}")
                        ai_response = ask_brain_autopilot(body, sender, subject)
                        
                        if "IGNORE" in ai_response:
                            print("🤖 AI identified spam. Ignoring.")
                            continue
                        
                        elif "HUMAN_HELP" in ai_response:
                            report = (
                                f"⚠️ <b>I NEED YOUR HELP</b>\n"
                                f"From: {sender}\n"
                                f"Subject: {subject}\n\n"
                                f"Client seems confused. Please reply manually."
                            )
                            send_telegram(report)
                        else:
                            # REAL CLIENT? SEND IT! 🚀
                            print(f"🚀 Replying to {reply_to}...")
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
                                send_telegram(f"❌ Failed to Reply: {success}")
                        
            except Exception as e:
                print(f"Error: {e}")
                continue

        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    check_mail()
    
