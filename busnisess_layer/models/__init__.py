# from .Clinics import Clinics
# from .Reception import Reception  
# from .Doctor import Doctor
# from .Patient import Patient
# from .Section import Section
# from .Process import Process
# from .Procedure import Procedure
# from .Percentages import Percentages
# from .Payments import Payments
# from .Invoice import Invoice
# from .Bills import Bills

# from flask import Flask 
# from configDB.config import db ,Config

# def create_app():
#     app = Flask(__name__)
#     # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/hospi' 
#     app.config['SQLALCHEMY_DATABASE_URI'] =  Config.SQLALCHEMY_DATABASE_URI

#     app.config['SECRET_KEY'] = Config.SECRET_KEY
#     db.init_app(app)
#     return app
from flask_sqlalchemy import SQLAlchemy

from configDB.config import db

from .Clinics import Clinics
from .Section import Section
from .Doctor import Doctor
from .Process import Process
from .Patient import Patient
from .Visit import Visit
from .Procedure import Procedure
from .Percentages import Percentages
from .Payments import Payments
from .Invoice import Invoice
from .Bills import Bills
from .Reception import Reception
from .Featurs import Featurs
from .Featursplans import Featursplans
from .Plan import Plan 
