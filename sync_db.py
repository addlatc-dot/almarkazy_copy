#!/usr/bin/env python
"""
Database Schema Synchronization Script for Railway Deployment
This script ensures the database schema matches the SQLAlchemy models
Run this BEFORE the Flask app starts
"""

import os
import sys
import logging
from flask import Flask
from configDB.config import db, Config
from sqlalchemy import text, inspect
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create Flask app with database configuration"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def check_column_exists(session, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        result = session.execute(
            text(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table_name}' AND COLUMN_NAME='{column_name}'")
        )
        return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking column {table_name}.{column_name}: {e}")
        return None


def add_column_if_missing(session, table_name, col_definition):
    """Add a column to a table if it doesn't exist"""
    col_name = col_definition.split()[0]
    
    if check_column_exists(session, table_name, col_name):
        logger.info(f"✓ Column '{col_name}' already exists in '{table_name}'")
        return True
    
    try:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_definition}"
        session.execute(text(sql))
        session.commit()
        logger.info(f"✓ Created column '{col_name}' in '{table_name}'")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"✗ Failed to create column '{col_name}': {e}")
        return False


def migrate_doctor_table(session):
    """Add missing columns to doctor table"""
    logger.info("\n--- Syncing 'doctor' table ---")
    
    columns_to_add = [
        "average_consultation_time FLOAT DEFAULT 0 COMMENT 'Average consultation time in seconds'",
        "total_consultation_seconds INT DEFAULT 0 COMMENT 'Total consultation seconds'",
        "consultation_count INT DEFAULT 0 COMMENT 'Number of consultations'",
        "last_button_click_timestamp DATETIME COMMENT 'Last next patient click'",
        "last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp'"
    ]
    
    success_count = 0
    for col_def in columns_to_add:
        if add_column_if_missing(session, 'doctor', col_def):
            success_count += 1
    
    return success_count == len(columns_to_add)


def create_consultation_time_table(session):
    """Create consultation_time tracking table"""
    logger.info("\n--- Creating 'consultation_time' table ---")
    
    table_check = session.execute(
        text("SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='consultation_time'")
    ).fetchone()
    
    if table_check:
        logger.info("✓ Table 'consultation_time' already exists")
        return True
    
    create_sql = """
    CREATE TABLE consultation_time (
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    try:
        session.execute(text(create_sql))
        session.commit()
        logger.info("✓ Created table 'consultation_time'")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"✗ Failed to create consultation_time table: {e}")
        return False


def verify_database_connection(session):
    """Verify database connection is working"""
    try:
        session.execute(text("SELECT 1"))
        logger.info("✓ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def sync_database():
    """Main database synchronization function"""
    logger.info("=" * 60)
    logger.info("DATABASE SCHEMA SYNCHRONIZATION")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            # Log connection details (without password)
            safe_uri = db_uri.split('@')[1] if '@' in db_uri else "localhost"
            logger.info(f"Database: {safe_uri}")
            
            session = db.session
            
            # Verify connection
            if not verify_database_connection(session):
                logger.error("Cannot proceed without database connection")
                return False
            
            # Run migrations
            success = True
            success &= migrate_doctor_table(session)
            success &= create_consultation_time_table(session)
            
            if success:
                logger.info("\n" + "=" * 60)
                logger.info("✓ DATABASE SCHEMA SYNCHRONIZED SUCCESSFULLY")
                logger.info("=" * 60)
                return True
            else:
                logger.warning("\n" + "=" * 60)
                logger.warning("⚠ Some migrations may have failed - check logs above")
                logger.warning("=" * 60)
                return False
                
        except Exception as e:
            logger.error(f"Fatal error during synchronization: {e}")
            logger.exception(e)
            return False


if __name__ == '__main__':
    success = sync_database()
    sys.exit(0 if success else 1)
