import logging
import sys
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

csrf = CSRFProtect()
talisman = Talisman()


def configure_logging(app):
    """Set up structured logging to stdout for Render log capture."""

    log_level = logging.DEBUG if app.debug else logging.INFO

    # Formatter: timestamp | level | module | message
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Stream handler — stdout so Render captures it
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # Apply to Flask app logger
    app.logger.setLevel(log_level)
    app.logger.handlers.clear()
    app.logger.addHandler(stream_handler)
    app.logger.propagate = False  # ← prevents double logging via root logger

    # Wire into gunicorn's logger in production so logs aren't swallowed
    gunicorn_logger = logging.getLogger('gunicorn.error')
    if gunicorn_logger.handlers:
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    # Also configure the root logger so SQLAlchemy and other libs surface warnings
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    if not root_logger.handlers:
        root_logger.addHandler(stream_handler)

    app.logger.info("Logging configured — level: %s", logging.getLevelName(log_level))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Validate critical config before initialising anything
    required_vars = ['SECRET_KEY', 'SQLALCHEMY_DATABASE_URI']
    missing = [var for var in required_vars if not app.config.get(var)]
    if missing:
        raise RuntimeError(f"App cannot start. Missing required config: {missing}")

    # Logging must be configured early so all subsequent init steps are visible
    configure_logging(app)
    app.logger.info("Starting JudgeAccount.com application")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # Security headers via Talisman.
    # force_https and strict_transport_security are False because Render
    # terminates HTTPS at the proxy — Flask receives HTTP internally.
    # Redirecting to HTTPS here would cause redirect loops.
    talisman.init_app(
        app,
        force_https=False,
        strict_transport_security=False,
        frame_options='DENY',
        x_content_type_options=True,
        referrer_policy='strict-origin-when-cross-origin',
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self'",
            'style-src': "'self'",
            'img-src': "'self' data:",
            'font-src': "'self'",
            'connect-src': "'self'",
            'frame-src': "'none'",
            'object-src': "'none'",
        }
    )

    from app.email_utils import init_mail
    init_mail(app)

    from app import routes
    app.register_blueprint(routes.bp)
    from app import auth
    app.register_blueprint(auth.bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error("500 Internal Server Error: %s", str(error))
        return render_template('errors/500.html'), 500

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    app.logger.info("Application initialised successfully")
    return app