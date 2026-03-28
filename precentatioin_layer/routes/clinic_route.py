from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit
)
from busnisess_layer.functions.doctor_func import require_feature , require_feature_and_role
from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta
clinicBP = Blueprint('clinicBP',__name__)




# Routes for Bills Management
@clinicBP.route('/clinic_bills')
def clinic_bills():
    # Get clinic_id from session or request (adjust based on your auth system)
    clinic_id = session.get('clinic_id')    
    # Get all bills for the current clinic
    bills_data = Bills.query.filter_by(clinic_id=clinic_id).all()
      # Check if it's an AJAX request or direct page access
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'bills': [bill.to_dict() for bill in bills_data]})
    else:
        return render_template('clinic_management.html', active_tab='bills-tab', bills=bills_data)

    
    return render_template('clinic_management.html', active_tab='bills-tab', bills=bills)

@clinicBP.route('/add_bill', methods=['POST'])
@require_feature("add_bill")
def add_bill():
    try:
        clinic_id = session.get('clinic_id')
        
        # Get form data
        name = request.form.get('name')
        amount = float(request.form.get('amount'))
        date_issued = request.form.get('date_issued')
        status = request.form.get('status', 'غير مدفوع')
        description = request.form.get('description', '')
        section = request.form.get('section', '')  # Get section from form
        
        # Convert date string to datetime object
        if date_issued:
            date_issued = datetime.strptime(date_issued, '%Y-%m-%d')
        else:
            date_issued = datetime.utcnow()
        
        # Create new bill
        new_bill = Bills(
            clinic_id=clinic_id,
            name=name,
            amount=amount,
            date_issued=date_issued,
            status=status,
            description=description,  # Fixed: discription -> description
            bill_section=section  # Added section
        )
        
        # Add to database
        db.session.add(new_bill)
        db.session.commit()
        
        flash('تم إضافة الفاتورة بنجاح', 'success')
        return jsonify({'success': True, 'bill': new_bill.to_dict()})
    
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إضافة الفاتورة', 'error')
        return jsonify({'success': False, 'error': str(e)})

@clinicBP.route('/update_bill/<int:bill_id>', methods=['POST'])
def update_bill(bill_id):
    try:
        clinic_id = session.get('clinic_id')
        
        # Find the bill
        bill = Bills.query.filter_by(id=bill_id, clinic_id=clinic_id).first()
        
        if not bill:
            return jsonify({'success': False, 'error': 'الفاتورة غير موجودة'})
        
        # Update bill data
        bill.name = request.form.get('name', bill.name)
        bill.amount = float(request.form.get('amount', bill.amount))
        
        date_issued = request.form.get('date_issued')
        if date_issued:
            bill.date_issued = datetime.strptime(date_issued, '%Y-%m-%d')
            
        bill.status = request.form.get('status', bill.status)
        bill.description = request.form.get('description', bill.description)  # Fixed
        bill.bill_section = request.form.get('section', bill.bill_section)  # Added section
        
        # Save changes
        db.session.commit()
        
        return jsonify({'success': True, 'bill': bill.to_dict()})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@clinicBP.route('/delete_bill/<int:bill_id>', methods=['POST'])
def delete_bill(bill_id):
    try:
        clinic_id = session.get('clinic_id')
        print(f"Attempting to delete bill {bill_id} for clinic {clinic_id}")
        
        if not clinic_id:
            print("No clinic_id in session")
            return jsonify({'success': False, 'error': 'Clinic ID not found in session'})
        
        # Find the bill
        bill = Bills.query.filter_by(id=bill_id, clinic_id=clinic_id).first()
        
        if not bill:
            print(f"Bill {bill_id} not found for clinic {clinic_id}")
            return jsonify({'success': False, 'error': 'الفاتورة غير موجودة'})
        
        print(f"Deleting bill: {bill.id}, {bill.name}")
        # Delete the bill
        db.session.delete(bill)
        db.session.commit()
        
        print("Bill deleted successfully")
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting bill: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@clinicBP.route('/get_bills')
def get_bills():
    try:
        clinic_id = session.get('clinic_id')
        
        # Get all bills for the current clinic
        bills = Bills.query.filter_by(clinic_id=clinic_id).all()
        
        # Convert to list of dictionaries
        bills_data = [bill.to_dict() for bill in bills]
        
        return jsonify({'success': True, 'bills': bills_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

 
        return jsonify({"success": False, "error": str(e)})

@clinicBP.route('/clinic_report', methods=['GET', 'POST'])
@require_feature("clinic_report")
def clinic_report():
    clinic_id = session.get('clinic_id')
    clinic_name = db.session.query(Clinics.name_clinic).filter(Clinics.clinic_id == clinic_id).scalar()
    # Get month from request (both GET and POST)
    if request.method == 'GET':
        month = request.args.get('month', default=datetime.now().month, type=int)
    else:
        month = request.form.get('month', default=datetime.now().month, type=int)
    
    # Debug: Print current month being used
    print(f"Report month: {month} (Current month: {datetime.now().month})")
    
    # Debug: Check what procedures exist in this month
    all_procedures_this_month = (
        db.session.query(
            Procedure.id,
            Procedure.process_id,
            Procedure.final_cost,
            Procedure.status,
            Visit.doctor_id,
            Visit.visit_date
        )
        .join(Visit, Procedure.visit_id == Visit.id)
        .filter(
            Visit.clinic_id == clinic_id,
            extract('month', Visit.visit_date) == month
        )
        .all()
    )
    print(f"Total procedures in month {month}: {len(all_procedures_this_month)}")
    for proc in all_procedures_this_month:
        print(f"  Procedure ID: {proc.id}, Process ID: {proc.process_id}, Doctor ID: {proc.doctor_id}, Status: {proc.status}, Date: {proc.visit_date}")

    process_report = []
    visit_report = []
    combined_report = []
    sums = 0
    total_revenue = 0
    total_bills_month = 0
    total_bills_doctors = 0 

    # ---------- SAVE CHANGES ----------
    if request.method == 'POST' and 'save_changes' in request.form:
        try:
            for key, value in request.form.items():
                if key.startswith('percentage_'):
                    parts = key.split('_')
                    doctor_id = int(parts[1])
                    process_id = int(parts[2])

                    percentage = Percentages.query.filter_by(
                        doctor_id=doctor_id,
                        process_id=process_id
                    ).first()

                    if percentage:
                        percentage.percentage = float(value)
                    else:
                        percentage = Percentages(
                            doctor_id=doctor_id,
                            process_id=process_id,
                            percentage=float(value)
                        )
                        db.session.add(percentage)

            db.session.commit()
            flash('تم حفظ التغييرات بنجاح', 'success')
            return redirect(url_for('clinicBP.clinic_management', tab='revenue-process'))


        except Exception as e:
            db.session.rollback()
            flash(f'خطأ في الحفظ: {str(e)}', 'error')
            

    # ---------- REPORT GENERATION ----------
    doctors = Doctor.query.filter(Doctor.clinic_id == clinic_id).all()

    # Check which report was requested
    report_requested = False
    
    if request.method == 'POST':
        if 'combined_report' in request.form:
            report_requested = True
            # --- Combined report ---
            for doctor in doctors:
                visits_count = Visit.query.filter(
                    Visit.doctor_id == doctor.id,
                    Visit.visit_status == "مؤكد",
                    Visit.status == "كشف",
                    extract('month', Visit.visit_date) == month
                ).count()

                visits_revue_count = Visit.query.filter(
                    Visit.doctor_id == doctor.id,
                    Visit.visit_status == "مؤكد",
                    Visit.status == "اعادة",
                    extract('month', Visit.visit_date) == month
                ).count()
                total_revenue += visits_count * doctor.examination_fee + visits_revue_count * doctor.review_fee
                
                # Debug: Print visit counts
                print(f"Doctor {doctor.name}: Visits={visits_count}, Reviews={visits_revue_count}")
                
                # Check if doctor has any visits
                has_visits = visits_count > 0 or visits_revue_count > 0

                # Get procedures for this doctor in this month
                procedures = (
                    db.session.query(
                        Procedure.process_id,
                        func.count(Procedure.id).label("proc_count"),
                        func.sum(Procedure.final_cost).label("total_proc_cost")
                    )
                    .join(Visit, Procedure.visit_id == Visit.id)
                    .filter(
                        Visit.clinic_id == clinic_id,
                        Visit.doctor_id == doctor.id,
                        extract('month', Visit.visit_date) == month,
                        Visit.status != "ملغي",
                        Procedure.status == "completed"
                    )
                    .group_by(Procedure.process_id)
                    .all()
                )
                
                # Debug: Print procedures found for this doctor
                print(f"Doctor {doctor.name} (ID: {doctor.id}) - Month: {month}")
                print(f"Procedures found: {len(procedures)}")
                for proc in procedures:
                    print(f"  Process ID: {proc.process_id}, Count: {proc.proc_count}, Total Cost: {proc.total_proc_cost}")

                doctor_has_processes = False

                for proc in procedures:
                    doctor_has_processes = True
                    process = Process.query.get(proc.process_id)
                    percentage_record = Percentages.query.filter_by(
                        doctor_id=doctor.id,
                        process_id=proc.process_id
                    ).first() 
                    percentage_value = percentage_record.percentage if percentage_record else 0

                    revenue_share = int((float(percentage_value ) / 100) * 
                                        float(proc.total_proc_cost))
                    clinic_share = float(proc.total_proc_cost) - revenue_share
                    
                    combined_report.append({
                        "doctor_id": doctor.id,
                        "doctor_name": doctor.name,
                        "visits_count": visits_count,
                        "revue_visits_count": visits_revue_count,
                        "examination_fee": doctor.examination_fee,
                        "review_fee": doctor.review_fee,
                        "visits_revenue": (visits_count * doctor.examination_fee) + (visits_revue_count * doctor.review_fee),
                        "process_id": proc.process_id,
                        "process_name": process.name_process if process else "عملية محذوفة",
                        "process_count": proc.proc_count,
                        "process_cost": process.fee_process if process else 0,
                        "percentage": percentage_value,
                        "revenue_per_process": revenue_share,
                        "total_cost_process": clinic_share
                    })

                    sums += clinic_share
                
                # If doctor has visits but no procedures, add them to the report
                if has_visits and not doctor_has_processes:
                    combined_report.append({
                        "doctor_id": doctor.id,
                        "doctor_name": doctor.name,
                        "visits_count": visits_count,
                        "revue_visits_count": visits_revue_count,
                        "examination_fee": doctor.examination_fee,
                        "review_fee": doctor.review_fee,
                        "visits_revenue": (visits_count * doctor.examination_fee) + (visits_revue_count * doctor.review_fee),
                        "process_id": None,
                        "process_name": "لا توجد عمليات",
                        "process_count": 0,
                        "process_cost": 0,
                        "percentage": 0,
                        "revenue_per_process": 0,
                        "total_cost_process": 0
                    })

        

        elif 'visit_reopo' in request.form:
            report_requested = True
            # --- Visit report ---
            for doctor in doctors:
                visits_count = Visit.query.filter(
                    Visit.doctor_id == doctor.id,
                    Visit.visit_status == "مؤكد",
                    Visit.status == "كشف",
                    extract('month', Visit.visit_date) == month
                ).count()

                visits_revue_count = Visit.query.filter(
                    Visit.doctor_id == doctor.id,
                    Visit.visit_status == "مؤكد",
                    Visit.status == "اعادة",
                    extract('month', Visit.visit_date) == month
                ).count()

                fee = doctor.examination_fee * visits_count
                reveue_fee = doctor.review_fee * visits_revue_count
                total_revenue += fee + reveue_fee

                visit_report.append({
                    "name_doctor": doctor.name,
                    "total_visits": visits_count,
                    "total_revue_visits": visits_revue_count,
                    "revue_fee": doctor.review_fee,
                    "fee": doctor.examination_fee,
                    "revenue_per_doctor": reveue_fee + fee
                })
         
    bill_month = Bills.query.filter_by(clinic_id=clinic_id).filter(extract('month', Bills.date_issued) == month).all()
    for bill in bill_month:
        total_bills_month += bill.amount

    # Pass the active tab to the template
    active_tab = 'revenue-process-tab' if 'combined_report' in request.form else 'revenue-visit-tab' if 'visit_reopo' in request.form else ''

    return render_template(
        'clinic_management.html',
        process_report=process_report,
        sums=sums,
        visit_report=visit_report,
        total_revenue=total_revenue,
        combined_report=combined_report,
        month=month,
        active_tab=active_tab,
        report_requested=report_requested , 
        clinic_name=clinic_name , 
        total_bills_month=total_bills_month
    )

@clinicBP.route('/update_percentage', methods=['POST'])
def update_percentage():
    doctor_id = request.form['doctor_id']
    process_id = request.form['process_id']
    percentage = float(request.form['percentage'])

    process = Process.query.filter_by(id=process_id, doctor_id=doctor_id).first()
    if not process:
        return jsonify({"success": False, "message": "Process not found"})

    process.percentage = percentage
    db.session.commit()

    # احسب إيراد الدكتور للعملية دي
    revenue_per_process = (process.process_cost or 0) * (percentage / 100)

    return jsonify({
        "success": True,
        "message": "تم التحديث",
        "new_value": percentage,
        "revenue_per_process": revenue_per_process
    })


@clinicBP.route('/clinic_management', methods=['GET', 'POST'])
def clinic_management():
    # Retrieve the logged-in clinic ID from session
    clinic_id = session.get('clinic_id')  # Assuming you're storing clinic_id in session after login
    clinic = Clinics.query.filter_by(clinic_id=clinic_id).first()  # Use Clinics here
    sections = Section.query.filter_by(clinic_id=clinic_id).all()
    patients = Patient.query.filter_by(clinic_id=clinic_id).all()
    doctors = Doctor.query.filter_by(clinic_id=clinic_id).all()
    receptions = Reception.query.filter_by(clinic_id = clinic_id).all()
    bills_data = Bills.query.filter_by(clinic_id=clinic_id).all()

    today = date.today()
    month=date.month
    #visitors = Visit.query.filter_by(clinic_id=clinic_id,visit_date=today).all()
    visitors = Visit.query.filter_by(clinic_id=clinic_id).all()
    visit_month = Visit.query.filter(Visit.clinic_id==clinic_id,Visit.visit_status =="مؤكد",Visit.status=="كشف",extract('month',Visit.visit_date)==month).count()
    total_reven = 0 
  


    if not clinic_id:
        #return "Error: Clinic ID is missing from session. Pleaselog in again.", 400
        return render_template('clinic_login.html')

    def get_monthly_visits_by_doctor(clinic_id, year=None, month=None):
        # default to current year/month
        now = datetime.datetime.utcnow()
        year = year or now.year
        month = month or now.month

        # Query aggregated counts
        q = (
            db.session.query(
                Visit.doctor_id,
                func.count(Visit.id).label("visits")
            )
            .filter(
                Visit.clinic_id == clinic_id,
                extract("year", Visit.date_visit) == year,
                extract("month", Visit.date_visit) == month
            )
            .group_by(Visit.doctor_id)
        )

        # build a mapping {doctor_id: count}
        counts = {doctor_id: visits for doctor_id, visits in q}

        return counts
    

    

    # Fetch sections for the current clinic
    sections = Section.query.filter_by(clinic_id=clinic_id).all()

    if request.method == 'POST':
        # Adding a new section
        if 'add_section' in request.form:
            name_section = request.form.get('name_section')

            if not name_section:
                return "Section name is required.", 400

            # Check if the section already exists for this clinic
            existing_section = Section.query.filter_by(name_section=name_section, clinic_id=clinic_id).first()
            if existing_section:
                flash('القسم موجود بالفعل ', 'error')
                return redirect(url_for('clinicBP.clinic_management'))
                return "Section already exists for this clinic.", 400
           

            # Create new section with clinic_id
            new_section = Section(name_section=name_section, clinic_id=clinic_id)
            db.session.add(new_section)
            db.session.commit()
            return redirect(url_for('clinicBP.clinic_management'))

        # Adding a new doctor
        elif 'add_doctor' in request.form:
            username = request.form.get('doctor-username')
            name = request.form.get('doctor-name')
            phone=request.form.get('phone-doctor')
            password = request.form.get('doctor-password')
            examination_fee = request.form.get('examination-fee')
            review_fee = request.form.get('review-fee')
            section_id = request.form.get('doctor-section')

            # Validate input fields for doctor
            if not username or not name or not password or not section_id:
                return "All doctor fields are required.", 400

            # Check if the doctor already exists
            existing_doctor = Doctor.query.filter_by(username=username,clinic_id=clinic_id).first()
            if existing_doctor:



                flash('الدكتور موجود بالفعل ', 'error')
                return redirect(url_for('clinicBP.clinic_management'))

             #   return "Doctor already exists.", 400

            # Create new doctor with the clinic_id
            new_doctor = Doctor(
                username=username,
                name=name,
                phone=phone,
                password=password,
                section_id=section_id,
                review_fee=review_fee,
                examination_fee=examination_fee,
                clinic_id=clinic_id  # Use clinic_id from session
            )
            db.session.add(new_doctor)
            db.session.commit()
            return redirect(url_for('clinicBP.clinic_management'))
        
        elif 'add_reception' in request.form:
            email = request.form.get('reception-email')
            name = request.form.get('reception-name')
            phone=request.form.get('reception-phone')
            password = request.form.get('reception-password')
            clinic_id = clinic_id

            # Validate input fields for doctor
            if not email or not name or not password or not clinic_id:
                return "All doctor fields are required.", 400

            # Check if the doctor already exists
            existing_reception = Reception.query.filter_by(email=email,clinic_id=clinic_id).first()
            if existing_reception:
                flash('الريسيبشن موجود بالفعل ', 'error')
                return redirect(url_for('clinicBP.clinic_management'))

                

                # return "reception already exists.", 400

            # Create new doctor with the clinic_id
            new_reception = Reception(
                email=email,
                name=name,
                password=password,
                phone=phone,
                clinic_id=clinic_id  # Use clinic_id from session
            )
            db.session.add(new_reception)
            db.session.commit()
        #    return redirect(url_for('clinic_management'))

        elif 'add_process' in request.form:
            name_process = request.form.get('name-process')
            fee_process = request.form.get('fee')
            section_id=request.form.get('section-id')
            clinic_id = clinic_id

            # Validate input fields for doctor
            if not name_process or not section_id  or not clinic_id:
                return "All process fields are required.", 400

            # Check if the doctor already exists
            existing_process = Process.query.filter_by(name_process=name_process,clinic_id=clinic_id).first()
            if existing_process:
                flash('العملية موجود بالفعل ', 'error')
                return redirect(url_for('clinicBP.clinic_management'))
               
                return "process already exists.", 400

            # Create new doctor with the clinic_id
            new_process = Process(
                name_process=name_process,
                fee_process=fee_process,
                section_id=section_id,
                clinic_id=clinic_id  # Use clinic_id from session
            )
            db.session.add(new_process)
            db.session.commit()

        clinic_id = session.get('clinic_id')

        # Fetch patients and doctors related to the logged-in clinic
    patients = Patient.query.filter_by(clinic_id=clinic_id). all()
    doctors = Doctor.query.filter_by(clinic_id=clinic_id).options(joinedload(Doctor.section)).all()
    visitors = Visit.query.filter_by(clinic_id=clinic_id).all()
    sections = Section.query.filter_by(clinic_id=clinic_id).all()
  

    

    clinic_name = clinic.name_clinic
    # Collect doctor data with patient count
    doctor_data = []
    for doctor in doctors:
        patient_count = Patient.query.filter_by(doctor_id=doctor.id).count()
        doctor_data.append({'doctor': doctor, 'patient_count': patient_count})
 
    return render_template('clinic_management.html',
                           visitors = visitors 
                           ,clinic=clinic,
                           receptions = receptions
                           ,sections=sections
                           , clinic_name=clinic_name,patients=patients,
                            doctor_data=doctor_data,
                            bills=bills_data)

