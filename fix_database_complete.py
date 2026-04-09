#!/usr/bin/env python
"""
COMPLETE DATABASE FIX - All-in-one solution
Handles database schema setup, verification, and troubleshooting
Run this ONCE and your database will be perfectly configured
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
log_file = f"db_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        from flask import Flask
        from configDB.config import db, Config
        from sqlalchemy import text
        
        logger.info("\n" + "="*70)
        logger.info("COMPLETE DATABASE SCHEMA FIX")
        logger.info("="*70)
        logger.info(f"Log file: {log_file}\n")
        
        # Create Flask app
        logger.info("[1/5] Creating Flask app context...")
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            # Get database connection info
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            safe_uri = db_uri.split('@')[1] if '@' in db_uri else "unknown"
            logger.info(f"    Connected to: {safe_uri}\n")
            
            # Get raw connection
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            try:
                # Step 2: Check doctor table
                logger.info("[2/5] Checking doctor table columns...")
                cursor.execute("DESCRIBE doctor;")
                existing_cols = {row[0]: row[1] for row in cursor.fetchall()}
                logger.info(f"    Found {len(existing_cols)} existing columns")
                
                # Define required columns
                required_cols = {
                    'average_consultation_time': 'FLOAT DEFAULT 0',
                    'total_consultation_seconds': 'INT DEFAULT 0',
                    'consultation_count': 'INT DEFAULT 0',
                    'last_button_click_timestamp': 'DATETIME NULL',
                    'last_update_time': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
                }
                
                # Step 3: Add missing columns
                logger.info("\n[3/5] Adding missing columns...")
                added_count = 0
                for col_name, col_type in required_cols.items():
                    if col_name in existing_cols:
                        logger.info(f"    ✓ {col_name}: EXISTS ({existing_cols[col_name]})")
                    else:
                        try:
                            sql = f"ALTER TABLE doctor ADD COLUMN {col_name} {col_type};"
                            cursor.execute(sql)
                            connection.commit()
                            logger.info(f"    ✓ {col_name}: ADDED ({col_type})")
                            added_count += 1
                        except Exception as e:
                            connection.rollback()
                            logger.error(f"    ✗ {col_name}: FAILED - {e}")
                            raise
                
                if added_count > 0:
                    logger.info(f"    → Added {added_count} new columns")
                
                # Step 4: Create consultation_time table
                logger.info("\n[4/5] Checking consultation_time table...")
                cursor.execute("""
                    SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME='consultation_time' AND TABLE_SCHEMA=DATABASE()
                """)
                
                if cursor.fetchone():
                    logger.info("    ✓ consultation_time table: EXISTS")
                else:
                    logger.info("    → Creating consultation_time table...")
                    create_sql = """
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
                    cursor.execute(create_sql)
                    connection.commit()
                    logger.info("    ✓ consultation_time table: CREATED")
                
                # Step 5: Final verification
                logger.info("\n[5/5] Final verification...")
                cursor.execute("DESCRIBE doctor;")
                final_cols = {row[0]: row[1] for row in cursor.fetchall()}
                
                all_present = all(col in final_cols for col in required_cols.keys())
                
                if all_present:
                    logger.info("    ✓ All required columns present!")
                    logger.info("\n" + "="*70)
                    logger.info("✅ DATABASE SETUP COMPLETE & VERIFIED")
                    logger.info("="*70)
                    logger.info("\nYour database is now ready!")
                    logger.info("Summary:")
                    logger.info(f"  • Doctor table columns: {len(final_cols)}")
                    logger.info(f"  • Required columns: ✓ All present")
                    logger.info(f"  • Consultation_time table: ✓ Exists")
                    logger.info(f"\n✅ You can now push to Railway with confidence!")
                    return True
                else:
                    logger.error("\n❌ Some columns are still missing!")
                    missing = [col for col in required_cols if col not in final_cols]
                    for col in missing:
                        logger.error(f"  Missing: {col}")
                    return False
                    
            finally:
                cursor.close()
                connection.close()
    
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {e}")
        logger.exception(e)
        return False

if __name__ == '__main__':
    success = main()
    
    # Print log file location
    if os.path.exists(log_file):
        print(f"\n📝 Detailed log saved to: {log_file}")
    
    sys.exit(0 if success else 1)
