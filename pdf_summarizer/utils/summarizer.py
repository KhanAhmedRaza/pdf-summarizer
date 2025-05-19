import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_text(text, max_tokens=500):
    """
    Summarize text using OpenAI's GPT-3.5 model.
    
    Args:
        text (str): Text to summarize
        max_tokens (int): Maximum number of tokens for the summary
        
    Returns:
        str: Summarized text
    """
    try:
        # Prepare the prompt
        prompt = f"Please summarize the following text concisely, highlighting the key points and main ideas:\n\n{text}"
        
        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes PDF documents accurately and concisely."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.5,  # Lower temperature for more focused summaries
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        # Extract the summary from the response
        summary = response.choices[0].message['content'].strip()
        return summary
        
    except Exception as e:
        raise Exception(f"Error generating summary: {str(e)}")

def estimate_token_usage(text):
    """
    Estimate the number of tokens in the text.
    This is a rough approximation - OpenAI's tokenizer is more complex.
    
    Args:
        text (str): Text to estimate tokens for
        
    Returns:
        int: Estimated number of tokens
    """
    # A very rough approximation: 1 token ≈ 4 characters or 0.75 words
    return max(len(text) // 4, len(text.split()) // 0.75)

def optimize_text_for_summarization(text, max_input_tokens=3000):
    """
    Optimize text for summarization by truncating if necessary.
    
    Args:
        text (str): Text to optimize
        max_input_tokens (int): Maximum number of input tokens
        
    Returns:
        str: Optimized text
    """
    estimated_tokens = estimate_token_usage(text)
    
    if estimated_tokens <= max_input_tokens:
        return text
    
    # If text is too long, truncate it
    # This is a simple approach - more sophisticated approaches could be used
    # such as extracting key sentences or paragraphs
    
    # Approximate ratio to truncate
    ratio = max_input_tokens / estimated_tokens
    
    # Split by words and take the first portion
    words = text.split()
    truncated_words = words[:int(len(words) * ratio)]
    
    truncated_text = ' '.join(truncated_words)
    return truncated_text + "... [Text truncated due to length]"
