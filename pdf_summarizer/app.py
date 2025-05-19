import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import uuid
import secrets
from utils.pdf_processor import extract_text_from_pdf, preprocess_text
from utils.summarizer import summarize_text, optimize_text_for_summarization
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(24))
app.config['UPLOAD_FOLDER'] = '/tmp/pdf_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'apikey')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@summrize.site')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
def get_db_connection():
    conn = sqlite3.connect('pdf_summarizer.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user:
        return User(user['id'], user['email'], user['password'])
    return None

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_user_usage_today(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    
    # Check if there's a record for today
    usage = conn.execute(
        'SELECT count FROM usage_logs WHERE user_id = ? AND date = ?', 
        (user_id, today)
    ).fetchone()
    
    conn.close()
    
    if usage:
        return usage['count']
    return 0

def increment_user_usage(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    
    # Check if there's a record for today
    usage = conn.execute(
        'SELECT id FROM usage_logs WHERE user_id = ? AND date = ?', 
        (user_id, today)
    ).fetchone()
    
    if usage:
        # Update existing record
        conn.execute(
            'UPDATE usage_logs SET count = count + 1 WHERE id = ?',
            (usage['id'],)
        )
    else:
        # Create new record
        conn.execute(
            'INSERT INTO usage_logs (user_id, date, count) VALUES (?, ?, 1)',
            (user_id, today)
        )
    
    conn.commit()
    conn.close()

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        app.logger.error(f"Email error: {str(e)}")
        return False

# Jinja2 filters
@app.template_filter('nl2br')
def nl2br(value):
    return value.replace('\n', '<br>')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        usage_count = get_user_usage_today(current_user.id)
        remaining = max(0, 3 - usage_count)
    else:
        remaining = 0
    
    return render_template('index.html', remaining=remaining)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Email and password are required')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            flash('Email already exists')
            conn.close()
            return redirect(url_for('register'))
        
        conn.execute(
            'INSERT INTO users (email, password) VALUES (?, ?)',
            (email, generate_password_hash(password))
        )
        conn.commit()
        
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        user_obj = User(user['id'], user['email'], user['password'])
        login_user(user_obj)
        
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['email'], user['password'])
            login_user(user_obj)
            return redirect(url_for('index'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_pdf():
    # Check if user has reached daily limit
    usage_count = get_user_usage_today(current_user.id)
    if usage_count >= 3:
        flash('You have reached your daily limit of 3 summaries')
        return redirect(url_for('index'))
    
    # Check if file was uploaded
    if 'pdf_file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    
    # Check if file was selected
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    # Check if file is allowed
    if not allowed_file(file.filename):
        flash('Only PDF files are allowed')
        return redirect(url_for('index'))
    
    # Save file with secure filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    try:
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(filepath)
        
        # Optimize text for summarization
        optimized_text = optimize_text_for_summarization(extracted_text)
        
        # Generate summary using GPT-3.5
        summary = summarize_text(optimized_text)
        
        # Store summary in session
        session['summary'] = summary
        session['original_filename'] = filename
        
        # Increment usage count
        increment_user_usage(current_user.id)
        
        # Redirect to summary page
        return redirect(url_for('show_summary'))
    
    except Exception as e:
        flash(f'Error processing PDF: {str(e)}')
        return redirect(url_for('index'))
    
    finally:
        # Clean up the uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/summary')
@login_required
def show_summary():
    # Check if there's a summary to display
    if 'summary' not in session:
        flash('No summary available')
        return redirect(url_for('index'))
    
    # Get summary from session
    summary = session['summary']
    filename = session.get('original_filename', 'document.pdf')
    
    return render_template('summary.html', summary=summary, filename=filename)

@app.route('/email_summary', methods=['POST'])
@login_required
def email_summary():
    # Check if there's a summary to email
    if 'summary' not in session:
        flash('No summary available to email')
        return redirect(url_for('index'))
    
    email = request.form.get('email')
    if not email:
        flash('Email address is required')
        return redirect(url_for('show_summary'))
    
    summary = session['summary']
    filename = session.get('original_filename', 'document.pdf')
    
    subject = f"PDF Summary: {filename}"
    body = f"Here is your summary of {filename}:\n\n{summary}\n\nThank you for using PDF Summarizer!"
    
    if send_email(email, subject, body):
        flash('Summary has been sent to your email')
    else:
        flash('Failed to send email. Please try again later.')
    
    return redirect(url_for('show_summary'))

if __name__ == '__main__':
    # Use Gunicorn for production
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
