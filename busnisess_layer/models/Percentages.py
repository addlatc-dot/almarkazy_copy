from configDB.config import db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Percentages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey('process.id'), nullable=False)
    percentage = db.Column(db.Float, default=0)

    
    # Relationships
    doctor = db.relationship('Doctor', backref=db.backref('percentages', lazy=True))
    process = db.relationship('Process', backref=db.backref('percentages', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('doctor_id', 'process_id', name='_doctor_process_uc'),)
