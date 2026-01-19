# **Execution Plan (GCP & Firebase Edition)**

This document outlines the infrastructure and deployment steps for "The Sunroom" using your $2000 in GCP credits. This plan replaces the Vercel/Render strategy.

Our stack will be:

* **Frontend:** React/Vite (deployed to **Firebase Hosting**)  
* **Backend API:** FastAPI (`api_server.py`) (deployed to **Cloud Run**)  
* **Backend Worker:** Celery (`agents/tasks.py`) (deployed to **Cloud Run**)  
* **Broker:** Redis (deployed to **Memorystore for Redis**)  
* **Database:** Supabase (PostgreSQL \+ pgvector)

## **1\. Required Infrastructure & Setup**

You must set up these services before asking the Gemini CLI to write code.

1. **Supabase (Database & Auth):**  
   * Create a new project on [Supabase](https://supabase.com/).  
   * Enable the `vector` and `pgsodium` extensions.  
   * Run the entire `database_migration.sql` file in the SQL Editor.  
   * **Collect Keys:** `SUPABASE_URL`, `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_KEY`.  
2. **Google Cloud Console (GCP Project):**  
   * Create a new GCP Project (this is where your $2000 in credits live).  
   * **Enable APIs:** Go to `APIs & Services` \-\> `Library` and enable:  
     * `Gemini API` (or `AI Platform (Vertex AI) API`)  
     * `YouTube Data API v3`  
     * `Cloud Run Admin API`  
     * `Cloud Build API`  
     * `Memorystore for Redis API`  
   * **Create Gemini API Key:** (Credentials \-\> Create Credentials \-\> API Key).  
   * **Create OAuth Credentials:** (Credentials \-\> Create Credentials \-\> OAuth 2.0 Client ID).  
     * Select `Web application`.  
     * **CRITICAL:** Add your future redirect URIs. For now, add a placeholder.  
     * **Collect Keys:** `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.  
3. **Firebase (Frontend Hosting):**  
   * Go to the [Firebase Console](https://console.firebase.google.com/) and `Add project`.  
   * **Select your existing GCP Project** to link them.  
   * In your new Firebase project, go to `Hosting` and click `Get started`.  
4. **Memorystore for Redis (Broker):**  
   * In your GCP Project, go to `Memorystore for Redis` and create a new instance.  
   * This will give you a `HOST` IP and `PORT` (e.g., `10.0.0.3:6379`).  
   * **Collect Key:** Your `CELERY_BROKER_URL` will be `redis://10.0.0.3:6379/0`.  
   * **CRITICAL:** Your Cloud Run services will need a **Serverless VPC Connector** to be able to "see" this private Redis instance. The GCP console will guide you through setting this up.

## **2\. Order of Operations for Gemini CLI**

Follow this build order.

1. **Set Up Infrastructure:** Complete all steps in Section 1\.  
2. **Set Up Local Environment:**  
   * Create a new project directory.  
   * Create a `.env` file and paste *all* your secret keys (`SUPABASE_URL`, `GEMINI_API_KEY`, `CELERY_BROKER_URL`, etc.).  
3. **Create Backend Files:**  
   * Give the CLI your `prompts.py` file.  
   * Give the CLI your `agents/tasks.py` file.  
   * Give the CLI your `api_server.py` file.  
4. **Create Backend Deployment Files:**  
   * **Ask the CLI:** "Create a `Dockerfile` for my Python application. It must install `requirements.txt` (FastAPI, Celery, google-api-python-client, etc.) and copy `api_server.py`, `agents/tasks.py`, and `prompts.py` into the container."  
   * **Ask the CLI:** "Create a `requirements.txt` file based on all the imports in my Python files."  
5. **Build the Frontend:**  
   * **Ask the CLI:** "Based on `UI_Component_Plan.md`, create a new React \+ Vite application. Show me all the main JSX components (`CurationWorkbench.jsx`, `TopicsView.jsx`, etc.) and the main `App.jsx`."  
6. **Create Frontend Deployment Files:**  
   * **Ask the CLI:** "Create the `firebase.json` and `.firebaserc` files I need to deploy this React app to Firebase Hosting. The build command is `npm run build` and the build directory is `dist`."  
7. **Deploy (Using CLI-generated commands):**  
   * **Ask the CLI:** "Give me the `gcloud` command to:  
     * Build my `Dockerfile` using Cloud Build.  
     * Deploy the resulting container to **Cloud Run** as a web service named `sunroom-api`. It must be connected to my VPC Connector."  
   * **Ask the CLI:** "Give me the `gcloud` command to:  
     * Deploy the *same container* to **Cloud Run** as a background worker named `sunroom-worker`.  
     * It must *not* have a public URL.  
     * It must override the container's default command to run: `celery -A agents.tasks worker --loglevel=info`.  
     * It must also be connected to my VPC Connector."  
   * **Ask the CLI:** "Give me the `firebase` command to deploy my frontend." (It will be `firebase deploy --only hosting`).  
8. **Final Step:**  
   * Your `gcloud run deploy sunroom-api` command will give you a public URL (e.g., `https://sunroom-api-XXXX.a.run.app`).  
   * Go back to your **Google Cloud Console** \-\> `Credentials`.  
   * Add this public URL to your OAuth "Authorized redirect URIs" list:  
     * `https://sunroom-api-XXXX.a.run.app/api/v1/auth/youtube/callback`