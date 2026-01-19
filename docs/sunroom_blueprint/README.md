# **The "Sunroom" Project Blueprint (GCP Edition)**

This folder contains the complete architectural and implementation blueprints for "The Sunroom," an AI-powered synthesis partner for academic content creators.

This plan has been specifically designed to be deployed using the **Google Cloud Platform (GCP) ecosystem** (Firebase, Cloud Run, Memorystore) to leverage your GCP credits.

## **How to Use This Blueprint**

You can take these files to the Gemini CLI to generate the application code.

1. **Start Here:** Read the `Project_Overview.md` to understand the full system logic.  
2. **Infrastructure:** Use the `Execution_Plan.md` as your master guide for deployment.  
3. **Database:** Use `Database_Schema.md` to create your Supabase tables and functions.  
4. **Backend:** Use `api_server.py`, `agents/tasks.py`, `prompts.py`, and `Vector_Search_Logic.md` to build the complete backend.  
5. **Frontend:** Use `UI_Component_Plan.md` to build the user-facing React application.

## **Core Blueprint Files**

* **`README.md`**: This file.  
* **`Project_Overview.md`**: A high-level explanation of the 3-phase system and all agents.  
* **`UI_Component_Plan.md`**: The complete plan for the frontend, detailing all 5 views and their components.  
* **`Database_Schema.md`**: The complete Supabase SQL schema, including tables, RLS policies, and the new `User_Integrations` table for OAuth.  
* **`API_Specification.md`**: The full specification for all API endpoints, including the new OAuth 2.0 flow.  
* **`AI_Prompts.md`**: The exact, production-ready prompts for all intelligent agents.  
* **`Vector_Search_Logic.md`**: The specific `pgvector` SQL functions for Supabase.

## **Implementation Files**

* **`agents/tasks.py`**: The complete Python/Celery code for all backend agents, including the OAuth-based `TranscriptAgent`.  
* **`api_server.py`**: The complete Python/FastAPI server code that handles all API requests.  
* **`prompts.py`**: The final Python file containing all prompts, ready for import.  
* **`database_migration.sql`**: The final SQL file to run in Supabase to create your entire database.  
* **`Execution_Plan.md`**: **(Updated)** The new master plan for deploying this entire system on the **GCP/Firebase** stack.  
* 