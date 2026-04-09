# Average Consultation Time Feature - Implementation Guide

## Overview
This feature implements automatic tracking and calculation of average consultation times for each doctor based on "Next Patient" button clicks in the clinic management system.

## Architecture

### 1. Database Schema Changes

#### New Table: `consultation_time`
Stores individual consultation time records with the following structure:

```sql
consultation_time (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id INT FOREIGN KEY (doctor.id),
    clinic_id INT FOREIGN KEY (clinics.clinic_id),
    click_timestamp DATETIME,  # When "Next Patient" was clicked
    consultation_seconds INT,   # Valid interval in seconds
    previous_visit_id INT,      # Previous visit (optional reference)
    current_visit_id INT,       # Current visit (optional reference)
    date_recorded DATE,         # Date of consultation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### Modified Table: `doctor`
Added the following columns:

```sql
ALTER TABLE doctor ADD COLUMN (
    average_consultation_time FLOAT DEFAULT 0,    # Average in seconds
    total_consultation_seconds INT DEFAULT 0,     # Cumulative total
    consultation_count INT DEFAULT 0,             # Number of valid intervals
    last_button_click_timestamp DATETIME,         # Last "Next Patient" click
    last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Core Components

### 2. ConsultationTime Model
**File**: `/busnisess_layer/models/ConsultationTime.py`

Represents individual consultation time records in the database with relationships to:
- Doctor
- Clinic
- Previous and current visits

### 3. Consultation Time Functions
**File**: `/busnisess_layer/functions/consultation_time_func.py`

Key functions for managing consultation times:

#### `record_consultation_time(doctor_id, clinic_id, current_visit_id, previous_visit_id)`
**Purpose**: Records a consultation time when "Next Patient" button is clicked

**Logic Flow**:
1. Retrieves the doctor's last button click timestamp
2. Calculates time difference from current click
3. **Validates the interval**:
   - Ignores intervals < 60 seconds (MIN_CONSULTATION_SECONDS)
   - Ignores negative time differences (clock adjustments)
4. If valid:
   - Creates a ConsultationTime record in the database
   - Updates doctor's cumulative statistics:
     - `total_consultation_seconds += interval`
     - `consultation_count += 1`
     - `average_consultation_time = total / count`
5. Updates `last_button_click_timestamp` for next calculation
6. Returns detailed response with interval and validation status

**Returns**:
```python
{
    'success': bool,
    'message': str,
    'time_interval': int (seconds) or None,
    'stored': bool,  # Whether interval was valid/stored
    'reason': str    # Why it was accepted/rejected
}
```

**Example Scenarios**:

| Scenario | Time Diff | Action | Reason |
|----------|-----------|--------|--------|
| Doctor finishes quickly | 45 seconds | Ignored | Below 60s minimum |
| Double-click accident | 2 seconds | Ignored | Too short, accidental |
| Normal consultation | 5 minutes | Stored | Valid interval |
| Second click in session | 3 minutes | Stored | Valid interval |
| First click ever | N/A | Not stored | No previous timestamp |

#### `get_average_consultation_time(doctor_id)`
Returns current average consultation time (in seconds and minutes) for a doctor

#### `get_daily_consultation_stats(doctor_id, date)`
Returns daily statistics including min/max consultation times

#### `get_recent_consultation_times(doctor_id, limit)`
Returns most recent consultation records for analysis

#### `format_seconds_to_time_string(seconds)`
Converts seconds to human-readable format:
- `45s` → "45s"
- `180s` → "3m"
- `360s` → "6m"
- `3600s` → "1h"
- `3660s` → "1h 1m"

### 4. Integration with Doctor Route
**File**: `/precentatioin_layer/routes/doctor_route.py`

**Where Timestamps Are Recorded**:

1. **Next Patient Button** (`'next' in request.form`):
   - Records time when doctor advances to next patient
   - Called 3 times (for different scenarios):
     - First patient initialization
     - Normal next button click
     - Fallback when current visit not found

2. **Back Button** (`'back' in request.form`):
   - Records time when doctor goes back to previous patient
   - Uses same validation logic

3. **Patient Selection** (`'visit_id' in request.form`):
   - Records time when doctor selects patient from dropdown
   - Allows non-sequential patient navigation

**Example Code Flow**:
```python
# When "Next" button is clicked:
if 'next' in request.form:
    # ... patient navigation logic ...
    
    previous_visit_id = visitors[current_index].id
    next_visit_id = visitors[current_index + 1].id
    
    # Record the consultation time
    result = record_consultation_time(
        doctor_id=doctor_id,
        clinic_id=clinic_id,
        current_visit_id=next_visit_id,
        previous_visit_id=previous_visit_id
    )
    
    # Result contains validation status and interval info
    db.session.commit()
```

### 5. Patient Inquiry Display
**File**: `/precentatioin_layer/routes/patient_route.py`

When a patient searches for their appointment, the system:

1. Retrieves all doctors for the patient's visits
2. For each doctor, calls `get_average_consultation_time()`
3. Formats the result using `format_seconds_to_time_string()`
4. Adds to doctor visit data:
   ```python
   "average_consultation_seconds": float,
   "average_consultation_minutes": float,
   "average_consultation_formatted": str,  # "2m 30s"
   "consultation_count": int  # Number of valid consultations recorded
   ```

### 6. Frontend Display
**File**: `/precentatioin_layer/templates/home.html`

Average consultation time is displayed in two places:

1. **Subtitle** (next to doctor name):
   ```
   رقم الدور: 5 | د.محمد أحمد | أسنان | ⏱️ 2m 30s
   ```

2. **Meta Information Row** (more detailed):
   ```
   متوسط وقت الكشف: ⏱️ 2m 30s
   ```

Display is conditional - only shown if data is available.

## How It Works: Step-by-Step Example

### Scenario: Doctor conducting consultations

```
09:00 - Doctor starts day
        Button NOT clicked yet
        last_click = NULL
        average = 0

09:05 - Doctor clicks "Next" for first patient
        Action: Set last_click = 09:05
        Status: "First button click - no previous timestamp"
        Reason: Ignored (no baseline)
        
09:08 - Doctor clicks "Next" for second patient
        Calculation: 09:08 - 09:05 = 3 minutes = 180 seconds
        Validation: 180 > 60 ✓ Valid
        Action: Store record, update stats
        Stats update:
          - total_consultation_seconds = 180
          - consultation_count = 1
          - average_consultation_time = 180 / 1 = 180s (3 minutes)
        last_click = 09:08

09:10 - Doctor clicks "Next" for third patient (accidental double-click)
        Calculation: 09:10 - 09:08 = 2 minutes = 120 seconds
        Validation: 120 > 60 ✓ Valid
        Action: Store record
        Stats update:
          - total_consultation_seconds = 180 + 120 = 300
          - consultation_count = 2
          - average_consultation_time = 300 / 2 = 150s (2m 30s)
        last_click = 09:10

09:12 - Double-click accident (within 2 seconds)
        Calculation: 09:12 - 09:10 = 2 seconds
        Validation: 2 < 60 ✗ Invalid
        Action: Ignore record, don't update stats
        Reason: "Interval too short (2s < 60s minimum)"
        Stats unchanged, last_click updated to 09:12

09:14 - Doctor clicks "Next" legitimately
        Calculation: 09:14 - 09:12 = 2 minutes = 120 seconds
        Validation: 120 > 60 ✓ Valid
        Action: Store record
        Stats update:
          - total_consultation_seconds = 300 + 120 = 420
          - consultation_count = 3
          - average_consultation_time = 420 / 3 = 140s (2m 20s)
```

## Data Validation Rules

### Minimum Consultation Time
- **Default**: 60 seconds
- **Rationale**: Prevents counting accidental/rapid clicks
- **Configurable**: Change `MIN_CONSULTATION_SECONDS` in `consultation_time_func.py`

### Invalid Intervals (Ignored)
1. **Too short** (< 60 seconds):
   - Indicates accidental double-clicks
   - Not stored in database

2. **Negative values**:
   - System clock adjustment or server restart
   - Not stored

3. **First clock**:
   - No previous timestamp to compare
   - Not stored (only establishes baseline)

### Valid Intervals (Stored)
- Any interval >= 60 seconds
- Counted toward average calculation
- Stored for daily/historical analysis

## Key Features

### 1. Dynamic Updates
- Average updates in real-time after each button click
- No batch processing required
- Immediate availability for patient inquiries

### 2. Data Integrity
- Only valid intervals counted
- Automatic filtering of accidental inputs
- Cumulative tracking prevents recalculation

### 3. Flexibility
- Tracking works regardless of patient navigation method:
  - Next button
  - Back button
  - Dropdown selection
- Works across all clinics
- Per-doctor tracking

### 4. Historical Data
- ConsultationTime table maintains audit trail
- Supports daily/weekly/monthly reports
- Can be used for performance analytics

## Database Queries for Analysis

### Get doctor's average consultation time
```sql
SELECT 
    doctor_id,
    average_consultation_time as avg_seconds,
    (average_consultation_time / 60) as avg_minutes,
    consultation_count,
    last_button_click_timestamp
FROM doctor
WHERE doctor_id = ?;
```

### Get today's consultation count
```sql
SELECT 
    doctor_id,
    COUNT(*) as consultations_today,
    AVG(consultation_seconds) as avg_today,
    MIN(consultation_seconds) as min_today,
    MAX(consultation_seconds) as max_today
FROM consultation_time
WHERE doctor_id = ? AND DATE(date_recorded) = CURDATE();
```

### Get records that were ignored (too short)
```sql
SELECT * FROM consultation_time
WHERE consultation_seconds < 60 AND doctor_id = ?
ORDER BY date_recorded DESC;
```

## Configuration

### Minimum Consultation Time
File: `busnisess_layer/functions/consultation_time_func.py`
```python
MIN_CONSULTATION_SECONDS = 60  # Change this value as needed
```

Recommendations:
- **60 seconds**: Good for most clinics, filters obvious accidents
- **30 seconds**: More lenient, fewer filtered records
- **120 seconds**: Stricter, only counts substantial consultations

## Testing Recommendations

1. **Test accidental clicks**:
   - Click next button twice rapidly
   - Verify second interval is ignored
   - Check stats not updated

2. **Test normal flow**:
   - Click next button at normal intervals
   - Verify average updates correctly
   - Check patient page displays time

3. **Test edge cases**:
   - First click of the day
   - Long pauses between clicks
   - Clicking back button
   - Selecting from dropdown

4. **Test persistence**:
   - Verify data persists across sessions
   - Check historical data accumulation
   - Test daily reset scenarios

## Future Enhancements

1. **Weekly/Monthly Reports**: Aggregate statistics over time periods
2. **Doctor Alerts**: Notify when average drops/increases significantly
3. **Performance Metrics**: Integration with dashboard for analytics
4. **Custom Thresholds**: Allow clinic-specific minimum times
5. **Export Reports**: CSV/PDF export of consultation statistics
6. **Patterns**: Identify peak consultation hours
7. **Alerts**: Alert when doctor seems faster/slower than usual

## Files Modified/Created

### Created:
- `/busnisess_layer/models/ConsultationTime.py` - New model
- `/busnisess_layer/functions/consultation_time_func.py` - Calculation functions

### Modified:
- `/busnisess_layer/models/Doctor.py` - Added tracking fields
- `/busnisess_layer/models/__init__.py` - Added import
- `/precentatioin_layer/routes/doctor_route.py` - Added recording calls
- `/precentatioin_layer/routes/patient_route.py` - Added data retrieval
- `/precentatioin_layer/templates/home.html` - Added display

## Database Migration

Run these SQL commands to implement the schema changes:

```sql
-- Add columns to doctor table
ALTER TABLE doctor ADD COLUMN average_consultation_time FLOAT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN total_consultation_seconds INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN consultation_count INT DEFAULT 0;
ALTER TABLE doctor ADD COLUMN last_button_click_timestamp DATETIME;
ALTER TABLE doctor ADD COLUMN last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Create consultation_time table
CREATE TABLE consultation_time (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    clinic_id INT NOT NULL,
    click_timestamp DATETIME NOT NULL,
    consultation_seconds INT NOT NULL,
    previous_visit_id INT,
    current_visit_id INT,
    date_recorded DATE NOT NULL DEFAULT CURDATE(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE CASCADE,
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id) ON DELETE CASCADE,
    FOREIGN KEY (previous_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
    FOREIGN KEY (current_visit_id) REFERENCES visit(id) ON DELETE SET NULL,
    INDEX idx_doctor_date (doctor_id, date_recorded),
    INDEX idx_click_timestamp (click_timestamp)
);
```

## Troubleshooting

### Average not updating
1. Check if button clicks are happening (check `last_button_click_timestamp`)
2. Verify intervals are >= 60 seconds
3. Check Flask logs for any errors in `record_consultation_time()`

### All intervals being ignored
1. Check if all time differences are < 60 seconds
2. Verify system clock is correct (no obvious jumps)
3. Check `MIN_CONSULTATION_SECONDS` setting

### Patient page not showing average
1. Verify doctor has valid consultation records
2. Check `consultation_count` > 0 for that doctor
3. Verify template has `doc.average_consultation_formatted` variable

### Database errors
1. Ensure all migrations were run
2. Check foreign key constraints
3. Verify table column exists: `average_consultation_time`
