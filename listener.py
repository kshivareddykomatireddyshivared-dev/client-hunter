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

# --- 🛡️ JUNK FILTER ---

IGNORE_LIST = [
    "noreply", "no-reply", "alert", "digest", "newsletter", "update",
    "verify", "code", "otp", "statement", "bill", "invoice",
    "pokemon", "linkedin", "quora", "facebook", "instagram", "promotions",
    "marketing", "team", "support", "notifications", "security", "fedex", "tracking",
    "amazon", "adobe", "wordpress", "flipkart", "zomato", "swiggy", "bank",
    "report", "snapcalorie", "wemakescholars", "info", "contact", "hello",
    "donotreply", "automated", "bounced", "mailer-daemon", "postmaster"
]

# --- 🧠 HYBRID ENGINE ---

MODELS = [
    "openai/gpt-oss-120b",                  # 1. HUGE LIMIT (250k tokens/day) - SMARTEST
    "llama-3.3-70b-versatile",              # 2. High Quality (100k tokens)
    "moonshotai/kimi-k2-instruct-0905",     # 3. User Requested
    "qwen-2.5-32b",                         # 4. Coding Expert
    "llama-3.1-8b-instant"                  # 5. Speed Backup
]

# --- Load Secrets with Validation ---

required_env_vars = ["GMAIL_USER", "GMAIL_PASSWORD", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "GROQ_API_KEY"]
missing_vars = [var for var in required_env_vars if var not in os.environ]

if missing_vars:
    raise ValueError(f"❌ Missing environment variables: {', '.join(missing_vars)}")

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

client = Groq(api_key=GROQ_API_KEY)

def send_telegram(message):
    """Send notification to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Telegram returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")

def send_gmail_reply(to_email, subject, body):
    """Send email reply via Gmail SMTP"""
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        return str(e)

def ask_brain_autopilot(email_body, sender_name, subject_line):
    """AI analyzes email and decides response"""
    short_body = email_body[:2500]  # Increased context window

    system_prompt = f"""You are Shiva's AI Assistant analyzing email replies.

OUTPUT ONE OF THESE EXACT CODES:
1. "NEGATIVE_ABORT" - They said: stop, unsubscribe, not interested, remove me, NO, angry tone
2. "IGNORE" - Automated email (Amazon, tracking, bills, newsletters, receipts)
3. "INTERESTED" - They asked questions, want pricing, said "tell me more", curious, positive
4. "NEUTRAL" - Polite but non-committal ("thanks for reaching out", "I'll think about it")

FOR CODES 3 & 4: After the code, write a SHORT 2-sentence reply that:
- Answers their question briefly
- Guides them to WhatsApp for details: {WHATSAPP_LINK}
- Keep it under 50 words, professional tone

EXAMPLES:
Input: "What are your rates?"
Output: INTERESTED
Thanks for your interest! My rates depend on video length and complexity. Let's discuss your specific needs on WhatsApp: {WHATSAPP_LINK}

Input: "Stop emailing me"
Output: NEGATIVE_ABORT

Input: "Your order #12345 has shipped"
Output: IGNORE

Input: "Sounds interesting, tell me more"
Output: INTERESTED
Great! I specialize in Telugu/English scriptwriting for YouTube channels. Let's chat about your content goals here: {WHATSAPP_LINK}

Now analyze this email:
Sender: {sender_name}
Subject: {subject_line}
Body: {short_body}"""

    for model_name in MODELS:
        try:
            print(f"🧠 Thinking with {model_name}...")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this email."}
                ],
                temperature=0.6,
                max_tokens=300
            )
            return completion.choices[0].message.content

        except Exception as e:
            print(f"⚠️ {model_name} failed: {str(e)[:100]}")
            continue

    return "HUMAN_HELP"

def extract_email_body(msg):
    """Extract body text from email (supports HTML and plain text)"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            
            # Try plain text first
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                        break
                except:
                    continue
            
            # Fallback to HTML
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = payload.decode("utf-8", errors="ignore")
                        # Strip HTML tags (basic)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        except:
            pass
    
    return body.strip()

def is_junk_email(sender, subject):
    """Check if email is junk/automated"""
    combined = (sender + " " + subject).lower()
    
    for word in IGNORE_LIST:
        if word in combined:
            return True
    
    # Additional patterns
    if "@" not in sender:  # Malformed sender
        return True
    
    return False

def check_mail():
    """Main function to check and process emails"""
    print("🔍 Connecting to Gmail...")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=30)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, 'UNSEEN')
        if not messages or messages[0] == b'':
            print("✅ No new mail.")
            return

        email_ids = messages[0].split()
        recent_email_ids = email_ids[-15:]  # Check last 15 unread emails
        
        print(f"📬 Found {len(recent_email_ids)} unread emails")

        for e_id in recent_email_ids:
            try:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject_parts = decode_header(msg["Subject"] or "No Subject")
                        subject = ""
                        for part, encoding in subject_parts:
                            if isinstance(part, bytes):
                                subject += part.decode(encoding or "utf-8", errors="ignore")
                            else:
                                subject += str(part)
                        
                        sender = msg.get("From") or "Unknown"
                        
                        # --- JUNK FILTER ---
                        if is_junk_email(sender, subject):
                            print(f"🗑️ Junk: {sender[:50]}")
                            continue
                        
                        # Extract email address
                        reply_to = email.utils.parseaddr(sender)[1]
                        if not reply_to or "@" not in reply_to:
                            print(f"⚠️ Invalid email: {sender}")
                            continue

                        # Extract body
                        body = extract_email_body(msg)
                        
                        if not body or len(body) < 10:
                            print(f"⚠️ Empty email from {sender[:30]}")
                            continue

                        print(f"\n{'='*60}")
                        print(f"✅ Analyzing: {sender[:50]}")
                        print(f"📧 Subject: {subject[:60]}")
                        print(f"{'='*60}\n")
                        
                        # --- AI ANALYSIS ---
                        ai_response = ask_brain_autopilot(body, sender, subject)
                        
                        # --- DECISION MATRIX ---
                        
                        if "IGNORE" in ai_response:
                            print("🤖 AI: Spam/Automated. Skipping.\n")
                            continue
                        
                        elif "NEGATIVE_ABORT" in ai_response:
                            # 🛑 STOP! Don't reply. Just alert.
                            report = (
                                f"🛑 <b>CLIENT SAID NO</b>\n\n"
                                f"<b>From:</b> {html.escape(sender[:60])}\n"
                                f"<b>Subject:</b> {html.escape(subject[:60])}\n\n"
                                f"⚠️ Client is NOT interested. I did NOT reply."
                            )
                            send_telegram(report)
                            print("🛑 Negative response detected. Alert sent.\n")
                        
                        elif "HUMAN_HELP" in ai_response:
                            report = (
                                f"⚠️ <b>I NEED YOUR HELP</b>\n\n"
                                f"<b>From:</b> {html.escape(sender[:60])}\n"
                                f"<b>Subject:</b> {html.escape(subject[:60])}\n\n"
                                f"🤔 AI is confused. Please check manually."
                            )
                            send_telegram(report)
                            print("🤔 AI needs help. Alert sent.\n")
                        
                        else:
                            # ✅ INTERESTED or NEUTRAL -> SEND REPLY
                            
                            # Extract reply text (remove the code)
                            reply_text = ai_response
                            for code in ["INTERESTED", "NEUTRAL"]:
                                reply_text = reply_text.replace(code, "").strip()
                            
                            if len(reply_text) < 20:
                                # AI didn't generate reply properly
                                print("⚠️ AI response too short. Requesting human help.\n")
                                send_telegram(f"⚠️ AI reply was too short for {sender}. Check manually.")
                                continue
                            
                            print(f"🚀 Sending reply to {reply_to}...")
                            success = send_gmail_reply(reply_to, subject, reply_text)
                            
                            if success is True:
                                emoji = "🔥" if "INTERESTED" in ai_response else "📧"
                                report = (
                                    f"{emoji} <b>AUTO-REPLY SENT!</b>\n\n"
                                    f"<b>To:</b> {html.escape(sender[:60])}\n"
                                    f"<b>Subject:</b> {html.escape(subject[:60])}\n\n"
                                    f"<b>My Reply:</b>\n{html.escape(reply_text[:300])}"
                                )
                                send_telegram(report)
                                print(f"✅ Reply sent successfully!\n")
                            else:
                                send_telegram(f"❌ Failed to reply to {sender[:40]}\nError: {success}")
                                print(f"❌ Send failed: {success}\n")
                        
            except Exception as e:
                print(f"❌ Error processing email: {str(e)[:100]}")
                continue

        mail.close()
        mail.logout()
        print("\n✅ Finished checking emails")
    
    except imaplib.IMAP4.error as e:
        error_msg = f"❌ Gmail IMAP Error: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)
    
    except Exception as e:
        error_msg = f"❌ Critical Error: {str(e)[:200]}"
        print(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    check_mail()
                
