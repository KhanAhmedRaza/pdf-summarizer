import pytest
from flask import url_for
import io
import os
from unittest.mock import patch, MagicMock

def test_free_user_pdf_limit(app, login_as_free, free_user, mock_pdf_file):
    """Test that free users are limited to 5 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 5 PDFs
        usage = free_user.get_current_monthly_usage()
        usage.pdf_count = 5
        app.db.session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_free.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'academic',
                    'summary_format': 'plain_text'
                },
                content_type='multipart/form-data'
            )
        
        # Should return an error or redirect to an error page
        assert response.status_code in [403, 302]
        if response.status_code == 302:
            # If redirected, make sure it's not to the processing page
            assert '/pdf/process' not in response.location

def test_starter_user_pdf_limit(app, login_as_starter, starter_user, mock_pdf_file):
    """Test that starter users are limited to 50 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 50 PDFs
        usage = starter_user.get_current_monthly_usage()
        usage.pdf_count = 50
        app.db.session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_starter.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'academic',
                    'summary_format': 'interactive'
                },
                content_type='multipart/form-data'
            )
        
        # Should return an error or redirect to an error page
        assert response.status_code in [403, 302]
        if response.status_code == 302:
            # If redirected, make sure it's not to the processing page
            assert '/pdf/process' not in response.location

def test_pro_user_pdf_limit(app, login_as_pro, pro_user, mock_pdf_file):
    """Test that pro users are limited to 100 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 100 PDFs
        usage = pro_user.get_current_monthly_usage()
        usage.pdf_count = 100
        app.db.session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_pro.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'healthcare',
                    'summary_format': 'visual'
                },
                content_type='multipart/form-data'
            )
        
        # Should return an error or redirect to an error page
        assert response.status_code in [403, 302]
        if response.status_code == 302:
            # If redirected, make sure it's not to the processing page
            assert '/pdf/process' not in response.location

@patch('pdf_routes.check_page_limit')
def test_free_user_page_limit(mock_check_page_limit, app, login_as_free, mock_pdf_file):
    """Test that free users are limited to 20 pages per PDF."""
    # Mock the page count check to simulate a 21-page PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 21)
    
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_free.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'academic',
                'summary_format': 'plain_text'
            },
            content_type='multipart/form-data'
        )
    
    # Should return an error or redirect to an error page
    assert response.status_code in [403, 302]
    if response.status_code == 302:
        # If redirected, make sure it's not to the processing page
        assert '/pdf/process' not in response.location

@patch('pdf_routes.check_page_limit')
def test_starter_user_page_limit(mock_check_page_limit, app, login_as_starter, mock_pdf_file):
    """Test that starter users are limited to 20 pages per PDF."""
    # Mock the page count check to simulate a 21-page PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 21)
    
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_starter.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'legal',
                'summary_format': 'interactive'
            },
            content_type='multipart/form-data'
        )
    
    # Should return an error or redirect to an error page
    assert response.status_code in [403, 302]
    if response.status_code == 302:
        # If redirected, make sure it's not to the processing page
        assert '/pdf/process' not in response.location

@patch('pdf_routes.check_page_limit')
def test_pro_user_page_limit(mock_check_page_limit, app, login_as_pro, mock_pdf_file):
    """Test that pro users are limited to 30 pages per PDF."""
    # Mock the page count check to simulate a 31-page PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 31)
    
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_pro.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'healthcare',
                'summary_format': 'visual'
            },
            content_type='multipart/form-data'
        )
    
    # Should return an error or redirect to an error page
    assert response.status_code in [403, 302]
    if response.status_code == 302:
        # If redirected, make sure it's not to the processing page
        assert '/pdf/process' not in response.location

@patch('pdf_routes.check_page_limit')
def test_free_user_model_selection(mock_check_page_limit, app, login_as_free, free_user, mock_pdf_file):
    """Test that free users get GPT-3.5 for summarization."""
    # Mock the page count check to simulate a valid PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 10)
    
    # Mock the AI model selection
    with patch('models.User.get_ai_model') as mock_get_model:
        mock_get_model.return_value = "gpt-3.5-turbo"
        
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_free.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'academic',
                    'summary_format': 'plain_text'
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )
        
        # Verify the model selection was called
        mock_get_model.assert_called_once()
        
        # Verify the model is GPT-3.5
        assert free_user.get_ai_model() == "gpt-3.5-turbo"

@patch('pdf_routes.check_page_limit')
def test_starter_user_model_selection(mock_check_page_limit, app, login_as_starter, starter_user, mock_pdf_file):
    """Test that starter users get GPT-4 for summarization."""
    # Mock the page count check to simulate a valid PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 10)
    
    # Mock the AI model selection
    with patch('models.User.get_ai_model') as mock_get_model:
        mock_get_model.return_value = "gpt-4"
        
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_starter.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'legal',
                    'summary_format': 'interactive'
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )
        
        # Verify the model selection was called
        mock_get_model.assert_called_once()
        
        # Verify the model is GPT-4
        assert starter_user.get_ai_model() == "gpt-4"

@patch('pdf_routes.check_page_limit')
def test_pro_user_model_selection(mock_check_page_limit, app, login_as_pro, pro_user, mock_pdf_file):
    """Test that pro users get GPT-4 with enhanced features for summarization."""
    # Mock the page count check to simulate a valid PDF
    mock_check_page_limit.side_effect = lambda f: setattr(f, 'page_count', 20)
    
    # Mock the AI model selection
    with patch('models.User.get_ai_model') as mock_get_model:
        mock_get_model.return_value = "gpt-4"
        
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_pro.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'healthcare',
                    'summary_format': 'visual'
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )
        
        # Verify the model selection was called
        mock_get_model.assert_called_once()
        
        # Verify the model is GPT-4
        assert pro_user.get_ai_model() == "gpt-4"
        
        # Verify pro users have priority processing
        assert pro_user.has_priority_processing() == True
