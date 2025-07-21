import sys
import os

# Import required dependencies with error handling
try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_bcrypt import Bcrypt
    from flask_login import current_user, LoginManager
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install all required dependencies by running:")
    print("pip install -r requirements.txt")
    sys.exit(1)

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app(config_path='config.cfg'):
    """
    Create and configure the Flask application.
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        Flask: Configured Flask application instance
        
    Raises:
        FileNotFoundError: If configuration file is not found
        Exception: If database initialization fails
    """
    try:
        app = Flask(__name__)
        
        # Load configuration
        if not os.path.exists(config_path):
            # Try relative path from application directory
            config_path = os.path.join(os.path.dirname(__file__), config_path)
            
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        app.config.from_pyfile(config_path)

        # Initialize extensions
        db.init_app(app)
        bcrypt.init_app(app)
        login_manager.init_app(app)
        login_manager.login_view = '/'

        # Initialize database
        with app.app_context():
            try:
                from .models import User, Branch, Level, Coach, CoachBranch, CoachOffday, CoachPreference
                db.create_all()
                db.session.commit()
            except Exception as e:
                print(f"Warning: Database initialization failed: {e}")
                print("You may need to run init_db.py separately")

        # from application.forms import LoginForm, RegisterForm

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        @app.context_processor
        def get_user():
            return {'user': current_user}

        # Register blueprints
        try:
            from application.routes import pages_bp, api_bp, upload_bp, branch_bp, level_bp
            
            app.register_blueprint(pages_bp)
            app.register_blueprint(api_bp)
            app.register_blueprint(upload_bp)
            app.register_blueprint(branch_bp)
            app.register_blueprint(level_bp)
        except ImportError as e:
            print(f"Warning: Failed to import routes: {e}")
            print("Some application features may not be available")
        
        return app
        
    except Exception as e:
        print(f"Error creating Flask application: {e}")
        raise