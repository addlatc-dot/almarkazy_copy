import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
from sqlalchemy import func, and_, extract
from models.Reception import Reception
from models.Clinics import Clinics
from models.Reception import Reception
from busnisess_layer.models.Section import Section
from models.Doctor import Doctor
from models.Visit import Visit
from configDB.config import  db
from sqlalchemy.exc import SQLAlchemyError

def list_receptions(clinic_id): 
    try:
        receptions = Reception.query.filter_by(clinic_id=clinic_id).all()
        return receptions
    except SQLAlchemyError as e:
        print(f"Error fetching receptions: {e}")
        return None
    

def get_res(clinic_id):
    """
    Calculate revenue for a given month and doctor
    """
    revenue = Reception.query.filter(clinic_id==clinic_id).all()
    names = [r.name for r in revenue]

    return names

def calculate_revenue(clinic_id , doctor_id , month ):
    """
    Calculate revenue for a given month and doctor
    """
    clinic_id = clinic_id  # Retrieve the clinic ID from session
    month = month
    doctors = Doctor.query.filter(Doctor.clinic_id==clinic_id).all()
    visits_all = Visit.query.filter(Visit.clinic_id==clinic_id,Visit.visit_status =="مؤكد",Visit.status=="كشف",extract('month',Visit.visit_date)==month).all()

    sums =0
    report = []
    for doctor in doctors :     
        visits_count = Visit.query.filter(Visit.doctor_id == doctor.id,Visit.visit_status=="مؤكد" , Visit.status=="كشف",extract('month',Visit.visit_date)==month).count()
        fee = doctor.examination_fee * visits_count 
        sums +=fee
        report.append({"name_doctor":doctor.name , 
                    "total_visits":visits_count  ,
                    "fee":doctor.examination_fee ,
                    "revenue_per_doctor": fee})
    return report,sums

# with app.app_context():
    
#     print(calculate_revenue(6,49,6))

 