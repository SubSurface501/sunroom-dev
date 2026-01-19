\# Use an official Python runtime as a parent image  
FROM python:3.11-slim

\# Set the working directory in the container  
WORKDIR /app

\# Install system dependencies required for some Python packages  
RUN apt-get update && apt-get install \-y \\  
    build-essential \\  
 && rm \-rf /var/lib/apt/lists/\*

\# Copy the requirements file into the container  
COPY requirements.txt .

\# Install any needed packages specified in requirements.txt  
RUN pip install \--no-cache-dir \-r requirements.txt

\# Copy the backend application code into the container  
\# We assume api\_server.py, agents/tasks.py, and prompts.py  
\# are in the same directory as this Dockerfile when building.  
COPY api\_server.py .  
COPY agents/tasks.py .  
COPY prompts.py .

\# Download NLTK data (like 'punkt' for sent\_tokenize) during the build  
\# This avoids running the download in the container at runtime.  
RUN python \-m nltk.downloader punkt

\# Expose port 8000 for the FastAPI server  
EXPOSE 8000

\# Define the default command to run the API server.  
\# This will be overridden by the gcloud command when deploying the worker.  
CMD \["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "api\_server:app"\]  
