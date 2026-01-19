import os
import google.genai as genai
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnose_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not set. Please set it in your .env file.")
        return

    try:
        genai.configure(api_key=api_key)
        
        logger.info("Attempting to list available Gemini models...")
        response = genai.list_models()
        
        
        
        test_model_name = None
        for model in response:
            if "flash" in model.name: # Look for any model name containing "flash"
                test_model_name = model.name
                break # Found one, stop searching
        
        if not test_model_name:
            logger.warning("No 'flash' model found in the list. Skipping test generation.")
            return

        try:
            model = genai.GenerativeModel(test_model_name)
            response = model.generate_content("Ping", safety_settings={'HARASSMENT': 'block_none'})
            if response.text:
                logger.info(f"✓ Test generation successful with '{test_model_name}'. Response: {response.text.strip()[:50]}...")
            else:
                logger.warning(f"Test generation with '{test_model_name}' returned no text. This could indicate an issue.")
        except Exception as e:
            logger.error(f"✗ Test generation with '{test_model_name}' failed: {e}")
            logger.error("This often indicates quota issues, permission problems, or regional unavailability for this specific model.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during Gemini diagnosis: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    diagnose_gemini()
