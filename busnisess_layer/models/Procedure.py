from configDB.config import db

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Procedure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey('process.id'), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'), nullable=False)
    cost = db.Column(db.Integer, nullable=False   )
    discount = db.Column(db.Integer, default=0)  # Discount percentage
    final_cost = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # e.g., 'pending', 'completed'
    date_performed = db.Column(db.DateTime, default=datetime.utcnow)


    visit = db.relationship('Visit', backref='procedures')
    process = db.relationship('Process', backref='procedures')
