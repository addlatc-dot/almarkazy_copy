"""
WSGI entry point for Gunicorn in production

This file provides a clean entry point for production servers.
Railway and other deployment platforms use this to run the Flask app.
"""

from app import app

if __name__ == "__main__":
    app.run()
