import pytest
from flask import Flask
from flask_login import LoginManager, login_user, login_required, current_user
import os
import sys
import tempfile

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from models import User
from models import MonthlyUsage, Upload
from extensions import login_manager, db

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-key'
    app.config['LOGIN_DISABLED'] = False  # Make sure login is not disabled
    
    # Use in-memory SQLite for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login_manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Make db accessible via app.db for test convenience
    app.db = db
    
    # Import and register blueprints
    from routes import plans_bp
    app.register_blueprint(plans_bp, url_prefix='/plans')
    
    # Import and register PDF routes
    from pdf_routes import pdf_bp
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    
    # Create a test route for checking plan-specific features
    @app.route('/test/features/<feature>')
    def test_feature_access(feature):
        # Add debug prints at the beginning of this function
        from flask_login import current_user
        print(f"Route - Current user authenticated: {current_user.is_authenticated}")
        print(f"Route - Current user ID: {current_user.id if current_user.is_authenticated else 'None'}")
        print(f"Route - Current user plan: {current_user.plan_type if current_user.is_authenticated else 'None'}")
        
        if not current_user.is_authenticated:
            return "Unauthorized", 401
            
        if not current_user.can_access_feature(feature):
            return {"error": "Feature not available on your plan"}, 403
        return {"success": True, "feature": feature}, 200
    
    # Add a login route for testing
    @app.route('/login')
    def login():
        return "Login Page", 200
    
    # Add PDF upload route for testing if not in blueprint
    @app.route('/pdf/upload', methods=['GET', 'POST'])
    def pdf_upload_test():
        if not current_user.is_authenticated:
            return "Redirect to login", 302
        return "Upload page", 200
    
    # Create a context for the app
    with app.app_context():
        # Create all database tables
        db.create_all()  # Ensure tables are created
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
def free_user(app, db_session):
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
def login_as_free(app, client, free_user):
    """Log in as a free user."""
    with app.app_context():
        # Refresh the user to ensure it's attached to the current session
        free_user = db.session.merge(free_user)
        
        with app.test_request_context():
            login_user(free_user)
            app.preprocess_request()
            
            # Verify current_user is set
            assert current_user.is_authenticated
            assert current_user.id == free_user.id
    
    # Set session cookies for the test client
    with client.session_transaction() as session:
        session['user_id'] = free_user.id
        session['_fresh'] = True
        session['_id'] = 'test-session-id'
        session['_user_id'] = free_user.id
    
    return client


@pytest.fixture
def login_as_starter(app, client, starter_user):
    """Log in as a starter user."""
    # Properly authenticate the user in the Flask-Login system
    with app.test_request_context():
        login_user(starter_user)
        # Process the request to set current_user
        app.preprocess_request()
        
        # Verify current_user is set
        assert current_user.is_authenticated
        assert current_user.id == starter_user.id
    
    # Set session cookies for the test client
    with client.session_transaction() as session:
        session['user_id'] = starter_user.id
        session['_fresh'] = True
        session['_id'] = 'test-session-id'
        session['_user_id'] = starter_user.id
    
    return client

@pytest.fixture
def login_as_pro(app, client, pro_user):
    """Log in as a pro user."""
    # Properly authenticate the user in the Flask-Login system
    with app.test_request_context():
        login_user(pro_user)
        # Process the request to set current_user
        app.preprocess_request()
        
        # Verify current_user is set
        assert current_user.is_authenticated
        assert current_user.id == pro_user.id
    
    # Set session cookies for the test client
    with client.session_transaction() as session:
        session['user_id'] = pro_user.id
        session['_fresh'] = True
        session['_id'] = 'test-session-id'
        session['_user_id'] = pro_user.id
    
    return client

@pytest.fixture
def mock_pdf_file():
    """Use an existing PDF file for testing."""
    import os
    
    # Path to your existing PDF file
    pdf_path = r"C:\usr\doc\test.pdf"  # Use raw string for Windows path
    
    # Verify the file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Test PDF file not found at {pdf_path}")
    
    # Return the path to the existing file
    yield pdf_path
    
    # No cleanup needed since we're using an existing file


        
@pytest.fixture(scope="function")
def db_session(app):
    """Provide a database session for testing."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session = db.scoped_session(
            db.sessionmaker(bind=connection)
        )
        db.session = session
        
        yield session
        
        session.close()
        transaction.rollback()
        connection.close()


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
