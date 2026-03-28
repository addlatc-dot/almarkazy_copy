from configDB.config import db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(11), nullable=False)
    national_id = db.Column(db.Integer, nullable=True, unique=True)
    berth_date=db.Column(db.Date,nullable=False)
    age=db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(50), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date_seen = db.Column(db.DateTime, default=datetime.utcnow)
    date_visit = db.Column(db.Date, default=datetime.utcnow().date(),nullable=False)

    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    doctor = db.relationship('Doctor', backref='patients')
   # sections = db.relationship('Section', backref='patients')
    clinics_visited = db.Column(db.Text, nullable=True)  # List of visited clinics
   # name_section=db.relationship('Section',backref='patients')
    normalized_name = db.Column(db.String(255))  # Add this to your Patient model
    process_id = db.Column(db.Integer, db.ForeignKey('process.id'), nullable=True)
