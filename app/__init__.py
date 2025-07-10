from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    # Use environment variable for secret key or generate a random one
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    from .routes import bp
    app.register_blueprint(bp)
    return app
