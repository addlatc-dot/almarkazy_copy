from flask import Blueprint 
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from  busnisess_layer.functions.calculations import *
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit
)

from sqlalchemy import or_ , func ,and_ , extract

from datetime import datetime , date,timedelta

apiBP = Blueprint('apiBP',__name__)






@apiBP.route('/api/patient_account', methods=['POST'])
def api_patient_account():
    """
    POST JSON: { "patient_id": <id> }   OR { "name": "<patient name>" }
    Returns JSON with visits -> procedures, invoice, payments, totals, remaining.
    """
    clinic_id = require_clinic()
    #reception_id , clinic_id = require_reception()

    # Check if it's JSON or form data
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict() or {}
    
    patient_id = data.get("patient_id")
    patient_name=  data.get("name")
    patient_name_normalize = normalize_arabic(patient_name)

 


    if not patient_id and not patient_name:
        return jsonify({"error": "patient_id or name required"}), 400

    # find patient in this clinic
    if patient_id:
        patient = Visit.query.filter_by(patient_id=patient_id, clinic_id=clinic_id).first()
    else:
        # Use case-insensitive search for name
        patient = Visit.query.filter(
            Visit.clinic_id == clinic_id,
         or_( Visit.normalized_name== patient_name_normalize , Visit.patient_name==patient_name)
        ).first()

    if not patient:
        return jsonify({"error": "patient not found"}), 404

    # gather visits for patient
    visits = Visit.query.filter_by(patient_id=patient.patient_id, clinic_id=clinic_id).options(
        joinedload(Visit.doctor),
        joinedload(Visit.section)
    ).order_by(Visit.visit_date.desc()).all()

    result_visits = []
    for v in visits:
        # procedures for this visit
        procs = Procedure.query.filter_by(visit_id=v.id , status="completed").all()
        proc_list = []
        sum_after_proc_discounts = Decimal(0)
        for p in procs:
            # ensure final_cost is calculated
            final = Decimal(recalc_procedure(p) or 0)
            db.session.add(p)  # in case we changed final_cost
            proc_list.append({
                "id": p.id,
                "process_id": p.process_id,
                "description": p.description,
                "original_cost": money(p.cost),
                "discount_pct": p.discount,
                "final_cost": money(final)
            })
            sum_after_proc_discounts += final

        # invoice for this visit (one invoice per visit assumed)
        invoice = Invoice.query.filter_by(visit_id=v.id, clinic_id=clinic_id).first()
        if invoice is None:
            # create a transient invoice object for display (do not auto-create DB row unless needed)
            invoice_amount = float(sum_after_proc_discounts)
            invoice_total = invoice_amount
            invoice_discount = invoice.discount or 0 if invoice else 0
            invoice_id = None
            status = "no_invoice"
        else:
            # recalc invoice totals to be safe
            invoice_amount = invoice.amount
            invoice_total = invoice.total_amount
            invoice_discount = invoice.discount or 0
            invoice_id = invoice.id
            status = invoice.status
      
        # payments for invoice
        payments = []
        total_paid = Decimal(0)
        if invoice_id:
            pays = Payments.query.filter_by(invoice_id=invoice_id).order_by(Payments.payment_date.asc()).all()
            for pay in pays:
                payments.append({
                    "id": pay.id,
                    "paid_amount": money(pay.paid_amount),
                    "payment_date": pay.payment_date.isoformat(),
                    "method": pay.method
                })
                total_paid += Decimal(pay.paid_amount)

        remaining = Decimal(invoice_total) - total_paid

        result_visits.append({
            "visit_id": v.id,
        "visit_date": v.visit_date.isoformat() if v.visit_date else None,
        "section": v.section.name_section if v.section else None,
        "doctor": v.doctor.name if v.doctor else None,
        "procedures": proc_list,
        "invoice": {
            "id": invoice_id,
            "amount_before_visit_discount": money(invoice_amount),
            "visit_discount_pct": invoice_discount,  # Make sure this field exists
            "total_after_visit_discount": money(invoice_total),
            "status": status
        },
            "payments": payments,
            "total_paid": money(total_paid),
            "remaining": money(remaining)
        })

    # commit any changed procedure.final_costs
    db.session.commit()

    return jsonify({
        "patient": {"id": patient.patient_id, "name": patient.patient_name, "phone": patient.patient_phone},
        "visits": result_visits
    })


@apiBP.route('/api/procedure/<int:proc_id>/discount', methods=['POST'])
def api_update_procedure_discount(proc_id):
    """
    POST JSON: {"discount": 20}  -> percent
    Recalculates procedure.final_cost and related invoice totals.
    """
    clinic_id = require_clinic()
    payload = request.get_json() or {}
    discount = payload.get("discount")
    if discount is None:
        return jsonify({"error": "discount required"}), 400

    proc = Procedure.query.get(proc_id)
    if not proc:
        return jsonify({"error": "procedure not found"}), 404

    # Ensure procedure belongs to clinic via visit -> clinic_id
    visit = Visit.query.get(proc.visit_id)
    if not visit or visit.clinic_id != clinic_id:
        return jsonify({"error": "not authorized"}), 403

    proc.discount = int(discount)
    recalc_procedure(proc)
    db.session.add(proc)
    db.session.commit()
   
    create_or_get_invoice(proc.visit_id, clinic_id)
    # recalc invoice if exists - this also updates remaining_amounts
    invoice = Invoice.query.filter_by(visit_id=visit.id).first()
    if invoice:
        before, after = recalc_invoice(invoice)
    
    return jsonify({
        "procedure_id": proc.id,
        "final_cost": money(proc.final_cost),
        "discount": proc.discount
    })


@apiBP.route('/api/invoice/<int:invoice_id>/discount', methods=['POST'])
def api_update_invoice_discount(invoice_id):
    """
    POST JSON: {"discount": 5}  -> percent for the whole visit invoice
    """
    clinic_id = require_clinic()
    payload = request.get_json() or {}
    discount = payload.get("discount")
    if discount is None:
        return jsonify({"error": "discount required"}), 400

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404

    # verify clinic
    if invoice.clinic_id != clinic_id:
        return jsonify({"error": "not authorized"}), 403

    invoice.discount = int(discount)
    
    # recalc totals and update remaining_amounts
    before, after = recalc_invoice(invoice)

    return jsonify({
        "invoice_id": invoice.id,
        "amount_before_discount": money(before),
        "discount_pct": invoice.discount,
        "total_after_discount": money(after)
    })


@apiBP.route('/api/invoice/<int:invoice_id>/payment', methods=['POST'])
def api_add_payment(invoice_id):
    """
    POST JSON: {"paid_amount": 2000, "method": "كاش", "update_type": "total"}
    If update_type is "total", it sets the total paid amount for the invoice.
    If update_type is "add" (or omitted), it adds a new payment.
    """
    clinic_id = require_clinic()
    payload = request.get_json() or {}
    paid_amount = payload.get("paid_amount")
    method = payload.get("method", "كاش")
    update_type = payload.get("update_type", "add")  # "add" or "total"

    if paid_amount is None:
        return jsonify({"error": "paid_amount required"}), 400

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404
    if invoice.clinic_id != clinic_id:
        return jsonify({"error": "not authorized"}), 403

    # Get visit to access patient_id
    visit = Visit.query.get(invoice.visit_id)
    if not visit:
        return jsonify({"error": "visit not found"}), 404

    # ensure invoice totals are up-to-date
    recalc_invoice(invoice)

    if update_type == "total":
        # Handle total payment update
        current_paid = db.session.query(func.coalesce(func.sum(Payments.paid_amount), 0)).filter_by(invoice_id=invoice.id).scalar()
        additional_amount = Decimal(paid_amount) - Decimal(current_paid or 0)
        
        if additional_amount != 0:
            # Only create a new payment if there's a difference
            new_remaining = Decimal(invoice.total_amount) - Decimal(paid_amount)
            
            pay = Payments(
                invoice_id=invoice.id,
                id_clinic=clinic_id,
                visit_id=invoice.visit_id,
                paid_amount=float(additional_amount),
                method=f"{method} - تحديث إجمالي",
                patient_id=visit.patient_id,
                discount = 0,
                remaining_amount=float(max(new_remaining, 0))
            )
            db.session.add(pay)
            db.session.commit()
            
            # Update remaining amounts for all payments of this invoice
            update_remaining_amounts(invoice.id)
        
        # Use the target total paid amount
        new_total_paid = Decimal(paid_amount)
        new_remaining = Decimal(invoice.total_amount) - new_total_paid
        
    else:
        # Handle adding new payment (original logic)
        pays_sum = db.session.query(func.coalesce(func.sum(Payments.paid_amount), 0)).filter_by(invoice_id=invoice.id).scalar()
        current_remaining = Decimal(invoice.total_amount) - Decimal(pays_sum or 0)
        new_remaining = current_remaining - Decimal(paid_amount)

        pay = Payments(
            invoice_id=invoice.id,
            id_clinic=clinic_id,
            visit_id=invoice.visit_id,
            paid_amount=float(paid_amount),
            method=method,
            patient_id=visit.patient_id,
            remaining_amount=float(max(new_remaining, 0))
        )
        db.session.add(pay)
        db.session.commit()

        # Update remaining amounts for all payments of this invoice
        update_remaining_amounts(invoice.id)
        
        # Recalculate total paid after commit
        new_total_paid = db.session.query(func.coalesce(func.sum(Payments.paid_amount), 0)).filter_by(invoice_id=invoice.id).scalar()

    # Update invoice status
    if new_remaining <= 0:
        invoice.status = 'مدفوع'
        invoice.paid_amount = float(new_total_paid)
    else:
        invoice.status = 'غير مدفوع'
        invoice.paid_amount = float(new_total_paid)
    
    db.session.add(invoice)
    db.session.commit()

    return jsonify({
        "invoice_id": invoice.id,
        "paid_now": money(paid_amount) if update_type == "add" else money(additional_amount if 'additional_amount' in locals() else 0),
        "total_paid": money(new_total_paid),
        "remaining": money(max(new_remaining, 0))
    })


# Alternative: Create a separate endpoint for total payment updates
@apiBP.route('/api/invoice/<int:invoice_id>/set_total_payment', methods=['POST'])
def api_set_total_payment(invoice_id):
    """
    POST JSON: {"total_paid": 2000, "method": "تحديث حساب"}
    Sets the total paid amount for an invoice by calculating the difference.
    """
    clinic_id = require_clinic()
    payload = request.get_json() or {}
    total_paid = payload.get("total_paid")
    method = payload.get("method", "تحديث حساب")

    if total_paid is None:
        return jsonify({"error": "total_paid required"}), 400

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404
    if invoice.clinic_id != clinic_id:
        return jsonify({"error": "not authorized"}), 403

    # Get visit to access patient_id
    visit = Visit.query.get(invoice.visit_id)
    if not visit:
        return jsonify({"error": "visit not found"}), 404

    # ensure invoice totals are up-to-date
    recalc_invoice(invoice)

    # Calculate current total paid
    current_paid = db.session.query(func.coalesce(func.sum(Payments.paid_amount), 0)).filter_by(invoice_id=invoice.id).scalar()
    difference = Decimal(total_paid) - Decimal(current_paid or 0)
    
    if difference != 0:
        # Create adjustment payment
        new_remaining = Decimal(invoice.total_amount) - Decimal(total_paid)
        
        pay = Payments(
            invoice_id=invoice.id,
            id_clinic=clinic_id,
            visit_id=invoice.visit_id,
            paid_amount=float(difference),
            method=f"{method} - تسوية",
            patient_id=visit.patient_id,
            remaining_amount=float(max(new_remaining, 0))
        )
        db.session.add(pay)
        db.session.commit()
        
        # Update remaining amounts
        update_remaining_amounts(invoice.id)

    # Update invoice status
    new_remaining = Decimal(invoice.total_amount) - Decimal(total_paid)
    if new_remaining <= 0:
        invoice.status = 'مدفوع'
    else:
        invoice.status = 'غير مدفوع'
    
    invoice.paid_amount = float(total_paid)
    db.session.add(invoice)
    db.session.commit()

    return jsonify({
        "invoice_id": invoice.id,
        "adjustment": money(difference),
        "total_paid": money(total_paid),
        "remaining": money(max(new_remaining, 0))
    })


@apiBP.route('/api/invoice/<int:invoice_id>/recalc', methods=['POST'])
def api_recalc_invoice(invoice_id):
    """Force-recalculate invoice from DB data."""
    clinic_id = require_clinic()
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404
    if invoice.clinic_id != clinic_id:
        return jsonify({"error": "not authorized"}), 403

    before, after = recalc_invoice(invoice)
    pays_sum = db.session.query(func.coalesce(func.sum(Payments.paid_amount), 0)).filter_by(invoice_id=invoice.id).scalar()
    remaining = Decimal(after) - Decimal(pays_sum or 0)

    # update status
    invoice.status = 'مدفوع' if remaining <= 0 else 'غير مدفوع'
    db.session.add(invoice)
    db.session.commit()

    return jsonify({
        "invoice_id": invoice.id,
        "amount_before_discount": money(before),
        "total_after_discount": money(after),
        "total_paid": money(pays_sum or 0),
        "remaining": money(max(remaining, 0)),
        "status": invoice.status
    })

@apiBP.route('/get_processes/<section_id>')
def get_processes(section_id):
    processes = Process.query.filter_by(section_id=section_id).all()
    processes_list = [{'id': process.id, 'name': process.name_process} for process in processes]
    return jsonify(processes_list)
@apiBP.route('/get_process', methods=['GET'])
def getprocess():
    # Try to get clinic_id from different sources
    clinic_id = session.get('clinic_id')
    
    # If clinic_id not in session, try to get it from doctor's session
    if not clinic_id and session.get('doctor_id'):
        doctor = Doctor.query.get(session['doctor_id'])
        if doctor:
            clinic_id = doctor.clinic_id
    
    if not clinic_id:
        return jsonify({'error': 'clinic_id parameter is required'}), 400

    processes = Process.query.filter_by(clinic_id=clinic_id).all()
    process_list = [{
        'id': process.id, 
        'name': process.name_process,  # Changed from 'name_process' to 'name'
        'cost': process.fee_process    # Changed from 'fee_process' to 'cost'
    } for process in processes]

    return jsonify(process_list)

@apiBP.route('/save_procedures', methods=['POST'])
def save_procedures():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        visit_id = data.get('visit_id')
        diagnosis = data.get('diagnosis')
        procedures = data.get('procedures', [])
        
        # تحقق من وجود visit_id
        if not visit_id:
            return jsonify({'success': False, 'error': 'معرف الزيارة مطلوب'})
        
        # Get the visit and check if it belongs to the current doctor
        visit = Visit.query.get(visit_id)
        if not visit:
            return jsonify({'success': False, 'error': 'الزيارة غير موجودة'})
        
        if visit.doctor_id != doctor_id:
            return jsonify({'success': False, 'error': 'ليس لديك صلاحية لهذه الزيارة'})
        
        # تحديث التشخيص في الزيارة
        visit.diagnosis = diagnosis
        db.session.add(visit)
        
        # Clear existing procedures for this visit
       # Procedure.query.filter_by(visit_id=visit_id).delete()
        
        # Add new procedures
        for proc_data in procedures:
            # البحث بالإسم ومعرف العيادة للتأكد من وجود الإجراء
            process = Process.query.filter(
                Process.name_process.ilike(proc_data['name']),
                Process.clinic_id == visit.clinic_id
            ).first()
           
            if process:
                procedure = Procedure(
                    process_id=process.id,
                    visit_id=visit_id,
                    cost=proc_data['cost'],
                    description=diagnosis,
                    date_performed=datetime.now(),
                    status=proc_data.get('status', 'pending'),
                    
                )
                db.session.add(procedure)
            else:
                print(f"تحذير: الإجراء '{proc_data['name']}' غير موجود في العيادة")
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم الحفظ بنجاح'})
        
    except Exception as e:
        db.session.rollback()
        print(f"خطأ في الحفظ: {str(e)}")
        return jsonify({'success': False, 'error': f'خطأ في الحفظ: {str(e)}'})



@apiBP.route('/get_previous_procedures/<int:visit_id>')
def get_previous_procedures(visit_id):
    try:
        doctor_id = session.get('doctor_id')
        if not doctor_id:
            return jsonify([])
            
        # التحقق من أن الزيارة تخص الدكتور الحالي
        current_visit = Visit.query.filter_by(
            id=visit_id, 
            doctor_id=doctor_id
        ).first()
        
        if not current_visit:
            return jsonify([])
        
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify([])
        
        # الحصول على جميع زيارات المريض في هذه العيادة فقط
        patient_visits = Visit.query.filter_by(
            patient_id=current_visit.patient_id, 
            clinic_id=doctor.clinic_id
        ).all()
        
        visit_ids = [visit.id for visit in patient_visits]
        
        if not visit_ids:
            return jsonify([])
        
        # الحصول على جميع إجراءات المريض في هذه العيادة
        procedures = Procedure.query.filter(
            Procedure.visit_id.in_(visit_ids)
        ).order_by(Procedure.date_performed.desc()).all()  # ترتيب من الخادم
        
        procedure_list = []
        for proc in procedures:
            process = Process.query.get(proc.process_id)
            if process:
                procedure_list.append({
                    'id': proc.id,
                    'name': process.name_process,
                    'cost': proc.cost,
                    'status': proc.status,
                    'date': proc.date_performed.isoformat() if proc.date_performed else None,
                    'visit_date': proc.visit.visit_date.isoformat() if proc.visit.visit_date else None
                })
        
        return jsonify(procedure_list)
    except Exception as e:
        print(f"Error getting previous procedures: {e}")
        return jsonify([])
@apiBP.route('/update_procedure_status_batch', methods=['POST'])
def update_procedure_status_batch():
    try:
        # Get doctor_id from session instead of clinic_id
        doctor_id = session.get('doctor_id')
        if not doctor_id:
            return jsonify({"success": False, "error": "Doctor not logged in"})
        
        # Get doctor to access clinic_id
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found"})
        
        clinic_id = doctor.clinic_id
        
        payload = request.get_json() or {}
        updates = payload.get("updates", [])
        
        results = []
        for update in updates:
            procedure_id = update.get("procedure_id")
            status = update.get("status")
            
            if not procedure_id or not status:
                results.append({"procedure_id": procedure_id, "error": "Missing data"})
                continue
                
            procedure = Procedure.query.get(procedure_id)
            if not procedure:
                results.append({"procedure_id": procedure_id, "error": "Procedure not found"})
                continue
                
            # Verify doctor ownership through visit
            visit = Visit.query.get(procedure.visit_id)
            if not visit or visit.doctor_id != doctor_id:
                results.append({"procedure_id": procedure_id, "error": "Not authorized"})
                continue
                
            procedure.status = status
            if status == 'completed':
                procedure.date_performed = datetime.now()
                
                # Ensure invoice exists and recalculate
                invoice = create_or_get_invoice(procedure.visit_id, clinic_id)
                recalc_procedure(procedure)
                recalc_invoice(invoice)
                
            db.session.add(procedure)
            results.append({
                "procedure_id": procedure.id,
                "success": True,
                "status": procedure.status
            })
        
        db.session.commit()
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@apiBP.route('/update_procedure_status', methods=['POST'])
def update_procedure_status():
    try:
        data = request.get_json()
        procedure_id = data.get('procedure_id')
        status = data.get('status')
        
        procedure = Procedure.query.get(procedure_id)
        if not procedure:
            return jsonify({'success': False, 'error': 'الإجراء غير موجود'})
        
        # Get clinic_id from the procedure's visit
        visit = Visit.query.get(procedure.visit_id)
        if not visit:
            return jsonify({'success': False, 'error': 'الزيارة غير موجودة'})
        
        procedure.status = status
        if status == 'completed':
            procedure.date_performed = datetime.now()
            
            # Ensure invoice exists and recalculate it
            invoice = create_or_get_invoice(procedure.visit_id, visit.clinic_id)
            recalc_procedure(procedure)  # Recalculate final cost
            recalc_invoice(invoice)  # Recalculate invoice totals
            
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
