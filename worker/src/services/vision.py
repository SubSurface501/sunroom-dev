import os
import base64
from typing import List, Optional
import google.genai as genai
from PIL import Image
import io

class VisionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
             raise ValueError("GEMINI_API_KEY is required for VisionService")
        genai.configure(api_key=self.api_key)
        # Using Gemini 1.5 Flash for speed/cost balance, or Pro for quality
        self.model = genai.GenerativeModel('models/gemini-2.5-flash') 

    async def analyze_image(self, image_bytes: bytes, active_lenses: Optional[List[str]] = None) -> str:
        """
        Analyzes an image and returns a semantic description based on active lenses.
        """
        # 1. Construct the "Expert" System Prompt
        lens_context = " and ".join(active_lenses) if active_lenses else "General Knowledge"
        
        prompt = f"""
        You are an expert analyst in the fields of: {lens_context}.
        Analyze this image. 
        - If it is a chart, extract the data points and trends.
        - If it is a diagram, describe the relationships between components.
        - If it is art or a photo, describe the style, symbolism, and mood.
        
        Output a dense, semantic description suitable for embedding in a vector database. 
        Focus on the *meaning* and *information* within the image.
        """
        
        try:
            # 2. Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # 3. Call Vision Model
            response = self.model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            return f"Error analyzing image: {str(e)}"

    async def analyze_image_from_url(self, image_url: str, active_lenses: Optional[List[str]] = None) -> str:
        # Placeholder for URL fetching logic if needed later
        # Would require httpx to download bytes, then call analyze_image
        pass
