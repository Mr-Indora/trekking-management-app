"""
utils.py
--------
Small reusable helper functions and DECORATORS used across the whole app.

WHAT IS A DECORATOR? (in case you get asked this in viva)
------------------------------------------------------------
A decorator is a function that "wraps" another function to add extra
behaviour WITHOUT changing the original function's code. Here we use
decorators to protect routes - e.g. `@login_required` checks if someone is
logged in BEFORE the actual page code runs, and if not, it redirects them
to the login page instead of showing the protected page.
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(view_func):
    """
    Use this decorator on any route that should ONLY be visible to a
    logged-in user (any role). Example:

        @app.route('/dashboard')
        @login_required
        def dashboard():
            ...
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        # We store 'user_id' in the Flask session dictionary at login time
        # (see routes/auth.py -> login()). If it's missing, nobody is
        # logged in, so we send them to the login page.
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    return wrapped


def role_required(required_role):
    """
    Use this decorator (with an argument!) on routes that should only be
    accessible by ONE specific role. Example:

        @app.route('/admin/dashboard')
        @login_required
        @role_required('admin')
        def admin_dashboard():
            ...

    Because this decorator itself needs an argument (the role name), it is
    written as a "decorator factory" - a function that RETURNS a decorator.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get('role') != required_role:
                flash('You are not authorized to view that page.', 'danger')
                return redirect(url_for('auth.login'))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
