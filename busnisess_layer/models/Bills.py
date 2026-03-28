# from flask_sqlalchemy import SQLAlchemy
# db = SQLAlchemy()
# from sqlalchemy import Column, Integer, String, DateTime
# from sqlalchemy.orm import relationship
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from configDB.config  import   db 
class Bills(db.Model):
   
    id = db.Column(db.Integer, primary_key=True , autoincrement=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_issued = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='غير مدفوع')  # e.g., 'paid', 'unpaid'
    description = db.Column(db.String(400), nullable=True)
    bill_section = db.Column(db.String(50), nullable=True) 
    def to_dict(self):
        return {
            'id': self.id,
            'clinic_id': self.clinic_id,
            'name': self.name,
            'amount': self.amount,
            'date_issued': self.date_issued.strftime('%Y-%m-%d'),
            'status': self.status,
            'description': self.description,
            'bill_section': self.bill_section
        }