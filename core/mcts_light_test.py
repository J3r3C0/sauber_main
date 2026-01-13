
import unittest
import json
import os
from pathlib import Path
from core.mcts_light import MCTSLight

class TestMCTSLight(unittest.TestCase):
    def setUp(self):
        self.test_priors = "policies/test_priors.json"
        if os.path.exists(self.test_priors):
            os.remove(self.test_priors)
        self.mcts = MCTSLight(priors_path=self.test_priors)

    def test_initial_selection(self):
        candidates = [
            {"type": "ROUTE", "params": {"subtype": "local"}, "risk_gate": True},
            {"type": "ROUTE", "params": {"subtype": "webrelay"}, "risk_gate": True}
        ]
        # Both unvisited, should be equal or close
        chosen, scored = self.mcts.select_action("test_intent", candidates)
        self.assertIn(chosen["action_key"], ["ROUTE:local", "ROUTE:webrelay"])
        
    def test_risk_gate(self):
        candidates = [
            {"type": "ROUTE", "params": {"subtype": "safe"}, "risk_gate": True},
            {"type": "ROUTE", "params": {"subtype": "unsafe"}, "risk_gate": False}
        ]
        chosen, scored = self.mcts.select_action("test_intent", candidates)
        self.assertEqual(chosen["action_key"], "ROUTE:safe")
        self.assertEqual(scored[1]["select_score"], -999.0)

    def test_policy_update(self):
        intent = "test_intent"
        action = "ROUTE:local"
        self.mcts.update_policy(intent, action, 3.0)
        
        # Check if saved
        with open(self.test_priors, "r") as f:
            data = json.load(f)
            self.assertEqual(data[intent][action]["visits"], 1)
            self.assertEqual(data[intent][action]["mean_score"], 3.0)
            
        # Update again
        self.mcts.update_policy(intent, action, 1.0)
        self.assertEqual(self.mcts.data[intent][action]["mean_score"], 2.0)

    def tearDown(self):
        if os.path.exists(self.test_priors):
            os.remove(self.test_priors)

if __name__ == "__main__":
    unittest.main()
