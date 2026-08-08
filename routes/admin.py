"""
routes/admin.py
----------------
All routes that only the ADMIN role is allowed to use:
    - Dashboard with statistics
    - Add / Edit / Delete treks
    - Approve / Reject / Blacklist Trek Staff
    - View & blacklist Users
    - View all bookings
    - Search treks / staff / users by name or ID

Every route below is protected with:
    @login_required         -> must be logged in
    @role_required('admin') -> AND the logged-in account's role must be admin
So a Staff or User account trying to open these URLs directly is
automatically redirected away - this is our Role-Based Access Control.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db, execute_db
from utils import login_required, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _get_trek_or_404(trek_id):
    """Fetches one trek row by id, or aborts with a 404 (Not Found) page."""
    trek = query_db('SELECT * FROM treks WHERE id = ?', (trek_id,), one=True)
    if trek is None:
        abort(404)
    return trek


def _get_user_or_404(user_id):
    """Fetches one user row by id, or aborts with a 404 (Not Found) page."""
    user = query_db('SELECT * FROM users WHERE id = ?', (user_id,), one=True)
    if user is None:
        abort(404)
    return user


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """
    Admin landing page. Shows the 4 headline numbers required by the
    problem statement (Total Treks, Total Users, Total Staff, Total
    Bookings) plus a table of the most recent bookings.
    """
    total_treks = query_db('SELECT COUNT(*) AS c FROM treks', one=True)['c']
    total_users = query_db("SELECT COUNT(*) AS c FROM users WHERE role='user'", one=True)['c']
    total_staff = query_db("SELECT COUNT(*) AS c FROM users WHERE role='staff'", one=True)['c']
    total_bookings = query_db('SELECT COUNT(*) AS c FROM bookings', one=True)['c']

    # JOIN bookings with users + treks so the template can show readable
    # names instead of raw foreign-key IDs.
    recent_bookings = query_db(
        """SELECT b.id, u.name AS user_name, t.name AS trek_name,
                  b.booking_date, b.status
           FROM bookings b
           JOIN users u ON b.user_id = u.id
           JOIN treks t ON b.trek_id = t.id
           ORDER BY b.booking_date DESC
           LIMIT 5"""
    )

    return render_template(
        'admin/dashboard.html',
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings,
        recent_bookings=recent_bookings,
    )


# ---------------------------------------------------------------------
# TREK MANAGEMENT (Create / Read / Update / Delete = "CRUD")
# ---------------------------------------------------------------------

@admin_bp.route('/treks')
@login_required
@role_required('admin')
def treks():
    """Lists every trek. Supports a simple ?q= search box (name/location)."""
    query_text = request.args.get('q', '').strip()
    if query_text:
        like_pattern = f'%{query_text}%'
        all_treks = query_db(
            """SELECT * FROM treks
               WHERE name LIKE ? OR location LIKE ?
               ORDER BY id DESC""",
            (like_pattern, like_pattern),
        )
    else:
        all_treks = query_db('SELECT * FROM treks ORDER BY id DESC')
    return render_template('admin/treks.html', treks=all_treks, query_text=query_text)


@admin_bp.route('/treks/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_trek():
    """Admin creates a brand new trek."""
    # Only 'approved' (not blacklisted, not pending) staff can be assigned.
    staff_list = query_db("SELECT * FROM users WHERE role='staff' AND status='approved'")

    if request.method == 'POST':
        slots = int(request.form.get('total_slots'))
        assigned_staff_id = request.form.get('assigned_staff_id') or None

        execute_db(
            """INSERT INTO treks
               (name, location, difficulty, duration_days, total_slots,
                available_slots, start_date, end_date, description, status,
                assigned_staff_id, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get('name').strip(),
                request.form.get('location').strip(),
                request.form.get('difficulty'),
                int(request.form.get('duration_days')),
                slots,
                slots,  # available_slots starts equal to total_slots
                request.form.get('start_date'),
                request.form.get('end_date'),
                request.form.get('description', ''),
                request.form.get('status', 'Pending'),
                assigned_staff_id,
                request.form.get('image_url', '').strip() or None,
            ),
        )
        flash('Trek created successfully.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=None, staff_list=staff_list)


@admin_bp.route('/treks/edit/<int:trek_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_trek(trek_id):
    """Admin edits an existing trek's details."""
    trek = _get_trek_or_404(trek_id)
    staff_list = query_db("SELECT * FROM users WHERE role='staff' AND status='approved'")

    if request.method == 'POST':
        old_total = trek['total_slots']
        new_total = int(request.form.get('total_slots'))
        # If admin increases/decreases total slots, shift available_slots
        # by the SAME difference so existing bookings stay consistent.
        slot_difference = new_total - old_total
        new_available = max(0, trek['available_slots'] + slot_difference)

        assigned_staff_id = request.form.get('assigned_staff_id') or None

        execute_db(
            """UPDATE treks SET
                   name = ?, location = ?, difficulty = ?, duration_days = ?,
                   total_slots = ?, available_slots = ?, start_date = ?,
                   end_date = ?, status = ?, description = ?,
                   assigned_staff_id = ?, image_url = ?
               WHERE id = ?""",
            (
                request.form.get('name').strip(),
                request.form.get('location').strip(),
                request.form.get('difficulty'),
                int(request.form.get('duration_days')),
                new_total,
                new_available,
                request.form.get('start_date'),
                request.form.get('end_date'),
                request.form.get('status'),
                request.form.get('description', ''),
                assigned_staff_id,
                request.form.get('image_url', '').strip() or None,
                trek_id,
            ),
        )
        flash('Trek updated successfully.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=trek, staff_list=staff_list)


@admin_bp.route('/treks/delete/<int:trek_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_trek(trek_id):
    """
    Admin deletes a trek, but only if it has no bookings tied to it
    (Booked or Completed). This protects the "maintain complete booking
    history" requirement - once a trek has real booking history, we
    don't allow it to be wiped out.
    """
    trek = _get_trek_or_404(trek_id)
    has_bookings = query_db(
        'SELECT id FROM bookings WHERE trek_id = ? LIMIT 1', (trek_id,), one=True
    )
    if has_bookings:
        flash(f"Cannot delete \"{trek['name']}\" - it already has booking history.", 'danger')
        return redirect(url_for('admin.treks'))

    execute_db('DELETE FROM treks WHERE id = ?', (trek_id,))
    flash(f"Trek \"{trek['name']}\" was deleted.", 'info')
    return redirect(url_for('admin.treks'))


# ---------------------------------------------------------------------
# STAFF APPROVAL / BLACKLIST MANAGEMENT
# ---------------------------------------------------------------------

@admin_bp.route('/staff')
@login_required
@role_required('admin')
def staff_requests():
    """Shows staff accounts grouped into 3 tabs: Pending / Approved / Blacklisted."""
    pending = query_db("SELECT * FROM users WHERE role='staff' AND status='pending'")
    approved = query_db("SELECT * FROM users WHERE role='staff' AND status='approved'")
    blacklisted = query_db("SELECT * FROM users WHERE role='staff' AND status='blacklisted'")
    return render_template('admin/staff.html', pending=pending, approved=approved, blacklisted=blacklisted)


@admin_bp.route('/staff/<int:staff_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_staff(staff_id):
    staff = _get_user_or_404(staff_id)
    execute_db("UPDATE users SET status = 'approved' WHERE id = ?", (staff_id,))
    flash(f"{staff['name']} has been approved as Trek Staff.", 'success')
    return redirect(url_for('admin.staff_requests'))


@admin_bp.route('/staff/<int:staff_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_staff(staff_id):
    """Rejecting simply deletes the pending registration."""
    _get_user_or_404(staff_id)
    execute_db('DELETE FROM users WHERE id = ?', (staff_id,))
    flash('Staff registration request rejected.', 'info')
    return redirect(url_for('admin.staff_requests'))


@admin_bp.route('/staff/<int:staff_id>/blacklist', methods=['POST'])
@login_required
@role_required('admin')
def blacklist_staff(staff_id):
    staff = _get_user_or_404(staff_id)
    execute_db("UPDATE users SET status = 'blacklisted' WHERE id = ?", (staff_id,))
    flash(f"{staff['name']} has been blacklisted.", 'warning')
    return redirect(url_for('admin.staff_requests'))


@admin_bp.route('/staff/<int:staff_id>/unblock', methods=['POST'])
@login_required
@role_required('admin')
def unblock_staff(staff_id):
    """Admin can reinstate a previously blacklisted staff member."""
    staff = _get_user_or_404(staff_id)
    execute_db("UPDATE users SET status = 'approved' WHERE id = ?", (staff_id,))
    flash(f"{staff['name']} has been reinstated.", 'success')
    return redirect(url_for('admin.staff_requests'))


# ---------------------------------------------------------------------
# USER (TREKKER) MANAGEMENT
# ---------------------------------------------------------------------

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Lists all trekkers with an optional name/email search box."""
    query_text = request.args.get('q', '').strip()
    if query_text:
        like_pattern = f'%{query_text}%'
        all_users = query_db(
            "SELECT * FROM users WHERE role='user' AND (name LIKE ? OR email LIKE ?) ORDER BY id DESC",
            (like_pattern, like_pattern),
        )
    else:
        all_users = query_db("SELECT * FROM users WHERE role='user' ORDER BY id DESC")
    return render_template('admin/users.html', users=all_users, query_text=query_text)


@admin_bp.route('/users/<int:user_id>/blacklist', methods=['POST'])
@login_required
@role_required('admin')
def blacklist_user(user_id):
    user = _get_user_or_404(user_id)
    execute_db("UPDATE users SET status = 'blacklisted' WHERE id = ?", (user_id,))
    flash(f"{user['name']} has been blacklisted.", 'warning')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@login_required
@role_required('admin')
def unblock_user(user_id):
    user = _get_user_or_404(user_id)
    execute_db("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
    flash(f"{user['name']} has been reinstated.", 'success')
    return redirect(url_for('admin.users'))


# ---------------------------------------------------------------------
# BOOKINGS OVERVIEW & GLOBAL SEARCH
# ---------------------------------------------------------------------

@admin_bp.route('/bookings')
@login_required
@role_required('admin')
def bookings():
    """Admin can view every booking made in the system (full history)."""
    all_bookings = query_db(
        """SELECT b.id, u.name AS user_name, u.email AS user_email,
                  t.name AS trek_name, b.booking_date, b.status
           FROM bookings b
           JOIN users u ON b.user_id = u.id
           JOIN treks t ON b.trek_id = t.id
           ORDER BY b.booking_date DESC"""
    )
    return render_template('admin/bookings.html', bookings=all_bookings)


@admin_bp.route('/search')
@login_required
@role_required('admin')
def search():
    """
    A single search box that looks up treks, staff and users at once by
    name OR by numeric ID, as required by the problem statement:
    "Can search treks, staff, or users by name or ID".
    """
    query_text = request.args.get('q', '').strip()
    trek_results, staff_results, user_results = [], [], []

    if query_text:
        like_pattern = f'%{query_text}%'
        numeric_id = _safe_int(query_text)

        trek_results = query_db(
            'SELECT * FROM treks WHERE name LIKE ? OR id = ?', (like_pattern, numeric_id)
        )
        staff_results = query_db(
            "SELECT * FROM users WHERE role='staff' AND (name LIKE ? OR id = ?)",
            (like_pattern, numeric_id),
        )
        user_results = query_db(
            "SELECT * FROM users WHERE role='user' AND (name LIKE ? OR id = ?)",
            (like_pattern, numeric_id),
        )

    return render_template(
        'admin/search.html',
        query_text=query_text,
        trek_results=trek_results,
        staff_results=staff_results,
        user_results=user_results,
    )


def _safe_int(value):
    """
    Converts a search string to int for ID matching; returns -1 if it's
    not a valid number (so the 'id = -1' comparison simply matches
    nothing instead of crashing the query).
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
