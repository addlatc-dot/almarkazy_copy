# Railway Deployment - Database Schema Error FIX

## ❌ What's Happening (The Root Cause)

Your Flask models define these columns on the `Doctor` class:
```python
average_consultation_time = db.Column(db.Float, default=0)
total_consultation_seconds = db.Column(db.Integer, default=0)
consultation_count = db.Column(db.Integer, default=0)
last_button_click_timestamp = db.Column(db.DateTime, nullable=True)
last_update_time = db.Column(db.DateTime, ...)
```

**BUT** these columns don't exist in your Railway MySQL database yet.

When SQLAlchemy runs `Doctor.query.filter_by(username=email).first()`, it generates this SQL:
```sql
SELECT doctor.id, doctor.username, ... doctor.average_consultation_time, 
       doctor.total_consultation_seconds, ... 
FROM doctor WHERE doctor.username = 'user@email.com'
```

Since `average_consultation_time` doesn't exist in the database → **Error 1054: Unknown column**

---

## ✅ Solution: 3-Step Fix

### Option 1: Automatic Setup (Recommended)

1. **Push the new files to Railway:**
   ```bash
   git add setup_railway_db.py verify_db_schema.py Procfile
   git commit -m "Add automatic database schema setup"
   git push origin main
   ```

2. **Railway will:**
   - Run `setup_railway_db.py` → Creates missing columns ✓
   - Run `verify_db_schema.py` → Confirms they exist ✓
   - Start Flask app → Works! ✓

3. **Check logs:**
   ```
   Railway Dashboard → Web Service → Logs
   Look for: "✅ DATABASE SETUP SUCCESSFUL"
   ```

---

### Option 2: Manual SQL Setup (If Option 1 doesn't work)

1. **Go to Railway Dashboard:**
   - Click your MySQL service
   - Click "Connect" → Use a MySQL client

2. **Run this SQL in your Railway MySQL console:**

```sql
-- Add columns to doctor table
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS average_consultation_time FLOAT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS total_consultation_seconds INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS consultation_count INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS last_button_click_timestamp DATETIME NULL;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Create consultation_time table
CREATE TABLE IF NOT EXISTS consultation_time (
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

-- Verify
DESCRIBE doctor;
SHOW TABLES LIKE 'consultation_time';
```

3. **After running SQL:**
   - Restart your Railway web service
   - Error should be gone!

---

### Option 3: Run Locally Then Push

1. **Locally, test the setup script:**
   ```bash
   python setup_railway_db.py
   ```

2. **Verify it worked:**
   ```bash
   python verify_db_schema.py
   ```

3. **Once verified locally, push to Railway:**
   ```bash
   git push origin main
   ```

---

## 🔍 How to Verify It Worked

### In Railway Dashboard:

1. Go to Web Service → Variables
2. Click "MySQL Service" link to open the database client
3. Run:
```sql
DESCRIBE doctor;
```

Look for these columns in the output:
- ✓ `average_consultation_time`
- ✓ `total_consultation_seconds`
- ✓ `consultation_count`
- ✓ `last_button_click_timestamp`
- ✓ `last_update_time`

### Or run the verification script:

```bash
# Locally:
python verify_db_schema.py

# Output should show:
# ✓ average_consultation_time: float
# ✓ total_consultation_seconds: int
# ✓ consultation_count: int
# ✓ last_button_click_timestamp: datetime
# ✓ last_update_time: datetime
```

---

## 🚨 Still Getting Errors?

### Issue 1: "File not found" errors in Procfile
- Make sure you pushed: `setup_railway_db.py`, `verify_db_schema.py`
- Check they're in the root folder
- Restart web service after pushing

### Issue 2: Connection string issues
Check Railway env variables are set:
```
MYSQLHOST=xxxx
MYSQLUSER=xxxx
MYSQLPASSWORD=xxxx
MYSQL_DATABASE=hospi
```

If missing, go to:
- Railway Dashboard → Web Service → Variables
- Click "MySQL" to link it and auto-fill variables

### Issue 3: Still says "Unknown column" after setup
- Run `verify_db_schema.py` locally to see actual status
- Check you're connecting to the same database
- Verify `MYSQL_DATABASE` env var matches the database name

### Issue 4: Multiple databases issue
If you have multiple MySQL instances on Railway:
- Make sure your web service is linked to the **correct** MySQL
- Check you're using the right credentials
- Run `verify_db_schema.py` to confirm which DB you're connected to

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────┐
│      YOUR FLASK APP on Railway      │
├─────────────────────────────────────┤
│                                     │
│  Procfile runs in order:            │
│  1. setup_railway_db.py             │
│     └─ Creates missing columns      │
│                                     │
│  2. verify_db_schema.py             │
│     └─ Confirms columns exist       │
│                                     │
│  3. gunicorn (starts Flask)         │
│     └─ Connects using Doctor model  │
│        with valid columns           │
│                                     │
├─────────────────────────────────────┤
│    Railway MySQL (raids)            │
│  ✓ doctor table (with new columns)  │
│  ✓ consultation_time table          │
│  ✓ All other tables                 │
└─────────────────────────────────────┘
```

---

## 🎯 Quick Checklist

- [ ] Push code with new files to Railway
- [ ] Check Railway logs for "DATABASE SETUP SUCCESSFUL"
- [ ] Run `verify_db_schema.py` to confirm columns
- [ ] Check MySQL console: `DESCRIBE doctor;`
- [ ] Verify 5 new columns exist
- [ ] Try logging in - error should be gone!

---

## 📝 Files You Have Now

| File | Purpose |
|------|---------|
| `setup_railway_db.py` | Creates missing columns (runs first in Procfile) |
| `verify_db_schema.py` | Checks if columns exist (runs second, for debugging) |
| `RAILWAY_MANUAL_MIGRATION.sql` | Manual SQL to run if automatic fails |
| `Procfile` | Updated to run setup before gunicorn |

---

## 💡 Why This Failed Before

The first migration script (`sync_db.py`) might have:
1. Failed silently when running on Railway
2. Hit a timeout before completing
3. Not had permission to modify the database
4. Not logged errors properly

The new scripts use **direct Python + raw SQL** which is more reliable and has **better error logging**.

---

## 🚀 Next Steps

1. **Immediately**: Run Option 1 (push and let Railway auto-fix)
2. **If that fails**: Run Option 2 (manual SQL in MySQL console)
3. **To debug**: Run `python verify_db_schema.py` locally

Your app should work once these 5 columns are in the database!
