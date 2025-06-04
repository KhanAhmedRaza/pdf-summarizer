import pytest
from flask import url_for
import io
import os
from unittest.mock import patch, MagicMock

def test_free_user_cannot_use_gpt4(app, login_as_free, mock_pdf_file):
    """Test that free users cannot use GPT-4."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_free.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'academic',
                'summary_format': 'plain_text',
                'model': 'gpt-4'  # Trying to force GPT-4
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow using GPT-4
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_free_user_cannot_access_legal_documents(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access legal document types."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_free.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'legal',  # Legal documents are not for free users
                'summary_format': 'plain_text'
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow legal document type
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_free_user_cannot_access_interactive_format(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access interactive summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_free.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'academic',
                'summary_format': 'interactive'  # Interactive format is not for free users
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow interactive format
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_free_user_cannot_access_visual_format(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access visual summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_free.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'academic',
                'summary_format': 'visual'  # Visual format is not for free users
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow visual format
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_starter_user_cannot_access_healthcare_documents(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access healthcare document types."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_starter.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'healthcare',  # Healthcare documents are for pro users only
                'summary_format': 'interactive'
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow healthcare document type
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_starter_user_cannot_access_visual_format(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access visual summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_starter.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'legal',
                'summary_format': 'visual'  # Visual format is for pro users only
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow visual format
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_starter_user_cannot_access_flowchart_format(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access flowchart summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        response = login_as_starter.post(
            '/pdf/upload',
            data={
                'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                'document_type': 'legal',
                'summary_format': 'flowchart'  # Flowchart format is for pro users only
            },
            content_type='multipart/form-data'
        )
    
    # Should not allow flowchart format
    assert response.status_code in [403, 400, 302]
    if response.status_code == 302:
        # If redirected, verify it's not to a successful processing page
        assert '/pdf/process' not in response.location or 'error' in response.location

def test_feature_access_by_plan(app, db_session, free_user, starter_user, pro_user):
    """Test feature access using direct checks."""
    with app.app_context():
        # Refresh users
        free_user = db_session.merge(free_user)
        starter_user = db_session.merge(starter_user)
        pro_user = db_session.merge(pro_user)
        
        # Test free user access
        assert not free_user.can_access_feature('legal')
        assert not free_user.can_access_feature('interactive')
        assert not free_user.can_access_feature('priority_support')
        
        # Test starter user access
        assert starter_user.can_access_feature('legal')
        assert starter_user.can_access_feature('interactive') 
        assert starter_user.can_access_feature('priority_support')
        
        # Test pro user access
        assert pro_user.can_access_feature('legal')
        assert pro_user.can_access_feature('healthcare')
        assert pro_user.can_access_feature('visual')


