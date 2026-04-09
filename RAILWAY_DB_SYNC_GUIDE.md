# Railway Deployment Guide - Database Synchronization

## Overview
Your project has **two separate services** on Railway:
- **MySQL Database** (raids) - Main application database
- **Redis Database** - For caching and real-time updates

This guide explains how to properly configure database synchronization.

---

## 1. Railway Variables Setup

### A. MySQL Database Variables
After creating a MySQL service on Railway, set these **environment variables** in your web service:

```
# Railway automatically provides these from MySQL plugin:
MYSQLHOST=your-mysql-host
MYSQLUSER=your-mysql-user
MYSQLPASSWORD=your-mysql-password
MYSQLPORT=3306
MYSQL_DATABASE=hospi  # Your chosen database name
```

**OR use the combined URL variable:**
```
DATABASE_URL=mysql+pymysql://user:password@host:3306/hospi
```

### B. Redis Variables
After creating a Redis service on Railway:

```
REDIS_URL=redis://user:password@host:port
```

### C. Additional Variables
```
SECRET_KEY=your-very-long-random-string-min-32-chars
FLASK_ENV=production
PORT=8080
```

---

## 2. Configuration Files

### Your `configDB/config.py` handles both scenarios:
✓ **Priority 1**: Uses `DATABASE_URL` if set
✓ **Priority 2**: Falls back to individual MySQL variables
✓ **Priority 3**: Uses localhost defaults

**Current implementation is correct** ✓

---

## 3. Database Synchronization Process

Your `sync_db.py` script running in Procfile does:

1. **Connects to MySQL** using Railway credentials
2. **Checks if columns exist** in the `doctor` table
3. **Adds missing columns** if needed:
   - `average_consultation_time`
   - `total_consultation_seconds`
   - `consultation_count`
   - `last_button_click_timestamp`
   - `last_update_time`
4. **Creates `consultation_time` table** if it doesn't exist
5. **Commits changes** and starts the Flask app

---

## 4. Procfile Execution Flow

```
web: python sync_db.py && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 main:app
```

**Step-by-step:**
```
1. python sync_db.py         ← Runs db synchronization (logs output)
                               ├─ Connects to Railway MySQL
                               ├─ Checks/creates columns
                               └─ Returns exit code 0 if successful

2. && gunicorn ...           ← Only runs if sync_db.py succeeds (exit code 0)
                               ├─ Starts web server
                               ├─ Loads Flask app
                               └─ Listens on 0.0.0.0:5000 (Railway remaps to PORT)
```

---

## 5. Troubleshooting

### Issue: "Unknown column" error still appearing

**Solution 1**: Check Railway logs for sync_db.py output
```
Go to: Railway Dashboard → Your Project → Web Service → Logs
Look for: "DATABASE SCHEMA SYNCHRONIZATION" section
```

**Solution 2**: Verify database credentials
```
In Railway: MySQL Service → Variables tab
Ensure MYSQLHOST, MYSQLUSER, MYSQLPASSWORD are set
```

**Solution 3**: Manual database check
```bash
# Connect to Railway MySQL and verify columns exist
mysql -h $MYSQLHOST -u $MYSQLUSER -p$MYSQLPASSWORD -D hospi
SHOW COLUMNS FROM doctor LIKE '%consultation%';
```

### Issue: Procfile command fails

**Solution**: Add timeout to sync_db.py
- Large databases need time to add columns
- Increase Procfile timeout if needed:
```
web: timeout 300 python sync_db.py && gunicorn ...
```

### Issue: Can't connect to MySQL

**Solution**: Verify connection string
- Test in Railway terminal:
```bash
python -c "from configDB.config import Config; print(Config.SQLALCHEMY_DATABASE_URI[:20])"
```

---

## 6. Two-Database Architecture

```
┌─────────────────────────────────────────┐
│         YOUR FLASK APP (Railway)         │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ MySQL (raid) │    │ Redis        │  │
│  │              │    │              │  │
│  │ • doctor     │    │ • Cache      │  │
│  │ • patient    │    │ • Sessions   │  │
│  │ • clinic     │    │ • Real-time  │  │
│  │ • visit      │    │              │  │
│  │ • etc        │    │              │  │
│  └──────────────┘    └──────────────┘  │
│                                         │
│  Connections via:                       │
│  • DATABASE_URL / MYSQL* env vars      │
│  • REDIS_URL env var                   │
│                                         │
└─────────────────────────────────────────┘
```

---

## 7. First Deployment Checklist

- [ ] Create MySQL service on Railway
- [ ] Create Redis service on Railway
- [ ] Link databases to your web service
- [ ] Set environment variables (MYSQL*, REDIS_URL, SECRET_KEY)
- [ ] Push code with new `sync_db.py`
- [ ] Check Logs - look for "DATABASE SCHEMA SYNCHRONIZED"
- [ ] Test your application
- [ ] Verify doctor table has new columns:
  ```bash
  DESCRIBE doctor;  # Check columns exist
  ```

---

## 8. Deployment Command

```bash
# Push to Railway (assuming Railway CLI installed)
railway up

# Or if using Git deployment:
git push origin main
# (Railway auto-deploys if configured)
```

---

## Quick Reference

| Component | Configuration | Priority |
|-----------|---------------|----------|
| MySQL | DATABASE_URL or MYSQL_* vars | Railway MySQL plugin |
| Redis | REDIS_URL | Railway Redis plugin |
| Sync | sync_db.py in Procfile | Runs before gunicorn |
| App | gunicorn + eventlet | Runs after successful sync |

---

## Next Steps

1. **Review your current Railway setup** - check if databases are linked
2. **Push the new `sync_db.py`** - triggers automatic schema sync
3. **Monitor logs** - watch for successful schema synchronization
4. **Test queries** - verify columns exist and app works

For more help, provide your Railway logs from the web service. Look for the "DATABASE SCHEMA SYNCHRONIZATION" section in the logs.
