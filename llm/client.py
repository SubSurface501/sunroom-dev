import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import google.generativeai as genai

import os
import logging
import json
import time
import random
from typing import Optional, List, Dict
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential
from llm.rate_limiter import rate_limit_wait

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    """
    V9.9 "Legacy-Stable" Bridge.
    Uses the google-cloud-aiplatform (vertexai) SDK for generation to avoid dependency conflicts,
    while using google-generativeai for the embedding API.
    """
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        if self.debug_mode:
            logger.warning("LLMClient is in DEBUG MODE. API calls will be mocked.")

        # Keep the "Auto-Pivot" Model Strategy, with 2.0 model as priority
        self.model_tiers = os.environ.get("GEMINI_MODEL_PRIORITY", 'gemini-2.0-flash-exp,gemini-1.5-pro,gemini-1.5-flash').split(',')
        self.active_model_index = 0
        
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "thesunroom-476921")
        self.location = os.environ.get("GCP_LOCATION", "us-central1")
        
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            logger.info(f"GOOGLE_APPLICATION_CREDENTIALS found at: {cred_path}")
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"Vertex AI Initialized for project:{self.project_id}")
        else:
            logger.warning(f"⚠️ GOOGLE_APPLICATION_CREDENTIALS path not found or invalid: {cred_path}")
        
        logger.info(f"LLMClient Initialized (SDK: vertexai) | Default Model: {self.get_active_model_name()}")

    def get_active_model_name(self) -> str:
        return self.model_tiers[self.active_model_index]

    def pivot_model(self) -> bool:
        """Switches to the next model in the tier list."""
        if self.active_model_index < len(self.model_tiers) - 1:
            self.active_model_index += 1
            logger.warning(f"↴ Pivoting to backup model: {self.get_active_model_name()}")
            return True
        logger.error("☠️ All models in the tier list have failed.")
        return False

    def chat_completion(self, prompt: str, json_schema: dict = None, temperature: float = 0.5, system_instruction: str = None, model: str = None):
        if self.debug_mode:
            return self._get_mock_response(prompt)

        def api_call():
            model_name = model or self.get_active_model_name()
            gen_model = GenerativeModel(model_name, system_instruction=[system_instruction] if system_instruction else None)
            
            # Use GenerationConfig from vertexai, which supports response_mime_type
            generation_config = GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json" if json_schema else "text/plain",
            )
            
            logger.info(f"Sending request to Vertex AI model: {model_name}...")
            response = gen_model.generate_content(prompt, generation_config=generation_config)
            return response.text

        return self._request_with_backoff(api_call)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embedding(self, text: str) -> List[float]:
        if self.debug_mode: return [0.0] * 768
        if not text or not text.strip(): return [0.0] * 768
        
        try:
            rate_limit_wait()
            # Use the google-generativeai SDK for its simpler embedding API
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="RETRIEVAL_DOCUMENT"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"GenAI Embedding failed: {e}")
            return [0.0] * 768

    def _get_mock_response(self, prompt: str) -> str:
        """Returns a mock JSON response based on keywords in the prompt."""
        if "ONTOLOGICAL CAGE" in prompt:
            return json.dumps({ "score": 0.9, "issues": [], "suggestion": "This looks good." })
        if "ENTITY_DISCOVERY_PROMPT" in prompt:
            return json.dumps({ "new_entities": [{"name": "Grizzled Barnaby", "role": "The blacksmith", "type": "character"}]})
        return json.dumps({"status": "ok", "message": "Default mock."})

    def _request_with_backoff(self, api_call_func, max_retries=5, base_delay=2):
        rate_limit_wait()
        delay = base_delay
        for attempt in range(max_retries):
            try:
                return api_call_func()
            except Exception as e:
                # Handle model not found by pivoting
                if "404" in str(e) or "not found" in str(e).lower():
                    logger.warning(f"Model {self.get_active_model_name()} not found. Pivoting...")
                    if self.pivot_model():
                        # We need to retry the request with the new model, so we continue the loop
                        continue 
                
                if attempt == max_retries - 1:
                    logger.error(f"Final attempt failed. Error: {e}")
                    raise
                delay *= 2
                sleep_time = delay + random.uniform(0, 1)
                logger.warning(f"API Error ({e}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

    # Image generation logic can be complex and model-specific.
    # This is a placeholder and may need adjustment based on the exact Vertex AI API for Imagen.
    def generate_image(self, prompt: str, output_path: str) -> Optional[str]:
        if self.debug_mode:
            return self._generate_placeholder_image(output_path, prompt)
        
        try:
            from vertexai.preview.vision_models import ImageGenerationModel
            model = ImageGenerationModel.from_pretrained("imagen@0.0.5")
            logger.info(f"Generating image with Imagen: {prompt[:50]}...")
            response = model.generate_images(prompt=prompt, number_of_images=1)
            if response and response.images:
                response.images[0].save(location=output_path)
                return output_path
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
        return None

    def _generate_placeholder_image(self, output_path: str, prompt: str) -> str:
        # Simple placeholder generation
        return None

def get_llm_client(debug_mode: bool = False) -> LLMClient:
    return LLMClient(debug_mode=debug_mode)