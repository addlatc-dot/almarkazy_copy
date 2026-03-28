from flask import Flask
from configDB import config  
   # import db from config.py

def create_app():
    app = Flask(__name__, template_folder="./precentatioin_layer/templates")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://almarkazy:almarkazypass@10.1.0.5/hospi'
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config.from_object(config)

    # init extensions
    config.db.init_app(app)

    # Register Blueprints if you have
    # from .routes import main_bp
    # app.register_blueprint(main_bp)

    return app
app=create_app()
