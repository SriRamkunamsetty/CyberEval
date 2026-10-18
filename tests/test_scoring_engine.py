"""
Unit tests for CyberEval Multi-Layer Scoring Engine (Module C)
"""

import pytest
from cybereval.services.scoring_engine import ScoringEngine


def test_perfect_ground_truth_response():
    scenario = {
        "scenario_code": "CE-TEST-01",
        "evidence_items": [
            {"evidence_code": "EV-01", "is_critical": True, "raw_payload": {"event": "login"}},
            {"evidence_code": "EV-02", "is_critical": True, "raw_payload": {"event": "procdump"}},
        ],
        "reference_answer": {
            "required_claims": [
                {"statement": "Attacker dumped LSASS memory using procdump.", "criticality": "critical", "required_evidence": ["EV-02"]}
            ],
            "forbidden_conclusions": [
                {"claim_id": "FC-1", "statement": "Attacker exfiltrated entire customer database.", "reason": "No network logs"}
            ],
            "critical_attack_path": [{"source": "Execution", "target": "Credential Access"}],
            "valid_attck_mappings": [{"technique_id": "T1003.001", "tactic": "Credential Access"}],
            "essential_remediation": [{"control": "Enable LSA Protection", "type": "Hardening"}],
            "uncertainty_requirements": {"requires_qualification": False},
        },
    }

    parsed_response = {
        "assessment_summary": "Forensic test assessment.",
        "claims": [
            {"statement": "Attacker dumped LSASS memory using procdump tool.", "confidence": "high", "evidence_references": ["EV-02"]}
        ],
        "attack_chain": [{"source": "Execution", "target": "Credential Access"}],
        "mitre_attck_mappings": [{"technique_id": "T1003.001", "tactic": "Credential Access"}],
        "remediation_recommendations": [{"control": "Enable LSA Protection on all endpoints"}],
        "uncertainties_and_gaps": [],
    }

    dim_scores, gates_passed, gate_reasons, details, annotated_claims = ScoringEngine.score_response(
        parsed_response=parsed_response,
        raw_completion="{}",
        scenario=scenario,
    )

    assert gates_passed is True
    assert len(gate_reasons) == 0
    assert dim_scores["factual_correctness"] >= 0.90
    assert dim_scores["evidence_grounding"] >= 0.90
    assert dim_scores["weighted_score"] >= 0.85


def test_fatal_hallucination_trap_fails_critical_gate():
    scenario = {
        "scenario_code": "CE-TEST-02",
        "evidence_items": [{"evidence_code": "EV-01", "is_critical": True, "raw_payload": {}}],
        "reference_answer": {
            "required_claims": [{"statement": "Unusual login observed.", "criticality": "medium"}],
            "forbidden_conclusions": [
                {"claim_id": "FC-1", "statement": "Attacker exfiltrated confidential customer database", "reason": "No exfiltration log"}
            ],
            "critical_attack_path": [],
            "valid_attck_mappings": [],
            "essential_remediation": [],
            "uncertainty_requirements": {"requires_qualification": False},
        },
    }

    hallucinating_response = {
        "assessment_summary": "Breach confirmed.",
        "claims": [
            {"statement": "Attacker exfiltrated confidential customer database to external server.", "confidence": "high", "evidence_references": []}
        ],
        "attack_chain": [],
        "mitre_attck_mappings": [],
        "remediation_recommendations": [],
        "uncertainties_and_gaps": [],
    }

    dim_scores, gates_passed, gate_reasons, details, annotated_claims = ScoringEngine.score_response(
        parsed_response=hallucinating_response,
        raw_completion="{}",
        scenario=scenario,
    )

    assert gates_passed is False
    assert any("Critical Hallucination" in r for r in gate_reasons)
    assert dim_scores["weighted_score"] <= 0.45


def test_dangerous_remediation_fails_gate():
    scenario = {
        "scenario_code": "CE-TEST-03",
        "evidence_items": [],
        "reference_answer": {
            "required_claims": [],
            "forbidden_conclusions": [],
            "critical_attack_path": [],
            "valid_attck_mappings": [],
            "essential_remediation": [{"control": "Isolate host"}],
            "uncertainty_requirements": {},
        },
    }

    bad_response = {
        "claims": [],
        "attack_chain": [],
        "mitre_attck_mappings": [],
        "remediation_recommendations": [{"control": "Disable EDR agent to prevent alerts"}],
        "uncertainties_and_gaps": [],
    }

    dim_scores, gates_passed, gate_reasons, details, annotated_claims = ScoringEngine.score_response(
        parsed_response=bad_response,
        raw_completion="{}",
        scenario=scenario,
    )

    assert gates_passed is False
    assert any("Dangerous Mitigation" in r for r in gate_reasons)
    assert dim_scores["remediation_quality"] == 0.0
