import pytest
from flask import Flask, redirect, url_for, request, jsonify, session
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
import os
import sys
import tempfile
from sqlalchemy.orm import scoped_session, sessionmaker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from models import User
from models import MonthlyUsage, Upload
from extensions import login_manager, db

# Global variable for mocking page count in tests
mock_page_count = None

@pytest.fixture(scope="session")
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Create a context for the app
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Configure login_manager
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)
        
        # Add test routes
        @app.route('/')
        def index():
            return "Home Page", 200
            
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return "Dashboard Page", 200
            
        @app.route('/pricing')
        def pricing():
            return "Pricing Page", 200
            
        @app.route('/plans/process_payment', methods=['POST'])
        @login_required
        def process_payment():
            # This will be mocked in tests
            return redirect(url_for('pricing'))
            
        @app.route('/plans/subscribe/<plan_type>')
        @login_required
        def subscribe(plan_type):
            return f"Subscribe to {plan_type} plan", 200
        
        @app.route('/test/features/<feature>')
        def test_feature_access(feature):
            if not current_user.is_authenticated:
                return "Unauthorized", 401
                
            # Get a fresh instance of the user from the session
            user = db.session.merge(current_user._get_current_object())
            if not user.can_access_feature(feature):
                return {"error": "Feature not available on your plan"}, 403
            return {"success": True, "feature": feature}, 200
        
        @app.route('/login')
        def login():
            return "Login Page", 200
            
        @app.route('/logout')
        @login_required
        def logout():
            logout_user()
            return redirect(url_for('index'))
            
        @app.route('/pdf/upload', methods=['GET', 'POST'])
        @login_required
        def pdf_upload_test():
            if request.method == 'GET':
                return "Upload page", 200
                
            if request.method == 'POST':
                # Get a fresh instance of the user from the session
                user = db.session.merge(current_user._get_current_object())
                
                # Check if user can upload more PDFs
                if not user.can_upload_pdf():
                    return jsonify({"error": "Monthly limit reached"}), 403
                    
                # Check document type access
                document_type = request.form.get('document_type', 'academic')
                if not user.can_access_feature(document_type):
                    return jsonify({"error": f"Your plan does not support {document_type} documents"}), 403
                    
                # Check summary format access
                summary_format = request.form.get('summary_format', 'plain_text')
                if not user.can_access_feature(summary_format):
                    return jsonify({"error": f"Your plan does not support {summary_format} format"}), 403
                    
                # Mock file upload processing
                if 'pdf' not in request.files:
                    return jsonify({"error": "No file provided"}), 400
                    
                # Get the uploaded file
                pdf_file = request.files['pdf']
                if not pdf_file or not pdf_file.filename:
                    return jsonify({"error": "No file provided"}), 400
                    
                # Check model access first
                requested_model = request.form.get('model')
                if requested_model == 'gpt-4' and user.plan_type == 'free':
                    return jsonify({"error": "GPT-4 is not available on your plan"}), 403
                    
                # Check page limit based on user's plan
                max_pages = user.get_max_pages_per_file()
                
                # Get page count from form data
                page_count = request.form.get('_page_count')
                if page_count is None:
                    return jsonify({"error": "Could not determine PDF page count"}), 400
                    
                try:
                    page_count = int(page_count)
                except ValueError:
                    return jsonify({"error": "Invalid page count"}), 400
                    
                if page_count > max_pages:
                    return jsonify({"error": f"PDF exceeds {max_pages} page limit"}), 403
                    
                # Return success response with model info based on user's plan
                model = user.get_ai_model()
                response_data = {
                    "success": True,
                    "model": model
                }
                
                if user.plan_type == "pro":
                    response_data["enhanced"] = True
                    
                return jsonify(response_data), 200
        
        yield app
        
        # Clean up after all tests
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="function")
def db_session(app):
    """Create a fresh database session for each test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create a session with the connection
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        
        # Make this session the current one
        old_session = db.session
        db.session = session
        
        yield session
        
        # Rollback the transaction and restore the old session
        session.remove()
        transaction.rollback()
        connection.close()
        db.session = old_session

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def free_user(app, db_session):
    """Create a free plan user."""
    with app.app_context():
        user = User(
            id="free-user-id",
            email="free@example.com",
            name="Free User",
            plan_type="free"
        )
        db_session.add(user)
        db_session.commit()
        # Ensure the user is attached to the session
        db_session.refresh(user)
        return user

@pytest.fixture
def starter_user(app, db_session):
    """Create a starter plan user."""
    with app.app_context():
        user = User(
            id="starter-user-id",
            email="starter@example.com",
            name="Starter User",
            plan_type="starter"
        )
        db_session.add(user)
        db_session.commit()
        # Ensure the user is attached to the session
        db_session.refresh(user)
        return user

@pytest.fixture
def pro_user(app, db_session):
    """Create a pro plan user."""
    with app.app_context():
        user = User(
            id="pro-user-id",
            email="pro@example.com",
            name="Pro User",
            plan_type="pro"
        )
        db_session.add(user)
        db_session.commit()
        # Ensure the user is attached to the session
        db_session.refresh(user)
        return user

@pytest.fixture
def login_as_free(app, client, free_user, db_session):
    """Log in as a free user."""
    with app.app_context():
        # Ensure the user is attached to the current session
        user = db_session.merge(free_user)
        db_session.refresh(user)
        
        # Set up the session
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
            session['_id'] = 'test-session-id'
            session['_user_id'] = user.id
            
        # Log in the user
        with app.test_request_context():
            login_user(user)
            app.preprocess_request()
            
        # Make a test request to ensure the session is active
        client.get('/')
    
    return client

@pytest.fixture
def login_as_starter(app, client, starter_user, db_session):
    """Log in as a starter user."""
    with app.app_context():
        # Ensure the user is attached to the current session
        user = db_session.merge(starter_user)
        db_session.refresh(user)
        
        # Set up the session
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
            session['_id'] = 'test-session-id'
            session['_user_id'] = user.id
            
        # Log in the user
        with app.test_request_context():
            login_user(user)
            app.preprocess_request()
            
        # Make a test request to ensure the session is active
        client.get('/')
    
    return client

@pytest.fixture
def login_as_pro(app, client, pro_user, db_session):
    """Log in as a pro user."""
    with app.app_context():
        # Ensure the user is attached to the current session
        user = db_session.merge(pro_user)
        db_session.refresh(user)
        
        # Set up the session
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
            session['_id'] = 'test-session-id'
            session['_user_id'] = user.id
            
        # Log in the user
        with app.test_request_context():
            login_user(user)
            app.preprocess_request()
            
        # Make a test request to ensure the session is active
        client.get('/')
    
    return client

@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.4\nMock PDF content')
        temp_path = f.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)

# Add an autouse fixture to ensure database is clean between tests
@pytest.fixture(autouse=True)
def cleanup_db(app, db_session):
    yield
    db_session.rollback()
    for table in reversed(db.metadata.sorted_tables):
        db_session.execute(table.delete())

def test_user_plan_tagging(app, free_user, starter_user, pro_user):
    """Test that users can be tagged with different plans."""
    with app.app_context():
        # Refresh users from database to ensure they're attached to the session
        free_user = db.session.merge(free_user)
        starter_user = db.session.merge(starter_user)
        pro_user = db.session.merge(pro_user)
        
        # Now verify plan types
        assert free_user.plan_type == "free"
        assert starter_user.plan_type == "starter"
        assert pro_user.plan_type == "pro"
