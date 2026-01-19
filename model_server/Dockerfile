FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# Install system dependencies if any (usually not needed for base prediction)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Vertex AI default is 8080)
EXPOSE 8080

# Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
