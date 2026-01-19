from fastapi import FastAPI, HTTPException, Request
import torch
from diffusers import StableDiffusionPipeline
import base64
from io import BytesIO
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global Model Variable
pipe = None

@app.on_event("startup")
def load_model():
    global pipe
    logger.info("Loading Stable Diffusion Model...")
    
    model_id = os.environ.get("MODEL_ID", "runwayml/stable-diffusion-v1-5")
    
    try:
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id, 
            torch_dtype=torch.float16,
            use_safetensors=True
        )
        
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
            logger.info("Model loaded to CUDA (GPU).")
        else:
            logger.warning("CUDA not available. Loading to CPU (Slow!).")
            pipe = pipe.to("cpu")
            
        # Enable optimizations
        # pipe.enable_attention_slicing() 
        logger.info("Model Ready.")
        
    except Exception as e:
        logger.fatal(f"Failed to load model: {e}")
        raise e

@app.get("/health")
def health_check():
    """Vertex AI Health Check."""
    if pipe is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy"}

@app.post("/predict")
async def predict(request: Request):
    """
    Vertex AI Prediction Endpoint.
    Expects format: {"instances": [{"prompt": "..."}]}
    """
    if pipe is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    instances = body.get("instances", [])
    if not instances:
        raise HTTPException(status_code=400, detail="No instances found")
    
    # Process first instance (Vertex batching can be handled later)
    instance = instances[0]
    prompt = instance.get("prompt")
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in instance")
        
    logger.info(f"Generating for prompt: {prompt}")
    
    try:
        # Generation
        image = pipe(prompt).images[0]
        
        # Convert to Base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Return in Vertex AI format
        return {"predictions": [img_str]}
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
