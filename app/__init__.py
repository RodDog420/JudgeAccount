from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager

db = SQLAlchemy()  # Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

def create_app(config_class=Config):
    app = Flask(__name__)
    
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    
    # Register blueprints (routes)
    from app import routes
    app.register_blueprint(routes.bp)
    from app import auth
    app.register_blueprint(auth.bp)
    
    # Created database tables when they didn't exist with code immediately below:
    # with app.app_context():
    #    db.create_all()
    # But(!) Database tables are now managed by Flask-Migrate
    # Now using 'flask db migrate' and 'flask db upgrade' to manage schema changes

    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    return app
