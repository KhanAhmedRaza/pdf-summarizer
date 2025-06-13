from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from extensions import db, login_manager
from models import User
from utils.pdf_processor import extract_text_from_pdf
from utils.summarizer import generate_summary
from datetime import datetime
import os
from oauth import setup_oauth
from authlib.integrations.flask_client import OAuth

main_bp = Blueprint('main', __name__)

# Initialize OAuth
oauth = OAuth()

@main_bp.record_once
def on_load(state):
    app = state.app
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'token_endpoint_auth_method': 'client_secret_post'
        }
    )

@main_bp.route('/manage/migrate', methods=['GET'])
def run_migration():
    # Add some basic security (like an admin check or secret token)
    if request.args.get('token') != os.environ.get('MIGRATION_SECRET_TOKEN'):
        return "Unauthorized", 401
        
    # Import Flask-Migrate's upgrade function
    from flask_migrate import upgrade as db_upgrade
    
    # Run the migration
    db_upgrade()
    
    return "Migration completed successfully"

@login_manager.user_loader
def load_user(user_id):
    # Load user directly from the database using SQLAlchemy
    return User.query.get(user_id)

# Routes
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    # Check if a file was uploaded
    if 'pdf_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('main.index'))
    
    file = request.files['pdf_file']
    
    # Check if file is empty
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('main.index'))
    
    # Check if file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed', 'error')
        return redirect(url_for('main.index'))
    
    # Check file size for free tier (if not logged in or no premium)
    if not current_user.is_authenticated:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > current_app.config['FREE_TIER_MAX_SIZE']:
            flash('File size exceeds the free tier limit (5MB). Please upgrade or upload a smaller file.', 'error')
            return redirect(url_for('main.index'))
    
    # Save the file
    filename = secure_filename(file.filename)
    temp_id = str(uuid.uuid4())
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{temp_id}_{filename}")
    file.save(file_path)
    
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        # Store in session for later use
        session['pdf_text'] = text
        session['pdf_filename'] = filename
        session['pdf_path'] = file_path
        
        # If user is logged in, generate summary immediately
        if current_user.is_authenticated:
            # Check usage limit
            if check_usage_limit(current_user.id):
                flash('You have reached your daily limit of 3 summaries. Please upgrade for unlimited summaries.', 'warning')
                return redirect(url_for('main.index'))
            
            # Generate summary
            summary = generate_summary(text)
            
            # Track usage
            track_usage(current_user.id)
            
            # Store summary
            summary_id = str(uuid.uuid4())
            summaries_db[summary_id] = {
                'user_id': current_user.id,
                'filename': filename,
                'summary': summary,
                'created_at': datetime.now()
            }
            
            # Clean up the file
            os.remove(file_path)
            
            return redirect(url_for('main.summary', summary_id=summary_id))
        else:
            # For non-logged in users, show preview and prompt to sign in
            preview_text = text[:500] + '...' if len(text) > 500 else text
            return render_template('preview.html', filename=filename, preview_text=preview_text)
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        flash('Error processing PDF. Please try again with a different file.', 'error')
        # Clean up the file
        if os.path.exists(file_path):
            os.remove(file_path)
        return redirect(url_for('main.index'))

@main_bp.route('/summary/<summary_id>')
@login_required
def summary(summary_id):
    # Check if summary exists
    if summary_id not in summaries_db:
        flash('Summary not found', 'error')
        return redirect(url_for('main.index'))
    
    # Check if summary belongs to user
    summary_data = summaries_db[summary_id]
    if summary_data['user_id'] != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('summary.html', 
                          filename=summary_data['filename'],
                          summary=summary_data['summary'],
                          created_at=summary_data['created_at'])

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    print(f"Login route accessed with method: {request.method}")
    
    if request.method == 'POST':
        # Manual login form submitted
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Form data received - Email: {email}, Password: {'*' * len(password) if password else 'None'}")
        
        # Find user by email using SQLAlchemy
        user = User.query.filter_by(email=email).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            print(f"Login successful for user: {email}")
            login_user(user)
            
            # Check if there's a pending PDF in session
            if 'pdf_text' in session:
                return redirect(url_for('main.preview_to_summary'))
            
            return redirect(url_for('main.index'))
        else:
            print(f"Login failed for email: {email}")
            flash('Invalid email or password', 'danger')
    
    # For both GET requests and failed POST requests
    return render_template('login.html')

@main_bp.route('/login/google')
def login_google():
    # Google OAuth login
    return oauth.google.authorize_redirect(url_for('main.google_callback', _external=True))

@main_bp.route('/login/google/callback')
def google_callback():
    try:
        # Handle the OAuth callback
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new user with generated UUID
            user = User(
                email=user_info['email'],
                name=user_info.get('name', user_info['email']),
                oauth_provider='google',
                profile_pic=user_info.get('picture')  # Add profile picture if available
            )
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f"Created new user with email: {user.email}")
        else:
            # Update existing user's OAuth info if needed
            if not user.oauth_provider:
                user.oauth_provider = 'google'
                user.name = user_info.get('name', user.name)  # Update name if not set
                user.profile_pic = user_info.get('picture', user.profile_pic)  # Update profile pic if available
                db.session.commit()
                current_app.logger.info(f"Updated existing user with email: {user.email}")
        
        # Log in the user
        login_user(user)
        
        # Check if there's a pending PDF in session
        if 'pdf_text' in session:
            return redirect(url_for('main.preview_to_summary'))
        
        return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        flash('Error during Google login. Please try again.', 'error')
        return redirect(url_for('main.login'))

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('main.register'))
        
        try:
            # Create new user with generated UUID
            user = User(
                email=email,
                name=name,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            # Log in the new user
            login_user(user)
            
            flash('Registration successful!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('Error during registration. Please try again.', 'danger')
            return redirect(url_for('main.register'))
    
    return render_template('register.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main_bp.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html')

@main_bp.route('/api/test/reset', methods=['POST'])
def reset_test_data():
    """Reset test data - only for testing purposes."""
    if not current_app.config['TESTING']:
        return jsonify({"error": "This endpoint is only available in testing mode"}), 403
        
    try:
        # Clear all test data
        db.session.query(User).delete()
        db.session.commit()
        return jsonify({"message": "Test data reset successful"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main_bp.route('/post_login')
@login_required
def post_login():
    """Handle post-login actions."""
    # Check if there's a pending PDF in session
    if 'pdf_text' in session:
        return redirect(url_for('main.preview_to_summary'))
    
    return redirect(url_for('main.dashboard'))

# Continue for all other routes...