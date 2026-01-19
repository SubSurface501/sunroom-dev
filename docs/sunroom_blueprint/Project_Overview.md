# **Project Overview: The Sunroom**

## **1\. Core Vision & Workflow**

**Objective:** This document outlines the complete user journey from initial sign-up to the successful and repeatable generation of multiple video scripts.

### **Phase 1: Onboarding & Library Population**

* **Step 1: Connect Services (New):** This is a one-time setup. The user (Dr. Sledge) navigates to his settings and clicks "Connect YouTube." He is redirected to a standard Google OAuth 2.0 consent screen, where he grants "The Sunroom" application permission to "View your YouTube captions."  
* **Step 2: Content Ingestion:**  
  * **Method A (Files):** User pastes transcripts or uploads PDFs (`Sources`). Clicks "Ingest."  
  * **Method B (YouTube):** User navigates to the "Import" page and clicks "Import from My Channel." The `TranscriptAgent` now runs *as an authenticated user*, using the token from Step 1 to securely and legitimately download transcripts via the YouTube Data API.

  ### **Phase 2: Automated Analysis & Manual Curation**

* **Step 3: Automated Processing (Backend):**  
  * The `ParserAgent` extracts text from all new `Sources` (from both Method A and B).  
  * `TokenizerAgent` identifies candidate `Atoms` (e.g., "Gnostic Archons").  
  * `CullAgent` removes "noise" (e.g., "like and subscribe").  
* **Step 4: Manual Curation (The Workbench):**  
  * **AI Baseline (External):** User clicks "Batch Process." The `EnrichmentAgent` queries Gemini and auto-fills the `Wikipage`'s `summary` and `type` with neutral, "Wikipedia-style" data. The `body` remains empty.  
  * **AI Synthesis (Internal):** User reviews the `summary`. They *optionally* click **\[✨ Synthesize Existing Notes\]**. The `BodySynthesizerAgent` runs, performing a RAG query *only on the user's own library* to synthesize all mentions of this `Atom` into a summary, which populates the `body` field.  
  * **User Curation (Expert):** The user now edits all fields. They correct the `summary`, and more importantly, add their own expert insights and synthesis to the AI-generated `body`. They then click "Approve."  
  * `IndexerAgent` runs in the background, creating embeddings for the new, fully curated `Atom` and its `Wikipage` content.

  ### **Phase 3: Proactive Synthesis & Content Generation**

* **(Steps 5-8 are unchanged...)**

  ## **2\. Complete Multi-Phase Agent Plan (15 Agents)**

  ### **Phase 1 & 2: The Curation & Ingestion Pipeline**

1. **`TranscriptAgent` (The API Client) (MODIFIED):** Runs on "Import from My Channel." It uses the user's stored OAuth token to make *authenticated* calls to the **YouTube Data API v3** to download transcripts.  
2. **`ParserAgent` (The Scribe):** Extracts text from all `Sources`.  
3. **`TokenizerAgent` (The Spotter):** Scans text, identifies candidates, creates "Discovered" `Atoms`.  
4. **`CullAgent` (The Janitor):** Filters "noise" from the discovered list.  
5. **`EnrichmentAgent` (The Researcher) \- (External OK):** Runs on "Batch Process" to auto-fill the `Wikipage` `summary` and `type`.  
6. **`BodySynthesizerAgent` (The Summarizer) \- (Internal Only):** Runs on `[✨ Synthesize]` button. Performs RAG on the user's *own library* to pre-populate the `Wikipage` `body`.

   ### **Phase 3: The Opportunity Discovery Engine (Step 5\)**

7. **`IndexerAgent` (The Librarian):** (Background Agent) Creates vector embeddings for all "Curated" `Atoms` and their `text_chunks`.  
8. **`CartographerAgent` (The Mapper):** Maps the entire vector space.  
9. **`ProspectorAgent` (The Bridge-Finder):** Runs "Illumination" search to find "Surprising Bridges."  
10. **`NoveltyAgent` (The Scorer):** Runs "Open-Endedness" search to score "Dense Clusters."  
11. **`TargetingAgent` (The Seeker):** Runs "Supervised Target" search.  
12. **`TrailheadAgent` (The Synthesizer):** Translates discoveries into "Natural Trailhead" cards.

    ### **Phase 3: The Scripting & Generation Pipeline (Steps 6-8)**

13. **`RetrievalAgent` (The Archivist) \- (Internal Only):** The "R" in RAG.  
14. **`ScriptingAgent` (The Writer) \- (Internal Only):** The "G" in RAG.  
15. **`CitationAgent` (The Fact-Checker):** Cleans machine tags into final citations.  
12. 