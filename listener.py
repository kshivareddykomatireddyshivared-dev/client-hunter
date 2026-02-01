import os
import imaplib
import requests

# Load Secrets
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASSWORD"]
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def debug_print(msg):
    print(f"🧐 DEBUG: {msg}")

def test_telegram():
    debug_print("--- STEP 1: TESTING TELEGRAM ---")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": "🚨 DIAGNOSTIC TEST: I am alive!"}
    
    try:
        response = requests.post(url, data=payload)
        debug_print(f"Telegram API Status: {response.status_code}")
        debug_print(f"Telegram API Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ TELEGRAM IS WORKING!")
        else:
            print("❌ TELEGRAM FAILED. Check your Chat ID or Token.")
    except Exception as e:
        print(f"❌ TELEGRAM ERROR: {e}")

def test_gmail():
    debug_print("\n--- STEP 2: TESTING GMAIL ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        print("✅ Gmail Login Success!")
        
        mail.select("inbox")
        
        # Search for ANY email (Read or Unread) just to test connection
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()
        
        count = len(email_ids)
        print(f"✅ Gmail Connection Good! Found {count} total emails in your Inbox.")
        
        if count == 0:
            print("⚠️ Inbox is empty? (This is rare)")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"❌ GMAIL FAILED: {e}")

if __name__ == "__main__":
    print("🚀 STARTING DIAGNOSTIC MODE...")
    test_telegram()
    test_gmail()
    print("🏁 DIAGNOSTIC FINISHED.")
    
