from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user
import os
from werkzeug.utils import secure_filename
from models import db, Upload, MonthlyUsage
import tempfile


def plan_required(min_plan_level):
    """
    Decorator to restrict access based on user's plan level
    min_plan_level can be 'free', 'starter', or 'pro'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            plan_levels = {
                'free': 0,
                'starter': 1,
                'pro': 2
            }
            
            user_plan_level = plan_levels.get(current_user.plan_type, 0)
            required_plan_level = plan_levels.get(min_plan_level, 0)
            
            if user_plan_level < required_plan_level:
                flash(f"This feature requires a {min_plan_level.capitalize()} plan or higher.", "warning")
                return redirect(url_for('pricing'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def feature_required(feature_name):
    """
    Decorator to restrict access based on specific features available to user's plan
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            # For API requests or when testing
            if request.is_xhr or request.headers.get('X-Test-Request'):
                return {"error": "Feature not available on your plan"}, 403
            # For normal browser requests
            else:
                flash(f"This feature is not available on your current plan.", "warning")
                return redirect(url_for('pricing'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_upload_limits(f):
    """
    Decorator to check if user has reached their monthly PDF upload limit
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if not current_user.can_upload_pdf():
            flash(f"You have reached your monthly PDF upload limit for your {current_user.plan_type.capitalize()} plan.", "warning")
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def check_page_limit(f):
    """
    Decorator to check if uploaded PDF exceeds page limit for user's plan
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if 'pdf' not in request.files:
            flash("No file part", "error")
            return redirect(request.url)
            
        file = request.files['pdf']
        
        if file.filename == '':
            flash("No selected file", "error")
            return redirect(request.url)
            
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            flash("Only PDF files are allowed", "error")
            return redirect(request.url)
            
        # Save file temporarily to check page count
        temp_dir = tempfile.gettempdir()
        filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Get page count (using PyPDF2 or similar library)
        # This is a placeholder - in a real app you would use a PDF library
        try:
            import PyPDF2
            with open(temp_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
        except Exception as e:
            os.remove(temp_path)
            flash(f"Error processing PDF: {str(e)}", "error")
            return redirect(request.url)
            
        # Check if page count exceeds limit
        max_pages = current_user.get_max_pages_per_file()
        if page_count > max_pages:
            os.remove(temp_path)
            flash(f"Your PDF has {page_count} pages, but your plan only allows {max_pages} pages per file.", "warning")
            return redirect(url_for('dashboard'))
            
        # Store page count in session for later use
        request.page_count = page_count
        request.temp_pdf_path = temp_path
            
        return f(*args, **kwargs)
    return decorated_function

def track_pdf_usage(document_type, summary_format):
    """
    Decorator to track PDF usage after successful processing
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # After successful processing, update usage statistics
            if hasattr(request, 'page_count') and hasattr(request, 'temp_pdf_path'):
                # Get or create current monthly usage
                usage = current_user.get_current_monthly_usage()
                
                # Increment PDF count
                usage.increment_pdf_count()
                
                # Estimate token count (very rough estimate)
                # In a real app, you would get this from the AI service response
                estimated_tokens = request.page_count * 500  # Rough estimate
                
                # Create upload record
                upload = Upload(
                    user_id=current_user.id,
                    filename=os.path.basename(request.temp_pdf_path),
                    page_count=request.page_count,
                    token_count=estimated_tokens,
                    document_type=document_type,
                    summary_format=summary_format
                )
                
                db.session.add(upload)
                usage.add_token_usage(estimated_tokens)
                db.session.commit()
                
                # Clean up temp file
                if os.path.exists(request.temp_pdf_path):
                    os.remove(request.temp_pdf_path)
            
            return result
        return decorated_function
    return decorator

# Middleware class for enforcing plan limits
class PlanLimitMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        # This middleware would be called for every request
        # For simplicity, we'll implement the core logic in decorators instead
        return self.app(environ, start_response)
