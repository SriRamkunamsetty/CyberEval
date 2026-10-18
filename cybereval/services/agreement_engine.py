"""
CyberEval - Reviewer Disagreement & Inter-Rater Reliability Engine (Module H & Innovation 3)
Calculates Cohen's Kappa, tracks reviewer disagreement, and flags ambiguous benchmark scenarios.
"""

from typing import List, Dict, Any, Tuple
from cybereval.schemas.review import InterRaterAgreementResponse


class AgreementEngine:
    """Computes inter-rater reliability metrics and detects ambiguous benchmark cases."""

    @classmethod
    def compute_inter_rater_agreement(
        cls,
        dataset_version_id: str,
        paired_decisions: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]],
        # Each tuple is: (decision_reviewer_a, decision_reviewer_b, scenario_context)
    ) -> InterRaterAgreementResponse:
        """
        Computes Cohen's Kappa across double-blind reviewed tasks.
        """
        if not paired_decisions:
            return InterRaterAgreementResponse(
                dataset_version_id=dataset_version_id,
                total_double_reviewed_tasks=0,
                observed_agreement_pct=100.0,
                expected_agreement_pct=50.0,
                cohens_kappa=1.0,
                interpretation="Almost Perfect (No Disputed Double Reviews)",
                ambiguous_scenarios_flagged=[],
                disagreements_by_dimension={},
            )

        n = len(paired_decisions)
        agreements = 0
        categories = ["ACCEPT", "QUALIFIED", "REJECT"]
        
        counts_a = {cat: 0 for cat in categories}
        counts_b = {cat: 0 for cat in categories}

        disagreements_by_dim = {
            "factual_correctness": 0,
            "evidence_grounding": 0,
            "attack_chain_validity": 0,
            "remediation_quality": 0,
            "uncertainty_calibration": 0,
        }
        ambiguous_scenarios = []

        for dec_a, dec_b, scen in paired_decisions:
            v_a = dec_a.get("overall_verdict", "ACCEPT")
            v_b = dec_b.get("overall_verdict", "ACCEPT")

            counts_a[v_a] = counts_a.get(v_a, 0) + 1
            counts_b[v_b] = counts_b.get(v_b, 0) + 1

            if v_a == v_b:
                agreements += 1
            else:
                # Disagreement occurred
                ambiguous_scenarios.append({
                    "scenario_code": scen.get("scenario_code", "CE-UNKNOWN"),
                    "scenario_title": scen.get("title", ""),
                    "reviewer_a_verdict": v_a,
                    "reviewer_b_verdict": v_b,
                    "reviewer_a_notes": dec_a.get("notes", ""),
                    "reviewer_b_notes": dec_b.get("notes", ""),
                })

            # Check dimensional rubric discrepancies
            rub_a = dec_a.get("rubric_ratings", {})
            rub_b = dec_b.get("rubric_ratings", {})
            for dim in disagreements_by_dim:
                if abs(rub_a.get(dim, 1.0) - rub_b.get(dim, 1.0)) > 0.3:
                    disagreements_by_dim[dim] += 1

        # Observed agreement Po
        p_o = agreements / max(1, n)

        # Expected agreement Pe
        p_e = sum((counts_a[cat] / max(1, n)) * (counts_b[cat] / max(1, n)) for cat in categories)

        # Cohen's Kappa
        kappa = (p_o - p_e) / (1.0 - p_e) if (1.0 - p_e) != 0 else 1.0
        kappa = max(-1.0, min(1.0, kappa))

        if kappa >= 0.81:
            interpretation = "Almost Perfect"
        elif kappa >= 0.61:
            interpretation = "Substantial"
        elif kappa >= 0.41:
            interpretation = "Moderate"
        elif kappa >= 0.21:
            interpretation = "Fair"
        else:
            interpretation = "Slight / Poor (High Ambiguity Detected)"

        return InterRaterAgreementResponse(
            dataset_version_id=dataset_version_id,
            total_double_reviewed_tasks=n,
            observed_agreement_pct=round(p_o * 100, 1),
            expected_agreement_pct=round(p_e * 100, 1),
            cohens_kappa=round(kappa, 3),
            interpretation=interpretation,
            ambiguous_scenarios_flagged=ambiguous_scenarios,
            disagreements_by_dimension=disagreements_by_dim,
        )
