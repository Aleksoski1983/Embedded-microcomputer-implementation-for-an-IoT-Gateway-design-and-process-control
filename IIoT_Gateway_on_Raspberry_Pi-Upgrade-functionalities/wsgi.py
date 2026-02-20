"""
WSGI entry point for production deployment with Gunicorn
Usage: gunicorn --workers 2 --bind 0.0.0.0:5000 wsgi:app
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app)
