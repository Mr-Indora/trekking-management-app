"""
routes/auth.py
---------------
Everything related to LOGGING IN, LOGGING OUT and REGISTERING new accounts.

We use a Flask "Blueprint" (auth_bp) to group all authentication-related
routes together instead of dumping every route into one giant app.py file.
Each route below talks to the database using the helper functions defined
in db.py (query_db for SELECT, execute_db for INSERT/UPDATE/DELETE).
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """
    The very first page a visitor sees. If already logged in, send them to
    their role-specific dashboard; otherwise send them to the login page.
    """
    if 'user_id' in session:
        return redirect(url_for(f"{session['role']}.dashboard"))
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration page for Trek Staff and Users (Trekkers) ONLY.
    The Admin account is NOT created here - as per the problem statement,
    "Admin must pre-exist in the database (no admin registration)". The
    admin account is instead auto-created on first app startup
    (see db.py -> seed_admin()).
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        contact = request.form.get('contact', '').strip()
        role = request.form.get('role')  # 'staff' or 'user' only

        # ---- Basic server-side validation ----
        if role not in ('staff', 'user'):
            flash('Please select a valid role.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        existing = query_db('SELECT id FROM users WHERE email = ?', (email,), one=True)
        if existing:
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        # Trek Staff must be approved by Admin before they can log in.
        # Trekkers (users) can use the app immediately after registering.
        initial_status = 'pending' if role == 'staff' else 'approved'

        execute_db(
            """INSERT INTO users (name, email, password_hash, role, contact, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                email,
                generate_password_hash(password),  # hash - never store plain text
                role,
                contact,
                initial_status,
                datetime.utcnow().isoformat(),
            ),
        )

        if role == 'staff':
            flash('Registration successful! Please wait for Admin approval before logging in.', 'info')
        else:
            flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    A SINGLE login form is used for all three roles (Admin, Staff, User).
    After checking the email/password, we read the account's `role` column
    to decide which dashboard to redirect the person to.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        account = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)

        # check_password_hash() compares the typed password against the
        # stored hash - we never compare plain-text passwords directly.
        if not account or not check_password_hash(account['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        if account['status'] == 'blacklisted':
            flash('Your account has been blacklisted by the Admin. Contact support.', 'danger')
            return redirect(url_for('auth.login'))

        if account['role'] == 'staff' and account['status'] == 'pending':
            flash('Your staff account is awaiting Admin approval.', 'warning')
            return redirect(url_for('auth.login'))

        # ---- Login successful: save identity in the session cookie ----
        # Flask's `session` is a secure, signed cookie - it cannot be
        # tampered with by the user without invalidating its signature.
        session['user_id'] = account['id']
        session['name'] = account['name']
        session['role'] = account['role']

        flash(f"Welcome back, {account['name']}!", 'success')
        return redirect(url_for(f"{account['role']}.dashboard"))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Clears the session, effectively logging the person out."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
