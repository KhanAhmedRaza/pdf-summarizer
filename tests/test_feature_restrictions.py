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

def test_feature_access_by_plan(app, login_as_free, login_as_starter, login_as_pro):
    """Test feature access for different plans using the test route."""
    
    # Test features that should be accessible to all plans
    for client in [login_as_free, login_as_starter, login_as_pro]:
        response = client.get('/test/features/plain_text')
        assert response.status_code == 200
        
        response = client.get('/test/features/academic')
        assert response.status_code == 200
        
        response = client.get('/test/features/business')
        assert response.status_code == 200
    
    # Test features that should be accessible to starter and pro plans only
    for feature in ['legal', 'interactive', 'todo_list', 'priority_support']:
        # Free user should not have access
        response = login_as_free.get(f'/test/features/{feature}')
        assert response.status_code == 403
        
        # Starter and Pro users should have access
        for client in [login_as_starter, login_as_pro]:
            response = client.get(f'/test/features/{feature}')
            assert response.status_code == 200
    
    # Test features that should be accessible to pro plan only
    for feature in ['healthcare', 'finance', 'tech', 'visual', 'flowchart', 'community_access']:
        # Free and Starter users should not have access
        for client in [login_as_free, login_as_starter]:
            response = client.get(f'/test/features/{feature}')
            assert response.status_code == 403
        
        # Pro user should have access
        response = login_as_pro.get(f'/test/features/{feature}')
        assert response.status_code == 200
