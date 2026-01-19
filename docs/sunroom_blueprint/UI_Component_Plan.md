# **UI/UX Component Plan: The Sunroom**

This document outlines the five major views (pages) of the Sunroom application. It describes the components in each view and the API endpoints they interact with. This plan is designed to be used by the Gemini CLI to generate the frontend application.

## **1\. View: Settings & Integrations (/settings)**

**Purpose:** A one-time setup for the user (Dr. Sledge) to grant "The Sunroom" permission to access their external accounts, specifically YouTube.

**Key Components:**

* **Integration List:** A list of available services.  
* **"YouTube" Integration Card:**  
  * **Default State:** Shows "YouTube" and a **"Connect"** button.  
  * **Connected State:** Shows "YouTube" with a green check and the text "Connected as @TheEsotericaChannel." Includes a "Disconnect" button.

**Data Flow & API Calls (The OAuth 2.0 Flow):**

1. User clicks **"Connect"**.  
2. **Frontend API Call:** GET /api/v1/auth/youtube/start.  
3. **Frontend Action:** The API returns a { "auth\_url": "..." }. The frontend *immediately redirects* the user's entire browser to this Google consent URL.  
4. **(User Approves on Google's Site):** Google handles the authentication and consent.  
5. **(Server-side Callback):** Google redirects the user to the GET /api/v1/auth/youtube/callback endpoint. Your backend server handles this, exchanges the code for a refresh\_token, and saves it to the User\_Integrations table.  
6. **Frontend Action:** The server, upon success, redirects the user's browser back to the /settings page.  
7. **Frontend API Call:** The /settings page re-loads and fetches the user's integration status. The "YouTube" card now shows the "Connected" state.

## **2\. View: Ingestion Hub (/ingest)**

**Purpose:** The main entry point for adding new Sources to the user's library.

**Key Components:**

* **Tabbed Interface:**  
  * **Tab 1: "Upload Files / Paste Text"**  
    * **File Dropzone:** A standard "drag and drop" area for PDF files.  
    * **Text Area:** A large text box for pasting raw transcript text.  
    * **Metadata Fields:** Simple text inputs for "Title" and "Author."  
    * **"Ingest" Button:** The primary action button.  
  * **Tab 2: "Import from YouTube"**  
    * **Disabled State:** If the user has not completed the /settings flow, this tab is greyed out with a message: "Please connect your YouTube account in Settings."  
    * **Enabled State:**  
      * A list of the user's YouTube playlists (fetched from the YouTube API).  
      * A button: **"Import All Transcripts from Channel"**.

**Data Flow & API Calls:**

* **On "Ingest" Button Click (Tab 1):**  
  1. The frontend uploads the file (if any) to Supabase Storage and gets a file\_upload\_id.  
  2. **Frontend API Call:** POST /api/v1/sources with the body { "title": "...", "raw\_text": "...", "file\_upload\_id": "..." }.  
  3. **Frontend Action:** The API returns 202 Accepted. The UI shows a global notification: "Success\! Your source is being processed." The user does not wait.  
* **On "Import All Transcripts" Button Click (Tab 2):**  
  1. **Frontend API Call:** POST /api/v1/sources/youtube\_batch with the body { "playlist\_ids": \["..."\] }.  
  2. **Frontend Action:** The API returns 202 Accepted. The UI shows a notification: "Import started\! Your transcripts are being fetched and will appear in the Curation Workbench."

## **3\. View: Curation Workbench (/workbench)**

**Purpose:** This is the primary "human-in-the-loop" interface. This is where the user curates "Discovered" Atoms into "Curated" knowledge.

**Key Components (3-Column Layout):**

* **Column 1: Atom Queue**  
  * **Title:** "Discovered Atoms"  
  * **"Batch Process All" Button:** A button at the top of the list.  
  * **Atom List:** A scrollable list of all Atoms with status="discovered". Each item shows the Atom.name.  
* **Column 2: Wikipage Editor**  
  * **Atom Name:** The name of the Atom selected from Column 1 (e.g., "Shi'ur Qomah").  
  * **Type (Dropdown):** A dropdown menu pre-filled with the Wikipage.type (e.g., "Text," "Person").  
  * **Summary (Text Input):** A small text input pre-filled with the Wikipage.summary from the EnrichmentAgent.  
  * **Body (Rich Text Editor):** A large, rich-text editor (like TipTap or Quill). This is where the user adds their expert synthesis.  
  * **\[✨ Synthesize Existing Notes\] Button:** Positioned directly above the Body editor.  
  * **Action Buttons:** A green **"Approve"** button and a red "Archive" button.  
* **Column 3: Contextual Mentions**  
  * **Title:** "Mentions in Your Library"  
  * **Content:** A list of text snippets from the original Sources (PDFs/transcripts) where this Atom was found. This provides context for *why* the Atom was created.

**Data Flow & API Calls:**

1. **Page Load:**  
   * **Frontend API Call:** GET /api/v1/atoms?status=discovered to populate Column 1\.  
2. **User Clicks "Batch Process All":**  
   * **Frontend API Call:** POST /api/v1/atoms/enrich with the atom\_ids of all items in Column 1\.  
   * **Frontend Action:** The UI shows a loading state. As the EnrichmentAgent completes, the summary and type fields in Column 2 will populate when an Atom is selected.  
3. **User Clicks \[✨ Synthesize Existing Notes\]:**  
   * **Frontend API Call:** POST /api/v1/wikipages/{atom\_id}/synthesize\_body.  
   * **Frontend Action:** The UI shows a loading spinner *inside* the Body editor. The API returns 202 Accepted. The frontend must then poll or use a WebSocket to listen for the Wikipage.body field to be updated, at which point it populates the editor.  
4. **User Clicks "Approve":**  
   * **Frontend API Call:** PUT /api/v1/wikipages/{atom\_id} with the full, user-edited { "summary": "...", "body": "...", "type": "..." }.  
   * **Frontend Action:** On success (200 OK), the Atom is removed from the "Discovered" list in Column 1\.

## **4\. View: Topics & Discovery (/topics)**

**Purpose:** The main "payoff" view where the user discovers new content ideas ("Natural Trailheads").

**Key Components:**

* **Section 1: "Find a Topic" (Supervised Target)**  
  * A prominent search bar with the prompt: "What do you want to write about?"  
  * A "Search" button.  
  * A results area *below* the search bar that will hold a single "Trailhead Card."  
* **Section 2: "Natural Trailheads" (Proactive Discovery)**  
  * A title: "Proactive Discoveries from Your Library"  
  * A grid of **"Trailhead Cards"**.  
  * **Trailhead Card:** Each card displays the { title, insight, suggested\_topic } from the TrailheadAgent. Each card has a **"Generate Script"** button.

**Data Flow & API Calls:**

1. **Page Load:**  
   * **Frontend API Call:** GET /api/v1/discovery/trailheads to populate the grid in Section 2\.  
2. **User Searches in Section 1:**  
   * **Frontend API Call:** GET /api/v1/discovery/search?q={user\_query\_text}.  
   * **Frontend Action:** The API returns 200 OK with a single "Trailhead" object. The UI displays this object in the "Trailhead Card" in the results area.  
3. **User Clicks "Generate Script" (on any card):**  
   * **Frontend API Call:** POST /api/v1/scripts (sending the trailhead\_id or atom\_ids).  
   * **Frontend Action:** The API returns 202 Accepted with a { "script\_id": "..." }. The frontend *immediately redirects* the user to /scripts/{script\_id}.

## **5\. View: Script Editor (/scripts/{script\_id})**

**Purpose:** To display the final, AI-generated script for review and export.

**Key Components:**

* **Main Content Area (2-Column Layout):**  
  * **Column 1: Script Editor**  
    * A large rich-text editor, pre-filled with the final script content.  
    * A "Loading" state: When the page first loads, this area shows a message: "Your script is being written by the ScriptingAgent. This may take a moment..."  
  * **Column 2: Citations Sidebar**  
    * A list of all unique, human-readable citations (e.g., "Source: *Scholem, 1965, pg. 42*") that were parsed from the script.

**Data Flow & API Calls:**

1. **Page Load (e.g., /scripts/uuid-123):**  
   * **Frontend API Call:** GET /api/v1/scripts/uuid-123.  
2. **Frontend Logic (Polling):**  
   * **Case 1: response.status \== "generating":** The UI shows the "Loading..." message. It then re-calls GET /api/v1/scripts/uuid-123 every 5 seconds (polling).  
   * **Case 2: response.status \== "complete":** The polling stops. The UI:  
     1. Populates the rich-text editor with the response.content.  
     2. Parses the content to find all citations.  
     3. Populates the "Citations Sidebar" with the unique citations.