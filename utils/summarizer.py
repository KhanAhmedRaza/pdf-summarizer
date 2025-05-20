import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_summary(text, max_tokens=500):
    """
    Generate a summary of the provided text using OpenAI's GPT model.
    
    Args:
        text (str): The text to summarize
        max_tokens (int): Maximum length of the summary
        
    Returns:
        str: The generated summary
    """
    try:
        # For testing mode, return a mock summary
        if os.environ.get('TESTING', 'False').lower() == 'true':
            return "This is a test summary generated for automated testing purposes."
        
        # Use OpenAI API to generate summary
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes PDF documents."},
                {"role": "user", "content": f"Please summarize the following text in a concise, well-structured format. Focus on the key points and main ideas:\n\n{text}"}
            ],
            max_tokens=max_tokens,
            temperature=0.5,
        )
        
        # Extract and return the summary
        summary = response.choices[0].message.content.strip()
        return summary
    
    except Exception as e:
        # Log the error and return a generic message
        print(f"Error generating summary: {str(e)}")
        return "An error occurred while generating the summary. Please try again later."
