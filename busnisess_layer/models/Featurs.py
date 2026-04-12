 
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from configDB.config import db 

class Featurs(db.Model):
    id = db.Column(db.Integer , primary_key = True , autoincrement=True)
    code= db.Column(db.String(70)  , nullable=False )
    discreption = db.Column(db.String(100), nullable = True)