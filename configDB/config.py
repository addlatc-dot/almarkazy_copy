import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config:
    # Handle both situations:
    # 1. If DATABASE_URL is set (either by Railway or manually)
    # 2. If Railway MySQL provides individual variables
    
    if os.environ.get('DATABASE_URL'):
        _db_url = os.environ.get('DATABASE_URL')
        # Convert mysql:// to mysql+pymysql:// if needed
        if _db_url.startswith('mysql://'):
            _db_url = 'mysql+pymysql://' + _db_url[len('mysql://'):]
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # Railway MySQL provides these individual variables
        mysql_user = os.environ.get('MYSQLUSER', 'almarkazy')
        mysql_password = os.environ.get('MYSQLPASSWORD', 'almarkazypass')
        mysql_host = os.environ.get('MYSQLHOST', 'localhost')
        mysql_port = os.environ.get('MYSQLPORT', '3306')
        mysql_database = os.environ.get('MYSQL_DATABASE', 'hospi')
        
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Railway: set SECRET_KEY as an environment variable (a long random string).
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
