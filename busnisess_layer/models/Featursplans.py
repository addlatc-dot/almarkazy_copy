 
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from configDB.config import db 

class Featursplans(db.Model):
    id = db.Column(db.Integer, primary_key=True , autoincrement=True)
    plan_id = db.Column(db.Integer , db.ForeignKey('plan.id'))
    featur_id = db.Column(db.Integer , db.ForeignKey('featurs.id'))
    allowed=db.Column(db.Boolean , nullable=False )
 