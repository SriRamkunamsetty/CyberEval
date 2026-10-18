"""
Unit tests for Attack Chain Completeness & Invariant Engine (Module E)
"""

from cybereval.services.attack_chain import AttackChainAnalyzer


def test_valid_attack_chain_and_attck_mappings():
    ref = {
        "critical_attack_path": [
            {"source": "Initial Access", "target": "Execution"},
            {"source": "Execution", "target": "Persistence"},
        ],
        "valid_attck_mappings": [
            {"technique_id": "T1566.001", "tactic": "Initial Access"},
            {"technique_id": "T1059.001", "tactic": "Execution"},
        ],
    }

    model_chain = [
        {"source": "Initial Access", "target": "Execution"},
        {"source": "Execution", "target": "Persistence"},
    ]
    model_attck = [
        {"technique_id": "T1566.001", "tactic": "Initial Access"},
        {"technique_id": "T1059.001", "tactic": "Execution"},
    ]

    path_score, attck_score, diag = AttackChainAnalyzer.evaluate_attack_chain(
        model_attack_chain=model_chain,
        model_attck_mappings=model_attck,
        reference_answer=ref,
    )

    assert path_score == 1.0
    assert attck_score == 1.0
    assert diag["has_causal_cycles"] is False


def test_circular_causality_penalized():
    ref = {
        "critical_attack_path": [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
        ],
        "valid_attck_mappings": [],
    }

    # Circular chain: A -> B -> C -> A
    circular_chain = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"},
    ]

    path_score, attck_score, diag = AttackChainAnalyzer.evaluate_attack_chain(
        model_attack_chain=circular_chain,
        model_attck_mappings=[],
        reference_answer=ref,
    )

    assert diag["has_causal_cycles"] is True
    assert path_score < 1.0
