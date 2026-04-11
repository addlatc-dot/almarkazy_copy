# Flask Migration Workflow Guide
## Before Uploading to MySQL Server

**Current Status:** ✅ SQL file is ready (`hospi_final_fixed.sql`)

### All Three Fixes Applied:
1. ✅ Removed circular FK on berth_date
2. ✅ Added FK for doctor.current_patient → patient.id
3. ✅ Added FK for section.doctor_id → doctor.id

---

## Step 1: Import Corrected SQL into Current Database

### For Local MySQL:
```bash
mysql -u root -p hospi < hospi_final_fixed.sql
```

### For Railway (Remote):
```bash
# First, get connection string from Railway
mysql --protocol=TCP -h YOUR_RAILWAY_HOST -u YOUR_USER -p YOUR_PASSWORD YOUR_DB < hospi_final_fixed.sql
```

**Expected Result:** 15 tables created/updated with proper foreign keys

---

## Step 2: Verify Database Schema
```bash
# Check if all tables exist
mysql -u root -p hospi -e "SHOW TABLES;"

# Verify FK constraints
mysql -u root -p hospi -e "
SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'hospi' AND CONSTRAINT_NAME != 'PRIMARY'
ORDER BY TABLE_NAME;
"
```

---

## Step 3: Run Flask Migrations

### 3a. Activate Virtual Environment
```bash
# Navigate to project directory
cd /home/namish/almarkazy_copy

# Activate virtual environment (choose one based on your setup)
source markazyenv/bin/activate
# OR
source almarkzyenv/bin/activate
```

### 3b. Check Current Migration State
```bash
flask db current
```

**Expected:** Shows current migration version or "No migration applied"

### 3c. Create New Migration
```bash
# This captures schema from SQLAlchemy models and compares with database
flask db migrate -m "Fix FK constraints and collations"
```

**What to expect:**
- Flask-Migrate will detect the new FK constraints
- It will generate a migration file in `migrations/versions/`
- File name format: `xxxxxxxxxxxxx_fix_fk_constraints_and_collations.py`

### 3d. Review Generated Migration (IMPORTANT)
```bash
# View the migration file
cat migrations/versions/[newest_migration_file].py
```

**Verify it contains:**
- ✅ doctor.current_patient FK constraint
- ✅ section.doctor_id FK constraint
- ✅ Removal of circular berth_date FK (if present)

### 3e. Apply Migration to Database
```bash
flask db upgrade
```

**Expected Output:**
- `INFO  [alembic.runtime.migration] Context impl MySQLImpl.`
- `INFO  [alembic.runtime.migration] Will assume non-transactional DDL.`
- `INFO  [alembic.runtime.migration] Running upgrade ... done`
- Status shows migration applied successfully

### 3f. Verify Migration Applied
```bash
# Check current migration
flask db current

# Should show the new migration version
```

---

## Step 4: Validate Complete Schema

```bash
# Option 1: In Python shell (recommended)
cd /home/namish/almarkazy_copy

# Activate venv first
source markazyenv/bin/activate

# Enter Python shell
python3 << 'EOF'
from app import app, db
from flask_sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    
    # List all tables
    print("TABLES:")
    for table in inspector.get_table_names():
        print(f"  ✓ {table}")
    
    # List all FK constraints
    print("\nFOREIGN KEY CONSTRAINTS:")
    for table in inspector.get_table_names():
        fks = inspector.get_foreign_keys(table)
        if fks:
            for fk in fks:
                print(f"  {table}.{fk['constrained_columns'][0]} → {fk['referred_table']}.{fk['referred_columns'][0]}")
EOF
```

```bash
# Option 2: Direct MySQL query
mysql -u root -p hospi -e "
SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'hospi'
AND CONSTRAINT_NAME IN ('doctor_patient_fk', 'section_doctor_fk', 'berth_date')
ORDER BY TABLE_NAME;
"
```

---

## Step 5: Run Application Tests

```bash
# Verify Flask app starts without errors
flask run

# Should see: "Running on http://127.0.0.1:5000"
# Press Ctrl+C to stop
```

---

## Step 6: Now Ready for Upload!

Once all migrations pass ✅, your database is:
- ✅ Schema-consistent with Flask models
- ✅ All FK constraints properly defined
- ✅ Collations standardized (utf8mb4_unicode_ci)
- ✅ Ready for production/Railway upload

### Next Steps:
1. **Export DB** (if needed):
   ```bash
   mysqldump -u root -p hospi > hospi_production.sql
   ```

2. **Upload to Railway** (if using Railway):
   ```bash
   mysql --protocol=TCP -h YOUR_RAILWAY_HOST -u YOUR_USER -p YOUR_PASSWORD YOUR_DB < hospi_production.sql
   ```

3. **Deploy Flask app to Railway**

---

## Troubleshooting

### ❌ `flask db migrate` shows "No changes detected"
**Solution:**
- Check if model definitions match database
- Ensure database already has the correct schema from `hospi_final_fixed.sql`

### ❌ `flask db upgrade` fails with FK error
**Solution:**
1. Check for circular references (already fixed ✅)
2. Verify all referenced tables/columns exist
3. Ensure collations match: `COLLATE utf8mb4_unicode_ci`

### ❌ Migration won't apply due to constraint issues
**Solution:**
```bash
# Drop conflicting FK (if needed)
mysql -u root -p hospi -e "ALTER TABLE visit DROP FOREIGN KEY berth_date;"

# Retry migration
flask db upgrade
```

---

## Summary

| Task | Status |
|------|--------|
| ✅ SQL fixes applied | Ready |
| ✅ Collations standardized | utf8mb4_unicode_ci |
| ✅ Circular FK removed | berth_date |
| ✅ Missing FKs added | doctor.current_patient, section.doctor_id |
| ⏳ Flask migration cycle | Ready to start (Step 3) |
| ⏳ Application tests | Ready after migration |
| ⏳ Production upload | After all tests pass |

**Commands Quick Reference:**
```bash
# 1. Import SQL
mysql -u root -p hospi < hospi_final_fixed.sql

# 2. Create migration
flask db migrate -m "Fix FK constraints"

# 3. Apply migration
flask db upgrade

# 4. Verify
flask db current
```

---

**File Created:** `2024-11-09`
**Database:** hospi
**Flask-Migrate Version:** (check with `flask db --version`)

