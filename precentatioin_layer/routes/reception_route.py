from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.functions.doctor_func import broadcast_patient_event
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit
)
from flask_sse import sse

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
                        name=name,  normalized_name=normalized_name, phone=phone, national_id=national_id,berth_date = berth_date,
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
                    
                    # Broadcast SSE event to the doctor's stream (new patient)
                    broadcast_patient_event(
                        doctor_id=doctor_id,
                        event_type='new_patient',
                        visit_id=new_visit.id,
                        patient_id=new_patient.id,
                        patient_name=name,
                        patient_phone=phone
                    )
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
            if status == "كشف":
                base_amount = doctor.examination_fee
            elif status == "اعادة":
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
            
            # Broadcast SSE event to the doctor's stream (new patient)
            broadcast_patient_event(
                doctor_id=doctor_id,
                event_type='new_patient',
                visit_id=new_visit.id,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_phone=patient_phone
            )
            
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
        
        flash("Visit updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating visit: {str(e)}", "error")
    
    return redirect(url_for('receptionBP.reception_home'))


