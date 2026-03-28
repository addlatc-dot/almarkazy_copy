
from flask import jsonify, request, session, abort 
import re
from busnisess_layer.models import Process , Reception , Procedure , Payments , Invoice 
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from decimal import Decimal, ROUND_HALF_UP
from configDB.config import db
# helper to round money (optional)
def money(x):
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


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
def require_clinic():
    clinic_id = session.get("clinic_id")
    if not clinic_id:
        abort(401, description="Clinic not logged in")
    return clinic_id

def require_reception():
    reception_id = session.get('reception_id')
    if not reception_id:
        abort(401, description="reception not logged in")

    reception = Reception.query.get(reception_id)
    if not reception:
        abort(401, description="reception not found")

    return reception_id ,reception.clinic_id

def recalc_procedure(proc: Procedure):
    """Recalculate final_cost for a Procedure based on cost and discount (percentage)."""
    try:
        cost = Decimal(proc.cost or 0)
        discount_pct = Decimal(proc.discount or 0)
        final = cost - (cost * discount_pct / Decimal(100))
        proc.final_cost = int(final) if isinstance(proc.cost, int) and isinstance(proc.discount, int) else float(final)
    except Exception:
        proc.final_cost = proc.cost
    return proc.final_cost


def create_or_get_invoice(visit_id, clinic_id):
    """Ensure there is an invoice for the given visit, create if not exists."""
    invoice = Invoice.query.filter_by(visit_id=visit_id, clinic_id=clinic_id).first()
    if invoice is None:
        # Calculate initial amount from procedures
        procedures = Procedure.query.filter_by(visit_id=visit_id, status='completed').all()
        total_amount = sum(recalc_procedure(p) or 0 for p in procedures)
        
        invoice = Invoice(
            visit_id=visit_id,
            clinic_id=clinic_id,
            discount=0,
            amount=total_amount,
            total_amount=total_amount,
            status="غير مدفوع",
            paid_amount = 0 
        )
        db.session.add(invoice)
        db.session.commit()
    return invoice
def update_remaining_amounts(invoice_id):
    """Update remaining_amount for all payments of an invoice"""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return
    
    payments = Payments.query.filter_by(invoice_id=invoice_id).order_by(Payments.payment_date.asc()).all()
    total_paid = Decimal(0)
    
    for payment in payments:
        
        total_paid += Decimal(payment.paid_amount)
        remaining = Decimal(invoice.total_amount) - total_paid
        payment.remaining_amount = float(max(remaining, 0))
        db.session.add(payment)
    
    db.session.commit()


def recalc_invoice(invoice: Invoice):
    """Recalculate invoice amounts from procedures of its visit and invoice.discount."""
    # load procedures for visit
    procedures = Procedure.query.filter_by(visit_id=invoice.visit_id, status="completed").all()
    total_before = Decimal(0)
    for p in procedures:
        # ensure final_cost is correct
        final = Decimal(recalc_procedure(p) or 0)
        total_before += final

    inv_discount_pct = Decimal(invoice.discount or 0)
    total_after = total_before - (total_before * inv_discount_pct / Decimal(100))

    # save numeric fields consistently
    invoice.amount = float(total_before)  # sum of final_costs before visit-level discount
    invoice.total_amount = float(total_after)
    db.session.add(invoice)
    db.session.commit()
    
    # Update remaining amounts for all payments since invoice total changed
    update_remaining_amounts(invoice.id)
    
    return float(total_before), float(total_after)