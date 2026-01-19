# MirrorMind V7: Deployment Manual
## Operations Guide for "The Collective" Infrastructure

**Version:** 7.0
**Stack:** Python/Celery (Worker), Next.js (Web), Supabase (DB), Redis (Broker)

---

### 1. Prerequisites
*   **Docker Desktop:** Required for local orchestration.
*   **Supabase Project:** Must have `pgvector` enabled.
*   **OpenAI/Gemini API Keys:** Required for the Intelligence Layer.
*   **Python 3.11+:** For local worker development.

### 2. Environment Configuration
Create a `.env` file in the root directory. **DO NOT COMMIT THIS FILE.**

```env
# Database (Supabase)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-service-role-key"
DB_HOST="aws-0-us-east-1.pooler.supabase.com"
DB_PORT="6543"
DB_NAME="postgres"
DB_USER="postgres.your-user"
DB_PASSWORD="your-password"

# AI Models
GEMINI_API_KEY="your-google-key"
OPENAI_API_KEY="your-openai-key"

# Worker Infrastructure
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="rpc://"

# Security
SECRET_KEY="your-internal-secret"
```

### 3. Database Migration (The Schema)
The system relies on a strict SQL schema.
Run migrations in order found in `migrations/`:

```bash
# Example: Apply migration 065 (Epoch Protocol)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/065_add_epoch_protocol.sql
```
*Critical:* Ensure RLS policies are enabled (`migrations/051_final_nodes_rls_fix.sql`) before going to production.

### 4. Local Development (The "Hybrid" Mode)
We run the Frontend and API locally, but the Worker inside Docker (optional) or locally for debugging.

**Terminal 1: Redis**
```bash
docker run -p 6379:6379 redis
```

**Terminal 2: The Worker (The Brain)**
```bash
# Windows (Powershell)
$env:PYTHONPATH="."; celery -A worker.src.agents.tasks worker --loglevel=info -P solo
```
*Note:* `-P solo` is required on Windows to avoid process forking issues.

**Terminal 3: The API Server (The Bridge)**
```bash
python api_server.py
```

**Terminal 4: The Frontend (The Face)**
```bash
cd sunroom-web
npm run dev
```

### 5. Production Deployment (GCP/Fly.io)

#### A. The Worker (Docker)
Build the worker image using `Dockerfile.worker`.
```bash
docker build -f Dockerfile.worker -t sunroom-worker .
docker push gcr.io/your-project/sunroom-worker
```
Deploy to a VM or Container Service (e.g., Cloud Run is hard for Celery; prefer GKE or a VM with Docker Compose).

#### B. The Frontend (Vercel)
Deploy `sunroom-web` to Vercel.
*   Add `NEXT_PUBLIC_API_URL` environment variable pointing to your hosted API Server.

#### C. The API Server
Deploy `api_server.py` to Cloud Run or a lightweight VM.

### 6. Troubleshooting
*   **"Connection Refused"**: Check if Redis is running.
*   **"Hallucinations"**: Check `worker.log`. If the `ReviewAgent` is crashing, the system fails open (in V6) or closed (in V7). Ensure `ReviewAgent` is initialized.
*   **"Auth Failed"**: Check RLS policies in Supabase. The `service_role` key bypasses RLS, but the user client does not.