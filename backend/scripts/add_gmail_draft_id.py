"""
Database Migration: Add gmail_draft_id column to email_drafts table
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database.connection import engine

def main():
    """Add gmail_draft_id column to email_drafts table"""

    print("=" * 60)
    print("Database Migration: Add gmail_draft_id Column")
    print("=" * 60)
    print()

    try:
        with engine.connect() as conn:
            # Add column if it doesn't exist
            print("[INFO] Adding gmail_draft_id column...")
            conn.execute(text(
                "ALTER TABLE email_drafts ADD COLUMN IF NOT EXISTS gmail_draft_id VARCHAR NULL"
            ))

            # Add index for faster lookups
            print("[INFO] Creating index on gmail_draft_id...")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_email_drafts_gmail_id ON email_drafts(gmail_draft_id)"
            ))

            conn.commit()

            # Verify column was added
            print("[INFO] Verifying column...")
            result = conn.execute(text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'email_drafts' AND column_name = 'gmail_draft_id'
                """
            ))

            row = result.fetchone()
            if row:
                print(f"[OK] Column verified: {row[0]} ({row[1]})")
            else:
                print("[WARN] Column verification failed - but may still exist")

        print()
        print("=" * 60)
        print("[SUCCESS] Migration Complete!")
        print("=" * 60)
        print()
        print("Gmail draft sync is now enabled.")
        print("Restart your backend server to apply changes.")
        print()

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
