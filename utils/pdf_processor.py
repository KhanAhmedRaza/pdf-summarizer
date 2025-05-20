import os
import PyPDF2
from io import BytesIO

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        # For testing mode, return mock text
        if os.environ.get('TESTING', 'False').lower() == 'true':
            return "This is mock text extracted from a PDF for testing purposes."
        
        # Extract text from PDF
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        
        return text
    
    except Exception as e:
        # Log the error and re-raise
        print(f"Error extracting text from PDF: {str(e)}")
        raise
