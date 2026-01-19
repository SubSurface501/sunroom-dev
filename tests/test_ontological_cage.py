import unittest
from unittest.mock import MagicMock, patch
from worker.src.agents.reviewer import ReviewAgent, OntologicalCage, ReviewStatus, ViolationType

class TestOntologicalCage(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_worker = MagicMock()
        self.mock_llm = MagicMock()
        self.agent = ReviewAgent(self.mock_db, self.mock_worker, self.mock_llm)
        self.cage = OntologicalCage(self.agent)

    @patch('worker.src.agents.reviewer.get_persona_profile')
    def test_physics_violation_symbolic(self, mock_get_profile):
        """Test a hard symbolic violation (Prohibited terms)."""
        mock_get_profile.return_value = {'fidelity_weight': 0.5}
        prohibitions = ["magic", "wizard", "spell"]
        draft = "The wizard cast a fireball spell."
        
        result = self.cage.review_draft(
            volume_id="vol123",
            node_id="node123",
            draft_text=draft,
            prohibitions=prohibitions
        )
        
        self.assertEqual(result.status, ReviewStatus.HARD_FAIL)
        self.assertEqual(result.violation_type, ViolationType.SYMBOLIC)
        # Draft contains 'wizard' and 'spell', not 'magic'
        self.assertIn("wizard", str(result.issues).lower())

    @patch('worker.src.agents.reviewer.get_persona_profile')
    def test_voice_violation_semantic(self, mock_get_profile):
        """Test a semantic voice violation."""
        mock_get_profile.return_value = {'fidelity_weight': 0.9}
        # Mock DB for volume user_id
        mock_response = MagicMock()
        mock_response.data = {'user_id': 'user123'}
        self.mock_db.table().select().eq().single().execute.return_value = mock_response
        
        # Mock LLM Response for a Fail
        self.mock_llm.chat_completion.return_value = """
        {
            "score": 0.3,
            "status": "FAIL",
            "issues": ["Voice inconsistency: Character sounds too cheerful."],
            "character_audit": { "Kaelen": "Fail: He is cynical, not optimistic." },
            "suggestion": "Make him sound more bitter."
        }
        """
        
        stances = {"Kaelen": "He is a cynical scientist who hates magic."}
        draft = "Kaelen smiled and said, 'Everything is going to be wonderful!'"
        
        result = self.cage.review_draft(
            volume_id="vol123",
            node_id="node123",
            draft_text=draft,
            character_stances=stances
        )
        
        self.assertEqual(result.status, ReviewStatus.SOFT_FAIL)
        self.assertEqual(result.violation_type, ViolationType.SEMANTIC)
        self.assertIn("Kaelen", result.character_audit)
        self.assertIn("Fail", result.character_audit["Kaelen"])

    @patch('worker.src.agents.reviewer.get_persona_profile')
    def test_narrative_intent_mismatch(self, mock_get_profile):
        """Test when the draft fails to meet author's intent."""
        mock_get_profile.return_value = {'fidelity_weight': 0.5}
        # Mock DB and LLM
        mock_response = MagicMock()
        mock_response.data = {'user_id': 'user123'}
        self.mock_db.table().select().eq().single().execute.return_value = mock_response
        
        self.mock_llm.chat_completion.return_value = """
        {
            "score": 0.1,
            "status": "FAIL",
            "issues": ["Intent Mismatch: The draft does not reveal the traitor."],
            "character_audit": {},
            "suggestion": "Include the scene where the letter is found."
        }
        """
        
        intent = "The draft must reveal that Marcus is the traitor."
        draft = "The characters sat by the fire and discussed the price of grain."
        
        result = self.cage.review_draft(
            volume_id="vol123",
            node_id="node123",
            draft_text=draft,
            narrative_intent=intent
        )
        
        self.assertEqual(result.status, ReviewStatus.HARD_FAIL) # Score 0.1 < 0.2
        self.assertIn("traitor", str(result.issues).lower())

if __name__ == '__main__':
    unittest.main()
