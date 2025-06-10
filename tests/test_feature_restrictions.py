import pytest
from flask import url_for
import io
import os
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import MultiDict, FileStorage

class MockFileStorage(FileStorage):
    """Custom FileStorage class that supports page count."""
    def __init__(self, stream, filename, content_type, page_count):
        super().__init__(stream=stream, filename=filename, content_type=content_type)
        self._page_count = page_count
        self.page_count = page_count

def create_test_data(file_data, page_count, document_type, summary_format='plain_text', model=None):
    """Helper function to create test data with consistent format."""
    # Create form data
    data = MultiDict()
    data.add('document_type', document_type)
    data.add('summary_format', summary_format)
    data.add('_page_count', str(page_count))
    if model:
        data.add('model', model)
    
    # Create a FileStorage instance
    file_storage = FileStorage(
        stream=file_data,
        filename='test.pdf',
        content_type='application/pdf'
    )
    data.add('pdf', file_storage)
    return data

def test_free_user_cannot_use_gpt4(app, login_as_free, mock_pdf_file):
    """Test that free users cannot use GPT-4."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='academic',
            summary_format='plain_text',
            model='gpt-4'  # Trying to force GPT-4
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "GPT-4 is not available on your plan" in response.get_data(as_text=True)

def test_free_user_cannot_access_legal_documents(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access legal document types."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='legal',  # Legal documents are not for free users
            summary_format='plain_text'
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support legal documents" in response.get_data(as_text=True)

def test_free_user_cannot_access_interactive_format(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access interactive summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='academic',
            summary_format='interactive'  # Interactive format is not for free users
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support interactive format" in response.get_data(as_text=True)

def test_free_user_cannot_access_visual_format(app, login_as_free, mock_pdf_file):
    """Test that free users cannot access visual summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='academic',
            summary_format='visual'  # Visual format is not for free users
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support visual format" in response.get_data(as_text=True)

def test_starter_user_cannot_access_healthcare_documents(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access healthcare document types."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='healthcare',  # Healthcare documents are for pro users only
            summary_format='interactive'
        )
        
        response = login_as_starter.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support healthcare documents" in response.get_data(as_text=True)

def test_starter_user_cannot_access_visual_format(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access visual summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='legal',
            summary_format='visual'  # Visual format is for pro users only
        )
        
        response = login_as_starter.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support visual format" in response.get_data(as_text=True)

def test_starter_user_cannot_access_flowchart_format(app, login_as_starter, mock_pdf_file):
    """Test that starter users cannot access flowchart summary formats."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='legal',
            summary_format='flowchart'  # Flowchart format is for pro users only
        )
        
        response = login_as_starter.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "Your plan does not support flowchart format" in response.get_data(as_text=True)

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


