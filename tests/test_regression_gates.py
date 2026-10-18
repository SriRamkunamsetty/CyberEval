"""
Unit tests for Regression Testing & CI/CD Release Gates (Module G & Innovation 4)
"""

from cybereval.services.regression_engine import RegressionEngine


def test_approved_release_gate():
    baseline_run = {
        "id": "run-base",
        "model_name": "baseline-expert",
        "overall_score": 0.88,
        "factual_correctness": 0.90,
        "evidence_grounding": 0.85,
        "attack_chain_validity": 0.85,
        "unsupported_claim_rate": 0.05,
        "critical_gates_passed": True,
    }
    candidate_run = {
        "id": "run-cand",
        "model_name": "candidate-v2",
        "overall_score": 0.91,
        "factual_correctness": 0.92,
        "evidence_grounding": 0.88,
        "attack_chain_validity": 0.90,
        "unsupported_claim_rate": 0.04,
        "critical_gates_passed": True,
    }

    resp = RegressionEngine.compare_runs(
        candidate_run=candidate_run,
        baseline_run=baseline_run,
        candidate_responses=[],
        baseline_responses=[],
    )

    assert resp.is_gate_passed is True
    assert resp.gate_verdict == "RELEASE_APPROVED"
    assert resp.overall_score_delta > 0.0


def test_blocked_by_regression_drop():
    baseline_run = {
        "id": "run-base",
        "overall_score": 0.90,
        "unsupported_claim_rate": 0.05,
        "critical_gates_passed": True,
    }
    candidate_run = {
        "id": "run-cand",
        "overall_score": 0.70,  # 20% drop!
        "unsupported_claim_rate": 0.25,
        "critical_gates_passed": False,
    }

    resp = RegressionEngine.compare_runs(
        candidate_run=candidate_run,
        baseline_run=baseline_run,
        candidate_responses=[],
        baseline_responses=[],
    )

    assert resp.is_gate_passed is False
    assert resp.gate_verdict == "BLOCKED_BY_CRITICAL_GATES"
    assert len(resp.blocked_reasons) >= 1
