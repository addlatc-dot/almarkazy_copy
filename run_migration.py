import os
import sys

from flask import Flask
from configDB.config import db, Config
from sqlalchemy import text
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def run_migration():
    app = create_app()
    with app.app_context():
        print(f"Database URI starting with: {app.config['SQLALCHEMY_DATABASE_URI'][:15]}...")
        
        # 1. Update doctor table
        columns = [
            "average_consultation_time FLOAT DEFAULT 0",
            "total_consultation_seconds INT DEFAULT 0",
            "consultation_count INT DEFAULT 0",
            "last_button_click_timestamp DATETIME",
            "last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        ]
        
        print("\n--- Updating 'doctor' table ---")
        for col in columns:
            col_name = col.split()[0]
            try:
                # Using SQLAlchemy text() for raw SQL Execution
                db.session.execute(text(f"ALTER TABLE doctor ADD COLUMN {col};"))
                print(f"✅ Created column: {col_name}")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg or '1060' in error_msg:
                    print(f"ℹ️ Column already exists: {col_name}")
                else:
                    print(f"⚠️ Error creating column {col_name}: {e}")
                    db.session.rollback()

        # 2. Create consultation_time table
        print("\n--- Creating 'consultation_time' table ---")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS consultation_time (
            id INT PRIMARY KEY AUTO_INCREMENT,
            doctor_id INT NOT NULL,
            clinic_id INT NOT NULL,
            click_timestamp DATETIME NOT NULL,
            consultation_seconds INT NOT NULL,
            previous_visit_id INT,
            current_visit_id INT,
            date_recorded DATE NOT NULL DEFAULT (CURRENT_DATE),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE CASCADE,
            FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id) ON DELETE CASCADE,
            FOREIGN KEY (previous_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
            FOREIGN KEY (current_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
            INDEX idx_doctor_date (doctor_id, date_recorded),
            INDEX idx_click_timestamp (click_timestamp)
        );
        """
        try:
            db.session.execute(text(create_table_sql))
            print("✅ Verified/Created table: consultation_time")
        except Exception as e:
            print(f"⚠️ Error creating consultation_time table: {e}")
            db.session.rollback()

        # Commit all successful changes
        try:
            db.session.commit()
            print("\n🎉 All database migrations completed successfully!")
        except Exception as e:
            print(f"❌ Failed to commit transactions: {e}")

if __name__ == '__main__':
    run_migration()
