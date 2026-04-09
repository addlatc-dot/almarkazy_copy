# Railway Environment Variables - Quick Setup

## After Creating MySQL + Redis Services on Railway

### Copy these variable names into your web service on Railway Dashboard:

#### From MySQL Service (automatically available after linking):
```
MYSQLHOST
MYSQLUSER  
MYSQLPASSWORD
MYSQLPORT
MYSQL_DATABASE=hospi    # Set the value to your database name
```

#### From Redis Service (automatically available after linking):
```
REDIS_URL
```

#### Add these manually:
```
SECRET_KEY=<generate-long-random-string-with-special-chars>
FLASK_ENV=production
```

---

## ✓ Correct Setup (What Should Work)

In Railway Dashboard → Web Service → Variables:

| Variable | Value | Source |
|----------|-------|--------|
| MYSQLHOST | `postgres-1.railway.app` | MySQL service |
| MYSQLUSER | `root` | MySQL service |
| MYSQLPASSWORD | `abc123xyz` | MySQL service |
| MYSQLPORT | `3306` | MySQL service |
| MYSQL_DATABASE | `hospi` | You set this |
| REDIS_URL | `redis://default:pass@host:6379` | Redis service |
| SECRET_KEY | `your-32-char-min-random-secret` | You generate |

---

## ❌ Common Mistakes to Avoid

1. **Wrong database name** - If you named it `almarkazy`, use:
   ```
   MYSQL_DATABASE=almarkazy
   ```

2. **Missing Redis** - If app uses Redis but REDIS_URL isn't set, it will fail

3. **Not linking services** - In Railway:
   - Web service → Variables
   - Click "Link" next to MySQL service
   - Click "Link" next to Redis service
   - This auto-populates the variables

4. **Hardcoded localhost** - Remove any hardcoded `localhost` connections from code

---

## Test Variables Are Working

Railway logs should show:
```
✓ Database connection verified
✓ Column 'average_consultation_time' already exists in 'doctor'
✓ Table 'consultation_time' already exists
✓ DATABASE SCHEMA SYNCHRONIZED SUCCESSFULLY
```

If you see connection errors, variables are wrong.

---

## Get Variables From Railway Dashboard

1. Go to your project
2. Click MySQL service → Variables tab
3. Click Redis service → Variables tab
4. Inside your web service → open Variables
5. Click "Reference" on MySQL/Redis to auto-fill

This is the easiest method to avoid typos.
