
from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit

)
from flask_socketio import SocketIO
from flask_sse import sse

from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta

doctorBP = Blueprint('doctorBP',__name__)

# Doctor login route
@doctorBP.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch doctor by username
        doctor = Doctor.query.filter_by(username=username).first()

        if doctor and doctor.password == password:
            session['doctor_id'] = doctor.id
            return redirect(url_for('doctor_home'))
        else:
            return "Invalid credentials. Please try again."

    return render_template('clinic_login.html')
    
@doctorBP.route('/cancel_visit', methods=['POST'])
def cancel_visit():
    if request.method == 'POST':
        visit_id = request.form.get('visit_id')
        visit = Visit.query.get(visit_id)
        
        if visit:
            try:
                # Update status instead of deleting
                visit.visit_status = 'ملغي'
                db.session.commit()
                flash("تم إلغاء الزيارة بنجاح", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"حدث خطأ: {str(e)}", "error")
        else:
            flash("الزيارة غير موجودة", "error")
    
    return redirect(url_for('receptionBP.reception_home'))  # Redirect back to visits page


@doctorBP.route('/cancel_patient', methods=['POST'])
def cancel_patient():
    if request.method == 'POST':
        visit_id = request.form.get('visit_id')  # Changed from patient_id to visit_id
        visit_to_cancel = Visit.query.get(visit_id)
        
        if not visit_to_cancel:
            flash("الزيارة غير موجودة", "error")
        else:
            visit_to_cancel.visit_status = "ملغي"  # Update status only
            db.session.commit()  # Save changes
            flash("تم إلغاء الزيارة بنجاح", "success")
    
    return redirect(url_for('doctorBP.doctor_home'))  # Redirect back
@doctorBP.route('/doctor/home', methods=['GET', 'POST'])
def doctor_home():
    doctor_id = session.get('doctor_id')
    doctor = Doctor.query.get(doctor_id)
    
    if not doctor:
        flash("Doctor not found", "error")
        return redirect(url_for('doctorBP.doctor_login'))

    clinic_id = doctor.clinic_id
    clinic = Clinics.query.filter_by(clinic_id=clinic_id).first()
    
    if not clinic:
        flash("Clinic not found", "error")
        return redirect(url_for('doctorBP.doctor_login'))

    clinic_name = clinic.name_clinic
    patients = Patient.query.filter_by(doctor_id=doctor_id).all()
    
    # Get today's visitors for this doctor
    visitors = Visit.query.filter(
        Visit.doctor_id == doctor_id, 
        func.date(Visit.visit_date) == datetime.today().date(),
        Visit.visit_status == "مؤكد"
    ).all()

    # Get available procedures for this doctor's section
    procedures = Process.query.filter_by(section_id=doctor.section_id).all()

    # استخدام الجلسة لتخزين visit_id الحالي
    current_visit_id = session.get('current_visit_id')
    current_patient_obj = None
    current_patient_index = None
    
    # البحث عن الزيارة الحالية
    if current_visit_id:
        current_visit = next((visit for visit in visitors if visit.id == current_visit_id), None)
        if current_visit:
            current_patient_obj = Patient.query.get(current_visit.patient_id)
            current_patient_index = visitors.index(current_visit) if current_visit in visitors else None
        else:
            # إذا لم توجد الزيارة، نمسحها من الجلسة
            session.pop('current_visit_id', None)
            current_visit_id = None
    
    # إذا لم يكن هناك visit_id محدد، نأخذ أول زيارة
    if not current_visit_id and visitors:
        current_visit_id = visitors[0].patient_id
        session['current_visit_id'] = current_visit_id
        current_patient_obj = Patient.query.get(visitors[0].patient_id)
        current_patient_index = 0

    if request.method == 'POST':
        if 'next' in request.form and visitors:
            if not current_visit_id:
                # إذا لم يكن هناك زيارة حالية، نأخذ الأولى
                session['current_visit_id'] = visitors[0].id
                doctor.current_patient=visitors[0].patient_id
                db.session.commit()
#                sse.publish({"number": doctor.current_patient, "doctor_id": doctor.id}, type="number")

            else:
                # البحث عن الزيارة الحالية في القائمة
                current_index = next((i for i, visit in enumerate(visitors) 
                                   if visit.id == current_visit_id), None)
                if current_index is not None and current_index + 1 < len(visitors):
                    # التالي في القائمة
                    session['current_visit_id'] = visitors[current_index + 1].id
                    doctor.current_patient=visitors[current_index + 1].patient_id
                elif current_index is None and visitors:
                    # إذا لم توجد في القائمة، نأخذ الأولى
                    session['current_visit_id'] = visitors[0].patient_id
                db.session.commit()
#                sse.publish({"number": doctor.current_patient, "doctor_id": doctor.id}, type="number")

            return redirect(url_for('doctorBP.doctor_home'))
            
        elif 'back' in request.form and visitors:
            if current_visit_id:
                # البحث عن الزيارة الحالية في القائمة
                current_index = next((i for i, visit in enumerate(visitors) 
                                   if visit.id == current_visit_id), None)
                if current_index is not None and current_index > 0:
                    # السابق في القائمة
                    session['current_visit_id'] = visitors[current_index - 1].id
                    doctor.current_patient=visitors[current_index - 1].patient_id
                    db.session.commit()
 #                   sse.publish({"number": doctor.current_patient, "doctor_id": doctor.id}, type="number")

                elif current_index is None and visitors:
                    # إذا لم توجد في القائمة، نأخذ الأولى
                    session['current_visit_id'] = visitors[0].patient_id
                    doctor.current_patient=visitors[0].patient_id
                    db.session.commit()
  #                  sse.publish({"number": doctor.current_patient, "doctor_id": doctor.id}, type="number")

            return redirect(url_for('doctorBP.doctor_home'))
            
        elif 'visit_id' in request.form:  # عند اختيار مريض من القائمة
            new_visit_id = request.form.get('visit_id')
            patient = Visit.query.get(new_visit_id)
          
            if new_visit_id:
                session['current_visit_id'] = int(new_visit_id)
                doctor.current_patient= patient.patient_id
                db.session.commit()
            return redirect(url_for('doctorBP.doctor_home'))

    # تحديث القيم بعد معالجة POST
    current_visit_id = session.get('current_visit_id')
    if current_visit_id:
        current_visit = next((visit for visit in visitors if visit.id == current_visit_id), None)
        if current_visit:
            current_patient_obj = Patient.query.get(current_visit.patient_id)
            current_patient_index = visitors.index(current_visit) if current_visit in visitors else None

    return render_template('doctor_home.html', 
                         doctor=doctor, 
                         clinic_name=clinic_name,
                         patients=patients,
                         current_patient=current_patient_obj,
                         current_patient_number=current_patient_index + 1 if current_patient_index is not None else None,
                         visitors=visitors,
                         clinic=clinic,
                         procedures=procedures,
                         current_visit_id=current_visit_id)  # إرسال visit_id إلى القالب
