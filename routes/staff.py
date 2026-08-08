"""
routes/staff.py
----------------
Routes usable ONLY by an approved Trek Staff account.

A staff member can:
    - See a dashboard summarising the treks assigned to them by Admin
    - Open one of their assigned treks to:
        * update available slots / status (Open / Closed)
        * view the list of participants (users) who booked that trek
        * mark the trek as "Ongoing" (started) or "Completed"
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from db import query_db, execute_db
from utils import login_required, role_required

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


def _get_own_trek_or_404(trek_id):
    """
    Security helper: fetches a trek ONLY if it is assigned to the
    currently logged-in staff member. This stops one staff member from
    viewing/editing a trek belonging to a different staff member simply by
    guessing a URL like /staff/treks/5.
    """
    trek = query_db('SELECT * FROM treks WHERE id = ?', (trek_id,), one=True)
    if trek is None:
        abort(404)
    if trek['assigned_staff_id'] != session['user_id']:
        abort(403)  # 403 = Forbidden
    return trek


@staff_bp.route('/dashboard')
@login_required
@role_required('staff')
def dashboard():
    """Staff landing page - summary cards + table of assigned treks."""
    my_treks = query_db(
        'SELECT * FROM treks WHERE assigned_staff_id = ? ORDER BY id DESC',
        (session['user_id'],),
    )

    total_participants = 0
    open_treks_count = 0
    # We attach a `participant_count` value onto each trek row (as a plain
    # dict) so the dashboard table can show it without extra template logic.
    treks_with_counts = []
    for trek in my_treks:
        trek_dict = dict(trek)
        count = query_db(
            "SELECT COUNT(*) AS c FROM bookings WHERE trek_id = ? AND status = 'Booked'",
            (trek['id'],),
            one=True,
        )['c']
        trek_dict['participant_count'] = count
        total_participants += count
        if trek['status'] == 'Open':
            open_treks_count += 1
        treks_with_counts.append(trek_dict)

    return render_template(
        'staff/dashboard.html',
        my_treks=treks_with_counts,
        total_participants=total_participants,
        open_treks_count=open_treks_count,
    )


@staff_bp.route('/treks/<int:trek_id>')
@login_required
@role_required('staff')
def manage_trek(trek_id):
    """Shows full details of one assigned trek + its list of participants."""
    trek = _get_own_trek_or_404(trek_id)
    # We only show 'Booked' participants (not cancelled ones) since that's
    # the actively confirmed participant list for the trip.
    participants = query_db(
        """SELECT b.id, b.booking_date, b.status,
                  u.name AS user_name, u.email AS user_email
           FROM bookings b
           JOIN users u ON b.user_id = u.id
           WHERE b.trek_id = ? AND b.status = 'Booked'
           ORDER BY b.booking_date""",
        (trek_id,),
    )
    return render_template('staff/trek_manage.html', trek=trek, participants=participants)


@staff_bp.route('/treks/<int:trek_id>/update', methods=['POST'])
@login_required
@role_required('staff')
def update_trek(trek_id):
    """
    Staff updates available slots and status, as required by the problem
    statement ("Can update trek details such as: Available slots, Trek
    status").
    """
    trek = _get_own_trek_or_404(trek_id)

    new_available_slots = int(request.form.get('available_slots'))
    # Never allow available_slots to exceed total_slots or go negative -
    # this keeps the booking count consistent no matter what staff types.
    new_available_slots = max(0, min(new_available_slots, trek['total_slots']))
    new_status = request.form.get('status')

    execute_db(
        'UPDATE treks SET available_slots = ?, status = ? WHERE id = ?',
        (new_available_slots, new_status, trek_id),
    )
    flash('Trek details updated.', 'success')
    return redirect(url_for('staff.manage_trek', trek_id=trek_id))


@staff_bp.route('/treks/<int:trek_id>/mark-started', methods=['POST'])
@login_required
@role_required('staff')
def mark_started(trek_id):
    """Staff marks a trek as currently in-progress."""
    trek = _get_own_trek_or_404(trek_id)
    execute_db("UPDATE treks SET status = 'Ongoing' WHERE id = ?", (trek_id,))
    flash(f"Trek \"{trek['name']}\" marked as Ongoing.", 'success')
    return redirect(url_for('staff.manage_trek', trek_id=trek_id))


@staff_bp.route('/treks/<int:trek_id>/mark-completed', methods=['POST'])
@login_required
@role_required('staff')
def mark_completed(trek_id):
    """
    Staff marks a trek as completed once the trip is over. We also mark
    every 'Booked' participant's booking as 'Completed' so the user's
    "Trekking History" page (routes/user.py -> history()) shows it correctly.
    """
    trek = _get_own_trek_or_404(trek_id)
    execute_db("UPDATE treks SET status = 'Completed' WHERE id = ?", (trek_id,))
    execute_db(
        "UPDATE bookings SET status = 'Completed' WHERE trek_id = ? AND status = 'Booked'",
        (trek_id,),
    )
    flash(f"Trek \"{trek['name']}\" marked as Completed.", 'success')
    return redirect(url_for('staff.manage_trek', trek_id=trek_id))


@staff_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def profile():
    """Lets a staff member update their own name/contact details."""
    if request.method == 'POST':
        name = request.form.get('name').strip()
        contact = request.form.get('contact', '').strip()
        execute_db('UPDATE users SET name = ?, contact = ? WHERE id = ?', (name, contact, session['user_id']))
        session['name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('staff.profile'))

    account = query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    return render_template('staff/profile.html', account=account)
