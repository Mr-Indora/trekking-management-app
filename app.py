"""
app.py
------
This is the MAIN ENTRY POINT of the Trekking Management Application.

Run the project with:
    python app.py

Then open  http://127.0.0.1:5000  in your browser.

WHAT HAPPENS WHEN THIS FILE RUNS?
------------------------------------
1. We create a Flask application (create_app()).
2. We connect our raw-SQLite database helper (db.py) to the app, and tell
   Flask to automatically close the DB connection after every request
   (app.teardown_appcontext).
3. We register 4 "Blueprints" (auth, admin, staff, user) - each one is a
   separate file inside routes/ grouping related URLs together, instead of
   dumping every route into this one file.
4. We create the SQLite database + tables programmatically (db.init_db)
   the first time the app runs, and seed one default Admin account.
"""

from flask import Flask
from config import Config
import db as database

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.staff import staff_bp
from routes.user import user_bp


def create_app():
    """Application Factory: builds and configures one Flask app instance."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure every SQLite connection opened during a request is properly
    # closed once that request finishes (success OR error).
    app.teardown_appcontext(database.close_db)

    # Register every blueprint so Flask knows about their routes.
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_bp)

    # Creates trekking.db + tables (if missing) and seeds the Admin account.
    database.init_db(app)

    register_template_filters(app)

    return app


def register_template_filters(app):
    """
    Custom Jinja2 filters used inside our .html templates.

    Since we store dates/timestamps as plain ISO-format TEXT in SQLite
    (raw sqlite3 has no native DATE type), `format_date` converts that
    text back into a nice human-readable string like "07 Aug 2026" for
    display, e.g. {{ booking.booking_date | format_date }} in a template.
    """
    from datetime import datetime

    @app.template_filter('format_date')
    def format_date(value, fmt='%d %b %Y'):
        if not value:
            return ''
        # booking_date is stored as a full ISO datetime string
        # (e.g. "2026-08-07T10:15:30.123456"); trek start/end dates are
        # stored as plain "YYYY-MM-DD" strings from the HTML date input.
        for parse_format in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, parse_format).strftime(fmt)
            except ValueError:
                continue
        return value  # fall back to showing the raw text if parsing fails

    @app.template_global('trek_photo')
    def trek_photo(trek, width=500, height=320):
        """
        Returns a photo URL to show for a trek card.

        If the Admin added a custom `image_url` when creating/editing the
        trek, we use that. Otherwise we fall back to a auto-generated
        placeholder photo from Lorem Picsum (https://picsum.photos) using
        the trek's own id as a fixed "seed" - this means the SAME trek
        always gets the SAME placeholder photo (instead of a random one
        on every page reload), which makes the browsing experience feel
        consistent, just like a real trekking website.
        """
        custom_url = trek['image_url'] if 'image_url' in trek.keys() else None
        if custom_url:
            return custom_url
        trek_id = trek['id'] if 'id' in trek.keys() else 0
        return f'https://picsum.photos/seed/trek{trek_id}/{width}/{height}'


# Module-level `app` object so commands like `flask run` / WSGI servers can
# find it via `app:app`.
app = create_app()


if __name__ == '__main__':
    # debug=True gives auto-reload + detailed error pages during
    # development. Set debug=False before any real deployment.
    app.run(debug=True, host='0.0.0.0', port=5000)
