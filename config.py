"""
config.py
---------
Central place to keep configuration values for the Flask app.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration variables required by Flask."""

    # SECRET_KEY signs the session cookie (used for login sessions and
    # flash messages). In a real production deployment this should be a
    # long random string stored outside the source code.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'trekking-management-secret-key-2026')
