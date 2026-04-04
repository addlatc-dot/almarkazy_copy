from configDB.config import db

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    patient_name = db.Column(db.String(100),db.ForeignKey('patient.name'),nullable=False)
    normalized_name = db.Column(db.String(255))  # Add this to your Patient model
    berth_date=db.Column(db.Date,db.ForeignKey('patient.berth_date'),nullable=False)
    age=db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50),db.ForeignKey('patient.status'), nullable=False)
    national_id= db.Column(db.Integer,db.ForeignKey('patient.national_id'),nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)  # Add this for clinic tracking
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    date_visit = db.Column(db.Date, nullable=True)
    visit_status = db.Column(db.String(50), default="مؤكد")  # New column for status ('ongoing', 'delayed', 'completed')
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    patient_phone= db.Column(db.String(11),db.ForeignKey('patient.phone'),nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey('process.id'), nullable=True)
    percentage = db.Column(db.Integer , default = 0 )
    queue_position = db.Column(db.Integer, nullable=True)  # Original queue position - set once, never changed

    # Relationships
    
    doctor = db.relationship('Doctor', backref='visits', lazy='joined')
    section = db.relationship('Section', backref='visits', lazy='joined')
