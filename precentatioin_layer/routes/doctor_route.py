
from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.functions.doctor_func import broadcast_patient_event, broadcast_patient_order_changed
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit

)
from flask_socketio import SocketIO
from flask_sse import sse
import redis
import json

from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta

doctorBP = Blueprint('doctorBP',__name__)

# SSE Stream endpoint for real-time doctor updates
@doctorBP.route('/stream/doctor_<int:doctor_id>', methods=['GET'])
def doctor_stream(doctor_id):
    """
    SSE endpoint that streams real-time updates for a specific doctor
    Subscribes to Redis channel: doctor_{doctor_id}
    URL: /stream/doctor_<doctor_id>
    """
    # Verify doctor session
    session_doctor_id = session.get('doctor_id')
    print(f"🔍 Doctor stream request: doctor_id={doctor_id}, session_doctor_id={session_doctor_id}")
    
    if session_doctor_id != doctor_id:
        print(f"❌ Unauthorized access to doctor stream: session_doctor_id={session_doctor_id} != doctor_id={doctor_id}")
        print(f"   Session data: {dict(session)}")
        return jsonify({'error': 'Unauthorized'}), 401
    
    print(f"✅ Doctor stream authorized for doctor_id={doctor_id}")
    
    def generate():
        """Generator that yields SSE formatted events from Redis"""
        try:
            # Connect to Redis
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            pubsub = redis_client.pubsub()
            
            # Subscribe to doctor-specific channel
            channel_name = f'doctor_{doctor_id}'
            pubsub.subscribe(channel_name)
            
            # Initial connection message
            yield f'data: {{"type": "connected", "doctor_id": {doctor_id}}}\n\n'
            
            # Stream events from Redis
            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Publish the event data as SSE
                    event_data = message['data']
                    yield f'data: {event_data}\n\n'
        except Exception as e:
            print(f"❌ Error in doctor stream: {e}")
            yield f'data: {{"type": "error", "message": "Connection error"}}\n\n'
    
    return generate(), {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}

# SSE Stream endpoint for clinic-level updates (for reception staff)
@doctorBP.route('/stream/clinic_<int:clinic_id>', methods=['GET'])
def clinic_stream(clinic_id):
    """
    SSE endpoint that streams real-time updates for all staff in a clinic
    Subscribes to Redis channel: clinic_{clinic_id}
    URL: /stream/clinic_<clinic_id>
    Used by: Reception staff, doctors, clinic admins, and PUBLIC patient pages
    
    Note: This endpoint allows unauthenticated access for patient pages
    but anyone can listen to clinic events (which are public information)
    """
    # Optionally verify clinic session if user is authenticated
    # If not authenticated, allow access anyway (for public patient pages)
    session_clinic_id = session.get('clinic_id')
    session_doctor_id = session.get('doctor_id')
    session_reception_id = session.get('reception_id')
    
    # Allow if:
    # 1. Clinic ID matches authenticated session (doctor/reception), OR
    # 2. User has a doctor_id session with matching clinic, OR
    # 3. No session - allow public access for patient pages
    
    is_authenticated = session_clinic_id == clinic_id or session_doctor_id or session_reception_id
    
    # For now, we'll allow unauthenticated access since clinic information is public
    # and patients need to see their queue status
    print(f"✅ SSE clinic_stream accessed for clinic_id={clinic_id}")
    print(f"   Session clinic_id: {session_clinic_id}, doctor_id: {session_doctor_id}, reception_id: {session_reception_id}")
    
    def generate():
        """Generator that yields SSE formatted events from Redis"""
        try:
            # Connect to Redis
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            pubsub = redis_client.pubsub()
            
            # Subscribe to clinic-specific channel
            channel_name = f'clinic_{clinic_id}'
            pubsub.subscribe(channel_name)
            
            # Initial connection message
            yield f'data: {{"type": "connected", "clinic_id": {clinic_id}}}\n\n'
            
            # Stream events from Redis
            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Publish the event data as SSE
                    event_data = message['data']
                    yield f'data: {event_data}\n\n'
        except Exception as e:
            print(f"❌ Error in clinic stream: {e}")
            yield f'data: {{"type": "error", "message": "Connection error"}}\n\n'
    
    return generate(), {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}

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
                # Store info before updating
                doctor_id = visit.doctor_id
                patient_name = visit.patient_name
                patient_phone = visit.patient_phone
                patient_id = visit.patient_id
                
                # Update status instead of deleting
                visit.visit_status = 'ملغي'
                db.session.commit()
                
                # Broadcast cancel event to reception and other doctors
                if doctor_id:
                    broadcast_patient_event(
                        doctor_id=doctor_id,
                        event_type='cancel_visit',
                        visit_id=visit_id,
                        patient_id=patient_id,
                        patient_name=patient_name,
                        patient_phone=patient_phone
                    )
                
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
            # Store info before updating
            doctor_id = visit_to_cancel.doctor_id
            patient_name = visit_to_cancel.patient_name
            patient_phone = visit_to_cancel.patient_phone
            patient_id = visit_to_cancel.patient_id
            
            visit_to_cancel.visit_status = "ملغي"  # Update status only
            db.session.commit()  # Save changes
            
            # Broadcast cancel event
            if doctor_id:
                broadcast_patient_event(
                    doctor_id=doctor_id,
                    event_type='cancel_visit',
                    visit_id=visit_id,
                    patient_id=patient_id,
                    patient_name=patient_name,
                    patient_phone=patient_phone
                )
            
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
    
    # Get today's visitors for this doctor - ordered by visit time (earliest first)
    visitors = Visit.query.filter(
        Visit.doctor_id == doctor_id, 
        func.date(Visit.visit_date) == datetime.today().date(),
        Visit.visit_status == "مؤكد"
    ).order_by(Visit.visit_date.asc()).all()

    # Get available procedures for this doctor's section
    procedures = Process.query.filter_by(section_id=doctor.section_id).all()

    # استخدام الجلسة لتخزين visit_id الحالي
    current_visit_id = session.get('current_visit_id')
    current_patient_obj = None
    current_patient_index = None
    current_visit = None
    
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
                # Broadcast patient order change event
                from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                broadcast_patient_order_changed(doctor.id, clinic_id, visitors[0].patient_id, 1)

            else:
                # البحث عن الزيارة الحالية في القائمة
                current_index = next((i for i, visit in enumerate(visitors) 
                                   if visit.id == current_visit_id), None)
                if current_index is not None and current_index + 1 < len(visitors):
                    # التالي في القائمة
                    session['current_visit_id'] = visitors[current_index + 1].id
                    doctor.current_patient=visitors[current_index + 1].patient_id
                    db.session.commit()
                    # Broadcast patient order change event
                    from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                    broadcast_patient_order_changed(doctor.id, clinic_id, visitors[current_index + 1].patient_id, current_index + 2)
                elif current_index is None and visitors:
                    # إذا لم توجد في القائمة، نأخذ الأولى
                    session['current_visit_id'] = visitors[0].patient_id
                    doctor.current_patient=visitors[0].patient_id
                    db.session.commit()
                    # Broadcast patient order change event
                    from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                    broadcast_patient_order_changed(doctor.id, clinic_id, visitors[0].patient_id, 1)

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
                    # Broadcast patient order change event
                    from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                    broadcast_patient_order_changed(doctor.id, clinic_id, visitors[current_index - 1].patient_id, current_index)

                elif current_index is None and visitors:
                    # إذا لم توجد في القائمة، نأخذ الأولى
                    session['current_visit_id'] = visitors[0].patient_id
                    doctor.current_patient=visitors[0].patient_id
                    db.session.commit()
                    # Broadcast patient order change event
                    from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                    broadcast_patient_order_changed(doctor.id, clinic_id, visitors[0].patient_id, 1)

            return redirect(url_for('doctorBP.doctor_home'))
            
        elif 'visit_id' in request.form:  # عند اختيار مريض من القائمة
            new_visit_id = request.form.get('visit_id')
            patient = Visit.query.get(new_visit_id)
          
            if new_visit_id and patient:
                session['current_visit_id'] = int(new_visit_id)
                doctor.current_patient= patient.patient_id
                db.session.commit()
                # Find the index of the selected patient in the ordered visitors list
                selected_index = next((i for i, visit in enumerate(visitors) 
                                     if visit.id == int(new_visit_id)), None)
                if selected_index is not None:
                    # Broadcast patient order change event
                    from busnisess_layer.functions.doctor_func import broadcast_patient_order_changed
                    broadcast_patient_order_changed(doctor.id, clinic_id, patient.patient_id, selected_index + 1)
            return redirect(url_for('doctorBP.doctor_home'))

    # تحديث القيم بعد معالجة POST
    current_visit_id = session.get('current_visit_id')
    current_visit = None
    if current_visit_id:
        current_visit = next((visit for visit in visitors if visit.id == current_visit_id), None)
        if current_visit:
            current_patient_obj = Patient.query.get(current_visit.patient_id)
            current_patient_index = visitors.index(current_visit) if current_visit in visitors else None

    # Build visitors data with queue information
    visitors_with_queue = []
    for idx, visit in enumerate(visitors):
        visitors_with_queue.append({
            'visit': visit,
            'original_queue_position': visit.queue_position,  # Original position (never changes)
            'current_position': idx + 1,  # Current position in confirmed list
            'patients_ahead': idx  # How many patients are ahead
        })

    return render_template('doctor_home.html', 
                         doctor=doctor, 
                         clinic_name=clinic_name,
                         patients=patients,
                         current_patient=current_patient_obj,
                         current_patient_number=current_patient_index + 1 if current_patient_index is not None else None,
                         current_visit=current_visit if current_visit_id else None,
                         visitors=visitors,
                         visitors_with_queue=visitors_with_queue,
                         clinic=clinic,
                         procedures=procedures,
                         current_visit_id=current_visit_id)  # إرسال visit_id إلى القالب


@doctorBP.route('/doctor/visitors_poll', methods=['GET'])
def visitors_poll():
    """Polling endpoint: returns today's confirmed visitors for the doctor as JSON."""
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return jsonify({'error': 'Unauthorized'}), 401

    visitors = Visit.query.filter(
        Visit.doctor_id == doctor_id,
        func.date(Visit.visit_date) == datetime.today().date(),
        Visit.visit_status == "مؤكد"
    ).order_by(Visit.visit_date.asc()).all()

    data = [
        {
            'id': v.id,
            'patient_name': v.patient_name or '',
            'patient_phone': v.patient_phone or '',
            'status': v.status or '',
            'visit_status': v.visit_status or '',
        }
        for v in visitors
    ]
    return jsonify(data)
