from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from extensions import db
from models import User
from utils.pdf_processor import extract_text_from_pdf
from utils.summarizer import generate_summary
from datetime import datetime
import os

main_bp = Blueprint('main', __name__)

# Example route moved to blueprint
@app.route('/manage/migrate', methods=['GET'])
def run_migration():
    # Add some basic security (like an admin check or secret token)
    if request.args.get('token') != os.environ.get('MIGRATION_SECRET_TOKEN'):
        return "Unauthorized", 401
        
    # Import Flask-Migrate's upgrade function
    from flask_migrate import upgrade
    
    # Run the migration
    db_upgrade()
    
    return "Migration completed successfully"
    
@login_manager.user_loader
def load_user(user_id):
    # Load user directly from the database using SQLAlchemy
    return User.query.get(user_id)

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

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user
from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    print(f"Login route accessed with method: {request.method}")
    
    if request.method == 'POST':
        # Manual login form submitted
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Form data received - Email: {email}, Password: {'*' * len(password) if password else 'None'}")
        
        # Find user by email using SQLAlchemy
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            print(f"Login successful for user: {email}")
            login_user(user)
            
            # Check if there's a pending PDF in session
            if 'pdf_text' in session:
                return redirect(url_for('preview_to_summary'))
            
            return redirect(url_for('index'))
        else:
            print(f"Login failed for email: {email}")
            flash('Invalid email or password', 'danger')
    
    # For both GET requests and failed POST requests
    return render_template('login.html')

    
    
@app.route('/login/google')
def login_google():
    
    # Google OAuth login
    redirect_uri = url_for('login_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)
    
@app.route('/login/callback')
def login_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.userinfo(token=token)
        
        # Check if user exists in database
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new user if they don't exist
            import uuid
            user_id = str(uuid.uuid4())
            
            user = User(
                id=user_id,
                name=user_info['name'],
                email=user_info['email'],
                profile_pic=user_info.get('picture')
            )
            
            # Add user to database
            db.session.add(user)
            db.session.commit()
        
        # Log in the user
        login_user(user)
        
        # Check if there's a pending PDF in session
        if 'pdf_text' in session:
            return redirect(url_for('preview_to_summary'))
        
        # Redirect to dashboard or requested page
        next_page = session.get('next', '/')
        session.pop('next', None)
        return redirect(next_page)
    
    except Exception as e:
        print(f"Error in OAuth callback: {str(e)}")
        flash('Authentication failed', 'danger')
        return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered', 'danger')
                return render_template('register.html')
            
            # Create new user
            import uuid
            user_id = str(uuid.uuid4())
            password_hash = generate_password_hash(password)
            
            new_user = User(
                id=user_id,
                name=name,
                email=email,
                password_hash=password_hash
            )
            
            # Add user to database
            db.session.add(new_user)
            db.session.commit()
            
            # Log in the new user
            login_user(new_user)
            
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {str(e)}")
            flash('An error occurred during registration', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Your dashboard code here
    return render_template('dashboard.html')

@app.route('/summary/<summary_id>')
@login_required
def view_summary(summary_id):
    # Your summary viewing code here
    return render_template('summary.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/upgrade')
def upgrade():
    # Check if user is logged in
    if not current_user.is_authenticated:
        flash('Please log in to upgrade your account', 'warning')
        return redirect(url_for('login'))
    
    # This is a placeholder for your actual upgrade logic
    # You would typically:
    # 1. Show payment options
    # 2. Process payment
    # 3. Update user's subscription status in database
    
    return render_template('upgrade.html')  # Create this template or use an existing one



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
    
   
@app.route('/post_login')
@login_required
def post_login():
    intended_plan = session.pop('intended_plan', None)
    if intended_plan:
        return redirect(url_for('plans.select_plan', plan_type=intended_plan))
    return redirect(url_for('dashboard'))


# Continue for all other routes...