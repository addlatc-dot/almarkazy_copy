# Daily Reset Guide - Consultation Time Averaging

## What Changed

The consultation time averaging system has been updated to:

### ✅ **Before**
- Summed ALL consultation times (entire history)
- Divided by ALL counts (entire history)
- No automatic reset

### ✅ **After**
- Sums **only the LAST 5 consultations today**
- Divides by **count of those 5 visits**
- Can reset counters daily at midnight

---

## How It Works

### 1. **Calculation Logic**
When calculating `average_consultation_formatted` and `daily_average_formatted`:

```
Average = (Sum of Last 5 Consultations Today) / 5
```

**Example:**
- Last 5 consultation times today: 10m, 12m, 8m, 11m, 9m
- Sum = 50 minutes
- Average = 50 / 5 = **10 minutes**

---

### 2. **Backend Functions**

#### `get_daily_consultation_stats(doctor_id, date_filter=None)`
- Gets all consultation records for a specific date
- **Uses ONLY the last 5 records**
- Returns average based on those 5

#### `reset_daily_consultation_counters()`
- Resets for **ALL doctors** at once
- Clears these columns to ZERO:
  - `total_consultation_seconds`
  - `consultation_count`
  - `average_consultation_time`
  - `last_button_click_timestamp`

---

## How to Schedule Daily Reset

### **Option 1: Using Cron Job (Linux/Mac)**

Add to `/etc/crontab` or use `crontab -e`:

```bash
# Reset counters daily at 23:59 (11:59 PM)
59 23 * * * curl -X POST http://localhost:5000/admin/reset_daily_counters \
  -H "Authorization: Bearer your-secret-token-here"
```

Or for Docker container:
```bash
docker exec almarkazy-container curl -X POST http://localhost:5000/admin/reset_daily_counters \
  -H "Authorization: Bearer your-secret-token-here"
```

### **Option 2: Using Windows Task Scheduler**

1. Create a `.bat` file with:
```batch
curl -X POST http://localhost:5000/admin/reset_daily_counters ^
  -H "Authorization: Bearer your-secret-token-here"
```

2. Schedule it in Task Scheduler for 23:59 daily

### **Option 3: Manual Reset**

Call the endpoint manually whenever needed:
```bash
curl -X POST http://localhost:5000/admin/reset_daily_counters \
  -H "Authorization: Bearer ADMIN_RESET_TOKEN_VALUE"
```

---

## Security Setup

### **Step 1: Set Environment Variable**

Add to your `.env` file or Docker environment:

```env
ADMIN_RESET_TOKEN=your-super-secret-token-12345
```

### **Step 2: Use the Token**

In all reset requests, use:
```bash
Authorization: Bearer your-super-secret-token-12345
```

---

## Database Schema Requirements

Ensure your Doctor table has these columns:

```sql
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS `total_consultation_seconds` INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS `consultation_count` INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS `average_consultation_time` FLOAT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS `last_button_click_timestamp` DATETIME NULL;
ALTER TABLE doctor ADD COLUMN IF NOT EXISTS `last_update_time` DATETIME DEFAULT CURRENT_TIMESTAMP;
```

---

## API Endpoint

### **Endpoint:** `POST /admin/reset_daily_counters`

**Headers Required:**
```
Authorization: Bearer ADMIN_RESET_TOKEN
```

**Response Success (200):**
```json
{
  "success": true,
  "message": "Successfully reset counters for 12 doctors",
  "doctors_reset": 12
}
```

**Response Failure (401):**
```json
{
  "success": false,
  "message": "Unauthorized - valid token required"
}
```

---

## What Gets Reset at Midnight

For **EACH DOCTOR**:

| Column | Before Reset | After Reset |
|--------|-------------|------------|
| `total_consultation_seconds` | Various numbers | 0 |
| `consultation_count` | Various numbers | 0 |
| `average_consultation_time` | Calculated average | 0 |
| `last_button_click_timestamp` | Last timestamp | NULL |
| `last_update_time` | Old timestamp | Current UTC time |

**ConsultationTime records:** ✅ **NOT deleted** - kept for historical tracking

---

## Testing the Reset

### **Test 1: Before Reset**
```python
# In Python console or API
doctor = Doctor.query.get(1)
print(f"Avg: {doctor.average_consultation_time}")  # Should have value
print(f"Count: {doctor.consultation_count}")       # Should have value
```

### **Test 2: Trigger Reset**
```bash
curl -X POST http://localhost:5000/admin/reset_daily_counters \
  -H "Authorization: Bearer your-token"
```

### **Test 3: After Reset**
```python
doctor = Doctor.query.get(1)
print(f"Avg: {doctor.average_consultation_time}")  # Should be 0
print(f"Count: {doctor.consultation_count}")       # Should be 0
```

---

## Troubleshooting

### ❌ **Reset endpoint returns 401 Unauthorized**
- Check if `ADMIN_RESET_TOKEN` is set in environment
- Verify token matches in Authorization header
- Use `echo $ADMIN_RESET_TOKEN` to verify

### ❌ **Average showing old values**
- Reset wasn't triggered at midnight
- Manually call the endpoint
- Check logs: `tail -f logs/app.log`

### ❌ **Database errors**
- Ensure columns exist in `doctor` table
- Run the SQL ALTER statements (see above)
- Check database connection

---

## Example Cron Setup with Logging

For better debugging, save to a file:

```bash
# /home/user/reset_consultation.sh
#!/bin/bash
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] Starting consultation counter reset..." >> /var/log/consultation_reset.log
curl -s -X POST http://localhost:5000/admin/reset_daily_counters \
  -H "Authorization: Bearer your-secret-token-12345" >> /var/log/consultation_reset.log 2>&1
echo "[$TIMESTAMP] Reset completed." >> /var/log/consultation_reset.log
```

Then in crontab:
```bash
59 23 * * * /bin/bash /home/user/reset_consultation.sh
```

---

## Verification Checklist

- [x] Updated `get_daily_consultation_stats()` to use last 5 only
- [x] Added `reset_daily_consultation_counters()` function
- [x] Added `/admin/reset_daily_counters` endpoint
- [x] Set `ADMIN_RESET_TOKEN` environment variable
- [x] Scheduled daily reset at 23:59
- [x] Tested reset functionality
- [x] Verified database columns exist

---
