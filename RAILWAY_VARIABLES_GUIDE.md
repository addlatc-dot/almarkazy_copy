# How to Set Environment Variables in Railway

## 🎯 Quick Overview

Railway automatically creates some variables (like `DATABASE_URL` and `REDIS_URL`), but you need to manually add a few more.

---

## 📍 Where to Find Variables Section

### **Path in Railway Dashboard:**
```
Your Project → App Service → Variables (left sidebar)
```

### **Visual Steps:**

1. **Open Railway Dashboard**
   - Go to: https://railway.app/dashboard

2. **Select Your Project**
   - Click on your `almarkazy` project card

3. **Select App Service**
   - You'll see 3 service cards: App, MySQL, Redis
   - Click on the **App service** (Flask app)

4. **Click "Variables" Tab**
   - Left sidebar: Look for "Variables" option
   - Click it

---

## ➕ How to Add a Variable

### **Method 1: Simple Input (Easiest)**

1. In the **Variables** tab, click **"Add Variable"** button (or **"+"** icon)
2. You'll see two input fields:
   - **Left field**: Variable name (e.g., `FLASK_ENV`)
   - **Right field**: Variable value (e.g., `production`)
3. Type the name and value
4. Click **"✓"** checkmark or press **Enter**
5. Variable is saved automatically! ✅

### **Method 2: Copy-Paste from File**

If you have many variables:

1. Click **"Edit as RAW"** or similar option
2. You can paste multiple variables at once
3. Format: `KEY=VALUE` (one per line)
4. Click **"Save"**

---

## 📋 Variables You Need to Add

### **1️⃣ FLASK_ENV**
```
Name:  FLASK_ENV
Value: production
```
- Tells Flask to run in production mode (no debug)

### **2️⃣ SECRET_KEY** (⚠️ IMPORTANT)
```
Name:  SECRET_KEY
Value: [GENERATE A RANDOM STRING - see below]
```

**How to generate SECRET_KEY:**

Option A: Use Railway's generator
- Click the **"🔄 Generate"** button next to the input field
- Railway creates a random string automatically

Option B: Generate locally in terminal
- Run this command in your terminal:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- Copy the output (looks like: `abc123XyZ_abc123XyZ_abc123XyZ`)
- Paste as the value in Railway

### **3️⃣ PORT**
```
Name:  PORT
Value: 8080
```
- Tells the app which port to listen on

### **4️⃣ SQLALCHEMY_TRACK_MODIFICATIONS** (Optional)
```
Name:  SQLALCHEMY_TRACK_MODIFICATIONS
Value: False
```
- Prevents SQLAlchemy from sending signals (improves performance)

---

## 🔗 Auto-Generated Variables (Already Set by Railway)

These are created automatically when you add MySQL and Redis services:

### **DATABASE_URL**
- ✅ **Automatically set by Railway** when you add MySQL
- Format: `mysql+pymysql://user:password@host:port/database`
- Your app automatically reads this
- **No action needed** ✅

### **REDIS_URL**
- ✅ **Automatically set by Railway** when you add Redis
- Format: `redis://user:password@host:port/database`
- Your app automatically reads this
- **No action needed** ✅

---

## 📸 Step-by-Step Screenshots (Text Version)

### **Screen 1: Variables Tab**
```
┌─────────────────────────────────────────┐
│  App Service Dashboard                  │
├─────────────────────────────────────────┤
│ Left Sidebar:                           │
│  • Settings                             │
│  ► Variables  ◄─ CLICK HERE            │
│  • Logs                                 │
│  • Deploy                               │
│  • Connect                              │
└─────────────────────────────────────────┘
```

### **Screen 2: Variables Editor**
```
┌─────────────────────────────────────────┐
│  Variables                              │
├─────────────────────────────────────────┤
│  [+ Add Variable] button                │
│                                         │
│  Existing Variables:                    │
│  DATABASE_URL = mysql+pymysql://...    │
│  REDIS_URL = redis://...                │
│  (These are auto-set by Railway)       │
└─────────────────────────────────────────┘
```

### **Screen 3: Add Variable Dialog**
```
┌─────────────────────────────────────────┐
│  Add Variable                           │
├─────────────────────────────────────────┤
│  Name:  [FLASK_ENV____________]        │
│  Value: [production____________]       │
│                                         │
│  [Cancel]  [Add Variable]              │
└─────────────────────────────────────────┘
```

---

## ✅ Complete Variable Setup Example

After adding all variables, your Variables section should show:

```
DATABASE_URL       mysql+pymysql://user:pass@...  (auto-set)
REDIS_URL          redis://user:pass@...          (auto-set)
FLASK_ENV          production                      (you added)
SECRET_KEY         abc123XyZ_abc123XyZ_abc...     (you added)
PORT               8080                            (you added)
SQLALCHEMY_TM      False                           (optional)
```

---

## 🔄 Update a Variable Later

1. Go to **Variables** tab
2. Find the variable you want to change
3. Click the **⚙️ (settings)** icon or the value field
4. Edit it
5. Click **"✓"** or **"Update"**
6. App automatically restarts with new value ✅

---

## 🚨 Common Mistakes to Avoid

❌ **Mistake 1:** Using single quotes in values
- ❌ Don't: `'production'`
- ✅ Do: `production`

❌ **Mistake 2:** Leaving SECRET_KEY as default
- ❌ Don't: `dev-secret-key-change-me`
- ✅ Do: Generate a random string

❌ **Mistake 3:** Forgetting DATABASE_URL
- ✅ It's auto-set by Railway, no action needed
- Just verify it's there in the Variables list

❌ **Mistake 4:** Wrong variable names (case-sensitive)
- ❌ Don't: `flask_env` or `Flask_Env`
- ✅ Do: `FLASK_ENV` (exact case)

---

## 🔒 Security Tips

1. **Never commit `.env` files to GitHub**
   - ✅ Already in `.gitignore`

2. **Use complex SECRET_KEY**
   - Generate with `secrets.token_urlsafe(32)`
   - At least 32 characters

3. **Rotate SECRET_KEY if leaked**
   - Generate a new one
   - Update in Railway Variables

4. **Don't share Railway dashboard link**
   - Anyone with access can see variables

---

## ❓ FAQ About Variables

**Q: Why is DATABASE_URL already set?**
A: When you add MySQL service to the project, Railway automatically creates and configures the DATABASE_URL variable.

**Q: Can I see the auto-generated DATABASE_URL value?**
A: Yes! Go to MySQL service → Variables tab → You'll see the full connection string.

**Q: What if I make a typo in a variable?**
A: Just edit it again and fix the typo. App will restart automatically.

**Q: Do I need to restart the app after changing variables?**
A: No, Railway automatically restarts the app with new variables.

**Q: Can I use the same SECRET_KEY across multiple apps?**
A: Not recommended. Generate a unique SECRET_KEY for each app.

---

## ✨ Next Steps

1. ✅ Go to Railway dashboard
2. ✅ Click your app service
3. ✅ Go to **Variables** tab
4. ✅ Add these 4 variables:
   - FLASK_ENV = production
   - SECRET_KEY = [generated string]
   - PORT = 8080
   - SQLALCHEMY_TRACK_MODIFICATIONS = False
5. ✅ Verify DATABASE_URL and REDIS_URL are already there
6. ✅ Monitor app logs to confirm it starts correctly

---

## 🆘 Troubleshooting

**Problem: "Variable not updating in my app"**
- Solution: Wait 30 seconds for app to restart
- Check Logs tab to see if restart happened

**Problem: "Can't find Variables tab"**
- Solution: Make sure you're in the **App service**, not MySQL/Redis

**Problem: "DATABASE_URL not showing"**
- Solution: Make sure you added MySQL service first
- Go to MySQL service → Variables → Copy DATABASE_URL manually

**Problem: "App keeps crashing after adding variable"**
- Solution: Check the value doesn't have quotes or special chars
- Go to Logs tab to see the error message

