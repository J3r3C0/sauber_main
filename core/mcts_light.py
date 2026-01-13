import json
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

def ucb_light_select_score(
    *,
    mean_score: float,
    visits: int,
    parent_visits: int,
    c: float = 0.5,
    risk_penalty: float = 0.0,
) -> float:
    """
    UCB-Light selection score:
      select = mean + c*sqrt(log(parent_visits)/(visits+1)) - risk_penalty
    """
    pv = max(1, int(parent_visits))
    v = max(0, int(visits))
    explore = c * math.sqrt(math.log(pv) / (v + 1))
    return float(mean_score) + explore - float(risk_penalty)

class MCTSLight:
    def __init__(self, priors_path: str = "policies/priors.json", c: float = 0.5):
        self.priors_path = Path(priors_path)
        self.c = c
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.priors_path.exists():
            return {"schema_version": "priors_v1"}
        with open(self.priors_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        self.priors_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.priors_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_parent_visits(self, intent: str) -> int:
        intent_data = self.data.get(intent, {})
        return sum(a.get("visits", 0) for a in intent_data.values())

    def select_action(self, intent: str, candidates: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        candidates: List of Action objects with 'type', 'params', 'risk_gate'
        Returns (chosen_candidate, candidates_with_scores)
        """
        intent_data = self.data.get(intent, {})
        parent_visits = self.get_parent_visits(intent)
        
        scored_candidates = []
        for cand in candidates:
            # We use action_type as the key in priors: "TYPE:subtype" or just "TYPE"
            # Here we assume candidate has a unique 'action_key' or we build it
            action_type = cand.get("type")
            subtype = cand.get("params", {}).get("subtype", "")
            action_key = f"{action_type}:{subtype}" if subtype else action_type
            
            prior = intent_data.get(action_key, {"visits": 0, "mean_score": 0.0, "risk_gate": True})
            
            # Risk Gate check (hard stop)
            if not cand.get("risk_gate", prior.get("risk_gate", True)):
                cand["select_score"] = -999.0
                cand["action_key"] = action_key
                scored_candidates.append(cand)
                continue

            visits = prior["visits"]
            mean_score = prior["mean_score"]
            
            ucb = ucb_light_select_score(
                mean_score=mean_score,
                visits=visits,
                parent_visits=parent_visits,
                c=self.c
            )
            
            cand["select_score"] = round(ucb, 4)
            cand["action_key"] = action_key
            scored_candidates.append(cand)

        # Filter out risk-gated ones for selection
        valid_candidates = [c for c in scored_candidates if c["select_score"] > -900]
        
        if not valid_candidates:
            # Fallback if everything is gated? (Should be handled by caller)
            return scored_candidates[0] if scored_candidates else None, scored_candidates

        # Choose best
        chosen = max(valid_candidates, key=lambda c: c["select_score"])
        return chosen, scored_candidates

    def update_policy(self, intent: str, action_key: str, score: float):
        if intent not in self.data:
            self.data[intent] = {}
        
        prior = self.data[intent].get(action_key, {
            "visits": 0,
            "mean_score": 0.0,
            "last_scores": [],
            "risk_gate": True
        })
        
        n = prior["visits"]
        old_mean = prior["mean_score"]
        
        new_n = n + 1
        new_mean = (old_mean * n + score) / new_n
        
        prior["visits"] = new_n
        prior["mean_score"] = round(new_mean, 4)
        
        if "last_scores" not in prior:
            prior["last_scores"] = []
        prior["last_scores"].append(round(score, 4))
        if len(prior["last_scores"]) > 20:
            prior["last_scores"].pop(0)
            
        self.data[intent][action_key] = prior
        self._save()

# Global mcts instance
mcts = MCTSLight()
