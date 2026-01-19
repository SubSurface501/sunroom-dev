import logging
import json
import re
from typing import Optional, List, Any, Dict, Tuple
from enum import Enum
from pydantic import BaseModel

from .base import BaseAgent
from db import schemas
from db.crud import get_persona_profile, get_node

logger = logging.getLogger(__name__)

class ViolationType(str, Enum):
    SYMBOLIC = "symbolic"   # Deterministic keyword/tag violation (HARD FAIL)
    SEMANTIC = "semantic"   # LLM-detected logic/tone issue (SOFT FAIL)
    NONE = "none"

class CanonViolationError(Exception):
    """Raised when the Ontological Cage rejects a draft due to hard constraints."""
    pass

class ReviewStatus(str, Enum):
    PASS = "pass"
    SOFT_FAIL = "soft_fail" # Retry allowed
    HARD_FAIL = "hard_fail" # Abort immediately

class ReviewResult(BaseModel):
    status: ReviewStatus
    score: float
    violation_type: ViolationType = ViolationType.NONE
    issues: List[str] = []
    character_audit: Dict[str, str] = {} # Character name -> Voice evaluation
    suggestion: Optional[str] = None
    
    def is_fatal(self) -> bool:
        return self.status == ReviewStatus.HARD_FAIL

class OntologicalCage:
    """
    The Deterministic Logic Gate.
    Wraps the LLM-based Reviewer with hard symbolic checks.
    """
    def __init__(self, review_agent: 'ReviewAgent'):
        self.agent = review_agent

    def check_physics(self, draft_text: str, prohibitions: List[str]) -> Tuple[bool, List[str]]:
        """
        Performs a deterministic Symbolic Tag Match.
        Returns (passed: bool, violations: List[str]).
        """
        if not prohibitions:
            return True, []

        draft_lower = draft_text.lower()
        violations = []
        
        # Simple regex word boundary check for each prohibition
        for term in prohibitions:
            # We assume prohibitions are single words or short phrases
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, draft_lower):
                violations.append(term)
        
        if violations:
            return False, violations
        return True, []

    def review_draft(self, 
                    volume_id: str, 
                    node_id: str, 
                    draft_text: str, 
                    user_context: str = "", 
                    domain_context: str = "", 
                    prohibitions: Optional[List[str]] = None,
                    character_stances: Optional[Dict[str, str]] = None,
                    narrative_intent: Optional[str] = None,
                    simulation_trace: Optional[List[Dict]] = None) -> ReviewResult:
        """
        The Main Entry Point.
        1. Symbolic Check (Physics) -> Fail Closed
        2. Semantic Check (LLM) -> Soft/Hard Fail based on score
        """
        # 1. HARD AUDIT (Symbolic)
        if prohibitions:
            passed_physics, violations = self.check_physics(draft_text, prohibitions)
            if not passed_physics:
                logger.critical(f"🚫 [OntologicalCage] SYMBOLIC VIOLATION: {violations}")
                return ReviewResult(
                    status=ReviewStatus.HARD_FAIL,
                    score=0.0,
                    violation_type=ViolationType.SYMBOLIC,
                    issues=[f"Canon Violation: Forbidden concepts found: {violations}"],
                    suggestion="Remove all forbidden concepts immediately."
                )

        # 2. SEMANTIC AUDIT (LLM via ReviewAgent)
        try:
            # We delegate the "thinking" to the ReviewAgent
            llm_report = self.agent._execute_llm_review(
                volume_id, draft_text, user_context, domain_context, prohibitions, character_stances, narrative_intent, simulation_trace
            )
            
            score = llm_report.get('score', 0.0)
            issues = llm_report.get('issues', [])
            character_audit = llm_report.get('character_audit', {})
            suggestion = llm_report.get('suggestion')

            # State Machine Logic (Hardened for V7)
            if score >= 0.8:
                return ReviewResult(status=ReviewStatus.PASS, score=score, character_audit=character_audit)
            
            elif score < 0.4:
                # Severe semantic failure or massive voice drift
                # If score is critically low (<0.2), it's a HARD_FAIL (Fail-Closed)
                return ReviewResult(
                    status=ReviewStatus.HARD_FAIL if score < 0.2 else ReviewStatus.SOFT_FAIL, 
                    score=score,
                    violation_type=ViolationType.SEMANTIC,
                    issues=issues,
                    character_audit=character_audit,
                    suggestion=suggestion
                )
            else:
                # 0.4 <= score < 0.8 -> Soft Fail (Retry)
                return ReviewResult(
                    status=ReviewStatus.SOFT_FAIL,
                    score=score,
                    violation_type=ViolationType.SEMANTIC,
                    issues=issues,
                    character_audit=character_audit,
                    suggestion=suggestion
                )

        except Exception as e:
            logger.error(f"Review agent failed: {e}")
            # If the LLM crashes, we Default to SOFT FAIL to allow retry or manual intervention
            return ReviewResult(
                status=ReviewStatus.SOFT_FAIL, 
                score=0.0, 
                violation_type=ViolationType.NONE,
                issues=[f"System Error: {str(e)}"]
            )

class ReviewAgent(BaseAgent):
    """
    The Semantic Auditor (LLM).
    Now focused purely on the 'Subjective/Scientific' review.
    """
    
    def run_task(self, 
                 volume_id: str, 
                 node_id: str, 
                 draft_text: str, 
                 user_context: str = "", 
                 domain_context: str = "", 
                 prohibitions: Optional[List[str]] = None,
                 character_stances: Optional[Dict[str, str]] = None,
                 narrative_intent: Optional[str] = None,
                 simulation_trace: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Legacy entry point for compatibility. 
        Instantiates a Cage temporarily or uses internal logic.
        Ideally, callers should use OntologicalCage directly.
        """
        cage = OntologicalCage(self)
        result = cage.review_draft(
            volume_id, 
            node_id, 
            draft_text, 
            user_context, 
            domain_context, 
            prohibitions,
            character_stances,
            narrative_intent,
            simulation_trace
        )
        
        # Logging for observability
        if result.status != ReviewStatus.PASS:
            logger.warning(f"Review Failed for Node {node_id}: {result.issues}")
            if node_id and not node_id.startswith("page_"): # Don't flag temp IDs
                self._flag_node(node_id, result.model_dump(), None) # User ID will be fetched if needed
        else:
            logger.info(f"Review Passed (Score {result.score})")
            
        return result.model_dump()

    def _execute_llm_review(self, 
                            volume_id: str,
                            draft_text: str, 
                            user_context: str, 
                            domain_context: str, 
                            prohibitions: Optional[List[str]],
                            character_stances: Optional[Dict[str, str]] = None,
                            narrative_intent: Optional[str] = None,
                            simulation_trace: Optional[List[Dict]] = None) -> Dict:
        """
        Internal method to call the LLM. 
        Contains the core logic from the original run_task.
        """
        # 0. Identify User & Fidelity
        user_id = None
        try:
            vol_res = self.db.table("StoryVolumes").select("user_id").eq("id", volume_id).single().execute()
            user_id = vol_res.data['user_id'] if vol_res.data else None
        except Exception: pass
            
        fidelity_weight = 0.5
        if user_id:
            profile = get_persona_profile(self.db, user_id)
            if profile:
                fidelity_weight = profile.get('fidelity_weight', 0.5) if isinstance(profile, dict) else getattr(profile, 'fidelity_weight', 0.5)

        # 1. Construct the Character Context Block
        char_block = ""
        if character_stances:
            char_block = "## CHARACTER VOICE LEDGER (MANDATORY VOICES)\n" + "\n".join([f"- **{k}**: {v}" for k, v in character_stances.items()])

        # 2. Construct the Narrative Intent Block
        intent_block = ""
        if narrative_intent:
            intent_block = f"## NARRATIVE INTENT (THE GOAL)\nThe author explicitly stated this scene must: {narrative_intent}\n"

        # 3. Policy Setup
        if domain_context and "ABSOLUTE TRUTH HIERARCHY" in domain_context:
            stance_instruction = (
                "You are a CANON EXECUTIONER. The Universe Rules are absolute physical laws. "
                "Any attempt to use 'Personal Knowledge' to bypass or 'scientifically explain' a Universe prohibition "
                "is a CRITICAL FAILURE. No synthesis allowed. Contradictions are NOT acceptable."
            )
        else:
            stance_instruction = "Seek synthesis. Acknowledge tensions between metaphor and truth."
            if fidelity_weight < 0.3:
                stance_instruction = "Lenient editor. Prioritize voice over strict accuracy."
            elif fidelity_weight > 0.7:
                stance_instruction = "Strict peer reviewer. Prioritize Domain Truth."
        
        # 4. V9.8: Construct Simulation Trace Block
        trace_block = ""
        if simulation_trace:
            formatted_trace = []
            for i, step in enumerate(simulation_trace):
                action = step.get('action', {})
                result = step.get('result', {})
                formatted_trace.append(f"  {i+1}. ACTION: {action.get('action_type', 'N/A')} -> TARGET: {action.get('target_id', 'N/A')}")
                formatted_trace.append(f"     - RESULT: {'Success' if result.get('success') else 'Fail'}. {result.get('message', '')}")
            trace_block = "## SIMULATION TRACE (GROUND TRUTH)\nThis is the record of what PHYSICALLY happened. It is immutable.\n" + "\n".join(formatted_trace) + "\n"

        # 5. LLM AUDIT
        prohibitions_str = f"\nSTRICT PROHIBITIONS: {prohibitions}" if prohibitions else ""
        
        prompt = f"""
        You are the ONTOLOGICAL CAGE, a continuity engine for a high-end novel.
        Your job is to REJECT any draft that violates the Laws of Physics, the Established Canon, or the Character Voices.

        {trace_block}

        SOURCE A (User): {user_context}
        SOURCE B (Canon): {domain_context}
        
        {intent_block}

        {char_block}

        {prohibitions_str}

        ## THE DRAFT TO REVIEW
        "{draft_text}"
        
        POLICY: {stance_instruction}

        TASK:
        1. **Trace Audit (HIGHEST PRIORITY):** Does the draft's physical events (movement, taking items, using objects) EXACTLY match the sequence and outcomes in the Simulation Trace? Any deviation is a HARD FAIL (Score 0.0). The prose must be a creative description of the trace, not a different story.
        2. **Physics Check:** Does the draft violate the strict prohibitions? (If so, Score 0.0)
        3. **Intent Check:** Does the draft achieve the 'Narrative Intent'?
        4. **Voice Audit:** Check EACH character's dialogue against their Ledger. 
           - If a cynical character sounds cheerful, mark it as a Voice Violation. (If so, Score 0.4 or lower)
        
        Return JSON format:
        {{
            "score": float (0.0 to 1.0),
            "status": "PASS"|"FAIL",
            "issues": ["list", "of", "violations"],
            "character_audit": {{ "CharacterName": "Pass" or "Fail: Reason" }},
            "suggestion": "How to fix it"
        }}
        """
        
        resp = self.llm.chat_completion(prompt, json_schema=None)
        report = self._clean_and_parse_json(resp)

        # Clip the score to a maximum of 1.0 to handle LLM over-enthusiasm
        report['score'] = min(1.0, float(report.get('score', 0.0)))
        logger.info(f"[Reviewer] Clipped score: {report['score']}")
        
        return report

    def _clean_and_parse_json(self, text: str) -> Dict:
        try:
            cleaned = text
            if "```json" in cleaned: cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in cleaned: cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
            return json.loads(cleaned.strip())
        except Exception:
            logger.error("Failed to parse Reviewer JSON response.")
            return {"score": 0.0, "status": "FAIL", "issues": ["JSON Parsing Error"]}

    def _flag_node(self, node_id: str, report: dict, user_id: Optional[str]):
        """Metadata flagging for long-term tracking of issues."""
        try:
            node = get_node(self.db, node_id)
            if node:
                # node is a Pydantic model (schemas.Node), so we access attributes directly
                content = node.content or {}
                metadata = content.get('metadata', {}) or {}
                
                metadata['review'] = report
                
                # Update nodes in the database
                content['metadata'] = metadata
                self.db.table("Nodes").update({"content": content}).eq("id", node.id).execute()
                logger.info(f"Flagged node {node.id} with review.")
        except Exception as e:
            logger.error(f"Failed to flag node {node_id}: {e}")