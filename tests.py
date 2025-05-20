import os
import unittest
import tempfile
from app import app, users_db, summaries_db, usage_db

class PDFSummarizerTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        
        # Reset test data before each test
        self.reset_test_data()
        
        # Create a test PDF file
        self.test_pdf_content = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'
        self.test_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        self.test_pdf.write(self.test_pdf_content)
        self.test_pdf.close()
        
        # Create a large test PDF file (exceeding 5MB limit)
        self.large_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        self.large_pdf.write(b'%PDF-1.4' + b'0' * (5 * 1024 * 1024 + 1000))
        self.large_pdf.close()
    
    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.test_pdf.name):
            os.unlink(self.test_pdf.name)
        if os.path.exists(self.large_pdf.name):
            os.unlink(self.large_pdf.name)
    
    def reset_test_data(self):
        response = self.app.post('/api/test/reset')
        self.assertEqual(response.status_code, 200)
    
    def register_user(self, email='test@example.com', password='password', name='Test User'):
        return self.app.post('/register', data={
            'email': email,
            'password': password,
            'name': name
        }, follow_redirects=True)
    
    def login_user(self, email='test@example.com', password='password'):
        return self.app.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)
    
    def test_landing_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Summarize Any PDF in Seconds Using AI', response.data)
    
    def test_register_and_login(self):
        # Test registration
        response = self.register_user()
        self.assertEqual(response.status_code, 200)
        
        # Test logout
        self.app.get('/logout', follow_redirects=True)
        
        # Test login
        response = self.login_user()
        self.assertEqual(response.status_code, 200)
    
    def test_upload_without_login(self):
        # Upload a PDF without being logged in
        with open(self.test_pdf.name, 'rb') as pdf:
            response = self.app.post('/upload_pdf', data={
                'pdf_file': (pdf, 'test.pdf')
            }, follow_redirects=True)
        
        # Should show preview page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign in or create an account', response.data)
    
    def test_upload_with_login(self):
        # Register and login
        self.register_user()
        
        # Upload a PDF while logged in
        with open(self.test_pdf.name, 'rb') as pdf:
            response = self.app.post('/upload_pdf', data={
                'pdf_file': (pdf, 'test.pdf')
            }, follow_redirects=True)
        
        # Should redirect to summary page
        self.assertEqual(response.status_code, 200)
    
    def test_file_size_limit(self):
        # Try to upload a file larger than 5MB without being logged in
        with open(self.large_pdf.name, 'rb') as pdf:
            response = self.app.post('/upload_pdf', data={
                'pdf_file': (pdf, 'large_test.pdf')
            }, follow_redirects=True)
        
        # Should show error about file size
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'File size exceeds', response.data)
    
    def test_usage_limit(self):
        # Register and login
        self.register_user()
        
        # Upload PDFs until reaching the limit (3 per day)
        for i in range(3):
            with open(self.test_pdf.name, 'rb') as pdf:
                response = self.app.post('/upload_pdf', data={
                    'pdf_file': (pdf, f'test{i}.pdf')
                }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
        
        # Try to upload one more
        with open(self.test_pdf.name, 'rb') as pdf:
            response = self.app.post('/upload_pdf', data={
                'pdf_file': (pdf, 'test_extra.pdf')
            }, follow_redirects=True)
        
        # Should show error about usage limit
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'daily limit', response.data)
    
    def test_google_auth_simulation(self):
        # Test the Google auth simulation
        response = self.app.get('/auth/google')
        self.assertEqual(response.status_code, 200)
        
        # Simulate Google callback
        response = self.app.post('/auth/google/callback', data={
            'email': 'google_user@example.com',
            'name': 'Google User'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
