from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.functions.doctor_func import broadcast_patient_event
from busnisess_layer.functions.whatsapp_service import send_appointment_whatsapp, build_auto_lookup_url
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit
)
from flask_sse import sse
import uuid

from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta

receptionBP = Blueprint('receptionBP',__name__)

@receptionBP.route('/reception/home', methods=['GET', 'POST'])
def reception_home():
    reception_id = session.get('reception_id')
    if not reception_id:
        flash("Please log in first", "error")
        return redirect(url_for('clinic_login'))

    # ✅ Get clinic_id from Reception
    clinic_id = db.session.query(Reception.clinic_id)\
           .filter(Reception.id == reception_id)\
           .scalar()
    if not clinic_id:
        flash("Reception account not found", "error")
        return redirect(url_for('clinic_login'))
     
    sections = Section.query.filter_by(clinic_id=clinic_id).all()
    
    clinic_patients = Patient.query \
        .filter_by(clinic_id=clinic_id)\
        .options(
            joinedload(Patient.doctor).joinedload(Doctor.section)
        ).all()
    today = date.today()
    clinic_visitors = Visit.query.filter(Visit.clinic_id == clinic_id, func.date(Visit.visit_date) == today).all()
    #doctors=Doctor.query.filter_by(section_id).all()
 

    def normalize_arabic(text):
        if not text:
            return ''
        text = re.sub(r'[إأآا]', 'ا', text)
        text = re.sub(r'[ى]', 'ي', text)
        text = re.sub(r'[ئ]', 'ي', text)
        text = re.sub(r'[ؤ]', 'و', text)
        text = re.sub(r'[ة]', 'ه', text)
        text = re.sub(r'[\u064B-\u0652]', '', text)  # Remove harakat (diacritics)
        return text
   
    today = date.today()  # Returns datetime.date(2023, 12, 25)

    

    visitors = Visit.query.filter(Visit.clinic_id == clinic_id, func.date(Visit.visit_date) == today).all()
   
   
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_patient':
            # Add new patient logic
           
            name = request.form['name']
            normalized_name = normalize_arabic(name)
            phone = request.form['phone']
            age = request.form['berth_date']
            berth_date =   date.today().year  - int(age)
         #  berth_convert = datetime.strptime(berth_date, "%d-%m-%Y").date()  # Note: '%Y-%m-%d' and added parentheses for .date()
         #  formatted_date = berth_convert.strftime("%Y-%m-%d")
         # age = date.today().year - berth_convert.year - ((date.today().month, date.today().day) < (berth_convert.month, berth_convert.day))
           
            gender=request.form['gender']
            status=request.form['status']
            national_id = request.form['national_id']
            section_id = request.form['section']
            doctor_id = request.form['doctor']
            date_visit=request.form['date_visit']
            # process_id = request.form['process']
            # if not process_id :
            #     process_id=None
            if not date_visit :
                date_visit=date.today()
           


           # len(national_id) != 14 or
            if  len(phone) != 11:
                flash("Invalid National ID or Phone number.", "error")
            else:
                existing_patient = Patient.query.filter_by(
                   normalized_name=normalized_name,  phone=phone, clinic_id=clinic_id
                ).first()
                if existing_patient:
                    flash("Patient already exists in this clinic.", "error")
                    return redirect(url_for('receptionBP.reception_home'))
                
                # Parse date_visit to get date and time
                if isinstance(date_visit, str):
                    try:
                        visit_datetime = datetime.fromisoformat(date_visit.replace('T', ' '))
                        visit_date_obj = visit_datetime.date()
                        visit_time = visit_datetime.time()
                    except:
                        visit_date_obj = date.today()
                        visit_time = datetime.now().time()
                else:
                    visit_date_obj = date_visit if isinstance(date_visit, date) else date.today()
                    visit_time = datetime.now().time()
                
                # Check if another patient already has an appointment with this doctor at the same time
                time_conflict = Visit.query.filter(
                    Visit.doctor_id == doctor_id,
                    Visit.clinic_id == clinic_id,
                    func.date(Visit.visit_date) == visit_date_obj,
                    func.hour(Visit.visit_date) == visit_time.hour,
                    func.minute(Visit.visit_date) == visit_time.minute,
                    Visit.visit_status == "مؤكد"
                ).first()
                
                if time_conflict:
                    flash(f"Doctor already has a patient scheduled at {visit_time.strftime('%I:%M %p')} on this date.", "error")
                    return redirect(url_for('receptionBP.reception_home'))

                else:
                    new_patient = Patient(
                        name=name,  normalized_name=normalized_name, phone=phone, national_id=national_id or None,berth_date = berth_date,
                        gender=gender,status = status , age=age ,date_visit=date_visit,section=section_id, doctor_id=doctor_id, clinic_id=clinic_id ,#process_id=process_id
                    )
                    db.session.add(new_patient)
                    db.session.commit()
                             
                    new_visit = Visit(
                            patient_id=new_patient.id,
                            patient_name=name,
                            normalized_name=normalized_name,
                            national_id=national_id,
                            section_id=section_id,
                            age=age,
                            berth_date = berth_date,
                            gender=gender,
                            status= status ,
                            doctor_id=doctor_id,
                            clinic_id=clinic_id,
                            visit_status="مؤكد",
                            patient_phone= phone,
                            #process_id=process_id,
                           # visit_date= date.today(),
                            visit_date=date_visit ,
                            percentage=0
                             
                        )
                    db.session.add(new_visit)
                    db.session.commit()
                    
                    # Generate lookup token for WhatsApp auto-lookup
                    lookup_token = uuid.uuid4().hex
                    new_visit.lookup_token = lookup_token
                    db.session.commit()
                    
                    # Broadcast SSE event to the doctor's stream (new patient)
                    broadcast_patient_event(
                        doctor_id=doctor_id,
                        event_type='new_patient',
                        visit_id=new_visit.id,
                        patient_id=new_patient.id,
                        patient_name=name,
                        patient_phone=phone
                    )
                    
                    # Send WhatsApp notification to the patient
                    try:
                        doctor_obj = Doctor.query.get(doctor_id)
                        clinic_obj = Clinics.query.filter_by(clinic_id=clinic_id).first()
                        auto_url = build_auto_lookup_url(lookup_token)
                        
                        # Format date and time for the message
                        if isinstance(date_visit, str):
                            try:
                                vdt = datetime.fromisoformat(date_visit.replace('T', ' '))
                                wa_date = vdt.strftime('%Y-%m-%d')
                                wa_time = vdt.strftime('%I:%M %p')
                            except:
                                wa_date = str(date.today())
                                wa_time = datetime.now().strftime('%I:%M %p')
                        else:
                            wa_date = str(date.today())
                            wa_time = datetime.now().strftime('%I:%M %p')
                        
                        send_appointment_whatsapp(
                            patient_phone=phone,
                            clinic_name=clinic_obj.name_clinic if clinic_obj else 'العيادة',
                            doctor_name=doctor_obj.name if doctor_obj else 'الطبيب',
                            appointment_date=wa_date,
                            appointment_time=wa_time,
                            auto_lookup_url=auto_url
                        )
                    except Exception as wa_err:
                        print(f"⚠️ WhatsApp notification failed: {wa_err}")
                    
                    flash("Patient successfully added.", "success")
                    return redirect(url_for('receptionBP.reception_home'))

        elif action == 'edit_patient':
            # Edit existing patient logic
            patient_id = request.form['patient_id']
            section_id = request.form['section']
            doctor_id = request.form['doctor']
            patient = Patient.query.get(patient_id)
            if patient:
                old_doctor_id = patient.doctor_id
                patient.section = section_id
                patient.doctor_id = doctor_id
                db.session.commit()
                
                # Broadcast edit event to both old and new doctor
                if old_doctor_id:
                    broadcast_patient_event(
                        doctor_id=old_doctor_id,
                        event_type='edit_patient',
                        visit_id=None,
                        patient_id=patient_id,
                        patient_name=patient.name,
                        patient_phone=patient.phone
                    )
                
                broadcast_patient_event(
                    doctor_id=doctor_id,
                    event_type='edit_patient',
                    visit_id=None,
                    patient_id=patient_id,
                    patient_name=patient.name,
                    patient_phone=patient.phone
                )
                
                flash("Patient updated successfully.", "success")
            else:
                flash("Patient not found.", "error")

        elif action == 'cancel_patient':
            # cancel patient logic
            patient_id = request.form.get('patient_id')
            patient_to_delete = Visit.query.get(patient_id)
            if patient_to_delete:
                doctor_id = patient_to_delete.doctor_id
                patient_name = patient_to_delete.patient_name
                patient_phone = patient_to_delete.patient_phone
                
                Visit.query.filter_by(patient_id=patient_id).update({"visit_status":"cancelled"})
                db.session.delete(patient_to_delete)
                db.session.commit()
                
                # Broadcast cancel event to the doctor
                if doctor_id:
                    broadcast_patient_event(
                        doctor_id=doctor_id,
                        event_type='cancel_visit',
                        visit_id=patient_id,
                        patient_id=patient_id,
                        patient_name=patient_name,
                        patient_phone=patient_phone
                    )
                
                flash("Patient deleted successfully.", "success")
            else:
                flash("Patient not found.", "error")

        elif action == 'add_new_visit':
            try:
                patient_id = request.form['patient_id']
                doctor_id = request.form['doctor_id']
                date_visit=request.form['date_visit']
          #      patient_phone = request.form['']
                existing_patient = Visit.query.filter(
                    Visit.patient_id==patient_id, 
                     Visit.clinic_id==clinic_id, Visit.doctor_id==doctor_id,
                    
                     func.date(Visit.visit_date) == date_visit,
                    Visit.visit_status=="مؤكد"
                ).first()
                if existing_patient:
                    flash("Patient already has a visit scheduled for this date and doctor.", "error")
                    return redirect(url_for('receptionBP.reception_home'))
                else:
                    new_visit = Visit(
                        patient_id=patient_id, doctor_id=doctor_id,
                        clinic_id=clinic_id, date_visit=date_visit,visit_status="مؤكد",patinet_phone=phone , percentage=0
                    )
                db.session.add(new_visit)
                db.session.commit()
                flash("New visit added.", "success")
                return redirect(url_for('receptionBP.reception_home'))
            except KeyError as e:
                flash(f"Missing form data: {e.args[0]}", "error")
                return redirect(url_for('receptionBP.reception_home'))
            

        # elif action == 'bills_visit':
        #     bills_patient = []
        #     patient_name = request.form['patient_name']
        #     patient_id= Patient.query.filter_by(name=patient_name,clinic_id=clinic_id).first().id
        #     visits= [visit.id  for visit in Visit.query.filter_by(patient_id=patient_id,clinic_id=clinic_id).all()]
        #     visits_patient = Visit.query.filter_by(patient_id=patient_id,clinic_id=clinic_id).all()
        #     percentage_visit = Visit.query.filter_by(patient_id=patient_id,clinic_id=clinic_id).first()
        #     for visits in visits_patient:
        #         bills_patient.append(
        #             {
        #                 "visit_name": visits.patient_name,
        #                 "visit_date": visits.visit_date,
        #                 "visit_status": visits.visit_status,
        #                 "name_porcess": visits.process.name_process,
        #                 "process_cost": visits.process.fee_process ,
        #                 "percentage":visits.precentage,
        #                 "final_cost " : int( visits.process.fee_process -((visits.precentage/100) * (visits.process.fee_process)) ) ,
        #                 "amount":amount_value ,
        #                 "amount_reveied":int( (visits.process.fee_process -((visits.precentage/100) * (visits.process.fee_process))) - amount_value)
                    
        #             }
        #         )



    clinic = Clinics.query.filter_by(clinic_id=clinic_id).first()
    clinic_name = clinic.name_clinic
        

    return render_template(
        'reception_home.html',
        clinic_name=clinic_name,
        clinic_patients=clinic_patients,
        all_patients=clinic_patients if request.args.get('show_all') else None,
        sections=sections,
        clinic_visitors=clinic_visitors,
        visitors=visitors,
        clinic_id=clinic_id
    )


@receptionBP.route('/reception/search', methods=['GET'])
def search_patient():
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
    reception = Reception.query.get(session['reception_id'])
    clinic_id = reception.clinic_id
   # clinic_id = session.get('clinic_id')
    name = request.args.get('name')
    normalized_input = normalize_arabic(name)
    phone=request.args.get('phone')
     
    patient = None
    ID = request.args.get('phone')

    
    
    query = Patient.query.filter(Patient.normalized_name == normalized_input)

    if phone or ID :
        query = query.filter(or_(Patient.phone == phone , Patient.id == ID ))
 

    patient_found = query.first()

    
    #clinic_id = patient_found.clinic_id
    sections = Section.query.filter_by(clinic_id=clinic_id).all()
    return render_template('reception_home.html', patient=patient_found ,sections=sections)


 
@receptionBP.route('/reception/add_visit', methods=['POST'])
def add_visit():
    """
    Add a new visit record for a patient with a specific doctor.
    This function handles the creation of a new visit appointment by a reception staff member.
    It performs multiple validations and checks before creating the visit record.
    Process:
    1. Validates reception staff login status and retrieves associated clinic_id
    2. Retrieves patient and appointment details from the request form
    3. Normalizes Arabic patient name for consistent searching
    4. Parses visit date and time from datetime-local input format
    5. Checks for duplicate confirmed visits (same patient, doctor, clinic, date)
    6. Checks for doctor schedule conflicts (same doctor, time slot, and date)
    7. Calculates queue position for the appointment
    8. Determines base amount for invoice based on visit status and process
    9. Creates a new Visit record with "مؤكد" (confirmed) status
    10. Broadcasts SSE event to notify the assigned doctor of new patient
    11. Creates an associated invoice record
    Returns:
        Redirect to 'receptionBP.reception_home' with appropriate flash message
    Raises:
        Flashes error messages for:
        - Missing reception login
        - Reception account not found
        - Duplicate confirmed visit on same day
        - Doctor time slot conflict
        - Missing patient_id or doctor_id
        - Database operation errors
    Note:
        - TODO: Verify that invoice creation is implemented after Visit commit
        - Normalizes Arabic text variations for consistent data handling
        - Uses func.date() and func.time() for database-level filtering
    """
    reception_id = session.get('reception_id')
    if not reception_id:
        flash("Please log in first", "error")
        return redirect(url_for('clinic_login'))

    # ✅ Get clinic_id from Reception
    clinic_id = db.session.query(Reception.clinic_id)\
           .filter(Reception.id == reception_id)\
           .scalar()
    if not clinic_id:
        flash("Reception account not found", "error")
        return redirect(url_for('clinic_login'))
     
 

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
        
   # clinic_id = session.get('clinic_id')
    patient_name = request.form.get('name')
    normalized_input=normalize_arabic(patient_name)
    patient_phone=request.form.get('phone')
    berth_date=request.form.get('berth_date')
    patient_id = request.form.get('patient_id')
    section_id = request.form.get('section')
    process_id = request.form['process']
    visit_date=request.form['date_visit']
    doctor_id = request.form.get('doctor')
    berth_date=request.form.get('berth_date')
    age = request.form.get('age')
    gender=request.form.get('gender')
    status=request.form.get('status')
    percentage =0 
    if not visit_date :
        visit_date = date.today()

    national_id=request.form.get('national_id')
    if not process_id :
        process_id= None
    
    # Parse visit_date if it's a string (from datetime-local input)
    if isinstance(visit_date, str):
        try:
            visit_datetime = datetime.fromisoformat(visit_date.replace('T', ' '))
            visit_date_obj = visit_datetime.date()
            visit_time = visit_datetime.time()
        except:
            visit_date_obj = date.today()
            visit_time = datetime.now().time()
    else:
        visit_date_obj = visit_date if isinstance(visit_date, date) else date.today()
        visit_time = datetime.now().time()
    
    # Check if patient already has a confirmed visit with this doctor on the same day
    existing_visit = Visit.query.filter(
                    Visit.patient_id==patient_id,
                    Visit.doctor_id==doctor_id,
                    Visit.clinic_id==clinic_id,
                    func.date(Visit.visit_date) == visit_date_obj,
                    Visit.visit_status=="مؤكد"
                ).first()
    if existing_visit:
        flash("Patient already has a confirmed visit with this doctor on the same day.", "error")
        return redirect(url_for('receptionBP.reception_home'))
    
    # Check if another patient already has an appointment with this doctor at the same time
    time_conflict = Visit.query.filter(
        Visit.doctor_id == doctor_id,
        Visit.clinic_id == clinic_id,
        func.date(Visit.visit_date) == visit_date_obj,
        func.hour(Visit.visit_date) == visit_time.hour,
        func.minute(Visit.visit_date) == visit_time.minute,
        Visit.visit_status == "مؤكد"
    ).first()
    
    if time_conflict:
        flash(f"Doctor already has a patient scheduled at {visit_time.strftime('%I:%M %p')} on this date. Please choose a different time.", "error")
        return redirect(url_for('receptionBP.reception_home'))
    
    elif patient_id and doctor_id:
        try:
            # Get doctor and process details for invoice calculation
            doctor = Doctor.query.get(doctor_id)
            process = Process.query.get(process_id) if process_id else None
                # Calculate base amount based on visit status
            if status == "كشف" and Visit.visit_status =="منتهي":
                base_amount = doctor.examination_fee
            elif status == "اعادة" and Visit.visit_status =="منتهي":
                base_amount = doctor.review_fee
            else:
                base_amount = process.fee_process if process else 0
            
            # Calculate queue_position: count all confirmed visits for this doctor on this date
            queue_count = Visit.query.filter(
                Visit.doctor_id == doctor_id,
                Visit.clinic_id == clinic_id,
                func.date(Visit.visit_date) == visit_date_obj,
                Visit.visit_status == "مؤكد"
            ).count()
            queue_position = queue_count + 1  # New visit gets the next position
            
            new_visit = Visit(
                        patient_id=patient_id,
                        patient_name=patient_name,
                        normalized_name=normalized_input,
                        national_id=national_id,
                        berth_date = berth_date ,
                        section_id=section_id,
                        doctor_id=doctor_id,
                        clinic_id=clinic_id,
                        visit_status="مؤكد",
                        age=age,
                        visit_date=visit_date,
                        gender=gender, 
                        status=status,
                        patient_phone= patient_phone,
                        process_id=process_id,
                        queue_position=queue_position
                        )
            db.session.add(new_visit)
            db.session.commit()
            
            # Generate lookup token for WhatsApp auto-lookup
            lookup_token = uuid.uuid4().hex
            new_visit.lookup_token = lookup_token
            db.session.commit()
            
            # Broadcast SSE event to the doctor's stream (new patient)
            broadcast_patient_event(
                doctor_id=doctor_id,
                event_type='new_patient',
                visit_id=new_visit.id,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_phone=patient_phone
            )
            
            # Send WhatsApp notification to the patient
            try:
                clinic_obj = Clinics.query.filter_by(clinic_id=clinic_id).first()
                auto_url = build_auto_lookup_url(lookup_token)
                
                # Format date and time for the message
                if isinstance(visit_date, str):
                    try:
                        vdt = datetime.fromisoformat(visit_date.replace('T', ' '))
                        wa_date = vdt.strftime('%Y-%m-%d')
                        wa_time = vdt.strftime('%I:%M %p')
                    except:
                        wa_date = str(date.today())
                        wa_time = datetime.now().strftime('%I:%M %p')
                else:
                    wa_date = str(date.today())
                    wa_time = datetime.now().strftime('%I:%M %p')
                
                send_appointment_whatsapp(
                    patient_phone=patient_phone,
                    clinic_name=clinic_obj.name_clinic if clinic_obj else 'العيادة',
                    doctor_name=doctor.name if doctor else 'الطبيب',
                    appointment_date=wa_date,
                    appointment_time=wa_time,
                    auto_lookup_url=auto_url
                )
            except Exception as wa_err:
                print(f"⚠️ WhatsApp notification failed: {wa_err}")
            
            # Create invoice for the visit 
            flash("New visit and invoice added successfully.", "success")
        except Exception as e:
               db.session.rollback()
               flash(f"Error adding visit:{e} ", "error")
            
    else:
        flash("Missing information for adding a visit.", "error")

    return redirect(url_for('receptionBP.reception_home'))



@receptionBP.route('/reception/filtered_visitors', methods=['GET'])
def filtered_visitors():
    clinic_id = session.get('clinic_id')
    if not clinic_id:
        return "Clinic ID not found.", 404

    filter_date_str = request.args.get('filter_date')
    filtered_visitors = []

    if filter_date_str:
        try:
            # Parse the date string directly as YYYY-MM-DD
            filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()

            # Query to get visitors for the specified date (ignoring time)
            filtered_visitors = Visit.query.filter(
                Visit.clinic_id == clinic_id,
                func.date(Visit.visit_date) == filter_date
            ).all()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")

    return render_template(
        'reception_home.html',
        filtered_visitors=filtered_visitors,
        filter_date=filter_date_str  # Pass the selected date to the template
    )


@receptionBP.route('/reception/edit_visit', methods=['POST'])
def edit_visit():
    """Edit visit details (especially time/date)"""
    reception_id = session.get('reception_id')
    if not reception_id:
        flash("Please log in first", "error")
        return redirect(url_for('clinic_login'))

    # ✅ Get clinic_id from Reception
    clinic_id = db.session.query(Reception.clinic_id)\
           .filter(Reception.id == reception_id)\
           .scalar()
    if not clinic_id:
        flash("Reception account not found", "error")
        return redirect(url_for('clinic_login'))

    try:
        visit_id = request.form.get('visit_id')
        new_visit_date = request.form.get('visit_date')
        
        visit = Visit.query.get(visit_id)
        if not visit:
            flash("Visit not found.", "error")
            return redirect(url_for('receptionBP.reception_home'))
        
        # Parse the new visit date
        if isinstance(new_visit_date, str):
            try:
                visit_datetime = datetime.fromisoformat(new_visit_date.replace('T', ' '))
                visit_date_obj = visit_datetime.date()
                visit_time = visit_datetime.time()
            except:
                flash("Invalid date format.", "error")
                return redirect(url_for('receptionBP.reception_home'))
        else:
            visit_date_obj = new_visit_date if isinstance(new_visit_date, date) else visit.visit_date.date()
            visit_time = visit.visit_date.time() if hasattr(visit.visit_date, 'time') else datetime.now().time()
        
        # Check if new time conflicts with another appointment for this doctor
        time_conflict = Visit.query.filter(
            Visit.id != visit_id,  # Don't check against itself
            Visit.doctor_id == visit.doctor_id,
            Visit.clinic_id == clinic_id,
            func.date(Visit.visit_date) == visit_date_obj,
            func.hour(Visit.visit_date) == visit_time.hour,
            func.minute(Visit.visit_date) == visit_time.minute,
            Visit.visit_status == "مؤكد"
        ).first()
        
        if time_conflict:
            flash(f"Doctor already has a patient scheduled at {visit_time.strftime('%I:%M %p')} on this date.", "error")
            return redirect(url_for('receptionBP.reception_home'))
        
        # Update visit date/time
        old_visit_date = visit.visit_date
        visit.visit_date = datetime.combine(visit_date_obj, visit_time)
        db.session.commit()
        
        # Broadcast edit event to the doctor
        broadcast_patient_event(
            doctor_id=visit.doctor_id,
            event_type='edit_patient',
            visit_id=visit_id,
            patient_id=visit.patient_id,
            patient_name=visit.patient_name,
            patient_phone=visit.patient_phone
        )
        
        # Broadcast to clinic to update expected times for patients
        from configDB.redis_helper import publish_event
        event_data = {
            'type': 'queue_reordered',
            'doctor_id': visit.doctor_id,
            'clinic_id': clinic_id
        }
        publish_event(f'clinic_{clinic_id}', event_data)
        
        flash("Visit updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating visit: {str(e)}", "error")
    
    return redirect(url_for('receptionBP.reception_home'))


@receptionBP.route('/reception/reorder_queue', methods=['POST'])
def reorder_queue():
    from busnisess_layer.functions.consultation_time_func import recalculate_all_patient_expected_times
    from configDB.redis_helper import publish_event
    reception_id = session.get('reception_id')
    if not reception_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    visit_id = data.get('visit_id')
    new_position = data.get('new_position')
    
    if not visit_id or not new_position:
        return jsonify({'error': 'Missing parameters'}), 400
        
    visit = Visit.query.get(visit_id)
    if not visit:
        return jsonify({'error': 'Visit not found'}), 404
        
    doctor_id = visit.doctor_id
    clinic_id = visit.clinic_id
    old_position = visit.queue_position or 0
    
    if old_position == new_position:
        return jsonify({'success': True})
    
    try:
        # Get all confirmed visits for this doctor today
        today = date.today()
        visits = Visit.query.filter(
            Visit.doctor_id == doctor_id,
            func.date(Visit.visit_date) == today,
            Visit.visit_status == "مؤكد"
        ).order_by(Visit.queue_position.asc()).all()
        
        # Shift positions
        if new_position > old_position:
            # Moving down: shift items between old and new position UP by 1
            for v in visits:
                current_v_pos = v.queue_position or 0
                if v.id != visit_id and old_position < current_v_pos <= new_position:
                    v.queue_position = max(0, current_v_pos - 1)
        else:
            # Moving up: shift items between new and old position DOWN by 1
            for v in visits:
                current_v_pos = v.queue_position or 0
                if v.id != visit_id and new_position <= current_v_pos < old_position:
                    v.queue_position = current_v_pos + 1
                    
        # Set the target visit's new position
        visit.queue_position = new_position
        db.session.commit()
        
        # Broadcast reorder event to clients so they can fetch updated queue times
        event_data = {
            'type': 'queue_reordered',
            'doctor_id': doctor_id,
            'clinic_id': clinic_id
        }
        publish_event(f'clinic_{clinic_id}', event_data)
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@receptionBP.route('/reception/api/appointments/monthly-summary', methods=['GET'])
def get_monthly_summary():
    reception_id = session.get('reception_id')
    if not reception_id:
        return jsonify({'error': 'Unauthorized'}), 401

    clinic_id = db.session.query(Reception.clinic_id).filter(Reception.id == reception_id).scalar()
    if not clinic_id:
        return jsonify({'error': 'Unauthorized'}), 401

    month_str = request.args.get('month')
    year_str = request.args.get('year')
    if not month_str or not year_str:
        return jsonify({'error': 'Missing month or year'}), 400

    try:
        month = int(month_str)
        year = int(year_str)
    except ValueError:
        return jsonify({'error': 'Invalid month or year'}), 400

    # Query visits for the given month and year
    visits = db.session.query(
        func.date(Visit.visit_date).label('day'),
        func.count(Visit.id).label('count')
    ).filter(
        Visit.clinic_id == clinic_id,
        extract('month', Visit.visit_date) == month,
        extract('year', Visit.visit_date) == year,
        Visit.visit_status != 'ملغي'
    ).group_by(func.date(Visit.visit_date)).all()

    # Format the result to {"YYYY-MM-DD": count, ...}
    result = {}
    for day, count in visits:
        if isinstance(day, str):
            result[day] = count
        elif isinstance(day, date):
            result[day.strftime('%Y-%m-%d')] = count

    return jsonify(result)

@receptionBP.route('/reception/api/appointments', methods=['GET'])
def get_daily_appointments():
    reception_id = session.get('reception_id')
    if not reception_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    clinic_id = db.session.query(Reception.clinic_id).filter(Reception.id == reception_id).scalar()
    if not clinic_id:
        return jsonify({'error': 'Unauthorized'}), 401

    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Missing date'}), 400

    try:
        filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    visits_query = Visit.query.filter(
        Visit.clinic_id == clinic_id,
        func.date(Visit.visit_date) == filter_date
    ).all()

    visitors = []
    for visit in visits_query:
        visit_time = visit.visit_date.strftime('%I:%M %p')
        # To avoid python localization issues with AM/PM we can pass as is.
        visitors.append({
            'id': visit.id,
            'doctor_name': visit.doctor.name if visit.doctor else 'Unknown',
            'visit_date_iso': visit.visit_date.strftime('%Y-%m-%dT%H:%M'),
            'visit_date_formatted': visit_time,
            'patient_name': visit.patient_name,
            'patient_phone': visit.patient_phone,
            'patient_id': visit.patient_id,
            'visit_status': visit.visit_status,
            'queue_position': visit.queue_position
        })
    
    return jsonify(visitors)

