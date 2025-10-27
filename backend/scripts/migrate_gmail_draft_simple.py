"""
Simple Database Migration: Add gmail_draft_id column to email_drafts table
This script connects directly to PostgreSQL without backend dependencies.
"""

import os
from pathlib import Path

# Try to load .env if it exists
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

def main():
    """Add gmail_draft_id column to email_drafts table"""

    print("=" * 60)
    print("Database Migration: Add gmail_draft_id Column")
    print("=" * 60)
    print()

    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        print("[ERROR] DATABASE_URL not found in environment variables")
        print()
        print("Please set DATABASE_URL in your .env file:")
        print("DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
        return 1

    print(f"[INFO] Connecting to database...")
    print()

    try:
        import psycopg2
        from psycopg2 import sql

        # Parse connection string
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'email_drafts' AND column_name = 'gmail_draft_id'
        """)

        if cursor.fetchone():
            print("[INFO] Column 'gmail_draft_id' already exists")
        else:
            # Add column
            print("[INFO] Adding gmail_draft_id column...")
            cursor.execute("""
                ALTER TABLE email_drafts
                ADD COLUMN gmail_draft_id VARCHAR NULL
            """)
            print("[OK] Column added successfully")

        # Create index if it doesn't exist
        print("[INFO] Creating index on gmail_draft_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_drafts_gmail_id
            ON email_drafts(gmail_draft_id)
        """)
        print("[OK] Index created successfully")

        # Commit changes
        conn.commit()

        # Verify column
        print("[INFO] Verifying column...")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'email_drafts' AND column_name = 'gmail_draft_id'
        """)

        row = cursor.fetchone()
        if row:
            print(f"[OK] Column verified: {row[0]} ({row[1]})")
        else:
            print("[WARN] Column verification failed")

        cursor.close()
        conn.close()

        print()
        print("=" * 60)
        print("[SUCCESS] Migration Complete!")
        print("=" * 60)
        print()
        print("Gmail draft sync is now enabled in the database.")
        print("Restart your backend server to apply changes.")
        print()

    except ImportError:
        print("[ERROR] psycopg2 not installed")
        print()
        print("Install it with: pip install psycopg2-binary")
        return 1
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
