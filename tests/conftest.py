import pytest
from flask import Flask
from flask_login import LoginManager, login_user
import os
import sys
import tempfile

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.db import db
from models.user import User
from models.usage import MonthlyUsage, Upload
from extensions import login_manager

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-key'
    
    # Use in-memory SQLite for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Import and register blueprints
    from routes import plans_bp
    app.register_blueprint(plans_bp, url_prefix='/plans')
    
    # Import and register PDF routes
    from pdf_routes import pdf_bp
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    
    # Create a test route for checking plan-specific features
    @app.route('/test/features/<feature>')
    @login_required
    def test_feature_access(feature):
        if not current_user.can_access_feature(feature):
            return {"error": "Feature not available on your plan"}, 403
        return {"success": True, "feature": feature}, 200
    
    # Create a context for the app
    with app.app_context():
        # Create all database tables
        db.create_all()
        yield app
        # Clean up after the test
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def auth_client(app, client):
    """A test client with authentication."""
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    return client

@pytest.fixture
def free_user(app):
    """Create a free plan user."""
    user = User(
        id="free-user-id",
        email="free@example.com",
        name="Free User",
        plan_type="free"
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def starter_user(app):
    """Create a starter plan user."""
    user = User(
        id="starter-user-id",
        email="starter@example.com",
        name="Starter User",
        plan_type="starter"
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def pro_user(app):
    """Create a pro plan user."""
    user = User(
        id="pro-user-id",
        email="pro@example.com",
        name="Pro User",
        plan_type="pro"
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def login_as_free(auth_client, free_user):
    """Log in as a free user."""
    with auth_client.session_transaction() as session:
        session['user_id'] = free_user.id
        session['_fresh'] = True
    return auth_client

@pytest.fixture
def login_as_starter(auth_client, starter_user):
    """Log in as a starter user."""
    with auth_client.session_transaction() as session:
        session['user_id'] = starter_user.id
        session['_fresh'] = True
    return auth_client

@pytest.fixture
def login_as_pro(auth_client, pro_user):
    """Log in as a pro user."""
    with auth_client.session_transaction() as session:
        session['user_id'] = pro_user.id
        session['_fresh'] = True
    return auth_client

@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.5\n%Test PDF file for testing')
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Clean up the file after the test
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
