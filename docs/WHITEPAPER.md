# MirrorMind V7: The Neurosymbolic Operating System
## A Manifesto for Deterministic Narrative Control

**Version:** 7.5 (The Ontological Cage)  
**Date:** December 2025  
**Author:** The Sun Room Engineering Team

---

### 1. The Problem: The Hallucination Tax
Generative AI, in its current "Black Box" paradigm, is fundamentally probabilistic. It predicts the *likely* next token, not the *true* next token. For creative workflows, this stochastic nature is a feature (creativity). For long-form intellectual property, it is a fatal bug (drift).

We call this the **Hallucination Tax**. 
Every minute a human spends verifying that an AI didn't invent a new magic system in Chapter 4, or ensuring that a character didn't forget their own trauma, is a tax on productivity. As context windows grow, this tax does not vanish; it compounds.

### 2. The Solution: The Neurosymbolic "White Box"
MirrorMind V7 (The Sun Room) is not an AI Agent. It is an **Operating System** that treats the Large Language Model (LLM) as a mere rendering engine (GPU), while retaining the "World Logic" (CPU) in a deterministic Graph Database.

We have inverted the standard architecture:
*   **Standard AI:** The Model holds the World State (Implicit/Fuzzy).
*   **MirrorMind:** The Database holds the World State (Explicit/Rigid). The Model is only allowed to *describe* it.

### 3. Core Architecture: The Ontological Cage
The heart of V7 is the **Ontological Cage**, a Fail-Closed logic gate that enforces continuity before text is committed to memory. It operates on three distinct layers:

#### Layer 1: The Symbolic Gate (Physics)
*   **Mechanism:** Regex/Tag-based prohibitions.
*   **Function:** If the Universe is "Materialist," words like *Magic*, *Spell*, or *Ghost* are mathematically impossible to write.
*   **Result:** Hard Rejection (Score 0.0).

#### Layer 2: The Semantic Ledger (Intent)
*   **Mechanism:** Vector-based Semantic Search + Intent Matching.
*   **Function:** The "Narrative Intent" (e.g., "Reveal the traitor") is passed to the Reviewer. If the generated prose is beautiful but fails to advance the plot, it is rejected.
*   **Result:** Narrative Drift is arrested at the sentence level.

#### Layer 3: The Voice Audit (Psychology)
*   **Mechanism:** Character Stance Verification via LLM Audit.
*   **Function:** Every character has a "Voice Ledger" (e.g., "Kaelen is a cynical Stoic"). If Kaelen speaks with uncharacteristic optimism, the Cage flags a **Voice Violation**.
*   **Result:** Characters remain consistent across million-word sagas.

### 4. The Mathematical Model: Resonant Energy
To quantify "Quality," we utilize an Energy-Based Model (EBM) that scores every generated thought against a geometric mean of three variables:

$$
P^*(x) = (\alpha \cdot \beta \cdot \gamma)^{1/3}
$$

Where:
*   **$\alpha$ (Internal Consistency):** Distance from the User's "Golden Samples" (Style).
*   **$\beta$ (External Novelty):** Distance from existing "Clichés" (via OpenAlex/Search).
*   **$\gamma$ (Trajectory Alignment):** Cosine similarity to the Narrative Arc (The Plan).

If $P^*(x) < 0.8$, the system triggers a **Simulated Annealing** loop, increasing "Temperature" (Randomness) to break out of the local minimum, then cooling down to crystallize the best output.

### 5. The "Greenlight" Protocol
Unlike "Agent Swarms" that spiral into chaos, MirrorMind uses a linear, stage-gated production pipeline:

1.  **The Architect (System 2):** Drafts the graph structure (Nodes & Edges). No prose is written until the logic is sound.
2.  **The Casting Director:** Freezes visual and psychological assets into a "Master Asset Bank."
3.  **The Writers' Room (Parallel):** Multiple agents write scenes in parallel, but they are constrained by the *same* Asset Bank and World Graph.
4.  **The Crystallizer:** Approved content is re-ingested into the Vector Database, becoming "Canon" for future generations.

### 6. Technical Stack
*   **Brain:** Python 3.11+, Celery, Redis (Asynchronous Orchestration)
*   **Memory:** Supabase (Postgres + pgvector)
*   **Interface:** Next.js 14, Tailwind CSS, React Force Graph
*   **Reasoning:** Hybrid RAG (Dense Vector + Keyword Search + Knowledge Graph)

### 7. Conclusion
We are not building a better Chatbot. We are building the printing press for the age of infinite leverage. By solving the Hallucination Tax, The Sun Room enables a single creator to orchestrate vast, coherent, and commercially viable intellectual property.