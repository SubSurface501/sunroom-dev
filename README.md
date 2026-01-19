# The Sun Room (MirrorMind V7)

> **Status:** Operational (The Collective Release)
> **Version:** 7.5 (Meta-Provenance & Autonomous Inquiry)
> **Date:** December 2025

**The Sun Room** is a cognitive engine and collaborative workspace designed to augment human creativity. Powered by **MirrorMind**, an advanced AI architecture, it acts not just as a text generator, but as a digital intellectual partner. It digests your personal library, learns your unique "resonance" (style, beliefs, core concepts), and helps you weave complex, graph-based narratives ("Story Volumes") that are mathematically tuned to be meaningful.

---

## ✨ Core Concepts

The system has evolved beyond simple RAG (Retrieval Augmented Generation) into a **Resonant-Energy Architecture**.

-   **The Energy-Based Model (EBM):** Unlike standard LLMs, MirrorMind uses an EBM to score generated content for **Novelty** (creative divergence) vs. **Resonance** (adherence to your established worldview). This is paired with **Simulated Annealing**, where the generation "temperature" decays over time, allowing wild ideas to crystallize into structured, coherent prose.
-   **The Collective:** Users can form "Projects" to share knowledge clusters ("Lenses") and collaborate on stories. A "Lens Market" allows you to borrow a collaborator's expertise (e.g., "User A's Physics Lens") to inform your own writing.
-   **Spatiotemporal Resonance:** The engine understands time. You can filter generation by historical eras from your own knowledge base (e.g., "Resonate with my thoughts from 2018-2019").
-   **Meta-Provenance:** Every generated thought is traceable back to its source. The UI allows you to inspect the exact source text or image that inspired any given paragraph.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Frontend** | Next.js, React, Tailwind CSS |
| **Backend API** | Python, FastAPI |
| **Task Queue** | Celery, Redis |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI/LLM** | Google Gemini 1.5 Pro |
| **Auth** | Google OAuth 2.0 |

---

## 🏗️ Project Structure

A brief overview of the key directories:

-   `sunroom-web/`: The Next.js frontend application.
-   `worker/`: Home of the Python-based autonomous agents (Celery workers).
-   `api_server.py`: The FastAPI backend that serves the UI and manages requests.
-   `db/`: Contains database schemas, CRUD operations, and session management.
-   `migrations/`: SQL files for database schema evolution.
-   `docs/`: Project documentation.

---

## 🤖 The Agentic Workforce

The system is composed of specialized autonomous agents located in `worker/src/agents/`:

-   **🕵️ Librarian (`librarian.py`):** Ingests sources (PDFs, YouTube) and extracts metadata.
-   **⚛️ Indexer (`indexing.py`):** Breaks content into "Atoms" and generates vector embeddings.
-   **🔍 Discovery (`discovery.py`):** Identifies and fills knowledge gaps by searching the web.
-   **📐 Architect (`architect_v2.py`):** Designs the graph-based "Blueprint" of a story.
-   **✍️ Storybook (`storybook.py`):** Drafts content for each node, tuned to the user's voice.
-   **💎 Crystallize (`crystallize.py`):** Ingests completed stories back into the AI's memory, closing the learning loop.

For a detailed breakdown of the core content processing workflow (Atomization and Reconstruction), see the [workflow guide](./docs/workflow_atomization_and_reconstruction.md).

---

## 🚀 Getting Started

### Prerequisites
-   **Python 3.11+**
-   **Node.js 18+**
-   **Redis:** For the Celery task queue. Can be run locally or via Docker.
-   **Supabase Account:** For the PostgreSQL database and vector store.

### 1. Environment Setup
Create a `.env` file in the root directory. See the `example.env` for the required variables. You will need to fill in your Supabase and Google Gemini API credentials.
```bash
# Example .env structure
DATABASE_URL="postgresql://user:password@host:port/postgres"
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-service-role-key"
GEMINI_API_KEY="your-gemini-api-key"
# ... and other variables
```

### 2. Installation
**Backend (Python):**
```bash
python -m venv venv
# On Windows
.\venv\Scripts\Activate
# On macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend (Next.js):**
```bash
cd sunroom-web
npm install
cd ..
```

---

## 🖥️ Local Development

You will need **three** separate terminals. Before starting, ensure your Redis server is running.

-   **If using Docker for Redis (recommended):** `docker run -p 6379:6379 -d redis/redis-stack-server`
-   **If installed locally:** Start the Redis server according to your OS instructions.

### Terminal 1: Celery Worker
This handles all asynchronous AI and data processing tasks.
```bash
# On Windows:
.\venv\Scripts\Activate
python -m celery -A worker.src.agents.tasks worker -l info --pool=solo

# On macOS/Linux:
source venv/bin/activate
celery -A worker.src.agents.tasks worker -l info --pool=solo
```

### Terminal 2: API Server
This runs the FastAPI backend.
```bash
# On Windows:
.\venv\Scripts\Activate
python api_server.py

# On macOS/Linux:
source venv/bin/activate
python api_server.py
```
*API will be available at `http://localhost:8000`*

### Terminal 3: Frontend
This runs the Next.js web application.
```bash
cd sunroom-web
npm run dev
```
*UI will be available at `http://localhost:3000`*

---

## 📝 Usage

### The Workflow
1.  **Ingest Content:** Go to the dashboard and upload a PDF or paste a YouTube URL. The Librarian and Indexer agents will process it into the knowledge base.
2.  **Draft a Blueprint:** Start a "New Volume" with a central theme. The Architect agent will generate a graph of chapters and sections.
3.  **Greenlight & Render:** Click "Greenlight" to have the Storybook agent write the narrative, node by node.
4.  **Crystallize:** Once finished, the story is "Crystallized" back into the AI's memory, making it available for future resonance.

### For Developers: Direct API testing
You can trigger the story drafting process directly via the API.
```powershell
# Example using PowerShell:
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/volumes/draft_structure" -Method POST -Headers @{"accept"="application/json"; "Content-Type"="application/json"} -Body '{ "user_id": "YOUR_USER_ID", "theme": "The nature of consciousness", "root_concept": "The Simulation Hypothesis" }'
```

---

## ☁️ Deployment

This application is designed to be deployed across multiple services.
-   **Frontend (`sunroom-web`):** Recommended for Vercel.
-   **Backend (`api_server.py` & Worker):** Recommended for Railway or any service that can run Python apps and background workers.

A `Procfile` for services like Heroku or Railway might look like this:
```
web: uvicorn api_server:app --host 0.0.0.0 --port $PORT
worker: celery -A worker.src.agents.tasks worker --loglevel=info
```

For a detailed guide on a more advanced deployment using **Google Cloud Platform**, see [`docs/gcp_deployment_guide.md`](./docs/gcp_deployment_guide.md).

---

## 🤝 Contributing
-   **Frontend:** `sunroom-web/`
-   **Agents:** `worker/src/agents/`
-   **Database:** `db/schemas.py` & `migrations/`

**Project The Sun Room** — *Where ideas go to grow.*
