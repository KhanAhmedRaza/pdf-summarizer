import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from oauth import setup_oauth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid
from utils.pdf_processor import extract_text_from_pdf
from utils.summarizer import generate_summary
import json
from functools import wraps
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
# Import the User model from models
from extensions import db, migrate, login_manager
from models import User
from routes import plans_bp
from pdf_routes import pdf_bp
from main_routes import main_bp
from flask_migrate import upgrade as db_upgrade

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(testing=False, **kwargs):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", **kwargs)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = '/tmp/pdf_uploads'
    app.config['FREE_TIER_MAX_SIZE'] = 5 * 1024 * 1024
    
    # Google OAuth configuration
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Database configuration
    app.config['TESTING'] = testing
    if testing:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(plans_bp, url_prefix='/plans')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    
    # Setup OAuth only if not testing
    if not testing:
        setup_oauth(app)
    
    # Initialize database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created or confirmed to exist!")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
    


