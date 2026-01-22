from flask import Flask
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

def create_app():
    app = Flask(__name__)

    # Use persistent secret key with fallback to environment variable
    secret_key = os.environ.get('SAMBA_MANAGER_SECRET_KEY') or os.environ.get('SECRET_KEY')
    if secret_key:
        app.config['SECRET_KEY'] = secret_key
    else:
        # Generate a more secure key (32 bytes = 256 bits)
        app.config['SECRET_KEY'] = os.urandom(32).hex()
        print("WARNING: Using generated secret key. Set SAMBA_MANAGER_SECRET_KEY environment variable for production.")

    # Initialize Flask-Limiter for rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    app.limiter = limiter  # Store limiter in app for access from blueprints

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    @login_manager.user_loader
    def load_user(user_id):
        from .auth import User
        return User.get(user_id)
    
    return app
