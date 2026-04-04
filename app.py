from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy import or_ , func ,and_ , extract
from sqlalchemy.orm import joinedload , relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, logout_user, login_required
from sqlalchemy.exc import IntegrityError
from datetime import datetime , date,timedelta
import os

from decimal import Decimal, ROUND_HALF_UP
from configDB import config 
from configDB.config import db, Config
from flask_socketio import SocketIO
from flask_sse import sse


def create_app():
    app = Flask(__name__ , template_folder="./precentatioin_layer/templates", static_folder="./precentatioin_layer/static")
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/hospi' 
    app.config['SQLALCHEMY_DATABASE_URI'] =  Config.SQLALCHEMY_DATABASE_URI
    
    # Configure Redis URL - use environment variable with fallback to localhost for development
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    app.config["REDIS_URL"] = redis_url
    
    app.register_blueprint(sse, url_prefix="/stream")
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    db.init_app(app)
    from precentatioin_layer.routes import clinicBP ,  receptionBP ,apiBP , doctorBP ,patientBP
    app.register_blueprint(clinicBP)
    app.register_blueprint(apiBP)
    app.register_blueprint(doctorBP)
    app.register_blueprint(patientBP)
    app.register_blueprint(receptionBP)


    
    return app
app = create_app()
from flask_cors import CORS

CORS(app)
 
from  busnisess_layer.functions.calculations import *
from busnisess_layer.models import (
    Clinics, Reception, Patient, Procedure, Process, 
    Doctor, Bills, Section, Percentages, Invoice , Visit , Plan , Featurs , Featursplans 
)

 
login_manager = LoginManager(app)
login_manager.login_view = 'assistant_login'  # The login page route

# Flask-Login User Loader
@login_manager.user_loader
def load_user(doctor_id):
    
    
    return Doctor.query.get(int(doctor_id))


# Error handlers for AJAX requests
@app.errorhandler(403)
def handle_forbidden(error):
    """Handle 403 Forbidden errors - return JSON for AJAX requests"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False, 
            'error': error.description or 'الميزة غير متاحة في خطتك'
        }), 403
    # For non-AJAX requests, show as notification and redirect
    flash(error.description or 'الميزة غير متاحة في خطتك', 'danger')
    return redirect(request.referrer or url_for('home'))


@app.errorhandler(401)
def handle_unauthorized(error):
    """Handle 401 Unauthorized errors - return JSON for AJAX requests"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False, 
            'error': 'غير مصرح - يرجى تسجيل الدخول'
        }), 401
    return redirect(url_for('clinic_login')), 401


# Route for the main home page
@app.route('/')
def home():
        return render_template('home.html')  # Render the home page with buttons

# Clinic login route (Redirect to clinic login page)
@app.route('/clinic_login', methods=['GET', 'POST'])
def clinic_login():
    if request.method == 'POST':
        email = request.form['Email']
        password = request.form['password']

        clinic = Clinics.query.filter_by(Email=email).first()
        doctor = Doctor.query.filter_by(username=email).first()
        reception=Reception.query.filter_by(email=email).first()
        
        # if clinic and clinic.password == password:
        #     session['clinic_id'] = clinic.clinic_id
        #     flash('Login successful!', 'success')
        #     return redirect(url_for('clinicBP.clinic_management'))
        # elif doctor and doctor.password==password :
        #     session['doctor_id'] = doctor.id
        #     flash('login doctor successful','success')
        #     return redirect(url_for('doctorBP.doctor_home'))
        # elif reception and reception.password == password :
        #     session['reception_id'] = reception.id
        #     flash('login reception successful','success')
        #     return redirect(url_for('receptionBP.reception_home'))
        
        if clinic and clinic.password == password:
            session['user_id'] = clinic.clinic_id
            session['user_type'] = "clinic"
            session['clinic_id'] = clinic.clinic_id
            flash('Login successful!', 'success')
            return redirect(url_for('clinicBP.clinic_management'))

        elif doctor and doctor.password == password:
            session['user_id'] = doctor.id
            session['doctor_id'] = doctor.id
            session['user_type'] = "doctor"
            session['clinic_id'] = doctor.clinic_id
            flash('Login doctor successful', 'success')
            return redirect(url_for('doctorBP.doctor_home'))

        elif reception and reception.password == password:
            session['user_id'] = reception.id
            session['reception_id'] = reception.id
            session['user_type'] = "reception"
            session['clinic_id'] = reception.clinic_id
            flash('Login reception successful', 'success')
            return redirect(url_for('receptionBP.reception_home'))

        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('clinic_login.html')
 

 


# @app.route('/add_bills', methods=['POST'])
# def add_bills():
#     try:
#         bills_data = request.get_json()  # نستقبل JSON من الـ AJAX
#         clinic_id = bills_data.get("clinic_id")

#         for bill in bills_data.get("bills", []):
#             new_bill = bills(
#                 clinic_id=clinic_id,
#                 name=bill.get("name"),
#                 amount=float(bill.get("amount")),
#                 date_issued=datetime.strptime(bill.get("date_issued"), "%Y-%m-%d") if bill.get("date_issued") else datetime.utcnow(),
#                 status=bill.get("status", "غير مدفوع"),
#                 discription=bill.get("discription")
#             )
#             db.session.add(new_bill)

#         db.session.commit()
#         return jsonify({"success": True, "message": "تم حفظ جميع الفواتير بنجاح"})

#     except Exception as e:
#  

# @app.route('/clinic_revenue')

# def clinic_revenue():
#     clinic_id = session.get('clinic_id')  # Retrieve the clinic ID from session
#     month = request.args.get('month', default=datetime.now().month, type=int)
#     doctors = Doctor.query.filter(Doctor.clinic_id==clinic_id).all()
#     visits_all = Visit.query.filter(Visit.clinic_id==clinic_id,Visit.visit_status =="مؤكد",Visit.status=="كشف",extract('month',Visit.visit_date)==month).all()

#     sums =0
#     report = []
#     for doctor in doctors :     
#         visits_count = Visit.query.filter(Visit.doctor_id == doctor.id,Visit.visit_status=="مؤكد" , Visit.status=="كشف",extract('month',Visit.visit_date)==month).count()
#         fee = doctor.examination_fee * visits_count 
#         reveue_fee = doctor.review_fee * visits_count
#         sums +=fee
#         report.append({"name_doctor":doctor.name , 
#                     "total_visits":visits_count  ,
#                     "total_revue":reveue_fee ,
#                     "fee":doctor.examination_fee ,

#                     "revenue_per_doctor": reveue_fee+fee})
     
    
    
#     return render_template('clinic_management.html',
                       
#                         visit_report=report,
#                         total_revenue=sums,
                      
#                         )
# @app.route('/clinic_report', methods=['GET', 'POST'])
# def clinic_report():
#     clinic_id = session.get('clinic_id')
#     month = request.args.get('month', default=datetime.now().month, type=int)
#     sums =0
#     report = []
#     doctors = Doctor.query.filter(Doctor.clinic_id == clinic_id).all()
#     for doctor in doctors:
#         processes = Process.query.filter(Process.clinic_id == clinic_id).all()
#         for process in processes:
#             # Count visits for this doctor, process, and month, excluding state 'ملغي'
#             count = Visit.query.filter(
#                 Visit.clinic_id == clinic_id,
#                 Visit.doctor_id == doctor.id,
#                 Visit.process_id == process.id,
#                 extract('month', Visit.visit_date) == month,
#                 Visit.status != "ملغي"
#             ).count()
#             if count > 0:
#                 report.append({
#                     "doctor_name": doctor.name,
#                     "process_name": process.name_process,
#                     "process_count": count,
#                     "process_cost": process.fee_process,
#                     "total_cost_process": count * process.fee_process,
#                     "examination_fee": doctor.examination_fee,
#                     "review_fee": doctor.review_fee 
#                 })
#                 sums += count * process.fee_process
#     return render_template('clinic_management.html' ,process_report=report , sums=sums)

@app.route('/clinic_logout')
def clinic_logout():
    session.pop('clinic_id', None)
    session.pop('doctor_id',None) 
    return redirect(url_for('clinic_login'))

 


from flask import flash, redirect, request, url_for, render_template, session
from sqlalchemy import or_


# Fetch doctors based on the section (Updated to use section id)
@app.route('/get_doctors/<section_id>')
def get_doctors(section_id):
    doctors = Doctor.query.filter_by(section_id=section_id).all()
    doctors_list = [{'id': doctor.id, 'name': doctor.name} for doctor in doctors]
    return jsonify(doctors_list)
# Routes for Assistant Doctor
from flask import redirect, url_for
def calculate_visits(visits, days=30):  # Default to last 30 days
    """Calculates total visits within a given timeframe."""
    today = date.today()
    start_date = today - timedelta(days=days)  # Calculate start date

    total_visits = 0
    for visit_date_str, count in visits.items():
        try:
            visit_date = datetime.datetime.strptime(visit_date_str, "%Y-%m-%d").date() # Parse the date
            if start_date <= visit_date <= today:
                total_visits += count
        except ValueError:
            print(f"Invalid date format: {visit_date_str}") # Handle invalid date formats

    return total_visits


def calculate_visits_last_month(visits):
    """Calculates total visits in the last full month."""
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)
    last_day_of_last_month = first_day_of_month - timedelta(days=1) # Last day of previous month
    first_day_of_last_month = date(last_day_of_last_month.year, last_day_of_last_month.month, 1) # First day of previous month

    total_visits = 0
    for visit_date_str, count in visits.items():
        try:
            visit_date = datetime.datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            if first_day_of_last_month <= visit_date <= last_day_of_last_month:
                total_visits += count
        except ValueError:
            print(f"Invalid date format: {visit_date_str}")

    return total_visits

#@app.route('/get_processes/<int:section_id>')
#def get_processes(section_id):
    #processes = Process.query.filter_by(section_id=section_id).all()
   # return jsonify([{'id': p.id, 'name': p.name_process} for p in processes])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('clinic_login'))
 
if __name__ == '__main__':
    app.run(debug=True  ,host = '0.0.0.0'  ,  port = 5000)



