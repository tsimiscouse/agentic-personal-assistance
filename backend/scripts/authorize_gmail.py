"""
Gmail API Authorization Script
Run this once to authorize Gmail API access
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

def main():
    """Authorize Gmail API access"""

    # Paths
    credentials_path = backend_dir / 'config' / 'google_credentials.json'
    token_path = backend_dir / 'config' / 'gmail_token.json'

    print("=" * 60)
    print("Gmail API Authorization")
    print("=" * 60)
    print()

    # Check if credentials file exists
    if not credentials_path.exists():
        print(f"[ERROR] Credentials file not found!")
        print(f"   Expected: {credentials_path}")
        print()
        print("Please download OAuth credentials from Google Cloud Console")
        print("and save as 'google_credentials.json' in backend/config/")
        return

    print(f"[OK] Found credentials: {credentials_path}")
    print()

    creds = None

    # Check if token already exists
    if token_path.exists():
        print(f"[INFO] Found existing token: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            print("[OK] Existing token loaded")
        except Exception as e:
            print(f"[WARN] Could not load existing token: {e}")
            print("   Creating new token...")

    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("[OK] Token refreshed successfully")
            except Exception as e:
                print(f"[ERROR] Error refreshing token: {e}")
                print("   Creating new token...")
                creds = None

        if not creds:
            print()
            print("[INFO] Starting OAuth flow...")
            print("   Your browser will open for authorization")
            print()

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path),
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                print()
                print("[OK] Authorization successful!")
            except Exception as e:
                print(f"[ERROR] Error during authorization: {e}")
                return

        # Save token
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"[OK] Token saved: {token_path}")
        except Exception as e:
            print(f"[ERROR] Error saving token: {e}")
            return

    print()
    print("=" * 60)
    print("[SUCCESS] Gmail API Authorization Complete!")
    print("=" * 60)
    print()
    print("You can now:")
    print("  1. Restart your backend server")
    print("  2. Create email drafts")
    print("  3. Drafts will sync to Gmail automatically!")
    print()
    print("Token valid for 7 days, then auto-refreshes.")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Authorization cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
