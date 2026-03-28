 
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from configDB.config import db 

class Plan(db.Model):
    id = db.Column(db.Integer , primary_key=True )
    name = db.Column(db.String(50) , nullable=False)
    active=db.Column(db.Boolean , nullable=False)