"""
CyberEval - Counterfactual Consistency Testing Engine (Innovation 2)
Tests models on paired scenarios differing by a single critical piece of evidence.
Validates whether models appropriately modulate certainty and conclusions when evidence changes.
"""

from typing import Dict, Any, Tuple


class CounterfactualTester:
    """Evaluates counterfactual reasoning sensitivity and certainty modulation."""

    @classmethod
    def evaluate_counterfactual_pair(
        cls,
        base_scenario: Dict[str, Any],
        variant_scenario: Dict[str, Any],
        base_response: Dict[str, Any],
        variant_response: Dict[str, Any],
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Compares model behavior across counterfactual scenario pairs.
        Returns: (counterfactual_score, passed, diagnostics)
        """
        delta_desc = variant_scenario.get("counterfactual_delta_description", "Evidence removed or modified")
        
        # Extract claims & confidence
        base_claims = base_response.get("claims", [])
        variant_claims = variant_response.get("claims", [])
        
        base_confidence = [c.get("confidence", "high").lower() for c in base_claims]
        variant_confidence = [c.get("confidence", "high").lower() for c in variant_claims]

        # Uncertainty handling check: Did variant response recognize missing evidence?
        variant_uncertainties = variant_response.get("uncertainties_and_gaps", [])
        
        # Check if variant model repeated base conclusion blindly
        base_stmts = [c.get("statement", "").lower() for c in base_claims]
        variant_stmts = [c.get("statement", "").lower() for c in variant_claims]
        
        identical_conclusions_count = 0
        for b_stmt in base_stmts:
            if b_stmt in variant_stmts:
                identical_conclusions_count += 1

        repetition_rate = identical_conclusions_count / max(1, len(base_stmts))
        
        # Modulated certainty: variant should have cautious confidence or explicit gaps
        has_cautious_confidence = any(c in ["cautious", "moderate", "low", "abstained"] for c in variant_confidence)
        has_stated_gaps = len(variant_uncertainties) > 0

        # Scoring logic:
        # If model repeated exact conclusion with high confidence despite missing evidence -> FAILED (score = 0.2)
        # If model modulated certainty or abstained appropriately -> PASSED (score = 1.0)
        if repetition_rate > 0.8 and not has_cautious_confidence and not has_stated_gaps:
            score = 0.2
            passed = False
            verdict = "FAILED_INSENSITIVITY: Model repeated conclusion despite missing critical evidence."
        elif has_cautious_confidence or has_stated_gaps:
            score = 1.0
            passed = True
            verdict = "PASSED: Model correctly modulated certainty and recognized the evidence deficit."
        else:
            score = 0.6
            passed = True
            verdict = "MARGINAL: Model partially adapted conclusion, but did not explicitly qualify uncertainty."

        diagnostics = {
            "delta_description": delta_desc,
            "repetition_rate": round(repetition_rate, 3),
            "certainty_modulated": has_cautious_confidence,
            "uncertainty_gaps_stated": variant_uncertainties,
            "counterfactual_verdict": verdict,
        }

        return score, passed, diagnostics
