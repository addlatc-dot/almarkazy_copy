from configDB.config import db

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Process(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_process = db.Column(db.String(50), nullable=False )
    fee_process = db.Column(db.Integer , nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    #dcotor_precentage = db.Column(db.Integer, nullable=False , foreign_key='doctor.percentage')
    section = db.relationship('Section', backref='processes')
    clinic = db.relationship('Clinics', backref='processes')

