"""
Migration script to add queue_position to existing visits
This script calculates and sets the queue_position for all visits that don't have one yet.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from configDB.config import db, Config
from busnisess_layer.models import Visit, Doctor, Clinics
from sqlalchemy import func
from datetime import datetime, date

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    db.init_app(app)
    return app

def migrate_queue_positions():
    """Add queue_position to all visits that don't have one"""
    app = create_app()
    
    with app.app_context():
        # Get all visits without a queue_position
        unprocessed_visits = Visit.query.filter(Visit.queue_position.is_(None)).all()
        
        if not unprocessed_visits:
            print("✅ All visits already have queue_position set!")
            return
        
        print(f"🔄 Processing {len(unprocessed_visits)} visits without queue_position...")
        
        processed = 0
        for visit in unprocessed_visits:
            try:
                # Get all confirmed visits for this doctor on the same date (excluding this one)
                visit_date = visit.visit_date.date() if hasattr(visit.visit_date, 'date') else visit.visit_date
                
                same_day_visits = Visit.query.filter(
                    Visit.doctor_id == visit.doctor_id,
                    Visit.clinic_id == visit.clinic_id,
                    func.date(Visit.visit_date) == visit_date,
                    Visit.visit_status == "مؤكد",
                    Visit.id != visit.id
                ).order_by(Visit.visit_date.asc()).all()
                
                # Calculate position
                position = len(same_day_visits) + 1
                visit.queue_position = position
                
                db.session.add(visit)
                processed += 1
                
                if processed % 50 == 0:
                    print(f"  Processed {processed}/{len(unprocessed_visits)}...")
                    
            except Exception as e:
                print(f"❌ Error processing visit {visit.id}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"✅ Successfully migrated {processed} visits with queue_position!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error committing migration: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    success = migrate_queue_positions()
    sys.exit(0 if success else 1)
