# V8 "The Prism" - Physics-First Narrative Roadmap

## 0. Executive Summary: The Neurosymbolic Shift
The current "Prose-First" approach (V7) suffers from the "Hallucination Tax": the LLM is responsible for both the narrative and the physical laws of the world. Because LLMs are probabilistic, they prioritize narrative tropes over logical consistency.

**V8 "The Prism"** inverts this causality. We move to a **State-First** model where Python code (The Physics Kernel) dictates the reality of the world, and the LLM acts as a "Renderer" that translates binary state changes into human-resonant prose.

---

## 1. Architecture Comparison: Why V7 Failed vs. Why V8 Succeeds

| Component | **V7: The Prose-First Author** | **V8: The Physics-First Simulation** | **The "Why" (Thinking)** |
| :--- | :--- | :--- | :--- |
| **Causality** | **Narrative -> State**. LLM writes a scene; we try to "guess" what changed in the world afterward. | **State -> Narrative**. Python executes a logic-gate; the LLM "paints" the result afterward. | Prevents "Action Hallucination" (e.g. using a key the player doesn't have). |
| **Logic Layer** | **Probabilistic (LLM)**. Decisions are based on word frequency and tropes. | **Deterministic (Python)**. Decisions are based on Boolean checks and Math. | Ensures that 1 + 1 always equals 2, regardless of how "creative" the prompt is. |
| **Memory** | **Textual Recall**. Uses RAG to find old summaries. Loses detail over time. | **Procedural Hashing**. Uses Seed + ID to regenerate the world mathematically. | Allows for "Infinite Object Permanence" without bloating the database. |
| **State Sync** | **Extracted**. We use an LLM "Analyst" to audit text. Slow and error-prone. | **Inherent**. The state is updated *before* the text is written. | Guaranteed consistency across nodes, chapters, and epochs. |
| **Fail-Safe** | **Soft-Fail**. The story continues even if it doesn't make sense. | **Fail-Closed**. The simulation stops if an illegal action is proposed. | Protects the "Canon" of the universe at all costs. |

---

## 2. The Four Implementation Gears (The Princeton Alignment)

### Gear 1: The Physics Kernel (Deterministic Truth)
We create a rigid Python layer that handles "Hard Physics."
*   **The Hybrid Ledger:**
    *   **Hard State (Python-Only):** `LocationID`, `Inventory[]`, `Health`, `TurnCount`, `EquippedItem`.
    *   **Soft State (LLM-proposal):** `Reputation`, `EmotionalState`, `PoliticalTension`.
*   **The Resolver:** A symbolic engine where an action like `Move(Gate)` is rejected if `HasItem(Key)` returns `False`. No tokens are wasted writing a "failure" scene if the action is physically impossible.

### Gear 2: Procedural Hashing (Scaling Memory)
Following the Princeton "Infinite World" model, we stop storing every environmental detail.
*   **The World Seed:** Every Universe gets a 256-bit seed.
*   **Deterministic Hash:** `hash(Seed + Location_ID)` generates the static atmosphere.
*   **Permanence:** If a character leaves a room and returns 10,000 turns later, the hash produces the *exact same* description (e.g., "The blue rug with the coffee stain") without ever storing that text in the database.

### Gear 3: The Perception Manifest (Structured Latent State)
We stop giving the Writer a "Change Log" and start giving it a "Field of Vision."
*   **The Manifest:** A JSON object passed to the Writer for every page.
    *   **Static:** Environmental data from the Procedural Hash.
    *   **Dynamic:** The current Hard State (Who is here? What is open?).
    *   **Narrative:** The current Soft State (What is the vibe?).
*   **The Goal:** By giving the LLM a full "Perception Manifest," it cannot "forget" that the room is dark or that the character is bleeding, because those variables are present in every prompt.

### Gear 4: The Self-Correction Bridge (Hybrid State Loop)
We allow the LLM to update "Hearts and Minds" but not "Gears and Levers."
*   **Soft State Updates:** After rendering a scene, the LLM proposes updates to the `SoftState` (e.g., "The NPC is now angry").
*   **The Auditor:** A small Python check ensures the LLM hasn't tried to sneak a `HardState` change (like giving itself gold) into the `SoftState` proposal.

---

## 3. The Execution Roadmap

### Phase 1: The Simulation Core
1.  **File:** `worker/src/simulation/actions.py` - Define the Pydantic "Verbs."
2.  **File:** `worker/src/simulation/engine.py` - Build the Boolean "Logic Gates" for physics.
3.  **File:** `worker/src/simulation/procedural.py` - Implement the Hash-based environmental generator.

### Phase 2: The Planner Shift
1.  Refactor `VolumeArchitectAgent`. Instead of writing "Beats," it outputs a `List[Action]`.
2.  Implement the **Simulation Loop**: Planner proposes -> Engine Validates -> Planner adjusts if Rejected.

### Phase 3: The Rendering Engine
1.  Refactor `StorybookAgent`. It receives the `PerceptionManifest` + `ActionOutcome`.
2.  It uses the **"Scribe Prompt"**: "You are a camera. You do not decide the outcome. Describe the events [X, Y, Z] that have already occurred in State [S]."

---

## 4. Expected Outcome
Upon completion, the system will be **Narratively Deterministic**. You can generate a story from a single "Seed Prose," and the internal logic will remain 100% consistent across a 50-chapter saga. Hallucinations will be confined to "adjectives" (imagination), never "objects" or "outcomes" (physics).
