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


from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://almarkazy:almarkazypass@localhost/hospi'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your_secret_key'
