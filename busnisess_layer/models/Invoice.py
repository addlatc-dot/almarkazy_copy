from configDB.config import db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True , autoincrement=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Integer, default=0 )  # Discount percentage
    total_amount = db.Column(db.Integer, nullable=False)
    paid_amount = db.Column (db.Integer , nullable=True)
    status = db.Column(db.String(50), default='غير مدفوع')  # e.g., 'paid', 'unpaid'

