from configDB.config import db

class Reception(db.Model):
    id=db.Column(db.Integer ,primary_key=True)
    name=db.Column(db.String(50),nullable=False)
    phone=db.Column(db.String(11),nullable=False)
    clinic_id=db.Column(db.Integer , db.ForeignKey('clinics.clinic_id'),nullable=False)
    email = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    clinic = db.relationship('Clinics', backref='receptions')

    # def __repr__(self):
    #     values = {c.name:getattr(self,c.name)for c in self.__table__.columns}
    #     return f"{values}"
    
