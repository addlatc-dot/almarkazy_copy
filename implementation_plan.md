# Deploy Almarkazy Flask App to Railway

## Overview

Your Flask application uses:
- **Flask** with blueprints (clinic, doctor, reception, patient, API)
- **MySQL** database (`hospi`)
- **Redis** (for Flask-SSE real-time events)
- **Gunicorn** as the WSGI server

Railway is a great fit — it provides managed **MySQL** and **Redis** as add-on services. We will deploy using a **Dockerfile** (which you already have, but it needs fixes).

---

## User Review Required

> [!IMPORTANT]
> Railway is a **paid service** after a short free trial ($5 credit). After the credit is used you'll need to add a payment method.

> [!WARNING]
> Your `configDB/config.py` has **hardcoded credentials** (username, password, host). We MUST switch these to **environment variables** so Railway can inject the real database URL. This requires a small code change.

> [!CAUTION]
> Your `SECRET_KEY` is currently `'your_secret_key'` — a weak, public string. We will replace it with a secure randomly-generated key set via Railway's environment variables.

---

## Proposed Changes

### 1. Fix `docker.dockerfile` → Rename to `Dockerfile`

Railway looks for a file literally named `Dockerfile` (capital D) by default.

#### [MODIFY] `docker.dockerfile` → rename to `Dockerfile`

Current problems:
- Last 3 lines (`FLASK_ENV`, `DATABASE_URL`, `REDIS_URL`) are inside the `CMD` layer — they're invalid Dockerfile syntax and do nothing.
- Uses `geventwebsocket` worker which is **not in `requirements.txt`** (will crash on deploy).
- `PORT` variable syntax `${PORT:-5000}` is shell syntax — needs `sh -c` wrapper.

**New content:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 app:app
```

---

### 2. Fix `configDB/config.py` — Use Environment Variables

#### [MODIFY] [config.py](file:///home/namish/almarkazy%20(Copy)/configDB/config.py)

Switch from hardcoded DB credentials to `DATABASE_URL` env var (Railway sets this automatically when you link a MySQL plugin).

```python
import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://almarkazy:almarkazypass@localhost/hospi'  # local fallback
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
```

---

### 3. Fix `app.py` — Use Environment Variables for Redis

#### [MODIFY] [app.py](file:///home/namish/almarkazy%20(Copy)/app.py)

Already reads `REDIS_URL` from env — this is correct ✅. No change needed here.

---

### 4. Fix `requirements.txt` — Add `eventlet`

#### [MODIFY] [requirements.txt](file:///home/namish/almarkazy%20(Copy)/requirements.txt)

The Dockerfile uses `gunicorn` with `eventlet` worker (needed for Flask-SocketIO). Add:
```
eventlet==0.38.2
```

---

### 5. Fix `.gitignore` — Add Sensitive Files

#### [MODIFY] [.gitignore](file:///home/namish/almarkazy%20(Copy)/.gitignore)

Currently only ignores `*.env`. Must also ignore:
```
.env
*.pem
__pycache__/
*.pyc
.venv/
venv/
almarkazyenv/
*.sql
```

> [!CAUTION]
> Your `almarkazySC_key.pem` SSH key is currently NOT in gitignore. It will be pushed to GitHub and exposed publicly! We must add `*.pem` to `.gitignore`.

---

### 6. Create `.env` file (local use only — NOT committed)

For local development, create a `.env` file:
```
DATABASE_URL=mysql+pymysql://almarkazy:almarkazypass@localhost/hospi
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=a-very-long-random-secret-key
```

---

## Open Questions

> [!IMPORTANT]
> Do you have a **GitHub account** with this project already pushed, or do we need to set that up first? Railway deploys from GitHub repositories.

> [!IMPORTANT]
> Your MySQL database (`hospi`) has existing data. Do you want to:
> - **A)** Start fresh with an empty database on Railway (tables auto-created by SQLAlchemy), OR
> - **B)** Import your existing data from `almarkazy.sql` into the Railway MySQL instance?

---

## Deployment Steps (After Code Fixes)

1. Push code to a **GitHub repository**
2. Go to [railway.app](https://railway.app) → sign in with GitHub
3. Create a **New Project** → **Deploy from GitHub repo**
4. Add **MySQL plugin** → Railway auto-sets `DATABASE_URL`
5. Add **Redis plugin** → Railway auto-sets `REDIS_URL`
6. Set environment variable: `SECRET_KEY` = (a strong random string)
7. Railway auto-detects `Dockerfile` and builds/deploys
8. (Optional) Import SQL dump to the Railway MySQL instance

## Verification Plan

- Visit the Railway-provided URL
- Test login for clinic, doctor, and reception accounts
- Verify real-time SSE events still work (patient updates)
- Monitor Railway logs for any startup errors
