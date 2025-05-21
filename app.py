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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload size
app.config['UPLOAD_FOLDER'] = '/tmp/pdf_uploads'
app.config['FREE_TIER_MAX_SIZE'] = 5 * 1024 * 1024  # 5MB for free tier
app.config['TESTING'] = os.environ.get('TESTING', 'False').lower() == 'true'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple in-memory user database (replace with real DB in production)
users_db = {}
summaries_db = {}
usage_db = {}

# User model
class User(UserMixin):
    def __init__(self, id, name, email, profile_pic=None):
        self.id = id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

@login_manager.user_loader
def load_user(user_id):
    # Here you would typically load the user from your database
    # For simplicity, we'll check if the user is in the session
    if 'user' in session and session['user']['id'] == user_id:
        user_data = session['user']
        return User(
            id=user_data['id'],
            name=user_data['name'],
            email=user_data['email'],
            profile_pic=user_data.get('profile_pic')
        )
    return None
# Setup OAuth - This goes AFTER the load_user function, not inside it
oauth = setup_oauth(app)
# Middleware to track usage
def track_usage(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    if user_id not in usage_db:
        usage_db[user_id] = {}
    
    if today not in usage_db[user_id]:
        usage_db[user_id][today] = 0
    
    usage_db[user_id][today] += 1
    return usage_db[user_id][today]

# Check if user has reached daily limit
def check_usage_limit(user_id, limit=3):
    today = datetime.now().strftime('%Y-%m-%d')
    if user_id not in usage_db or today not in usage_db[user_id]:
        return 0
    
    return usage_db[user_id][today] >= limit

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    # Check if a file was uploaded
    if 'pdf_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    
    # Check if file is empty
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    # Check if file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed', 'error')
        return redirect(url_for('index'))
    
    # Check file size for free tier (if not logged in or no premium)
    if not current_user.is_authenticated:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > app.config['FREE_TIER_MAX_SIZE']:
            flash('File size exceeds the free tier limit (5MB). Please upgrade or upload a smaller file.', 'error')
            return redirect(url_for('index'))
    
    # Save the file
    filename = secure_filename(file.filename)
    temp_id = str(uuid.uuid4())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{temp_id}_{filename}")
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
                return redirect(url_for('index'))
            
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
            
            return redirect(url_for('summary', summary_id=summary_id))
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
        return redirect(url_for('index'))

@app.route('/preview_to_summary', methods=['POST'])
@login_required
def preview_to_summary():
    # Check if PDF text is in session
    if 'pdf_text' not in session:
        flash('Session expired. Please upload your PDF again.', 'error')
        return redirect(url_for('index'))
    
    # Check usage limit
    if check_usage_limit(current_user.id):
        flash('You have reached your daily limit of 3 summaries. Please upgrade for unlimited summaries.', 'warning')
        return redirect(url_for('index'))
    
    # Generate summary
    text = session.get('pdf_text')
    filename = session.get('pdf_filename')
    file_path = session.get('pdf_path')
    
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
    
    # Clean up session and file
    for key in ['pdf_text', 'pdf_filename', 'pdf_path']:
        if key in session:
            session.pop(key)
    
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    return redirect(url_for('summary', summary_id=summary_id))

@app.route('/summary/<summary_id>')
@login_required
def summary(summary_id):
    # Check if summary exists
    if summary_id not in summaries_db:
        flash('Summary not found', 'error')
        return redirect(url_for('index'))
    
    # Check if summary belongs to user
    summary_data = summaries_db[summary_id]
    if summary_data['user_id'] != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    return render_template('summary.html', 
                          filename=summary_data['filename'],
                          summary=summary_data['summary'],
                          created_at=summary_data['created_at'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find user by email
        user = next((u for u in users_db.values() if u.email == email), None)
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            
            # Check if there's a pending PDF in session
            if 'pdf_text' in session:
                return redirect(url_for('preview_to_summary'))
            
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Check if email already exists
        if any(u.email == email for u in users_db.values()):
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user_id = str(uuid.uuid4())
        users_db[user_id] = User(
            id=user_id,
            email=email,
            password_hash=generate_password_hash(password),
            name=name
        )
        
        # Log in the new user
        login_user(users_db[user_id])
        
        # Check if there's a pending PDF in session
        if 'pdf_text' in session:
            return redirect(url_for('preview_to_summary'))
        
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's summaries
    user_summaries = {id: data for id, data in summaries_db.items() 
                     if data['user_id'] == current_user.id}
    
    # Get usage data
    today = datetime.now().strftime('%Y-%m-%d')
    usage_today = usage_db.get(current_user.id, {}).get(today, 0)
    remaining = max(0, 3 - usage_today)
    
    return render_template('dashboard.html', 
                          summaries=user_summaries,
                          usage_today=usage_today,
                          remaining=remaining)

# Google OAuth routes
@app.route('/auth/google')
def google_auth():
    # This would be implemented with a proper OAuth library in production
    # For now, we'll simulate the flow
    return render_template('google_auth_simulation.html')

@app.route('/auth/google/callback', methods=['POST'])
def google_callback():
    # Simulate Google auth callback
    email = request.form.get('email')
    name = request.form.get('name')
    
    # Check if user exists
    user = next((u for u in users_db.values() if u.email == email), None)
    
    if not user:
        # Create new user
        user_id = str(uuid.uuid4())
        users_db[user_id] = User(
            id=user_id,
            email=email,
            password_hash=None,  # Google auth doesn't use password
            name=name
        )
        user = users_db[user_id]
    
    login_user(user)
    
    # Check if there's a pending PDF in session
    if 'pdf_text' in session:
        return redirect(url_for('preview_to_summary'))
    
    return redirect(url_for('index'))

# API routes for testing
@app.route('/api/test/reset', methods=['POST'])
def reset_test_data():
    if not app.config['TESTING']:
        return jsonify({'error': 'Test endpoints only available in testing mode'}), 403
    
    # Reset test data
    users_db.clear()
    summaries_db.clear()
    usage_db.clear()
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
