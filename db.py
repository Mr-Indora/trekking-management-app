"""
db.py
-----
This file contains ALL the low-level database plumbing for the project.
We use Python's built-in `sqlite3` module directly (NOT an ORM), because:
    1. SQLite is the only database engine allowed by the project rules.
    2. Writing plain SQL makes it very easy to explain exactly what each
       query does during the viva.
    3. It keeps the project dependency-free (only Flask + Werkzeug needed).

HOW CONNECTIONS ARE MANAGED
-----------------------------
Flask gives us a special object called `g` (short for "global") that is
UNIQUE to each incoming request. We open one SQLite connection per request,
store it on `g.db`, and Flask automatically calls close_db() for us at the
end of every request (registered in app.py via app.teardown_appcontext).
This avoids leaking open database connections.
"""

import sqlite3
import os
from datetime import datetime
from flask import g, current_app
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'trekking.db')
SCHEMA_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'schema.sql')


def get_db():
    """
    Returns the SQLite connection for the CURRENT request. If one doesn't
    exist yet for this request, it creates it and stores it on `g` so that
    repeated calls within the same request reuse the same connection.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        # row_factory=sqlite3.Row lets us access columns both by index AND
        # by name (like a dictionary) - e.g. row['name'] - which is very
        # convenient inside Jinja2 templates.
        g.db.row_factory = sqlite3.Row
        # Turns on SQLite's foreign-key constraint enforcement (off by
        # default in SQLite for backward-compatibility reasons).
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(exception=None):
    """Closes the database connection at the end of a request, if one was opened."""
    db_conn = g.pop('db', None)
    if db_conn is not None:
        db_conn.close()


def query_db(query, args=(), one=False):
    """
    Runs a SELECT query and returns the results.
        one=False -> returns a list of sqlite3.Row objects
        one=True  -> returns a single sqlite3.Row object (or None)
    """
    cursor = get_db().execute(query, args)
    rows = cursor.fetchall()
    cursor.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    """
    Runs an INSERT / UPDATE / DELETE statement, commits the change, and
    returns the `lastrowid` (useful right after an INSERT to know the new
    row's auto-generated id).
    """
    db_conn = get_db()
    cursor = db_conn.execute(query, args)
    db_conn.commit()
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


def init_db(app):
    """
    Creates the database file + all tables by running schema.sql, but ONLY
    if the database file does not already exist. This is what satisfies
    the requirement: "The database must be created programmatically".

    Also inserts a single default Admin account (see seed_admin()) because
    admin registration is intentionally NOT available anywhere in the UI.
    """
    db_already_exists = os.path.exists(DB_PATH)

    with app.app_context():
        db_conn = get_db()
        if not db_already_exists:
            with open(SCHEMA_PATH, 'r') as schema_file:
                db_conn.executescript(schema_file.read())
            print('>> Database created from schema.sql')
        else:
            # The app was already run once before with an older schema.
            # Instead of forcing the student to delete trekking.db every
            # time we add a new column, we check for it and add it on the
            # fly. This is a tiny, hand-written "migration".
            _migrate_add_missing_columns(db_conn)
        seed_admin()
        close_db()


def _migrate_add_missing_columns(db_conn):
    """
    Looks at the REAL columns currently in the 'treks' table (using
    SQLite's PRAGMA table_info) and adds any column that schema.sql
    defines but the existing database file is still missing - e.g. when
    a new feature (like trek photos) is added after the DB already
    exists on someone's machine.
    """
    existing_columns = {row['name'] for row in db_conn.execute('PRAGMA table_info(treks)')}
    if 'image_url' not in existing_columns:
        db_conn.execute('ALTER TABLE treks ADD COLUMN image_url TEXT')
        db_conn.commit()
        print('>> Migrated existing database: added treks.image_url column')


def seed_admin():
    """
    Inserts the ONE default Admin account, only if no admin exists yet.
    Default credentials (change after first login in real deployment):
        Email    : admin@trekking.com
        Password : Admin@123
    """
    existing_admin = query_db("SELECT id FROM users WHERE role = 'admin'", one=True)
    if existing_admin:
        return

    execute_db(
        """INSERT INTO users (name, email, password_hash, role, contact, status, created_at)
           VALUES (?, ?, ?, 'admin', ?, 'approved', ?)""",
        (
            'System Admin',
            'admin@trekking.com',
            generate_password_hash('Admin@123'),
            '9999999999',
            datetime.utcnow().isoformat(),
        ),
    )
    print('>> Default admin account created: admin@trekking.com / Admin@123')
