"""
Consultation Time Tracking and Calculation Module

This module handles:
1. Recording timestamps when "Next Patient" button is clicked
2. Calculating time differences between consecutive clicks
3. Filtering out invalid intervals (< 60 seconds, duplicates)
4. Calculating and updating average consultation time
5. Storing valid consultation time records
"""

from datetime import datetime, timedelta
from configDB.config import db
from busnisess_layer.models import ConsultationTime, Doctor, Visit


# Minimum consultation time in seconds (invalid intervals shorter than this are ignored)
MIN_CONSULTATION_SECONDS = 60


def record_consultation_time(doctor_id, clinic_id, current_visit_id=None, previous_visit_id=None):
    """
    Records a consultation time when the doctor clicks "Next Patient".
    
    Args:
        doctor_id (int): ID of the doctor
        clinic_id (int): ID of the clinic
        current_visit_id (int, optional): Current visit ID
        previous_visit_id (int, optional): Previous visit ID
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'time_interval': int or None,  # Seconds between clicks
            'stored': bool,  # Whether the interval was stored (valid or not)
            'reason': str  # Why it was/wasn't stored
        }
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return {
                'success': False,
                'message': 'Doctor not found',
                'time_interval': None,
                'stored': False,
                'reason': 'Doctor does not exist'
            }
        
        current_time = datetime.utcnow().today()
        time_interval = None
        was_stored = False
        reason = ''
        
        # Check if there's a previous click timestamp
        if doctor.last_button_click_timestamp and doctor.last_button_click_timestamp.date() == current_time.date():
            # Calculate time difference
            time_diff = current_time - doctor.last_button_click_timestamp
            time_interval = int(time_diff.total_seconds())
            
           
            # last_click = doctor.last_button_click_timestamp
            # if doctor.last_button_click_timestamp and doctor.last_button_click_timestamp.date() == date.today():
            #     time_diff= current_time - doctor.last_button_click_timestamp
            #     time_interval = int(time_diff.total_seconds())
            # else:
            #     time_interval = 0

            # Validate the interval
            if time_interval < MIN_CONSULTATION_SECONDS:
                reason = f'Interval too short ({time_interval}s < {MIN_CONSULTATION_SECONDS}s minimum)'
                was_stored = False
            elif time_interval < 0:
                reason = 'Time interval is negative (clock adjustment?)'
                was_stored = False
            else:
                # Valid interval - store it
                consultation_record = ConsultationTime(
                    doctor_id=doctor_id,
                    clinic_id=clinic_id,
                    click_timestamp=current_time,
                    consultation_seconds=time_interval,
                    previous_visit_id=previous_visit_id,
                    current_visit_id=current_visit_id,
                    date_recorded=current_time.date()
                )
                db.session.add(consultation_record)
                db.session.flush()  # Ensure it's available for the query
                
                was_stored = True
                reason = 'Valid interval recorded'
                
                # ⏱️ Update doctor stats with ONLY TODAY'S LAST 5 RECORDS (not all-time)
                from datetime import date
                today = date.today()
                
                # Get today's records only, ordered by most recent first
                today_records = ConsultationTime.query.filter(
                    ConsultationTime.doctor_id == doctor_id,
                    ConsultationTime.date_recorded == today
                ).order_by(ConsultationTime.click_timestamp.desc()).all()
                
                # Use only the LAST 5 from today
                last_5_today = today_records[:5]
                
                if last_5_today:
                    # Calculate ONLY from today's last 5
                    total_today = sum(r.consultation_seconds for r in last_5_today)
                    count_today = len(last_5_today)
                    average_today = total_today / count_today
                    
                    # Set (NOT increment) the daily counters
                    doctor.total_consultation_seconds = total_today
                    doctor.consultation_count = count_today
                    doctor.average_consultation_time = average_today
                    
                    print(f"📊 Updated doctor {doctor_id} stats: total={total_today}s, count={count_today}, avg={round(average_today, 2)}s")
                else:
                    # If no records exist yet, just use this one
                    doctor.total_consultation_seconds = time_interval
                    doctor.consultation_count = 1
                    doctor.average_consultation_time = time_interval
        else:
            reason = 'First button click - no previous timestamp to compare'
            was_stored = False
        
        # Update the last button click timestamp
        doctor.last_button_click_timestamp = current_time
        doctor.last_update_time = current_time
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Timestamp recorded. {"Interval stored." if was_stored else "Interval ignored."}',
            'time_interval': time_interval,
            'stored': was_stored,
            'reason': reason
        }
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error recording consultation time: {str(e)}',
            'time_interval': None,
            'stored': False,
            'reason': str(e)
        }


def get_average_consultation_time(doctor_id):
    """
    Gets the current average consultation time for a doctor.
    
    Args:
        doctor_id (int): ID of the doctor
    
    Returns:
        dict: {
            'doctor_id': int,
            'average_seconds': float,
            'average_minutes': float,
            'total_consultations': int,
            'count': int,
            'last_updated': datetime
        }
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return None
        
        average_minutes = doctor.average_consultation_time / 60 if doctor.average_consultation_time else 0
        
        # Get daily statistics
        daily_stats = get_daily_consultation_stats(doctor_id)
        daily_avg_seconds = daily_stats['average_seconds'] if daily_stats else 0
        
        return {
            'doctor_id': doctor_id,
            'average_seconds': round(doctor.average_consultation_time, 2),
            'average_minutes': round(average_minutes, 2),
            'daily_average_seconds': round(daily_avg_seconds, 2),
            'daily_average_formatted': format_seconds_to_time_string(daily_avg_seconds),
            'total_consultations': doctor.total_consultation_seconds,
            'count': doctor.consultation_count,
            'last_updated': doctor.last_update_time
        }
    
    except Exception as e:
        return None


def get_daily_consultation_stats(doctor_id, date_filter=None):
    """
    Gets consultation statistics for a specific day (LAST 5 RECORDS ONLY).
    
    Args:
        doctor_id (int): ID of the doctor
        date_filter (date, optional): Date to filter by (default: today)
    
    Returns:
        dict with daily statistics based on last 5 consultations only
    """
    try:
        from datetime import date
        
        if date_filter is None:
            date_filter = date.today()
        
        # Get ALL records for today
        all_records = ConsultationTime.query.filter(
            ConsultationTime.doctor_id == doctor_id,
            ConsultationTime.date_recorded == date_filter
        ).order_by(ConsultationTime.click_timestamp.desc()).all()
        
        # Use only the LAST 5 records
        records = all_records[:5]
        
        if not records:
            return {
                'doctor_id': doctor_id,
                'date': date_filter,
                'count': 0,
                'total_seconds': 0,
                'average_seconds': 0,
                'average_minutes': 0,
                'min_seconds': None,
                'max_seconds': None
            }
        
        seconds_list = [r.consultation_seconds for r in records]
        total = sum(seconds_list)
        count = len(seconds_list)
        average = total / count if count > 0 else 0
        
        return {
            'doctor_id': doctor_id,
            'date': date_filter,
            'count': count,
            'total_seconds': total,
            'average_seconds': round(average, 2),
            'average_minutes': round(average / 60, 2),
            'min_seconds': min(seconds_list),
            'max_seconds': max(seconds_list),
            'records': records
        }
    
    except Exception as e:
        return None


def get_recent_consultation_times(doctor_id, limit=10):
    """
    Gets the most recent consultation time records for a doctor.
    
    Args:
        doctor_id (int): ID of the doctor
        limit (int): Number of records to return
    
    Returns:
        list of ConsultationTime objects
    """
    try:
        records = ConsultationTime.query.filter_by(doctor_id=doctor_id).order_by(
            ConsultationTime.click_timestamp.desc()
        ).limit(limit).all()
        
        return records
    
    except Exception as e:
        return []


def reset_doctor_consultation_stats(doctor_id):
    """
    Resets all consultation statistics for a doctor.
    
    Args:
        doctor_id (int): ID of the doctor
    
    Returns:
        bool: Success status
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return False
        
        # Delete all consultation time records
        ConsultationTime.query.filter_by(doctor_id=doctor_id).delete()
        
        # Reset doctor stats
        doctor.average_consultation_time = 0
        doctor.total_consultation_seconds = 0
        doctor.consultation_count = 0
        doctor.last_button_click_timestamp = None
        doctor.last_update_time = datetime.utcnow()
        
        db.session.commit()
        return True
    
    except Exception as e:
        db.session.rollback()
        return False


def reset_daily_consultation_counters():
    """
    Resets daily consultation counters for ALL doctors at end of day.
    Call this function at midnight (23:59:59) using a scheduled task.
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'doctors_reset': int (count of doctors reset)
        }
    """
    try:
        from datetime import date
        from busnisess_layer.models import Doctor
        
        # Get all doctors
        doctors = Doctor.query.all()
        reset_count = 0
        
        for doctor in doctors:
            # Reset the daily counters to zero
            doctor.total_consultation_seconds = 0
            doctor.consultation_count = 0
            doctor.average_consultation_time = 0
            doctor.last_button_click_timestamp = None
            doctor.last_update_time = datetime.utcnow()
            reset_count += 1
        
        db.session.commit()
        
        print(f"✅ Reset consultation counters for {reset_count} doctors at end of day")
        
        return {
            'success': True,
            'message': f'Successfully reset counters for {reset_count} doctors',
            'doctors_reset': reset_count
        }
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error resetting counters: {str(e)}',
            'doctors_reset': 0
        }


def format_seconds_to_time_string(seconds):
    """
    Formats seconds into a human-readable time string (hours and minutes only, no seconds).
    
    Args:
        seconds (int or float): Number of seconds
    
    Returns:
        str: Formatted time string (e.g., "5m" or "1h 5m")
    """
    if not seconds or seconds < 0:
        return "—"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return "< 1m"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining = seconds % 3600
        minutes = remaining // 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"


def get_all_doctors_average_consultation_times(clinic_id=None):
    """
    Gets average consultation times for all doctors (optionally filtered by clinic).
    
    Args:
        clinic_id (int, optional): Filter by clinic ID
    
    Returns:
        list of dicts with doctor average consultation times
    """
    try:
        query = Doctor.query
        
        if clinic_id:
            query = query.filter_by(clinic_id=clinic_id)
        
        doctors = query.all()
        
        result = []
        for doctor in doctors:
            avg = get_average_consultation_time(doctor.id)
            if avg:
                result.append(avg)
        
        return result
    
    except Exception as e:
        return []
