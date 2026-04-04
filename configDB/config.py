# from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
# from flask_sqlalchemy import SQLAlchemy
# # from flask_cors import CORS
 


# db =SQLAlchemy()
# db.init_app(app)
 
# def create_app():
#     app = Flask(__name__ , template_folder ="../testation/precentatioin_layer/templates")
#     app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/hospi'
#     app.config['SECRET_KEY'] = 'your_secret_key'
#     db.init_app(app)
#     return app


import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config:
    # Railway automatically sets DATABASE_URL when you add a MySQL plugin.
    # Falls back to local development credentials if not set.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://almarkazy:almarkazypass@localhost/hospi'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Railway: set SECRET_KEY as an environment variable (a long random string).
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
