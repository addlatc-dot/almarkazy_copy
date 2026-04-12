from configDB.config import db 

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_section = db.Column(db.String(50), nullable=False )
    doctors = db.relationship('Doctor', backref='section', lazy=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    clinic = relationship("Clinics", back_populates="sections")
