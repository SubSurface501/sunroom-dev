# UI Development Plan for The Sunroom

This document outlines the detailed plan for building the Graph Visualization ("The Constellation") and the Script Editor ("The Workbench") for "The Sunroom" project.

---

### 1. The Graph Visualization ("The Constellation")

**User Needs (The "Why"):**
*   **Serendipity:** Enable users to discover unexpected connections between ingested content.
*   **Spatial Context:** Provide a non-linear view of knowledge, revealing topic density and unexplored areas.
*   **Traceability:** Allow users to visually link generated `Trailheads` (Ideas) back to their originating `Atoms` (Concepts) and `Sources` (Videos/PDFs).

**UX/UI Design:**
*   **Visual Metaphor:** A night sky or neural network, featuring a dark background with glowing nodes.
*   **Node Types:**
    *   **Sources (Squares):** Represents raw content like Videos or PDFs.
    *   **Atoms (Circles):** Represents extracted core concepts. Node size will correspond to frequency or importance.
    *   **Trailheads (Stars/Triangles):** Represents generated content ideas.
*   **Interactions:**
    *   **Zoom/Pan:** Intuitive navigation across an infinite canvas.
    *   **Click-to-Inspect:** Clicking a node opens a **"Side Panel"** (Inspector) to display full text, summaries, or embedded media players without navigating away.
    *   **Filtering:** A control bar for dynamic visibility toggling (e.g., "Hide Sources," "Show only Atoms related to 'Consciousness'").

**Technical Implementation Strategy:**
*   **Library:** `react-force-graph-2d` (Canvas-based). Chosen for its performance with many nodes and its organic physics simulation, which aligns with the "Sunroom" metaphor.
*   **Data Structure:** A new API endpoint (`/api/v1/graph/data`) will be developed to transform existing SQL relations (`Sources` -> `Atoms_to_Sources` -> `Atoms` -> `Trailheads`) into a standardized JSON format comprising nodes and links.

---

### 2. The Script Editor ("The Workbench")

**User Needs (The "Why"):**
*   **Overcome Writer's Block:** Provide integrated assistance for content creation, guiding users through the writing process.
*   **Integrated Research:** Keep relevant `Atoms` (research notes) directly accessible alongside the text editor, eliminating context switching.
*   **Steerable Expansion:** Offer AI-powered suggestions and expansions based on highlighted text or selected `Atoms`.

**UX/UI Design:**
*   **Layout:** A two-column split view.
    *   **Left (65%):** The main editor area, designed for a clean, distraction-free writing experience (similar to Notion).
    *   **Right (35%):** The "Context Drawer," displaying `Atoms` relevant to the currently selected `Trailhead`.
*   **Drag-and-Drop:** Users can drag `Atoms` from the Context Drawer into the editor to paste citations or summaries.
*   **AI Commands:** A slash command (`/`) menu will trigger AI operations like "Draft Intro," "Rephrase," or "Suggest Transition."

**Technical Implementation Strategy:**
*   **Library:** **TipTap**. Selected for its headless nature (full UI control), React compatibility, and extensibility for custom nodes (e.g., embedded Atoms).
*   **State Management:** A new `script_content` column (JSON/HTML) will be added to the `Trailheads` table (or a dedicated `Scripts` table if a one-to-many relationship is desired) to persist draft content.

---

### Execution Plan

The development will proceed in two distinct phases, starting with the Graph Visualization to establish a discovery interface for ideas.

#### Phase 1: The Graph (Discovery)
1.  **Backend:** Create `/api/v1/graph` endpoint.
    *   Objective: Fetch all `Sources`, `Atoms`, and `Trailheads`, then format them into a `{ nodes: [...], links: [...] }` JSON structure.
2.  **Frontend:** Install `react-force-graph-2d`.
    *   Objective: Integrate the library into the React application.
3.  **Frontend:** Build `GraphView.tsx` component.
    *   Objective: Implement the force-directed graph, mapping different node types to appropriate colors and shapes.
4.  **Frontend:** Build `NodeInspector.tsx` (Side Panel) component.
    *   Objective: Display detailed information about a node when it is clicked, appearing as a side panel.

#### Phase 2: The Editor (Creation)
1.  **Backend:** Update Schema.
    *   Objective: Add a `content` column (storing JSON/HTML) to the `Trailheads` table.
    *   Objective: Create API endpoints to facilitate saving and loading of script content.
2.  **Frontend:** Install `TipTap` and its dependencies.
    *   Objective: Integrate the rich text editor library.
3.  **Frontend:** Build `ScriptEditor.tsx` component.
    *   Objective: Implement the core text editor, including Markdown shortcuts and custom node support.
    *   Objective: Develop the "Context Drawer" to display and allow interaction with `Atoms` relevant to the selected `Trailhead`.
