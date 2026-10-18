"""
Unit tests for Inter-Rater Reliability Engine and Cohen's Kappa (Module H & Innovation 3)
"""

from cybereval.services.agreement_engine import AgreementEngine


def test_perfect_inter_rater_agreement():
    paired_decisions = [
        ({"overall_verdict": "ACCEPT", "rubric_ratings": {}}, {"overall_verdict": "ACCEPT", "rubric_ratings": {}}, {}),
        ({"overall_verdict": "REJECT", "rubric_ratings": {}}, {"overall_verdict": "REJECT", "rubric_ratings": {}}, {}),
        ({"overall_verdict": "ACCEPT", "rubric_ratings": {}}, {"overall_verdict": "ACCEPT", "rubric_ratings": {}}, {}),
    ]

    res = AgreementEngine.compute_inter_rater_agreement(
        dataset_version_id="ver-1",
        paired_decisions=paired_decisions,
    )

    assert res.observed_agreement_pct == 100.0
    assert res.cohens_kappa == 1.0
    assert res.interpretation == "Almost Perfect"
    assert len(res.ambiguous_scenarios_flagged) == 0


def test_disagreement_detection_and_scenario_flagging():
    paired_decisions = [
        ({"overall_verdict": "ACCEPT", "rubric_ratings": {"factual_correctness": 1.0}},
         {"overall_verdict": "REJECT", "rubric_ratings": {"factual_correctness": 0.2}},
         {"scenario_code": "CE-AMBIG-01", "title": "Ambiguous Scenario"}),
    ]

    res = AgreementEngine.compute_inter_rater_agreement(
        dataset_version_id="ver-1",
        paired_decisions=paired_decisions,
    )

    assert res.observed_agreement_pct == 0.0
    assert len(res.ambiguous_scenarios_flagged) == 1
    assert res.ambiguous_scenarios_flagged[0]["scenario_code"] == "CE-AMBIG-01"
