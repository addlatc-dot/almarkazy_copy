"""
Migration script to add consultation time tracking columns to the doctor table.
Adds: average_consultation_time, total_consultation_seconds, consultation_count,
      last_button_click_timestamp, last_update_time
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from configDB.config import db, Config
from sqlalchemy import text

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    db.init_app(app)
    return app

def migrate_doctor_consultation_columns():
    """Add consultation time tracking columns to the doctor table if they don't exist."""
    app = create_app()

    with app.app_context():
        columns_to_add = [
            (
                "average_consultation_time",
                "ALTER TABLE doctor ADD COLUMN average_consultation_time FLOAT DEFAULT 0"
            ),
            (
                "total_consultation_seconds",
                "ALTER TABLE doctor ADD COLUMN total_consultation_seconds INT DEFAULT 0"
            ),
            (
                "consultation_count",
                "ALTER TABLE doctor ADD COLUMN consultation_count INT DEFAULT 0"
            ),
            (
                "last_button_click_timestamp",
                "ALTER TABLE doctor ADD COLUMN last_button_click_timestamp DATETIME"
            ),
            (
                "last_update_time",
                "ALTER TABLE doctor ADD COLUMN last_update_time DATETIME"
            ),
        ]

        success = True

        for column_name, alter_sql in columns_to_add:
            try:
                db.session.execute(text(alter_sql))
                db.session.commit()
                print(f"✅ Added column '{column_name}' to doctor table.")
            except Exception as e:
                db.session.rollback()
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg:
                    print(f"ℹ️  Column '{column_name}' already exists — skipping.")
                else:
                    print(f"❌ Error adding column '{column_name}': {str(e)}")
                    success = False

        # Set default values for existing rows where the new numeric columns are NULL
        update_statements = [
            "UPDATE doctor SET average_consultation_time = 0 WHERE average_consultation_time IS NULL",
            "UPDATE doctor SET total_consultation_seconds = 0 WHERE total_consultation_seconds IS NULL",
            "UPDATE doctor SET consultation_count = 0 WHERE consultation_count IS NULL",
        ]

        for update_sql in update_statements:
            try:
                db.session.execute(text(update_sql))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error setting default values: {str(e)}")
                success = False

        if success:
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with some errors. Check output above.")

        return success

if __name__ == '__main__':
    success = migrate_doctor_consultation_columns()
    sys.exit(0 if success else 1)
