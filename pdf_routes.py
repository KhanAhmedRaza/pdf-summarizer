from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from models import db, User, Upload, MonthlyUsage
from decorators import plan_required, feature_required, check_upload_limits, check_page_limit, track_pdf_usage
import os

# Create blueprint for PDF processing
pdf_bp = Blueprint('pdf', __name__)

@pdf_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@check_upload_limits
@check_page_limit
def upload_pdf():
    """Handle PDF upload with plan-specific restrictions"""
    if request.method == 'POST':
        # Get document type from form
        document_type = request.form.get('document_type', 'academic')
        
        # Check if user can access this document type
        if not current_user.can_access_feature(document_type):
            return jsonify({"error": f"Your plan does not support {document_type} documents"}), 403
        
        # Get summary format from form
        summary_format = request.form.get('summary_format', 'plain_text')
        
        # Check if user can access this summary format
        if not current_user.can_access_feature(summary_format):
            return jsonify({"error": f"Your plan does not support {summary_format} format"}), 403
        
        # Check if file was uploaded
        if 'pdf' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        # Get the uploaded file
        pdf_file = request.files['pdf']
        if not pdf_file or not pdf_file.filename:
            return jsonify({"error": "No file provided"}), 400
            
        # Check model access first
        requested_model = request.form.get('model')
        if requested_model == 'gpt-4' and current_user.plan_type == 'free':
            return jsonify({"error": "GPT-4 is not available on your plan"}), 403
            
        # Check page limit based on user's plan
        max_pages = current_user.get_max_pages_per_file()
        
        # Get page count from form data
        page_count = request.form.get('page_count')
        if page_count is None:
            return jsonify({"error": "Could not determine PDF page count"}), 400
            
        try:
            page_count = int(page_count)
        except ValueError:
            return jsonify({"error": "Invalid page count"}), 400
            
        if page_count > max_pages:
            return jsonify({"error": f"PDF exceeds {max_pages} page limit"}), 403
            
        # Process the PDF (this would be handled by the track_pdf_usage decorator)
        # In a real app, you would send the PDF to your summarization service here
        
        # Return success response with model info based on user's plan
        model = current_user.get_ai_model()
        response_data = {
            "success": True,
            "model": model
        }
        
        if current_user.plan_type == "pro":
            response_data["enhanced"] = True
            
        return jsonify(response_data), 200
    
    # GET request - show upload form with plan-specific options
    return render_template('upload.html', 
                          max_pages=current_user.get_max_pages_per_file(),
                          available_document_types=get_available_document_types(),
                          available_summary_formats=get_available_summary_formats())

@pdf_bp.route('/process')
@login_required
@track_pdf_usage(document_type=lambda: request.args.get('document_type', 'academic'),
                summary_format=lambda: request.args.get('summary_format', 'plain_text'))
def process():
    """Process the uploaded PDF with plan-specific AI model"""
    document_type = request.args.get('document_type', 'academic')
    summary_format = request.args.get('summary_format', 'plain_text')
    
    # In a real app, this would process the PDF with the appropriate AI model
    # For this mock implementation, we'll just show the plan-specific settings
    
    # Get AI model based on plan
    ai_model = current_user.get_ai_model()
    
    # Get processing priority
    priority = "High" if current_user.has_priority_processing() else "Standard"
    
    # Mock processing logic
    return render_template('processing.html',
                          document_type=document_type,
                          summary_format=summary_format,
                          ai_model=ai_model,
                          priority=priority)

# Helper functions for available features based on plan
def get_available_document_types():
    """Get document types available for current user's plan"""
    document_types = [
        {'id': 'academic', 'name': 'Academic'},
        {'id': 'business', 'name': 'Business'}
    ]
    
    if current_user.can_access_feature('legal'):
        document_types.append({'id': 'legal', 'name': 'Legal'})
    
    if current_user.can_access_feature('healthcare'):
        document_types.append({'id': 'healthcare', 'name': 'Healthcare'})
        
    if current_user.can_access_feature('finance'):
        document_types.append({'id': 'finance', 'name': 'Finance'})
        
    if current_user.can_access_feature('tech'):
        document_types.append({'id': 'tech', 'name': 'Technology'})
    
    return document_types

def get_available_summary_formats():
    """Get summary formats available for current user's plan"""
    formats = [
        {'id': 'plain_text', 'name': 'Plain Text'}
    ]
    
    if current_user.can_access_feature('interactive'):
        formats.append({'id': 'interactive', 'name': 'Interactive'})
        
    if current_user.can_access_feature('todo_list'):
        formats.append({'id': 'todo_list', 'name': 'To-Do List'})
        
    if current_user.can_access_feature('visual'):
        formats.append({'id': 'visual', 'name': 'Visual'})
        
    if current_user.can_access_feature('flowchart'):
        formats.append({'id': 'flowchart', 'name': 'Flowchart'})
    
    return formats
