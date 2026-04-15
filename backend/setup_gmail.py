"""
╔══════════════════════════════════════════════════════════╗
║  CIRS — Gmail API OAuth2 Setup Script                    ║
║  Run this ONCE to authorize Gmail API access             ║
║  Then gmail_token.json will be created automatically     ║
╚══════════════════════════════════════════════════════════╝

STEPS BEFORE RUNNING THIS:
1. Go to https://console.cloud.google.com
2. Create a new project (name: "CDGI-CIRS")
3. Enable Gmail API: APIs & Services → Enable APIs → search "Gmail API" → Enable
4. Create OAuth2 credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON file
   - Rename it to: credentials.json
   - Put it in this backend/ folder
5. Run: python setup_gmail.py
6. Browser will open → login with your Gmail → Allow
7. gmail_token.json will be created → done!
"""

import os, json

def setup():
    print("━"*55)
    print("  📧  CDGI CIRS — Gmail API Setup")
    print("━"*55)

    creds_file = "credentials.json"
    token_file = "gmail_token.json"
    scopes = ["https://www.googleapis.com/auth/gmail.send"]

    if not os.path.exists(creds_file):
        print(f"""
❌ credentials.json not found!

Please follow these steps:
1. Go to: https://console.cloud.google.com
2. Create/select project "CDGI-CIRS"
3. Go to: APIs & Services → Library
4. Search "Gmail API" → Click Enable
5. Go to: APIs & Services → Credentials
6. Click: Create Credentials → OAuth client ID
7. Application type: Desktop app
8. Name: CDGI-CIRS
9. Click Create → Download JSON
10. Rename downloaded file to: credentials.json
11. Copy credentials.json to this backend/ folder
12. Run this script again: python setup_gmail.py
""")
        return

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("\n❌ Google API libraries not installed!")
        print("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("\n🌐 Opening browser for Gmail authorization...")
            print("   → Login with your Gmail account")
            print("   → Click Allow to grant send permission\n")
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, scopes)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as f:
            f.write(creds.to_json())
        print(f"\n✅ Success! gmail_token.json created.")

    # Test send
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email_addr = profile.get("emailAddress", "unknown")
        print(f"✅ Connected to Gmail: {email_addr}")
        print(f"✅ All emails will be sent FROM: {email_addr}")
        print(f"\n📝 Add this to your .env file:")
        print(f"   EMAIL_FROM={email_addr}")
        print(f"   SMTP_USER={email_addr}")
        print(f"\n🚀 Gmail API is ready! Start your server: python app.py")
    except Exception as e:
        print(f"⚠️  Setup complete but test failed: {e}")
        print("    Try running: python app.py")

if __name__ == "__main__":
    setup()
