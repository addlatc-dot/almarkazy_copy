from configDB.config import db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(11), nullable=False, index=True)
    national_id = db.Column(db.String(14), nullable=True, unique=True)
    berth_date=db.Column(db.SmallInteger,nullable=True, index=True)
    age=db.Column(db.Integer, nullable=False, index=True)
    gender = db.Column(db.String(10), nullable=False, index=True)
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
