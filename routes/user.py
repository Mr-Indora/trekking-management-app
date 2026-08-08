"""
routes/user.py
---------------
Routes usable ONLY by an approved Trekker (User) account.

A trekker can:
    - Browse & search/filter treks that are currently 'Open'
    - View a single trek's details and book a slot on it
    - View their current bookings and cancel one if needed
    - View their trekking history (completed treks)
    - Edit their own profile
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from db import query_db, execute_db
from utils import login_required, role_required

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/dashboard')
@login_required
@role_required('user')
def dashboard():
    """
    Trekker dashboard: shows treks that are open for booking (with
    optional difficulty/location filters) plus a short list of the
    trekker's own recent bookings, matching the wireframe layout.
    """
    difficulty_filter = request.args.get('difficulty', 'All')
    location_filter = request.args.get('location', 'All')

    sql = "SELECT * FROM treks WHERE status = 'Open'"
    params = []
    if difficulty_filter != 'All':
        sql += ' AND difficulty = ?'
        params.append(difficulty_filter)
    if location_filter != 'All':
        sql += ' AND location = ?'
        params.append(location_filter)
    sql += ' ORDER BY start_date ASC'

    available_treks = query_db(sql, tuple(params))

    # Used to populate the location filter dropdown dynamically instead of
    # hard-coding location names in the template.
    all_locations = [row['location'] for row in query_db('SELECT DISTINCT location FROM treks ORDER BY location')]

    my_bookings = query_db(
        """SELECT b.id, b.booking_date, b.status,
                  t.id AS trek_id, t.name AS trek_name
           FROM bookings b
           JOIN treks t ON b.trek_id = t.id
           WHERE b.user_id = ?
           ORDER BY b.booking_date DESC
           LIMIT 5""",
        (session['user_id'],),
    )

    cancel_booking = request.args.get('cancel_booking')
    if cancel_booking:
        flash('Booking cancelled.', 'info')
        

    return render_template(
        'user/dashboard.html',
        treks=available_treks,
        my_bookings=my_bookings,
        difficulty_filter=difficulty_filter,
        location_filter=location_filter,
        all_locations=all_locations,
    )


@user_bp.route('/treks/<int:trek_id>')
@login_required
@role_required('user')
def trek_details(trek_id):
    """Shows full details of a single trek with a 'Book Now' button."""
    trek = query_db('SELECT * FROM treks WHERE id = ?', (trek_id,), one=True)
    if trek is None:
        abort(404)
    # Check if the current user already has an active booking for this
    # trek (so we can disable the Book button in the template).
    already_booked = query_db(
        "SELECT id FROM bookings WHERE user_id = ? AND trek_id = ? AND status = 'Booked'",
        (session['user_id'], trek_id),
        one=True,
    )
    return render_template('user/trek_details.html', trek=trek, already_booked=already_booked)


@user_bp.route('/treks/<int:trek_id>/book', methods=['POST'])
@login_required
@role_required('user')
def book_trek(trek_id):
    """
    Creates a booking for the current user.

    THREE business rules are enforced here (all required by the problem
    statement's "Other Core Functionalities" section):
        1. "Allow users to book only if trek status is Open"
        2. "Prevent overbooking beyond available slots"
        3. A user cannot book the SAME trek twice while already booked.
    """
    trek = query_db('SELECT * FROM treks WHERE id = ?', (trek_id,), one=True)
    if trek is None:
        abort(404)

    if trek['status'] != 'Open':
        flash('This trek is not currently open for booking.', 'danger')
        return redirect(url_for('user.trek_details', trek_id=trek_id))

    if trek['available_slots'] <= 0:
        flash('Sorry, this trek is fully booked (no slots available).', 'danger')
        return redirect(url_for('user.trek_details', trek_id=trek_id))

    existing_booking = query_db(
        "SELECT id FROM bookings WHERE user_id = ? AND trek_id = ? AND status = 'Booked'",
        (session['user_id'], trek_id),
        one=True,
    )
    if existing_booking:
        flash('You have already booked this trek.', 'warning')
        return redirect(url_for('user.trek_details', trek_id=trek_id))

    # Insert the new booking...
    execute_db(
        "INSERT INTO bookings (user_id, trek_id, booking_date, status) VALUES (?, ?, ?, 'Booked')",
        (session['user_id'], trek_id, datetime.utcnow().isoformat()),
    )
    # ...and reduce the slot count immediately so the very next visitor
    # sees the updated number. This is how overbooking is prevented.
    execute_db('UPDATE treks SET available_slots = available_slots - 1 WHERE id = ?', (trek_id,))

    flash(f"Trek \"{trek['name']}\" booked successfully!", 'success')
    return redirect(url_for('user.my_bookings'))


@user_bp.route('/bookings')
@login_required
@role_required('user')
def my_bookings():
    """Lists every booking (Booked/Cancelled/Completed) made by this user."""
    bookings = query_db(
        """SELECT b.id, b.booking_date, b.status,
                  t.id AS trek_id, t.name AS trek_name, t.start_date, t.end_date
           FROM bookings b
           JOIN treks t ON b.trek_id = t.id
           WHERE b.user_id = ?
           ORDER BY b.booking_date DESC""",
        (session['user_id'],),
    )
    return render_template('user/bookings.html', bookings=bookings)


@user_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@role_required('user')
def cancel_booking(booking_id):
    """
    Lets a user cancel one of their own 'Booked' bookings. The slot is
    given back to the trek so someone else can book it.
    """
    booking = query_db('SELECT * FROM bookings WHERE id = ?', (booking_id,), one=True)
    if booking is None:
        abort(404)

    # Security check: a user must only be able to cancel THEIR OWN booking.
    if booking['user_id'] != session['user_id']:
        flash('You cannot cancel a booking that is not yours.', 'danger')
        return redirect(url_for('user.my_bookings'))

    if booking['status'] != 'Booked':
        flash('Only an active booking can be cancelled.', 'warning')
        return redirect(url_for('user.my_bookings'))

    execute_db("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
    execute_db(
        'UPDATE treks SET available_slots = available_slots + 1 WHERE id = ?',
        (booking['trek_id'],),
    )
    flash('Booking cancelled.', 'info')
    return redirect(url_for('user.my_bookings'))


@user_bp.route('/history')
@login_required
@role_required('user')
def history():
    """Shows only 'Completed' bookings - the user's trekking history."""
    completed_bookings = query_db(
        """SELECT b.id, b.booking_date, b.status,
                  t.id AS trek_id, t.name AS trek_name, t.start_date, t.end_date
           FROM bookings b
           JOIN treks t ON b.trek_id = t.id
           WHERE b.user_id = ? AND b.status = 'Completed'
           ORDER BY b.booking_date DESC""",
        (session['user_id'],),
    )
    return render_template('user/history.html', bookings=completed_bookings)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('user')
def profile():
    """Lets a trekker edit their own name/contact information."""
    if request.method == 'POST':
        name = request.form.get('name').strip()
        contact = request.form.get('contact', '').strip()
        execute_db('UPDATE users SET name = ?, contact = ? WHERE id = ?', (name, contact, session['user_id']))
        session['name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.profile'))

    account = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    return render_template('user/profile.html', account=account)
