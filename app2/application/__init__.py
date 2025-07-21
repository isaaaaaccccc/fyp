from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import current_user, LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app(config_path='config.cfg'):
    app = Flask(__name__)
    app.config.from_pyfile(config_path)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = '/'

    with app.app_context():
        from .models import User, Branch, Level, Coach, CoachBranch, CoachOffday, CoachPreference, PopularTimeslots, EnrollmentCounts, BranchConfig, CoachAvailability
        db.create_all()
        db.session.commit()

    # from application.forms import LoginForm, RegisterForm

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def get_user():
        return {'user': current_user}

    from application.routes import pages_bp, api_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    
    return app