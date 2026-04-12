 
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from configDB.config import db 

class Clinics(db.Model):  
    clinic_id   = db.Column(db.Integer, primary_key=True  , autoincrement=True)
    Email = db.Column(db.String(255), nullable=False)
    name_clinic = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    phone_numbers = db.Column(db.String(200), nullable=False)
    addresses = db.Column(db.String(200), nullable=False)
    plan_id = db.Column(db.Integer , nullable=True)
    date_add = db.Column(db.DateTime, default=datetime.utcnow)
    sections = relationship("Section", back_populates="clinic")
