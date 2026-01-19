# Sunroom Test Suite

This directory contains scripts for running integration and end-to-end tests on the Sunroom system.

## Main Test Suite (`run_test_suite.py`)

This script is designed to test the full "Architecture of Universes" workflow under various conditions. It runs in a fast "debug mode" by mocking expensive AI calls, allowing you to verify the system's internal logic and data flow in seconds instead of hours.

### Prerequisites

1.  Ensure all Python dependencies are installed: `pip install -r requirements.txt`
2.  Ensure your `.env` file is correctly configured with your Supabase URL and service key.
3.  Ensure your database migrations are up to date.
4.  Ensure your Celery worker is **NOT** running. This script runs the agents directly and synchronously for easier debugging.

### How to Run

The script is executed from the project root directory (`sunroom_dev`). You must specify which scenario you want to test.

**1. Cold Start Scenario**

This test simulates the creation of the very first Universe and Volume in a clean environment.

```bash
python scripts/run_test_suite.py --scenario cold-start
```

*   **What it does:** Creates a new test Universe, a new Storyline, and a new Volume. It then runs the full `full_render` pipeline on that volume.
*   **Success looks like:** The script will print `✓ Cold Start Test Passed: Volume was successfully published.` and then clean up the created test data.

**2. Storyline Leakage Test**

This is the most important test for maintaining the "World Bible" logic. It ensures that plot-specific (`dynamic`) events from one storyline do not "leak" into a different storyline within the same universe.

```bash
python scripts/run_test_suite.py --scenario storyline-leakage
```

*   **What it does:** Creates a universe and two storylines (A and B). It injects one `static` memory ("The bridge exists") and one `dynamic` memory ("The bridge was destroyed") into Storyline A. It then generates a new volume in Storyline B about the bridge.
*   **Success looks like:** The script will print `✓ Test Passed: Static 'World Bible' context was used, and dynamic 'Ledger' context was correctly ignored.` The generated text for Storyline B should mention the bridge, but not that it was destroyed.

**3. Truth Hierarchy Conflict Test**

This test verifies that Universe-specific context (canon) correctly overrides conflicting general Personal knowledge.

```bash
python scripts/run_test_suite.py --scenario truth-conflict
```

*   **What it does:** Injects a "Personal" atom stating "Magic comes from crystals" and a "Universe" atom stating "Magic is forbidden." It then runs a story generation about casting a spell within that Universe.
*   **Success looks like:** The script will run to completion. Because this test runs in `debug` mode, it only verifies that the pipeline executes successfully. To *truly* verify the content, you would need to temporarily edit the script to run with `debug=False` and check that the final generated text mentions magic being forbidden, not coming from crystals.

**4. Rollback & Cleanup Integrity Test**

This test verifies that deleting a volume also correctly deletes all of its "crystallized" memories, preventing "ghosts" in the knowledge graph.

```bash
python scripts/run_test_suite.py --scenario rollback-integrity
```

*   **What it does:** Creates a temporary volume and several `Atoms` linked to it. It then calls the `delete_volume` function.
*   **Success looks like:** The script will query the database and verify that the volume AND all of its associated atoms have been deleted, printing `✓ Test Passed: Volume and all associated atoms were successfully deleted.`.

**5. Universe Isolation Test**

This test verifies that two completely separate universes do not "cross-contaminate" each other.

```bash
python scripts/run_test_suite.py --scenario isolation
```

*   **What it does:** Creates two universes (A and B) with distinct and conflicting canonical facts (e.g., "red sky" vs. "low gravity"). It then generates a story in Universe B and checks to ensure no facts from Universe A were used.
*   **Success looks like:** The script will run to completion. True verification requires running with `debug=False` and checking that the output text for Universe B does not contain any canonical facts from Universe A.

**6. RLS Security Regression Test (Coming Soon)********

This test will ensure that two separate Universes do not share knowledge, preventing creative cross-pollination.

```bash
python scripts/run_test_suite.py --scenario isolation
```

**3. Continuity Scenario (Coming Soon)**

This test will ensure that a new Storyline within an existing Universe correctly uses the "World Bible" (static atoms) but ignores the "Ledger" (dynamic atoms) from other storylines.

```bash
python scripts/run_test_suite.py --scenario continuity
```

**4. Crossover Scenario (Coming Soon)**

This test will verify the "Chimera" architecture by creating a story from two existing Universes and ensuring its crystallized memories are stored in a new, separate Chimera universe.

```bash
python scripts/run_test_suite.py --scenario crossover
```
