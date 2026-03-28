from configDB.config import db
# from sqlalchemy import Column, Integer, String, DateTime
# from sqlalchemy.orm import relationship
from datetime import datetime


class Payments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
    id_clinic = db.Column(db.Integer , db.ForeignKey('clinics.clinic_id' ), nullable=False)
    visit_id = db.Column(db.Integer , db.ForeignKey('visit.id'), nullable=False)
    paid_amount = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer , nullable=False)
    method = db.Column(db.String(50), nullable=True ,default ="كاش")
    remaining_amount = db.Column(db.Integer , nullable = False)
    
    
 
    invoice = db.relationship('Invoice', backref='payments')