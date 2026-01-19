import unittest
from unittest.mock import MagicMock, patch
from worker.src.agents.writers_room import WritersRoomAgent
from worker.src.agents.reviewer import ReviewStatus, ReviewResult, ViolationType

class TestWritersRoomCageIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_worker = MagicMock()
        
        # Mock LLM Client
        self.mock_llm_patcher = patch('worker.src.agents.writers_room.get_llm_client')
        self.mock_get_llm = self.mock_llm_patcher.start()
        self.mock_llm = MagicMock()
        self.mock_get_llm.return_value = self.mock_llm
        self.mock_llm.debug_mode = False # Add debug_mode attribute
        
        # Mock Domain Agent (to avoid instantiation issues)
        self.domain_patcher = patch('worker.src.agents.writers_room.DomainExpertAgent')
        self.domain_patcher.start()
        
        # Mock ReviewAgent (We want to verify interactions with it)
        self.review_patcher = patch('worker.src.agents.writers_room.ReviewAgent')
        self.mock_review_cls = self.review_patcher.start()
        self.mock_reviewer = MagicMock()
        self.mock_review_cls.return_value = self.mock_reviewer

        # Instantiate Agent
        self.agent = WritersRoomAgent(self.mock_db, self.mock_worker)

    def tearDown(self):
        self.mock_llm_patcher.stop()
        self.domain_patcher.stop()
        self.review_patcher.stop()

    def test_drafting_success_passes_audit(self):
        """
        Verify that a successful draft returns both the script and the review report.
        """
        # Setup Inputs
        trailhead = {"title": "Test Story", "premise": "A test"}
        outline = "- Scene 1: Intro"
        research = [{"content": "Fact 1"}]
        user_id = "user123"
        volume_id = "vol123"
        
        # Mock DB Calls for Context
        self.mock_db.table().select().eq().single().execute.return_value.data = None # Universe context
        
        # Mock LLM Draft Generation
        self.mock_llm.chat_completion.return_value = "This is a perfect draft."
        
        # Mock Cage Review (PASS)
        # Note: WritersRoom uses self.cage, which wraps self.reviewer
        # We need to mock the return value of self.cage.review_draft
        pass_result = ReviewResult(
            status=ReviewStatus.PASS,
            score=0.9,
            character_audit={"Hero": "Pass"},
            issues=[]
        )
        self.agent.cage.review_draft = MagicMock(return_value=pass_result)
        
        # Execute
        script, report = self.agent._phase_drafting(trailhead, outline, research, user_id, volume_id)
        
        # Verify
        self.assertEqual(script, "This is a perfect draft.")
        self.assertEqual(report['score'], 0.9)
        self.assertEqual(report['character_audit'], {"Hero": "Pass"})
        
        # Verify Wiring: Did we pass the outline as narrative_intent?
        self.agent.cage.review_draft.assert_called_once()
        call_args = self.agent.cage.review_draft.call_args[1]
        self.assertEqual(call_args['narrative_intent'], outline)
        self.assertEqual(call_args['volume_id'], volume_id)

    def test_drafting_hard_fail_aborts(self):
        """
        Verify that a HARD_FAIL in the Cage raises a ValueError and aborts.
        """
        # Setup Inputs
        trailhead = {"title": "Test Story", "premise": "A test"}
        outline = "- Scene 1: Intro"
        research = []
        user_id = "user123"
        volume_id = "vol123"
        
        # Mock DB Calls
        self.mock_db.table().select().eq().single().execute.return_value.data = None
        
        # Mock LLM Draft
        self.mock_llm.chat_completion.return_value = "The wizard cast a spell."
        
        # Mock Cage Review (HARD FAIL)
        fail_result = ReviewResult(
            status=ReviewStatus.HARD_FAIL,
            score=0.0,
            violation_type=ViolationType.SYMBOLIC,
            issues=["Forbidden concept: wizard"]
        )
        self.agent.cage.review_draft = MagicMock(return_value=fail_result)
        
        # Execute & Assert
        with self.assertRaises(ValueError) as cm:
            self.agent._phase_drafting(trailhead, outline, research, user_id, volume_id)
        
        self.assertIn("Ontological Violation", str(cm.exception))
        self.assertIn("Forbidden concept: wizard", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
