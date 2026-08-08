-- ============================================================================
-- schema.sql
-- ----------
-- Raw SQL table definitions for the Trekking Management Application.
-- This file is executed ONE TIME by db.py -> init_db() the first time the
-- app is started, which satisfies the project requirement that the
-- "database must be created programmatically" (no manual DB Browser use).
--
-- We keep ONE 'users' table for Admin + Trek Staff + Trekker(User) and use
-- the 'role' column to tell them apart. This avoids repeating the same
-- name/email/password columns in 3 separate tables.
-- ============================================================================

DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS treks;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------------------------
-- USERS table: stores Admin, Trek Staff and Trekker (User) accounts.
--   role   -> 'admin' | 'staff' | 'user'
--   status -> 'pending' | 'approved' | 'blacklisted'
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL,
    contact       TEXT,
    status        TEXT NOT NULL DEFAULT 'approved',
    created_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- TREKS table: every trekking event created by the Admin.
--   assigned_staff_id links to users.id of the staff member managing it.
-- ---------------------------------------------------------------------------
CREATE TABLE treks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    location          TEXT NOT NULL,
    difficulty        TEXT NOT NULL,
    duration_days     INTEGER NOT NULL,
    total_slots       INTEGER NOT NULL,
    available_slots   INTEGER NOT NULL,
    start_date        TEXT NOT NULL,
    end_date          TEXT NOT NULL,
    description       TEXT,
    status            TEXT NOT NULL DEFAULT 'Pending',
    assigned_staff_id INTEGER,
    -- Optional photo shown on trek cards (Admin can paste any image URL).
    -- If left blank, the templates fall back to an auto-generated
    -- placeholder photo (see static/css/style.css + templates) so every
    -- trek still looks good without the Admin needing to upload files.
    image_url         TEXT,
    FOREIGN KEY (assigned_staff_id) REFERENCES users (id)
);

-- ---------------------------------------------------------------------------
-- BOOKINGS table: links a User to a Trek they booked.
-- ---------------------------------------------------------------------------
CREATE TABLE bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    trek_id      INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'Booked',
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (trek_id) REFERENCES treks (id) ON DELETE CASCADE
);
