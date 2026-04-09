from configDB.config import db
from datetime import datetime

class ConsultationTime(db.Model):
    """
    Model to store individual consultation time records for each doctor.
    
    Each record represents a time interval between two "Next Patient" button clicks.
    Only valid intervals (>= 60 seconds) are stored in this table.
    """
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.clinic_id'), nullable=False)
    
    # Timestamp when "Next Patient" button was clicked
    click_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # The consultation time (in seconds) - time between this click and previous click
    consultation_seconds = db.Column(db.Integer, nullable=False)
    
    # Visit IDs involved (optional, for reference/debugging)
    previous_visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'), nullable=True)
    current_visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'), nullable=True)
    
    # Date of the consultation (for daily stats)
    date_recorded = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('Doctor', backref='consultation_times', lazy='joined')
    clinic = db.relationship('Clinics', backref='consultation_times', lazy='joined')
    previous_visit = db.relationship('Visit', foreign_keys=[previous_visit_id])
    current_visit = db.relationship('Visit', foreign_keys=[current_visit_id])
    
    def __repr__(self):
        return f'<ConsultationTime doctor_id={self.doctor_id} seconds={self.consultation_seconds}>'
