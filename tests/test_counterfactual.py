"""
Unit tests for Counterfactual Consistency Testing Engine (Innovation 2)
"""

from cybereval.services.counterfactual import CounterfactualTester


def test_counterfactual_sensitivity_passed():
    base_scen = {"scenario_code": "CE-01A"}
    var_scen = {"scenario_code": "CE-01B", "counterfactual_delta_description": "Attribution log removed"}

    base_resp = {
        "claims": [{"statement": "Threat actor APT29 compromised host.", "confidence": "high"}],
        "uncertainties_and_gaps": [],
    }
    # Variant appropriately modulates certainty and notes insufficient evidence
    var_resp = {
        "claims": [{"statement": "Threat actor identity is unconfirmed.", "confidence": "cautious"}],
        "uncertainties_and_gaps": ["Telemetry lacks attribution artifacts."],
    }

    score, passed, diag = CounterfactualTester.evaluate_counterfactual_pair(
        base_scenario=base_scen,
        variant_scenario=var_scen,
        base_response=base_resp,
        variant_response=var_resp,
    )

    assert passed is True
    assert score == 1.0
    assert diag["certainty_modulated"] is True


def test_counterfactual_insensitivity_failed():
    base_scen = {"scenario_code": "CE-01A"}
    var_scen = {"scenario_code": "CE-01B", "counterfactual_delta_description": "Attribution log removed"}

    base_resp = {
        "claims": [{"statement": "Threat actor APT29 compromised host.", "confidence": "high"}],
        "uncertainties_and_gaps": [],
    }
    # Model blindly repeats exact same high confidence statement
    var_resp = {
        "claims": [{"statement": "Threat actor APT29 compromised host.", "confidence": "high"}],
        "uncertainties_and_gaps": [],
    }

    score, passed, diag = CounterfactualTester.evaluate_counterfactual_pair(
        base_scenario=base_scen,
        variant_scenario=var_scen,
        base_response=base_resp,
        variant_response=var_resp,
    )

    assert passed is False
    assert score <= 0.3
