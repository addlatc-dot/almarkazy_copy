web: python setup_railway_db.py && python verify_db_schema.py && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8080} --timeout 120 main:app
