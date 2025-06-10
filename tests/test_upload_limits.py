import pytest
from flask import url_for
import io
import os
from unittest.mock import patch, MagicMock
from models import MonthlyUsage
from werkzeug.datastructures import MultiDict, FileStorage

def test_free_user_pdf_limit(app, login_as_free, free_user, mock_pdf_file, db_session):
    """Test that free users are limited to 5 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 5 PDFs
        usage = free_user.get_current_monthly_usage()
        usage.pdf_count = 5
        db_session.add(usage)
        db_session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_free.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'academic'
                },
                content_type='multipart/form-data'
            )
        
        assert response.status_code == 403
        assert "monthly limit" in response.get_data(as_text=True).lower()

def test_starter_user_pdf_limit(app, login_as_starter, starter_user, mock_pdf_file, db_session):
    """Test that starter users are limited to 50 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 50 PDFs
        usage = starter_user.get_current_monthly_usage()
        usage.pdf_count = 50
        db_session.add(usage)
        db_session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_starter.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'legal'
                },
                content_type='multipart/form-data'
            )
        
        assert response.status_code == 403
        assert "monthly limit" in response.get_data(as_text=True).lower()

def test_pro_user_pdf_limit(app, login_as_pro, pro_user, mock_pdf_file, db_session):
    """Test that pro users are limited to 100 PDFs per month."""
    with app.app_context():
        # Mock the MonthlyUsage to simulate having already uploaded 100 PDFs
        usage = pro_user.get_current_monthly_usage()
        usage.pdf_count = 100
        db_session.add(usage)
        db_session.commit()
        
        # Try to upload another PDF
        with open(mock_pdf_file, 'rb') as pdf:
            response = login_as_pro.post(
                '/pdf/upload',
                data={
                    'pdf': (io.BytesIO(pdf.read()), 'test.pdf'),
                    'document_type': 'healthcare'
                },
                content_type='multipart/form-data'
            )
        
        assert response.status_code == 403
        assert "monthly limit" in response.get_data(as_text=True).lower()

def mock_file_with_page_count(file_path, page_count):
    """Helper function to create a mock file with page count."""
    with open(file_path, 'rb') as f:
        file_data = io.BytesIO(f.read())
    
    class MockFile:
        def __init__(self, file_data, page_count):
            self.file_data = file_data
            self.page_count = page_count
            
        def read(self):
            return self.file_data.read()
            
        def seek(self, *args):
            self.file_data.seek(*args)
    
    return MockFile(file_data, page_count)

class MockFile:
    def __init__(self, file_data, page_count):
        self.file_data = file_data
        self._page_count = page_count
        self.filename = 'test.pdf'
        self.content_type = 'application/pdf'
        self.name = 'test.pdf'
        self._file = self
        
    def read(self, size=-1):
        return self.file_data.read(size)
        
    def seek(self, *args):
        self.file_data.seek(*args)
        
    def save(self, *args, **kwargs):
        pass
        
    @property
    def page_count(self):
        return self._page_count
        
    @property
    def stream(self):
        return self
        
    def close(self):
        self.file_data.close()

class MockFileStorage(FileStorage):
    """Custom FileStorage class that supports page count."""
    def __init__(self, stream, filename, content_type, page_count):
        super().__init__(stream=stream, filename=filename, content_type=content_type)
        self._page_count = page_count
        self.page_count = page_count

def create_test_data(file_data, page_count, document_type, summary_format='plain_text'):
    """Helper function to create test data with consistent format."""
    # Create form data
    data = MultiDict()
    data.add('document_type', document_type)
    data.add('summary_format', summary_format)
    data.add('_page_count', str(page_count))
    
    # Create a FileStorage instance
    file_storage = FileStorage(
        stream=file_data,
        filename='test.pdf',
        content_type='application/pdf'
    )
    data.add('pdf', file_storage)
    return data

def test_free_user_page_limit(app, login_as_free, mock_pdf_file):
    """Test that free users are limited to 20 pages per PDF."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=21,  # Exceeds free user limit
            document_type='academic'
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "PDF exceeds 20 page limit" in response.get_data(as_text=True)

def test_starter_user_page_limit(app, login_as_starter, mock_pdf_file):
    """Test that starter users are limited to 20 pages per PDF."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=21,  # Exceeds starter user limit
            document_type='legal'
        )
        
        response = login_as_starter.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "PDF exceeds 20 page limit" in response.get_data(as_text=True)

def test_pro_user_page_limit(app, login_as_pro, mock_pdf_file):
    """Test that pro users are limited to 30 pages per PDF."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=31,  # Exceeds pro user limit
            document_type='healthcare'
        )
        
        response = login_as_pro.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 403
    assert "PDF exceeds 30 page limit" in response.get_data(as_text=True)

def test_free_user_model_selection(app, login_as_free, mock_pdf_file):
    """Test that free users get GPT-3.5 for summarization."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='academic'
        )
        
        response = login_as_free.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    assert "gpt-3.5-turbo" in response.get_data(as_text=True)

def test_starter_user_model_selection(app, login_as_starter, mock_pdf_file):
    """Test that starter users get GPT-4 for summarization."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='legal'
        )
        
        response = login_as_starter.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    assert "gpt-4" in response.get_data(as_text=True)

def test_pro_user_model_selection(app, login_as_pro, pro_user, mock_pdf_file):
    """Test that pro users get GPT-4 with enhanced features for summarization."""
    with open(mock_pdf_file, 'rb') as pdf:
        file_data = io.BytesIO(pdf.read())
        data = create_test_data(
            file_data=file_data,
            page_count=10,  # Small file that should pass
            document_type='healthcare'
        )
        
        response = login_as_pro.post(
            '/pdf/upload',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert "gpt-4" in response_text
    assert "enhanced" in response_text
    
    # Verify pro users have priority processing
    assert pro_user.has_priority_processing() == True
