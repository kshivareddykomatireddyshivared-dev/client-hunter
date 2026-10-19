import os
import smtplib
import re
import asyncio
import html
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from googleapiclient.discovery import build
from groq import Groq
from email.mime.text import MIMEText

# ═══════════════════════════════════════════════════════════════════
# 📝 PASTE YOUR KEYS HERE - FILL IN ALL 6 FIELDS BELOW
# ═══════════════════════════════════════════════════════════════════

GMAIL_USER = " "  # Example: "myemail@gmail.com"
GMAIL_PASS = " "  # 16-char App Password from https://myaccount.google.com/apppasswords

TELEGRAM_TOKEN = " "  # From @BotFather
TELEGRAM_CHAT_ID = " "  # From @userinfobot

GROQ_API_KEY = " "  # From console.groq.com/keys
YOUTUBE_API_KEY = " "  # From console.cloud.google.com

# ═══════════════════════════════════════════════════════════════════
# ⚙️ SETTINGS (You can customize these)
# ═══════════════════════════════════════════════════════════════════

MY_NAME = "YOURNAME"
PORTFOLIO_LINK = "https://drive.google.com/drive/folders/#####your-folder-link######"

NICHES = [
   "Like AI agents"
   "Local AI" #replace with your niches
]

SUBSCRIBER_MIN = 8000  
SUBSCRIBER_MAX = 150000
EMAIL_DELAY_MIN = 0  # Set to 0 for instant sending
EMAIL_DELAY_MAX = 0

MODELS = [
    "gpt-oss-120b",
    "gpt-oss-20b",
    "qwen3-32b",
    "llama-3.3-70b-versatile"
]

# ═══════════════════════════════════════════════════════════════════

HISTORY_FILE = "hunter_history.txt"

# Validate config
missing = []
if not GMAIL_USER: missing.append("GMAIL_USER")
if not GMAIL_PASS: missing.append("GMAIL_PASS")
if not TELEGRAM_TOKEN: missing.append("TELEGRAM_TOKEN")
if not TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
if not GROQ_API_KEY: missing.append("GROQ_API_KEY")
if not YOUTUBE_API_KEY: missing.append("YOUTUBE_API_KEY")

if missing:
    print("\n" + "="*60)
    print("❌ ERROR: Missing configuration!")
    print("="*60)
    print("\nPlease fill in these fields at the top of agent.py:")
    for m in missing:
        print(f"  - {m}")
    print("\n💡 Open agent.py in a text editor and add your keys\n")
    exit(1)

print("✅ Config loaded")

# Test Gmail on startup
print("🔧 Testing Gmail SMTP...")
try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
    print("✅ Gmail authentication works!")
except smtplib.SMTPAuthenticationError:
    print("\n" + "="*60)
    print("❌ GMAIL AUTHENTICATION FAILED!")
    print("="*60)
    print("\nYour GMAIL_PASS is wrong!")
    print("\n🔧 Fix:")
    print("1. Go to: https://myaccount.google.com/apppasswords")
    print("2. Generate a NEW App Password")
    print("3. Copy exactly 16 characters (NO spaces)")
    print("4. Paste into GMAIL_PASS in agent.py")
    print("\nCurrent GMAIL_PASS length:", len(GMAIL_PASS), "chars (should be 16)")
    print("")
    exit(1)
except Exception as e:
    print(f"⚠️ Gmail test warning: {e}")

groq_client = Groq(api_key=GROQ_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(channel_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{channel_id}\n")

def search_youtube():
    results = []
    seen_channels = load_history()

    for niche in random.sample(NICHES, min(3, len(NICHES))):
        try:
            request = youtube.search().list(
                part="snippet",
                q=niche,
                type="video",
                maxResults=10
            )
            response = request.execute()

            for item in response.get('items', []):
                channel_id = item['snippet']['channelId']
                if channel_id in seen_channels:
                    continue

                chan_resp = youtube.channels().list(
                    part="snippet,statistics",
                    id=channel_id
                ).execute()

                if not chan_resp['items']:
                    continue

                channel = chan_resp['items'][0]
                desc = channel['snippet']['description']
                title = channel['snippet']['title']

                email_match = re.search(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    desc
                )

                subs = int(channel['statistics'].get('subscriberCount', 0))

                if email_match and SUBSCRIBER_MIN <= subs <= SUBSCRIBER_MAX:
                    email_addr = email_match.group(0).rstrip('.')

                    if email_addr.count('@') != 1:
                        continue

                    results.append({
                        "name": title,
                        "email": email_addr,
                        "desc": desc,
                        "subs": subs,
                        "channel_id": channel_id
                    })

                    seen_channels.add(channel_id)
                    save_to_history(channel_id)

                    print(f"✅ Found: {title} ({subs:,} subs)")

                    if len(results) >= 5:
                        return results

        except Exception as e:
            print(f"⚠️ Error: {str(e)[:100]}")
            continue

    return results

def generate_pitch(channel_name, channel_desc):
    prompt = f"""Write a short, direct, and professional cold email (under 120 words) proposing a freelance collaboration.

To: {channel_name}
Context: {channel_desc[:200]}

From: {MY_NAME}, Professional Telugu/English scriptwriter
Portfolio: {PORTFOLIO_LINK}

CRITICAL RULES:
1. DO NOT use any emojis whatsoever.
2. DO NOT use special characters, markdown formatting, asterisks (**), or brackets (< >).
3. Write purely in plain text.
4. DO NOT offer fake compliments or act like a fan.
5. Position me as an independent freelancer offering my services for a mutual collaboration, not an employee begging to grow their channel.

Format exactly like this:
Subject: [Direct, plain text subject line about freelance scriptwriting]

[Brief, professional introduction stating who I am and what I do]
[Direct proposal to collaborate on their upcoming Telugu/English videos as a freelance writer]
[Portfolio link]
[Professional call to action to discuss rates and availability]"""

    for model in MODELS:
        try:
            completion = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
            return completion.choices[0].message.content
        except:
            continue

    return f"""Subject: Collaboration Opportunity

Hi {channel_name} team,

I've been following your Telugu content and think we could collaborate. I'm {MY_NAME}, a scriptwriter specializing in Telugu/English YouTube content.

Portfolio: {PORTFOLIO_LINK}

Would you be open to discussing how I can help grow your channel?

Best,
{MY_NAME}"""

import socket

def send_gmail(to_email, subject, body):
    # Set a hard ceiling on ALL socket operations in this thread
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(20)

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = to_email

        if EMAIL_DELAY_MIN > 0:
            delay = random.randint(EMAIL_DELAY_MIN, EMAIL_DELAY_MAX)
            print(f"⏳ Waiting {delay}s...")
            time.sleep(delay)

        print(f"📧 Connecting to Gmail...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
        
        print(f"🔑 Logging in...")
        server.login(GMAIL_USER, GMAIL_PASS)
        
        print(f"📨 Sending to {to_email}...")
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        
        print(f"✅ SENT!")
        server.quit()
        return True

    except smtplib.SMTPAuthenticationError:
        return "AUTH_FAILED"
    except smtplib.SMTPRecipientsRefused as e:
        return f"BAD_RECIPIENT: {e}"
    except smtplib.SMTPException as e:
        return f"SMTP_ERROR: {e}"
    except socket.timeout:
        return "TIMEOUT: Gmail did not respond in time"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        socket.setdefaulttimeout(old_timeout)

async def start_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🏹 <b>Hunting for leads...</b>\n\n"
        f"🎯 Target: {SUBSCRIBER_MIN:,}-{SUBSCRIBER_MAX:,} subs\n"
        f"⏳ This may take 30 seconds...",
        parse_mode="HTML"
    )

    loop = asyncio.get_running_loop()
    leads = await loop.run_in_executor(None, search_youtube)

    if not leads:
        await update.message.reply_text(
            "❌ No new leads found.\n\n"
            "💡 Try again in 1 hour or delete hunter_history.txt"
        )
        return

    await update.message.reply_text(f"🎯 Found {len(leads)} leads!")

    for idx, lead in enumerate(leads):
        pitch = generate_pitch(lead['name'], lead['desc'])

        lead_id = f"{int(time.time())}_{idx}"
        context.user_data[f"pitch_{lead_id}"] = pitch
        context.user_data[f"name_{lead_id}"] = lead['name']
        context.user_data[f"email_{lead_id}"] = lead['email']

        safe_name = html.escape(lead['name'])

        keyboard = [[
            InlineKeyboardButton(
                f"🚀 Send Email",
                callback_data=f"send_{lead_id}"
            )
        ]]

        msg = (
            f"🎯 <b>{safe_name}</b>\n"
            f"👥 {lead['subs']:,} subs\n"
            f"📧 <code>{lead['email']}</code>\n\n"
            f"<b>Preview:</b>\n{html.escape(pitch[:150])}...\n\n"
            f"👇 Click to send"
        )

        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔘 BUTTON CLICK DETECTED!")
    query = update.callback_query
    await query.answer()
    print(f"🔘 Button Data: {query.data}")

    try:
        if not query.data.startswith("send_"):
            return

        lead_id = query.data.split("_", 1)[1]
        pitch = context.user_data.get(f"pitch_{lead_id}")
        name = context.user_data.get(f"name_{lead_id}")
        email = context.user_data.get(f"email_{lead_id}")

        if not pitch or not email:
            await query.edit_message_text(
                "⚠️ Data expired.\n\nRun /hunt again.\n\n"
                "💡 Tip: Don't restart bot between /hunt and clicking Send!"
            )
            return

        # Safer subject extraction
        subject = "Collaboration Opportunity"
        body = pitch
        lines = pitch.splitlines()

        for i, line in enumerate(lines):
            if line.strip().lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                # Rebuild body from everything except the subject line
                body = "\n".join(lines[:i] + lines[i+1:]).strip()
                break

        # Fallback if LLM gave us garbage
        if not subject:
            subject = "Collaboration Opportunity"
        if not body:
            body = f"Hi,\n\nI'm {MY_NAME}, a Telugu/English scriptwriter. I'd love to collaborate.\n\nPortfolio: {PORTFOLIO_LINK}"

        await query.edit_message_text(
            f"⏳ <b>SENDING EMAIL...</b>\n\n"
            f"To: {html.escape(name)}\n"
            f"Email: <code>{email}</code>\n\n"
            f"Please wait...",
            parse_mode="HTML"
        )

        # CRITICAL FIX: wrap the blocking SMTP call in a global timeout
        loop = asyncio.get_running_loop()
        try:
            success = await asyncio.wait_for(
                loop.run_in_executor(None, send_gmail, email, subject, body),
                timeout=35.0
            )
        except asyncio.TimeoutError:
            await query.edit_message_text(
                "❌ <b>SEND TIMEOUT</b>\n\n"
                "Gmail took too long to respond.\n"
                "This usually means rate limiting or a network issue.\n\n"
                "Try again in 2-3 minutes.",
                parse_mode="HTML"
            )
            return

        if success is True:
            await query.edit_message_text(
                f"✅ <b>EMAIL SENT!</b>\n\n"
                f"To: {html.escape(name)}\n"
                f"Email: <code>{email}</code>\n"
                f"Subject: {html.escape(subject)}\n"
                f"Time: {time.strftime('%H:%M:%S')}\n\n"
                f"<b>Message:</b>\n{html.escape(body[:300])}...\n\n"
                f"🎉 Check your Gmail Sent folder to verify!",
                parse_mode="HTML"
            )
        elif success == "AUTH_FAILED":
            await query.edit_message_text(
                f"❌ <b>GMAIL AUTH FAILED!</b>\n\n"
                f"Your GMAIL_PASS is wrong.\n\n"
                f"<b>Fix:</b>\n"
                f"1. Go to: myaccount.google.com/apppasswords\n"
                f"2. Generate NEW App Password\n"
                f"3. Update GMAIL_PASS in agent.py\n"
                f"4. Restart bot\n\n"
                f"Current password length: {len(GMAIL_PASS)} chars\n"
                f"(Should be exactly 16)",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ <b>SEND FAILED</b>\n\n"
                f"Error: {html.escape(str(success))[:400]}\n\n"
                f"Check your internet connection or try /test first.",
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"❌ Button error: {e}")
        try:
            await query.edit_message_text(
                f"❌ <b>ERROR</b>\n\n"
                f"{html.escape(str(e))[:200]}\n\n"
                f"Try /hunt again or restart bot.",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if Gmail works by sending email to yourself"""
    await update.message.reply_text("🧪 Testing Gmail... Sending email to yourself...")

    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(
        None,
        send_gmail,
        GMAIL_USER,
        "Test from Bot",
        f"This is a test email sent at {time.strftime('%H:%M:%S')}\n\nIf you received this, your bot works!"
    )

    if success is True:
        await update.message.reply_text(
            "✅ <b>TEST PASSED!</b>\n\n"
            "Gmail is working!\n"
            "Check your inbox for test email.\n\n"
            "Now try /hunt to find leads!",
            parse_mode="HTML"
        )
    elif success == "AUTH_FAILED":
        await update.message.reply_text(
            "❌ <b>TEST FAILED - Auth Error</b>\n\n"
            "Your GMAIL_PASS is wrong.\n\n"
            "Fix:\n"
            "1. Go to myaccount.google.com/apppasswords\n"
            "2. Generate NEW App Password (16 chars)\n"
            "3. Update GMAIL_PASS in agent.py\n"
            "4. Restart bot"
        )
    else:
        await update.message.reply_text(
            f"❌ <b>TEST FAILED</b>\n\n"
            f"Error: {str(success)[:200]}"
        )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print("🤖 EMAIL AGENT STARTING (MCP Headless Mode)")
        leads = search_youtube()
        if not leads:
            print("No leads found.")
        else:
            print(f"Found {len(leads)} leads:")
            for idx, lead in enumerate(leads):
                print(f"{idx+1}. {lead['name']} ({lead['subs']} subs) - {lead['email']}")
        sys.exit(0)

    print("="*60)
    print("🤖 EMAIL AGENT STARTING")
    print("="*60)
    print(f"Gmail: {GMAIL_USER}")
    print(f"Target: {SUBSCRIBER_MIN:,}-{SUBSCRIBER_MAX:,} subs")
    print(f"Contacted: {len(load_history())} channels")
    print("="*60)
    print()
    print("Commands:")
    print("  /test - Test Gmail (sends email to yourself)")
    print("  /hunt - Find YouTube leads")
    print()

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
      )

    app.add_handler(CommandHandler("hunt", start_hunt))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CallbackQueryHandler(button_click))

    print("✅ Bot ready!")
    app.run_polling(allowed_updates=Update.ALL_TYPES) 
