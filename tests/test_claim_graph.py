"""
Unit tests for Claim-to-Evidence Graph Engine (Module D & Innovation 1)
"""

from cybereval.services.claim_graph import ClaimEvidenceGraphEngine


def test_claim_extraction_and_graph_construction():
    evidence_items = [
        {"evidence_code": "EV-01", "evidence_type": "sysmon", "is_critical": True, "raw_payload": {"CommandLine": "wmic.exe"}},
        {"evidence_code": "EV-02", "evidence_type": "sysmon", "is_critical": True, "raw_payload": {"CommandLine": "procdump.exe"}},
    ]
    reference_answer = {
        "required_claims": [
            {"statement": "Lateral movement via WMI occurred.", "criticality": "high", "required_evidence": ["EV-01"]}
        ],
        "forbidden_conclusions": [
            {"claim_id": "FC-1", "statement": "All domain hashes were stolen and cracked.", "reason": "No cracking observed"}
        ],
    }
    model_claims = [
        {"statement": "Lateral movement via WMI occurred on the network.", "evidence_references": ["EV-01"]},
        {"statement": "Attacker also used stolen SSH keys to access external bastion.", "evidence_references": []},  # Unsupported
    ]

    annotated, metrics = ClaimEvidenceGraphEngine.analyze_claims(
        model_claims=model_claims,
        evidence_items=evidence_items,
        reference_answer=reference_answer,
    )

    assert len(annotated) == 2
    assert annotated[0]["status"] == "SUPPORTED"
    assert annotated[1]["status"] == "UNSUPPORTED"
    assert metrics["grounding_ratio"] == 0.5
    assert metrics["unsupported_claim_rate"] == 0.5

    # Build Graph
    graph_resp = ClaimEvidenceGraphEngine.build_claim_evidence_graph(
        scenario_code="CE-TEST-GRAPH",
        model_response_id="resp-123",
        annotated_claims=annotated,
        evidence_items=evidence_items,
        reference_answer=reference_answer,
    )

    assert len(graph_resp.nodes) >= 4  # 2 claims + 2 evidence items + 1 trap
    assert any(n.node_type == "evidence" for n in graph_resp.nodes)
    assert any(n.node_type == "claim" for n in graph_resp.nodes)
    assert any(e.relation == "SUPPORTS" for e in graph_resp.edges)
