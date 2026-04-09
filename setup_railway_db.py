#!/usr/bin/env python
"""
Railway Manual Database Schema Setup
Run this ONCE manually on Railway to set up missing columns
"""

import os
import sys
import logging
from flask import Flask
from configDB.config import db, Config
from sqlalchemy import text, inspect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    """Direct SQL approach - most reliable for Railway"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        
        try:
            logger.info("🔍 Checking doctor table schema...")
            
            # Get existing columns
            cursor.execute("DESCRIBE doctor;")
            existing_columns = {row[0] for row in cursor.fetchall()}
            logger.info(f"Existing columns: {existing_columns}")
            
            # Define required columns with their definitions
            required_columns = {
                'average_consultation_time': 'FLOAT DEFAULT 0',
                'total_consultation_seconds': 'INT DEFAULT 0',
                'consultation_count': 'INT DEFAULT 0',
                'last_button_click_timestamp': 'DATETIME NULL',
                'last_update_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
            }
            
            # Add missing columns
            for col_name, col_type in required_columns.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE doctor ADD COLUMN {col_name} {col_type};"
                    logger.info(f"Adding column: {col_name}")
                    cursor.execute(alter_sql)
                    logger.info(f"✓ Added: {col_name}")
                else:
                    logger.info(f"✓ Column already exists: {col_name}")
            
            logger.info("\n🔍 Checking consultation_time table...")
            
            # Check if consultation_time table exists
            cursor.execute("""
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME='consultation_time' AND TABLE_SCHEMA=DATABASE()
            """)
            
            if not cursor.fetchone():
                logger.info("Creating consultation_time table...")
                create_table_sql = """
                CREATE TABLE consultation_time (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    doctor_id INT NOT NULL,
                    clinic_id INT NOT NULL,
                    click_timestamp DATETIME NOT NULL,
                    consultation_seconds INT NOT NULL,
                    previous_visit_id INT,
                    current_visit_id INT,
                    date_recorded DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE CASCADE,
                    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id) ON DELETE CASCADE,
                    FOREIGN KEY (previous_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
                    FOREIGN KEY (current_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
                    INDEX idx_doctor_date (doctor_id, date_recorded),
                    INDEX idx_click_timestamp (click_timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
                cursor.execute(create_table_sql)
                logger.info("✓ Created consultation_time table")
            else:
                logger.info("✓ consultation_time table already exists")
            
            # Commit changes
            connection.commit()
            logger.info("\n" + "="*60)
            logger.info("✅ DATABASE SETUP SUCCESSFUL")
            logger.info("="*60)
            logger.info("\nYou can now run your Flask app without column errors!")
            
            return True
            
        except Exception as e:
            connection.rollback()
            logger.error(f"❌ Error: {e}")
            logger.exception(e)
            return False
        finally:
            cursor.close()
            connection.close()

if __name__ == '__main__':
    success = setup_database()
    sys.exit(0 if success else 1)
