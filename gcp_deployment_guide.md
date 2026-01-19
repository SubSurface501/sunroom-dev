# GCP Deployment Guide for The Sun Room

## 1. Prerequisites
- Google Cloud Project with Billing Enabled ($3100 Credits).
- GPU Quota Approved (NVIDIA T4).
- gcloud CLI installed locally.

## 2. Infrastructure Setup (Compute Engine)

1.  **Create VM Instance**:
    -   Name: `sunroom-core`
    -   Zone: `us-central1-a` (or any zone with T4 availability)
    -   Machine: `n1-standard-4`
    -   GPU: 1 x NVIDIA Tesla T4
    -   Image: Deep Learning on Linux (Debian 11 based, PyTorch 2.x, CUDA 12.1)
    -   Boot Disk: 100GB
    -   Firewall: Allow HTTP/HTTPS

2.  **Connect to VM**:
    -   Click "SSH" in GCP Console.

3.  **Deploy Code**:
    ```bash
    # On VM
    git clone https://github.com/YOUR_REPO/sunroom_dev.git
    cd sunroom_dev
    
    # Create .env file with your secrets
    nano .env 
    # (Paste contents of your local .env)
    
    # Start Services
    docker-compose up -d
    ```

4.  **Verify**:
    ```bash
    docker-compose logs -f worker
    # Look for "Device: NVIDIA Tesla T4"
    ```

## 3. Frontend Setup (Cloud Run)

1.  **Build & Deploy**:
    Open a terminal in your local `sunroom_dev` folder.
    
    ```bash
    cd sunroom-web
    
    # Authenticate
    gcloud auth login
    gcloud config set project YOUR_PROJECT_ID
    
    # Build
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/sunroom-web
    
    # Deploy
    gcloud run deploy sunroom-web \
      --image gcr.io/YOUR_PROJECT_ID/sunroom-web \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --memory 512Mi
    ```

2.  **Link Frontend to Backend**:
    -   Get the External IP of your `sunroom-core` VM.
    -   Update `NEXT_PUBLIC_API_URL` in your frontend environment variables (or redeploy with `--set-env-vars`).
    -   Note: For production, you should set up a static IP and domain/SSL for the VM (e.g., api.thesunroom.ca) so Cloud Run (HTTPS) can talk to it without Mixed Content warnings.

## 4. Maintenance
-   **Logs**: View logs in GCP Console > Logging.
-   **Updates**: `git pull` on VM + `docker-compose up -d --build`.
