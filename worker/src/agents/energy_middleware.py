import logging
import random
import math
from db.session import get_db
from llm.client import get_llm_client
from db.crud import match_atoms_by_embedding

logger = logging.getLogger(__name__)
print("LOADING UPDATED ENERGY MIDDLEWARE (DEBUG ENABLED)")

class EnergyModelMiddleware:
    """
    The Resonant-Energy Tuner (V4).
    Calculates the 'Energy' via Vector Search against the Archive.
    Harmonized for Saga Engine (Storyline & Epoch Aware).
    """
    def __init__(self):
        self.db = get_db()
        self.llm = get_llm_client()

    def cosine_similarity(self, v1, v2):
        """
        Calculates Cosine Similarity between two vectors.
        """
        if not v1 or not v2: return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)

    def calculate_energy(self, state_embedding: list[float], context_atoms: list[dict], trajectory_atoms: list[dict] = [], domain_agent=None, violation_penalty: float = 1.0) -> tuple[float, str]:
        """
        Calculates P* = (Alpha * Beta * Gamma)^(1/3) * ViolationPenalty
        """
        feedback = []
        
        # --- 0. Constraint Check (The Gate) ---
        if violation_penalty <= 0.0:
            return 0.0, "HARD FAIL: Canon Violation."
        if violation_penalty < 1.0:
            feedback.append(f"Penalty Applied ({violation_penalty:.2f}).")

        # --- 1. Alpha (Novelty) ---
        if not context_atoms:
            novelty_score = 1.0 
            feedback.append("Alpha: Max.")
        else:
            sims = []
            for a in context_atoms:
                emb = a.get('embedding')
                if not emb: continue
                if isinstance(emb, str):
                    try:
                        import json
                        emb = json.loads(emb)
                    except:
                        continue
                sims.append(self.cosine_similarity(state_embedding, emb))

            if sims:
                avg_sim = sum(sims) / len(sims)
                novelty_score = 1.0 - avg_sim
            else:
                novelty_score = 1.0

            if novelty_score < 0.3:
                feedback.append(f"Alpha Low ({novelty_score:.2f}): Too derivative.")
            else:
                feedback.append(f"Alpha OK ({novelty_score:.2f}).")

        # --- 2. Beta (Validity) ---
        real_science_count = sum(1 for a in context_atoms if a.get('source') == 'OpenAlex')
        if real_science_count > 0:
            validity_score = 0.7 + (0.3 * min(real_science_count, 3) / 3)
            feedback.append(f"Beta High ({validity_score:.2f}).")
        else:
            validity_score = 0.4
            feedback.append("Beta Neutral (0.40).")

        # --- 3. Gamma (Stability) ---
        if not trajectory_atoms:
            stability_score = 1.0 
            feedback.append("Gamma: New Trajectory started.")
        else:
            traj_sims = []
            for a in trajectory_atoms:
                emb = a.get('embedding')
                if not emb: continue
                if isinstance(emb, str):
                    try:
                        import json
                        emb = json.loads(emb)
                    except:
                        continue
                traj_sims.append(self.cosine_similarity(state_embedding, emb))
            
            if not traj_sims:
                 stability_score = 0.5
            else:
                stability_score = sum(traj_sims) / len(traj_sims)
            
            if stability_score < 0.4:
                feedback.append(f"Gamma Low ({stability_score:.2f}): Drift detected.")
                stability_score = 0.2
            else:
                feedback.append(f"Gamma Good ({stability_score:.2f}).")
                stability_score = 0.5 + (stability_score * 0.5)

        # --- Final Calculation ---
        base_energy = math.pow(novelty_score * validity_score * stability_score, 1/3)
        energy = base_energy * violation_penalty
        
        return energy, " ".join(feedback)

    def score_text(self, text: str, active_lenses: list[str] = None, time_range: dict = None, project_id: str = None, user_id: str = None, context_type: str = "general", exclusive_user_scope: bool = False, storyline_id: str = None, epoch_id: int = None) -> tuple[float, str]:
        """
        High-level facade to score a string text. 
        Storyline Aware & Strict Project Scoping.
        """
        if not text: return 0.0, "Empty text"
        
        # 1. Embed
        embedding = self.llm.get_embedding(text)
        
        # 2. Fetch Context
        filter_start = time_range.get('filter_start_date') if time_range else None
        filter_end = time_range.get('filter_end_date') if time_range else None

        # Logic for exclusive_user_scope (used in Alpha scoring)
        q_user = user_id
        q_proj = project_id
        if exclusive_user_scope:
            q_proj = None # We handle project filtering in post-processing
            
        # Fetch more matches if we need to filter by project to prevent cross-project leaks
        fetch_count = 20 if project_id else 5

        matches = match_atoms_by_embedding(
            self.db, 
            embedding, 
            match_threshold=0.4, 
            match_count=fetch_count, 
            filter_lenses=active_lenses,
            filter_start_date=filter_start,
            filter_end_date=filter_end,
            query_project_id=q_proj,
            query_user_id=q_user,
            filter_storyline_id=storyline_id, # Pass storyline context
            filter_epoch_id=epoch_id # Pass epoch context
        )
        
        # Post-Processing: Strict Project Scoping
        # Rule: Keep atoms that belong to THIS project OR are private (no project)
        # This runs even if exclusive_user_scope is True, ensuring Alpha checks 
        # "My Private Notes" + "My Project Notes" but NOT "My Notes in Other Projects"
        if project_id:
            matches = [
                m for m in matches 
                if (str(m.get('project_id')) == str(project_id)) or (not m.get('project_id'))
            ]
            matches = matches[:5]
        
        # 3. Calculate
        return self.calculate_energy(embedding, matches, trajectory_atoms=[])

    def retrieve_context(self, query: str, user_id: str, project_id: str = None) -> str:
        """
        MirrorMind 4-Stage Retrieval.
        """
        try:
            from db import crud
            context_stack = []
            
            profile = crud.get_persona_profile(self.db, user_id)
            if profile and profile.system_prompt_cache:
                context_stack.append(f"--- PERSONA ---\n{profile.system_prompt_cache}\n")

            query_embedding = self.llm.get_embedding(query)
            recent_mem = crud.get_recent_semantic_memory(self.db, user_id, 'monthly')
            if recent_mem:
                context_stack.append(f"--- CURRENT MINDSET (Last Month) ---\n{recent_mem.summary}\n")

            matches = match_atoms_by_embedding(
                self.db, 
                query_embedding, 
                match_threshold=0.6, 
                match_count=5, 
                query_user_id=user_id,
                query_project_id=project_id
            )
            if matches:
                atom_text = "\n".join([f"- {m['name']}: {m['content']}" for m in matches])
                context_stack.append(f"--- RELEVANT NOTES ---\n{atom_text}\n")

            return "\n".join(context_stack)

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return ""

    def tune_thought(self, generator_func, attempts: int = 3, threshold: float = 0.7, context_type: str = "plot", start_temp: float = 0.9, end_temp: float = 0.2, active_lenses: list[str] = None, time_range: dict = None, project_id: str = None, user_id: str = None, constraint_checker=None, storyline_id: str = None, epoch_id: int = None):
        """
        Executes the 'Generate -> Score -> Regenerate' loop with Simulated Annealing.
        Storyline Aware & Strict Project Scoping.
        """
        best_result = None
        best_score = -1.0
        
        for i in range(attempts):
            # Calculate Temperature
            if attempts > 1:
                progress = i / (attempts - 1)
                current_temp = start_temp - (progress * (start_temp - end_temp))
            else:
                current_temp = start_temp
                
            try:
                result = generator_func(temperature=current_temp)
            except TypeError:
                 result = generator_func()

            if not result: continue
            
            if isinstance(result, dict):
                text_to_score = result.get('summary', result.get('title', result.get('narrative_text', '')))
            else:
                text_to_score = str(result)
            
            # --- CONSTRAINT CHECK (Reviewer) ---
            violation_penalty = 1.0
            if constraint_checker:
                try:
                    penalty = constraint_checker(result)
                    if isinstance(penalty, (int, float)):
                        violation_penalty = float(penalty)
                    elif penalty is False:
                        violation_penalty = 0.0
                except Exception as e:
                    logger.warning(f"Constraint checker failed: {e}")
                    violation_penalty = 0.8

            # --- ADAPTER FOR NEW SIGNATURE ---
            # 1. Embed
            embedding = self.llm.get_embedding(text_to_score)
            
            # 2. Fetch Context
            query_proj = project_id
            filter_start = time_range.get('filter_start_date') if time_range else None
            filter_end = time_range.get('filter_end_date') if time_range else None

            fetch_count = 20 if project_id else 5

            matches = match_atoms_by_embedding(
                self.db, 
                embedding, 
                match_threshold=0.4, 
                match_count=fetch_count, 
                filter_lenses=active_lenses,
                filter_start_date=filter_start,
                filter_end_date=filter_end,
                query_project_id=query_proj,
                query_user_id=user_id,
                filter_storyline_id=storyline_id, # Pass storyline context
                filter_epoch_id=epoch_id # Pass epoch context
            )

            # Strict Project Scoping
            if project_id:
                matches = [
                    m for m in matches 
                    if (str(m.get('project_id')) == str(project_id)) or (not m.get('project_id'))
                ]
                matches = matches[:5]
            
            # 3. Calculate
            score, feedback = self.calculate_energy(embedding, matches, trajectory_atoms=[], violation_penalty=violation_penalty)
            # ---------------------------------
            
            if isinstance(result, dict):
                result['novelty_score'] = score
            
            logger.info(f"Tuning Attempt {i+1} ({context_type}) | Temp: {current_temp:.2f} | Score {score:.2f} (Penalty: {violation_penalty:.2f}) | Feedback: {feedback} | '{text_to_score[:30]}...' ")
            
            if score >= threshold:
                return result
            
            if score > best_score:
                best_score = score
                best_result = result
        
        logger.info(f"⚠️ Tuning exhausted. Returning best result (Score {best_score:.2f})")
        return best_result

    def get_attributed_context(self, query_text: str, user_id: str, project_id: str = None, lenses: list[str] = None) -> str:
        """
        Retrieves resonant atoms with User Attribution for the prompt.
        """
        embedding = self.llm.get_embedding(query_text)
        matches = match_atoms_by_embedding(
            self.db, embedding, 0.6, 5, filter_lenses=lenses, query_user_id=user_id, query_project_id=project_id
        )
        if not matches: return ""
        
        context_str = "Relevant Context:\n"
        for m in matches:
            attribution = f"User {m.get('user_id')[:8]}" # Simple ID attribution
            context_str += f"- [{attribution} | {m.get('metadata', {}).get('cluster_name', 'General')}]: {m['content'][:300]}...\n"
        return context_str

    def retrieve_epoch_style(self, universe_id: str, epoch_id: int = None) -> tuple[str, list[float]]:
        """
        Retrieves the Prose Style DNA for the current epoch.
        """
        if not epoch_id:
            uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
            if not uni_res.data or not uni_res.data.get('active_epoch_id'):
                return "Neutral, descriptive, and objective.", None
            epoch_id = uni_res.data['active_epoch_id']

        res = self.db.table("Epochs").select("style_summary, style_embedding").eq("id", epoch_id).single().execute()
        if not res.data:
            return "Neutral narrative style.", None
            
        return res.data.get('style_summary', "Neutral style."), res.data.get('style_embedding')
