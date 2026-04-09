 
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from configDB.config import db
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(11), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    current_patient = db.Column(db.Integer, nullable=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)  # Changed this to 'clinic_id'
    examination_fee =db.Column(db.Integer , nullable=False)
    review_fee = db.Column(db.Integer , nullable=False)
   # percentage = db.Column(db.Integer , nullable=False)

    # Consultation time tracking fields
    average_consultation_time = db.Column(db.Float, nullable=True, default=0)  # Average in seconds
    total_consultation_seconds = db.Column(db.Integer, nullable=True, default=0)  # Cumulative total
    consultation_count = db.Column(db.Integer, nullable=True, default=0)  # Number of valid intervals counted
    last_button_click_timestamp = db.Column(db.DateTime, nullable=True)  # Track last "Next Patient" click
    last_update_time = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)  # When average was last updated

