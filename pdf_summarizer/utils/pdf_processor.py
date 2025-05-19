import PyPDF2
from io import BytesIO

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    extracted_text = ""
    
    try:
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get the number of pages
            num_pages = len(pdf_reader.pages)
            
            # Extract text from each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                extracted_text += page.extract_text() + "\n\n"
            
            # Basic preprocessing
            extracted_text = extracted_text.strip()
            
            # Handle empty PDFs
            if not extracted_text:
                return "No text could be extracted from this PDF. It may contain scanned images or be password protected."
                
            return extracted_text
            
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def preprocess_text(text, max_tokens=4000):
    """
    Preprocess text to optimize for token usage.
    
    Args:
        text (str): Text to preprocess
        max_tokens (int): Maximum number of tokens to keep
        
    Returns:
        str: Preprocessed text
    """
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Simple token estimation (rough approximation)
    estimated_tokens = len(text.split())
    
    # If text is too long, truncate it
    if estimated_tokens > max_tokens:
        words = text.split()
        truncated_text = ' '.join(words[:max_tokens])
        return truncated_text + "... [Text truncated due to length]"
    
    return text
