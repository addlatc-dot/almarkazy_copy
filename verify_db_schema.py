#!/usr/bin/env python
"""
Database Schema Verification Tool
Checks if all required columns exist in Railway MySQL
"""

import os
import sys
import logging
from flask import Flask
from configDB.config import db, Config
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_database():
    """Verify database schema"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        try:
            logger.info("\n" + "="*60)
            logger.info("DATABASE SCHEMA VERIFICATION")
            logger.info("="*60)
            
            # Get DB info
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            safe_uri = db_uri.split('@')[1] if '@' in db_uri else "unknown"
            logger.info(f"\n📍 Connected to: {safe_uri}")
            
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Check doctor table columns
            logger.info("\n🔍 Checking 'doctor' table columns:")
            cursor.execute("DESCRIBE doctor;")
            columns = {row[0]: row[1] for row in cursor.fetchall()}
            
            required_columns = [
                'average_consultation_time',
                'total_consultation_seconds',
                'consultation_count',
                'last_button_click_timestamp',
                'last_update_time'
            ]
            
            all_exist = True
            for col in required_columns:
                if col in columns:
                    logger.info(f"  ✓ {col}: {columns[col]}")
                else:
                    logger.info(f"  ✗ MISSING: {col}")
                    all_exist = False
            
            # Check consultation_time table
            logger.info("\n🔍 Checking 'consultation_time' table:")
            cursor.execute("""
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME='consultation_time' AND TABLE_SCHEMA=DATABASE()
            """)
            
            if cursor.fetchone():
                logger.info("  ✓ consultation_time table EXISTS")
            else:
                logger.info("  ✗ MISSING: consultation_time table")
                all_exist = False
            
            cursor.close()
            connection.close()
            
            logger.info("\n" + "="*60)
            if all_exist:
                logger.info("✅ ALL REQUIRED COLUMNS EXIST - APP SHOULD WORK!")
            else:
                logger.info("❌ MISSING COLUMNS - RUN: python setup_railway_db.py")
                logger.info("\nOR run SQL manually in Railway MySQL console:")
                logger.info("  cat RAILWAY_MANUAL_MIGRATION.sql | mysql")
            logger.info("="*60 + "\n")
            
            return all_exist
            
        except Exception as e:
            logger.error(f"\n❌ Error connecting to database: {e}")
            logger.error(f"Connection string: {db_uri[:40]}...")
            return False

if __name__ == '__main__':
    success = check_database()
    sys.exit(0 if success else 1)
