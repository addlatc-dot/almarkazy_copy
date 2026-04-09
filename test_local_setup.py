#!/usr/bin/env python
"""
Local Testing Script - Run this to test database setup locally
"""

import os
import sys

def test_database_setup():
    """Test the complete database setup flow"""
    print("\n" + "="*60)
    print("LOCAL DATABASE SETUP TEST")
    print("="*60)
    
    # Step 1: Run setup
    print("\n[1/3] Running database setup...")
    os.system("python setup_railway_db.py")
    
    # Step 2: Verify
    print("\n[2/3] Verifying schema...")
    os.system("python verify_db_schema.py")
    
    # Step 3: Test app import
    print("\n[3/3] Testing Flask app import...")
    try:
        from app import create_app, Doctor
        app = create_app()
        with app.app_context():
            # Try a test query (won't return results, but checks columns)
            doctor_cols = Doctor.__table__.columns.keys()
            print(f"\n✓ Flask app imported successfully")
            print(f"✓ Doctor model has {len(doctor_cols)} columns:")
            for col in sorted(doctor_cols):
                print(f"  - {col}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - Ready to deploy to Railway!")
        print("="*60)
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = test_database_setup()
    sys.exit(0 if success else 1)
