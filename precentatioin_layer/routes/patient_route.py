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


def normalize_arabic(text):
    """Normalize Arabic text for consistent searching."""
    if not text:
        return ''
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ى]', 'ي', text)
    text = re.sub(r'[ئ]', 'ي', text)
    text = re.sub(r'[ؤ]', 'و', text)
    text = re.sub(r'[ة]', 'ه', text)
    text = re.sub(r'[\u064B-\u0652]', '', text)  # Remove diacritics
    return text


def _build_visit_results(visits, visit_date):
    """
    Shared helper: given a list of Visit objects and a date,
    build the 'results' dict used by home.html to display patient queue info.
    Returns (results, status_message).
    """
    results = []
    status_message = None

    if visits:
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

            # Determine current position
            try:
                patient_index = next((i + 1 for i, v in enumerate(current_patients) if v.patient_id == visit.patient_id), None)
            except ValueError:
                patient_index = None

            try:
                current_patient_index = next((i + 1 for i, v in enumerate(current_patients) if v.patient_id == doctor.current_patient), None) if doctor and doctor.current_patient else None
            except ValueError:
                current_patient_index = None

            original_queue_position = visit.queue_position

            if patient_index and current_patient_index:
                patients_ahead = max(patient_index - current_patient_index, 0)
            elif patient_index:
                patients_ahead = patient_index - 1
            else:
                patients_ahead = 0

            if doctor:
                avg_consultation = get_average_consultation_time(doctor.id)
                avg_seconds = avg_consultation['average_seconds'] if avg_consultation else 0
                avg_formatted = format_seconds_to_time_string(avg_seconds)
                daily_avg_formatted = avg_consultation['daily_average_formatted'] if avg_consultation and 'daily_average_formatted' in avg_consultation else '—'

                current_time = datetime.now()
                patients_ahead_count = patients_ahead if patients_ahead else 0
                expected_wait_seconds = (patients_ahead_count * avg_seconds) if avg_seconds > 0 else 0
                expected_wait_time = current_time + timedelta(seconds=expected_wait_seconds)
                expected_wait_formatted = format_seconds_to_time_string(expected_wait_seconds)

                doctor_visits[doctor.id] = {
                    "doctor_name": doctor.name,
                    "section_name": section.name_section if section else "غير محدد",
                    "your_number": patient_index,
                    "original_queue_position": original_queue_position,
                    "patients_ahead": patients_ahead,
                    "current_number": current_patient_index,
                    "visit_date": visit.visit_date,
                    "clinic_id": doctor.clinic_id,
                    "visit_status": visit.visit_status,
                    "average_consultation_seconds": avg_seconds,
                    "average_consultation_minutes": round(avg_seconds / 60, 2) if avg_seconds else 0,
                    "average_consultation_formatted": avg_formatted,
                    "daily_average_formatted": daily_avg_formatted,
                    "expected_wait_seconds": expected_wait_seconds,
                    "expected_wait_minutes": round(expected_wait_seconds / 60, 2) if expected_wait_seconds else 0,
                    "expected_wait_formatted": expected_wait_formatted,
                    "expected_wait_time": expected_wait_time,
                    "consultation_count": doctor.consultation_count
                }

        if doctor_visits:
            clinic_ids = set()
            for doc_data in doctor_visits.values():
                if 'clinic_id' in doc_data:
                    clinic_ids.add(doc_data['clinic_id'])

            primary_clinic_id = list(clinic_ids)[0] if clinic_ids else 1

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

    return results, status_message


@patientBP.route('/doctor/select_patient', methods=['POST'])
def select_patient():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return redirect(url_for('doctor_login'))
    
    visit_id = request.form.get('visit_id')
    if visit_id:
        visit = Visit.query.get(visit_id)
        if visit and visit.doctor_id == doctor_id:
            session['current_visit_id'] = visit.id
    
    return redirect(url_for('doctor_home'))


# Routes for Patients — Manual search
@patientBP.route('/patient', methods=['GET', 'POST'])
def patient():
    status_message = None
    results = []
    visit_date = date.today()
    patient_found = None

    request.method == 'POST'
    name = request.form['name']
    normalized_input = normalize_arabic(name)
    phone = request.form['phone']
    id = request.form['phone']

    query = Visit.query.filter(or_(Visit.normalized_name == normalized_input , Visit.patient_name==name))
    if phone or id : 
        query = query.filter(or_(Visit.patient_phone == phone , Visit.patient_id == id ))
      
    patient_found = query.first()

    if patient_found:
        visits = Visit.query.filter(
            Visit.patient_id == patient_found.patient_id,
            Visit.normalized_name.ilike(f"%{normalized_input}%"),
            func.date(Visit.visit_date) == visit_date
        ).order_by(Visit.visit_date.desc()).all()
    else:
        visits = Visit.query.filter(
            Visit.normalized_name.ilike(f"%{normalized_input}%"),
            Visit.patient_phone == phone,
            func.date(Visit.visit_date) == visit_date
        ).all()

    results, status_message = _build_visit_results(visits, visit_date)

    return render_template('home.html', 
                         status_message=status_message, 
                         results=results, 
                         patient_found=patient_found)


# Auto-lookup route — Patient clicks link from WhatsApp
@patientBP.route('/patient/auto/<token>', methods=['GET'])
def patient_auto_lookup(token):
    """
    Auto-lookup a patient's appointments using a unique token from WhatsApp.
    No name, phone, or ID required — the token identifies the visit/patient.
    """
    visit_date = date.today()
    
    # Find the visit by its unique lookup token
    token_visit = Visit.query.filter_by(lookup_token=token).first()
    
    if not token_visit:
        return render_template('home.html',
                             status_message="رابط غير صالح أو منتهي الصلاحية",
                             results=[],
                             patient_found=None,
                             auto_lookup=True)
    
    # Get all of today's visits for this patient
    visits = Visit.query.filter(
        Visit.patient_id == token_visit.patient_id,
        func.date(Visit.visit_date) == visit_date,
        Visit.visit_status == "مؤكد"
    ).order_by(Visit.visit_date.desc()).all()
    
    # If no visits today, also show the original visit (might be for another day)
    if not visits:
        visits = [token_visit]
    
    results, status_message = _build_visit_results(visits, visit_date)
    
    return render_template('home.html',
                         status_message=status_message,
                         results=results,
                         patient_found=token_visit,
                         auto_lookup=True)

