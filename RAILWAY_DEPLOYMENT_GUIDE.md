# Railway Deployment Guide for Almarkazy

## ✅ Pre-Deployment Checklist
- ✅ Code committed to GitHub branch `v1.0`
- ✅ Dockerfile created and ready
- ✅ Environment variables configured
- ✅ `.gitignore` updated (protects `.pem` files)

---

## 📋 Step-by-Step Deployment Instructions

### **STEP 1: Create Railway Account**
**Duration: 2 minutes**

1. Open browser and go to: https://railway.app
2. Click **"Start Free"** button
3. Click **"Sign in with GitHub"**
4. You'll see: `Authorize railwayapp to access your account`
5. Click **"Authorize railwayapp"**
6. GitHub will ask to authenticate — sign in with your GitHub credentials
7. You're now logged into Railway ✅

---

### **STEP 2: Create New Project & Deploy from GitHub**
**Duration: 3-5 minutes**

1. On Railway dashboard, click **"New Project"** (top right)
2. Select **"Deploy from GitHub repo"**
3. Click **"Connect GitHub"** (if not already connected)
   - Authorize Railway to access your repositories
4. Search for: `almarkazy_copy`
5. Find the repo in the list and click it
6. Select branch: **`v1.0`**
7. Click **"Deploy"**

**What happens:**
- Railway detects your `Dockerfile`
- Starts building Docker image (takes 2-3 minutes)
- You'll see build logs in real-time

---

### **STEP 3: Add MySQL Database Service**
**Duration: 1 minute**

1. In your Railway project, look for your **app service** card
2. Click the **"+"** button or **"Create"** → **"Add Service"**
3. Select **"Database"**
4. Choose **"MySQL"**
5. Click **"Create"**
6. Wait for MySQL to spin up (takes ~30 seconds)

**What Railway does automatically:**
- Creates MySQL database
- Sets `DATABASE_URL` environment variable automatically ✅
- No manual configuration needed!

---

### **STEP 4: Add Redis Cache Service**
**Duration: 1 minute**

1. Click **"+"** again or **"Create"** → **"Add Service"**
2. Select **"Database"**
3. Choose **"Redis"**
4. Click **"Create"**
5. Wait for Redis to spin up

**What Railway does automatically:**
- Creates Redis instance
- Sets `REDIS_URL` environment variable automatically ✅

---

### **STEP 5: Configure Environment Variables**
**Duration: 2 minutes**

1. Click on your **app service** (the Flask one)
2. Go to **"Variables"** tab (on the left sidebar)
3. Click **"Add Variable"** and add these one by one:

   **Variable 1: FLASK_ENV**
   - Key: `FLASK_ENV`
   - Value: `production`
   - Click ✓

   **Variable 2: PORT** (optional, already set)
   - Key: `PORT`
   - Value: `8080`
   - Click ✓

   **Variable 3: SECRET_KEY** (⚠️ IMPORTANT)
   - Key: `SECRET_KEY`
   - Value: Generate a secure random string:
     - Open another terminal and run:
       ```bash
       python -c "import secrets; print(secrets.token_urlsafe(32))"
       ```
     - Copy the output and paste as the value
   - Click ✓

   **Variable 4: SQLALCHEMY_TRACK_MODIFICATIONS** (optional)
   - Key: `SQLALCHEMY_TRACK_MODIFICATIONS`
   - Value: `False`
   - Click ✓

---

### **STEP 6: Wait for Build to Complete**
**Duration: 5-10 minutes**

1. Go back to your project view
2. Click on your **app service**
3. Check **"Deploy"** tab — watch the build logs
4. You should see:
   ```
   ✓ Build successful
   ✓ Deployment successful
   ```
5. One green **checkmark** = Ready to go ✅

---

### **STEP 7: Get Your Public URL**
**Duration: 1 minute**

1. In your **app service**, go to **"Settings"** tab
2. Look for **"Domains"** section
3. You'll see something like:
   ```
   https://almarkazy-production.up.railway.app
   ```
4. Click it to open your app! 🎉

**Or alternate method:**
- Click **"Open in browser"** button directly

---

### **STEP 8: Import Your Existing Database (OPTIONAL)**
**Duration: 5-10 minutes**

If you want to restore your existing `almarkazy.sql` data:

**Option A: Using Railway Data Tab (EASIEST)**
1. Click on **MySQL service**
2. Go to **"Data"** tab
3. Look for **"Import"** button
4. Select your `almarkazy.sql` file
5. Railway imports automatically ✅

**Option B: Using MySQL CLI**
1. Click on **MySQL service**
2. Go to **"Connect"** tab
3. Copy the **MySQL connection string**
4. In your terminal, run:
   ```bash
   cd "/home/namish/almarkazy (Copy)"
   mysql -h [host] -u [user] -p [password] [database] < almarkazy.sql
   ```
   - Replace `[host]`, `[user]`, `[password]`, `[database]` from the connection string

---

### **STEP 9: Test Your Deployment**
**Duration: 2-3 minutes**

1. Open your Railway URL in browser
2. You should see your Almarkazy home page
3. Test login with your clinic/doctor/reception credentials:
   - **Clinic Login**: Test accessing clinic management
   - **Doctor Login**: Test doctor dashboard
   - **Reception Login**: Test reception functions

**If there are errors:**
1. Click **app service** → **"Logs"** tab
2. Look for error messages
3. Common issues:
   - Database not connected: Check `DATABASE_URL` variable
   - Redis not working: Check `REDIS_URL` variable
   - Port issues: Make sure PORT=8080

---

## 📊 Deployment Status Checklist

After all steps, verify:

- [ ] Railway account created ✅
- [ ] Project deployed from GitHub ✅
- [ ] Dockerfile detected and built ✅
- [ ] MySQL service running ✅
- [ ] Redis service running ✅
- [ ] Environment variables set ✅
- [ ] App accessible at public URL ✅
- [ ] Database imported (if applicable) ✅
- [ ] App pages load without errors ✅

---

## 🔗 Useful Railway Links

- **Project Dashboard**: https://railway.app/dashboard
- **My Projects**: https://railway.app/dashboard/projects
- **Documentation**: https://docs.railway.app/

---

## ⚠️ Important Notes

1. **Free Tier**: Railway gives you $5 free credit. After that, you need a payment method.
2. **Sleepy deployments**: If your app is inactive for 7 days, Railway spins it down (free tier). Active use keeps it running.
3. **Database costs**: MySQL and Redis have minimal costs (~$1-5/month depending on usage).
4. **Scale up later**: As your app grows, you can upgrade resources through Railway dashboard.

---

## 📞 Troubleshooting

**Problem: "Unauthorized" when deploying**
- Solution: Re-authenticate GitHub in Railway settings

**Problem: "Database connection error"**
- Check MySQL service is running
- Verify `DATABASE_URL` is set in variables
- Check database name matches your `.sql` file

**Problem: "Redis connection error"**
- Check Redis service is running
- Verify `REDIS_URL` is set in variables

**Problem: App crashes after deployment**
- Check **Logs** tab for error messages
- Verify all environment variables are set
- Make sure `Dockerfile` has correct entry point

---

## ✅ You're Done! 🎉

Your Almarkazy app is now live on the internet and accessible to anyone with the URL!

**Next steps:**
- Share the public URL with users
- Monitor the app health in Railway dashboard
- Upgrade plan when needed

