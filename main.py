"""
Main entry point for the Almarkazy Flask application.

This file is the primary entry point used by production servers (Gunicorn, Waitress, etc.)
and Railway deployments.
"""

from app import app

if __name__ == "__main__":
    app.run()
