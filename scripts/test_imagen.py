
import os
import time
import logging
from dotenv import load_dotenv
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
project_id = os.environ.get("GCP_PROJECT_ID") or "thesunroom-476921"
location = os.environ.get("GCP_LOCATION") or "us-central1"

print(f"--- Testing Vertex AI Image Generation ---")
print(f"Project: {project_id}")
print(f"Location: {location}")

try:
    print("1. Initializing Vertex AI...")
    # Force explicit quota project
    os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = project_id
    vertexai.init(project=project_id, location=location)
    print("   [OK] Initialized.")

    print("2. Loading Model...")
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    print("   [OK] Model Loaded.")

    print("3. Generating Test Image...")
    start = time.time()
    response = model.generate_images(
        prompt="A golden key resting on an ancient stone pedestal, cinematic lighting, photorealistic",
        number_of_images=1,
        aspect_ratio="16:9",
        safety_filter_level="block_only_high"
    )
    end = time.time()
    print(f"   [OK] Generated in {end - start:.2f}s")

    if response.images:
        output_file = "test_image.png"
        response.images[0].save(output_file)
        print(f"   [OK] Saved to {output_file}")
    else:
        print("   [FAIL] No images returned.")

except Exception as e:
    print(f"\n[ERROR] Failed: {e}")
