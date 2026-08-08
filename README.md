# Trekking Management Application

A role-based web app (Admin / Trek Staff / User) built with **Flask + Jinja2 + Bootstrap + SQLite**, matching the App Dev I project statement (Trekking Management App V1).

---

## 1. How to Run It

```bash
# 1. Install the 2 dependencies (Flask + Werkzeug)
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open in browser
http://127.0.0.1:5000
```

The database (`trekking.db`) is created **automatically** the first time you run `app.py` — you never need DB Browser or any manual SQL. A default Admin account is also created automatically:

```
Email:    admin@trekking.com
Password: Admin@123
```

To start completely fresh, just delete `trekking.db` and run `python app.py` again.

---

## 2. Project Structure (what each file/folder is for)

> **What's new:** the UI now has a real trekking-site feel — a photo hero
> carousel on the login page, a photo **card grid** for browsing treks
> (like AllTrails trail cards), a hero banner on the trek details page,
> and small thumbnails in the Admin/Staff tables. Admin can paste a custom
> image URL per trek (with a live preview) or leave it blank for an
> auto-generated placeholder photo. Everything uses Bootstrap's own
> built-in Carousel/Card components — no extra framework added. If you
> already ran the app before this update, `db.py` auto-migrates your
> existing `trekking.db` (adds the new `image_url` column) — no need to
> delete it.


```
trekking_app/
├── app.py              # Entry point - creates the Flask app, registers blueprints
├── config.py            # App configuration (SECRET_KEY etc.)
├── db.py                 # ALL database logic (raw sqlite3, no ORM) - connect/query/execute/init
├── schema.sql           # CREATE TABLE statements for users, treks, bookings
├── utils.py              # login_required / role_required decorators (access control)
├── requirements.txt      # Only Flask + Werkzeug
├── routes/               # One file per role = one Blueprint per role
│   ├── auth.py            # /register, /login, /logout  (shared by all roles)
│   ├── admin.py            # everything under /admin/...
│   ├── staff.py             # everything under /staff/...
│   └── user.py               # everything under /user/...
├── templates/             # Jinja2 HTML templates (one folder per role)
│   ├── base.html            # master layout: sidebar + topbar + flash messages
│   ├── auth/                 # login.html, register.html
│   ├── admin/                  # dashboard, treks, trek_form, staff, users, bookings, search
│   ├── staff/                   # dashboard, trek_manage, profile
│   └── user/                     # dashboard, trek_details, bookings, history, profile
└── static/
    └── css/style.css        # small custom styles on top of Bootstrap
```

**Why this structure?** Each concern lives in its own file (routes split by role, database logic isolated in `db.py`, decorators isolated in `utils.py`). This is called *modular design* — it's exactly what an examiner expects to see, and it means you can explain any one file without reading the whole project.

---

## 3. Database Design (explain this from `schema.sql`)

Only **one** `users` table is used for Admin + Trek Staff + Trekker — a `role` column (`admin`/`staff`/`user`) tells them apart, instead of 3 near-identical tables. A `status` column (`pending`/`approved`/`blacklisted`) drives the staff-approval workflow and the blacklist feature.

```
users            treks                      bookings
--------         -----                       --------
id               id                          id
name             name                        user_id     -> users.id
email (unique)   location                    trek_id     -> treks.id
password_hash    difficulty                  booking_date
role             duration_days               status (Booked/Cancelled/Completed)
contact          total_slots
status           available_slots
created_at       start_date / end_date
                 description
                 status (Pending/Approved/Open/Ongoing/Closed/Completed)
                 assigned_staff_id -> users.id
```

`schema.sql` is executed **once** by `db.py -> init_db()` the very first time the app starts — this satisfies the "database must be created programmatically" rule (no DB Browser used, no manual table creation).

---

## 4. How Login / Access Control Works (`utils.py`)

- Passwords are **never stored in plain text** — `werkzeug.security.generate_password_hash()` hashes them at registration, `check_password_hash()` verifies them at login.
- After a successful login we store `user_id`, `name`, `role` in Flask's signed `session` cookie.
- `@login_required` (in `utils.py`) blocks a route unless someone is logged in.
- `@role_required('admin' / 'staff' / 'user')` additionally checks the role, so a Trekker can never open an Admin URL even by typing it directly in the browser.
- Trek Staff also needs **Admin approval** before they can log in (`status = 'pending'` blocks login until Admin approves them from `/admin/staff`).

---

## 5. Core Business Rules — and exactly where they live in the code

| Rule (from the problem statement) | Where it's enforced |
|---|---|
| Admin must pre-exist, no admin registration | `db.py -> seed_admin()`; `/register` only offers `staff`/`user` roles |
| Staff needs Admin approval before dashboard access | `routes/auth.py -> login()` checks `status == 'pending'` |
| Only assigned staff can manage a trek | `routes/staff.py -> _get_own_trek_or_404()` compares `trek.assigned_staff_id` to the logged-in staff's id |
| Users can only book if trek status is "Open" | `routes/user.py -> book_trek()` |
| Prevent overbooking beyond available slots | `routes/user.py -> book_trek()` checks `available_slots <= 0` before inserting |
| Booking history maintained per user | `bookings` table keeps every row (Booked/Cancelled/Completed), never deleted |
| Admin can search treks/staff/users by name or ID | `routes/admin.py -> search()` |

---

## 6. Plagiarism / Originality Notes (read this before submitting)

- All code here was written from scratch for **your** specific problem statement and wireframe — it is not copied from any tutorial or another student's repository.
- **You must still be able to explain every line** during the viva — that is the actual malpractice test (see `Malpractice Guidelines`, section 2.2: *"If you are unable to write simple logic, modify your own code, explain existing implementation, you may be flagged for malpractice"*).
- Recommended before you submit:
    1. **Read every file top to bottom once**, out loud if it helps. The comments explain the *why*, not just the *what*.
    2. **Type out (don't copy-paste) at least 2–3 small routes yourself** in your own words/style — e.g. rewrite `cancel_booking()` or `blacklist_user()` slightly differently. This personalizes your code and cements your understanding.
    3. **Make a real GitHub repo and commit in stages** (init → models/schema → auth → admin → staff → user → styling), not one giant final commit — the course explicitly checks for "proper GitHub commit history."
    4. Practice explaining, out loud, in under 2 minutes: *"How does a booking get created, and how do you stop overbooking?"* — walk through `book_trek()` in `routes/user.py`.
    5. Be ready to **live-modify code** in the viva — e.g. "add a `location` filter to the admin users search" or "change the Level of difficulty options." Since everything is plain SQL + Flask, changes are just editing one query or one route function.

---

## 7. Quick Viva Cheat-Sheet (things you'll likely be asked)

**Q: Why Blueprints?**
A: To split routes by role into separate files (`auth.py`, `admin.py`, `staff.py`, `user.py`) instead of one giant `app.py`. Cleaner, easier to navigate/explain.

**Q: Why no ORM (Flask-SQLAlchemy)?**
A: Raw `sqlite3` (Python's built-in module) keeps the project dependency-light and makes every database interaction a plain, explainable SQL query — good for a viva where you must explain exactly what each query does.

**Q: How do you stop two different roles from accessing each other's pages?**
A: `@role_required(role)` decorator in `utils.py`, applied on every route, checks `session['role']`.

**Q: How is overbooking prevented?**
A: `available_slots` is checked and decremented **atomically as part of the same request** in `book_trek()` before the INSERT — if slots are 0 the booking is refused with a flash message.

**Q: What happens when staff marks a trek Completed?**
A: `mark_completed()` in `routes/staff.py` updates the trek's status AND bulk-updates every `Booked` booking for that trek to `Completed`, which is what makes it show up under the user's Trekking History page.

**Q: Why one `users` table instead of three?**
A: Admin/Staff/User share almost identical fields (name, email, password). One table + a `role` column avoids duplicate schema and keeps login logic in a single place.

---

## 8. Default Login Credentials (for demo/testing)

| Role  | Email | Password |
|---|---|---|
| Admin | admin@trekking.com | Admin@123 |
| Staff / User | *(register your own via the Register page)* | — |

> Change the admin password after first login in any real deployment — it's hard-coded in `db.py -> seed_admin()` only as a starting point.

---

## 9. What's *not* included (per problem statement, these are separate deliverables)

- The **project report** (max 5 pages, with ER diagram, AI/LLM declaration, etc.)
- The **video walkthrough** you must record and upload to Drive
- Both are required alongside this code .zip for the actual portal submission — this repository is the "code" part only.
