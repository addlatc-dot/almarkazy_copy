from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.functions.consultation_time_func import (
    get_average_consultation_time, 
    format_seconds_to_time_string
)
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit
)


from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta

patientBP = Blueprint('patientBP',__name__)


@patientBP.route('/doctor/select_patient', methods=['POST'])
def select_patient():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return redirect(url_for('doctor_login'))
    
    visit_id = request.form.get('visit_id')
    if visit_id:
        visit = Visit.query.get(visit_id)
        if visit and visit.doctor_id == doctor_id:
            # تخزين visit_id في الجلسة بدلاً من patient_id في قاعدة البيانات
            session['current_visit_id'] = visit.id
    
    return redirect(url_for('doctor_home'))


# Routes for Patients
@patientBP.route('/patient', methods=['GET', 'POST'])
def patient():
    status_message = None
    results = []
    visit_date = date.today()
    patient_found = None

    def normalize_arabic(text):
        if not text:
            return ''
        text = re.sub(r'[إأآا]', 'ا', text)
        text = re.sub(r'[ى]', 'ي', text)
        text = re.sub(r'[ئ]', 'ي', text)
        text = re.sub(r'[ؤ]', 'و', text)
        text = re.sub(r'[ة]', 'ه', text)
        text = re.sub(r'[\u064B-\u0652]', '', text)  # Remove diacritics
        return text

    request.method == 'POST'
    name = request.form['name']
    normalized_input = normalize_arabic(name)
    phone = request.form['phone']
    id = request.form['phone']

    query = Visit.query.filter(or_(Visit.normalized_name == normalized_input , Visit.patient_name==name))
    if phone or id : 
        query = query.filter(or_(Visit.patient_phone == phone , Visit.patient_id == id ))
      
    patient_found = query.first()
      # Check if the patient exists
    

    if patient_found:
        # Fetch all visits for the patient today
        visits = Visit.query.filter(
            Visit.patient_id == patient_found.patient_id,
            Visit.normalized_name.ilike(f"%{normalized_input}%"),
            func.date(Visit.visit_date) == visit_date
        ).order_by(Visit.visit_date.desc()).all()
    else:
        # Try without patient_id if not found
        visits = Visit.query.filter(
            Visit.normalized_name.ilike(f"%{normalized_input}%"),
            Visit.patient_phone == phone,
            func.date(Visit.visit_date) == visit_date
        ).all()

    if visits:
        # Group visits by doctor
        doctor_visits = {}
        for visit in visits:
            doctor = Doctor.query.get(visit.doctor_id)
            section = Section.query.get(doctor.section_id) if doctor else None
            
            # Get all confirmed and finished patients for this doctor today
            current_patients = Visit.query.filter(
                Visit.doctor_id == visit.doctor_id,
                func.date(Visit.visit_date) == visit_date,
                or_(Visit.visit_status == "مؤكد", Visit.visit_status == "منتهي")
            ).order_by(Visit.visit_date).all()

            # Determine current position (only among confirmed patients)
            try:
                patient_index = next((i + 1 for i, v in enumerate(current_patients) if v.patient_id == visit.patient_id), None)
            except ValueError:
                patient_index = None

            try:
                current_patient_index = next((i + 1 for i, v in enumerate(current_patients) if v.patient_id == doctor.current_patient), None) if doctor and doctor.current_patient else None
            except ValueError:
                current_patient_index = None

            # Get original queue position (never changes)
            original_queue_position = visit.queue_position

            # Calculate patients ahead (relative to current patient being called)
            if patient_index and current_patient_index:
                patients_ahead = max(patient_index - current_patient_index, 0)
            elif patient_index:
                patients_ahead = patient_index - 1
            else:
                patients_ahead = 0

            if doctor:
                # Get average consultation time for this doctor
                avg_consultation = get_average_consultation_time(doctor.id)
                avg_seconds = avg_consultation['average_seconds'] if avg_consultation else 0
                avg_formatted = format_seconds_to_time_string(avg_seconds)
                daily_avg_formatted = avg_consultation['daily_average_formatted'] if avg_consultation and 'daily_average_formatted' in avg_consultation else '—'
                
                # Calculate expected wait time: (patients ahead) * (average consultation time)
                current_time = datetime.now()
                patients_ahead_count = patients_ahead if patients_ahead else 0
                expected_wait_seconds = (patients_ahead_count * avg_seconds) if avg_seconds > 0 else 0
                expected_wait_time = current_time + timedelta(seconds=expected_wait_seconds)
                expected_wait_formatted = format_seconds_to_time_string(expected_wait_seconds)
                
                doctor_visits[doctor.id] = {
                    "doctor_name": doctor.name,
                    "section_name": section.name_section if section else "غير محدد",
                    "your_number": patient_index,
                    "original_queue_position": original_queue_position,  # Original (never changes)
                    "patients_ahead": patients_ahead,  # How many ahead currently
                    "current_number": current_patient_index,
                    "visit_date": visit.visit_date,
                    "clinic_id": doctor.clinic_id,
                    "visit_status": visit.visit_status,  # Add visit status: مؤكد, منتهي, ملغي
                    "average_consultation_seconds": avg_seconds,
                    "average_consultation_minutes": round(avg_seconds / 60, 2) if avg_seconds else 0,
                    "average_consultation_formatted": avg_formatted,
                    "daily_average_formatted": daily_avg_formatted,
                    "expected_wait_seconds": expected_wait_seconds,
                    "expected_wait_minutes": round(expected_wait_seconds / 60, 2) if expected_wait_seconds else 0,
                    "expected_wait_formatted": expected_wait_formatted,
                    "expected_wait_time": expected_wait_time,  # Exact datetime when patient will be seen
                    "consultation_count": doctor.consultation_count
                }

        # Prepare results in the format you want
        if doctor_visits:
            # Collect all unique clinic IDs from doctors
            clinic_ids = set()
            for doc_data in doctor_visits.values():
                if 'clinic_id' in doc_data:
                    clinic_ids.add(doc_data['clinic_id'])
            
            # Get the first clinic_id for the main data attribute (fallback)
            primary_clinic_id = list(clinic_ids)[0] if clinic_ids else 1
            
            print(f"✅ Found {len(clinic_ids)} unique clinics: {clinic_ids}")
            print(f"📊 Patient search results: patient_name={visits[0].patient_name}, clinics={clinic_ids}")
            
            results = {
                "patient_name": visits[0].patient_name,
                "patient_phone": visits[0].patient_phone,
                "visit_date": visit_date,
                "clinic_id": primary_clinic_id,
                "all_clinic_ids": list(clinic_ids),
                "doctors": doctor_visits
            }
    else:
        status_message = "No visits found for the patient."

    return render_template('home.html', 
                         status_message=status_message, 
                         results=results, 
                         patient_found=patient_found)


    return jsonify(results if results else {"message": "No visits found"})
