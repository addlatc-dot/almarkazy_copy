
from datetime import datetime
from sqlalchemy import func, and_, extract
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash , abort 

from functools import wraps



from configDB.config import  db
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit , Plan , Featurs , Featursplans 
)
def get_receptions(clinic_id):
    """
    Calculate revenue for a given month and doctor
    """
    revenue = Reception.query.filter(clinic_id==clinic_id).all()
    names = [r.name for r in revenue]

    return names

def doctor_revenue(    clinic_id , month):

    """ now shoud be calculate number of visit in month in clincic and multiply with price of doctor and take all 
    and multiply on percntage of doctor 
    
    now the doctor have a precentage of more process 
    """
    
 
    results = []
    doctors = Doctor.query.filter(Doctor.clinic_id == clinic_id).all()
    for doctor in doctors:
        processes = Process.query.filter(Process.clinic_id == clinic_id).all()
        for process in processes:
            # Count visits for this doctor, process, and month, excluding state 'ملغي'
            count = Visit.query.filter(
                Visit.clinic_id == clinic_id,
                Visit.doctor_id == doctor.id,
                Visit.process_id == process.id,
                extract('month', Visit.visit_date) == month,
                Visit.status != "ملغي"
            ).count()
            if count > 0:
                results.append({
                    "doctor_name": doctor.name,
                    "process_name": process.name_process,
                    "process_count": count,
                    "process_cost": process.fee_process,
                    "total_cost_porcess": count * process.fee_process,
                    "examination_fee": doctor.examination_fee,
                    "review_fee": doctor.review_fee 
                })
    return results

def get_current_user():
    user_id = session.get("user_id")
    user_type = session.get("user_type")

    if not user_id or not user_type:
        return None, None

    if user_type == "doctor":
        return Doctor.query.get(user_id), "doctor"
    elif user_type == "reception":
        return Reception.query.get(user_id), "reception"
    elif user_type == "clinic":
        return Clinics.query.get(user_id), "clinic"
    return None, None


from functools import wraps
from flask import abort, session

def require_feature(feature_code):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            clinic_id = session.get("clinic_id")
            clinic = Clinics.query.get(clinic_id)
            if not clinic:
                abort(401)  # Unauthorized

            feature = Featurs.query.filter_by(code=feature_code).first()
            if not feature:
                abort(403, description="الميزة غير متاحة في خطتك")
            
            allowed = Featursplans.query.filter_by(
                plan_id=clinic.plan_id,
                featur_id=feature.id,
                allowed=True
            ).first()

            if not allowed:
                abort(403, description="الميزة غير متاحة في خطتك")

            return fn(*args , **kwargs)
        return wrapped
    return decorator

def require_feature_and_role(feature_code, allowed_roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user, role = get_current_user()
            if not user:
                abort(401)  # Unauthorized

            clinic = Clinics.query.get(user.clinic_id)
            if not clinic:
                abort(401)

            # تحقق من الميزة
            feature = Featurs.query.filter_by(code=feature_code).first()
            allowed = Featursplans.query.filter_by(
                plan_id=clinic.plan_id,
                feature_id=feature.id,
                allowed=True
            ).first()

            if not allowed:
                abort(403, description="الميزة غير متاحة في خطتك")

            # تحقق من الدور
            if allowed_roles and role not in allowed_roles:
                abort(403, description="صلاحياتك لا تسمح بالعملية")

            return fn(*args, **kwargs)
        return wrapped
    return decorator

# with app.app_context():

#     print( doctor_revenue(39,7,6) )


    