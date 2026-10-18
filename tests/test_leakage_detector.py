"""
Unit tests for Benchmark Leakage and Integrity Auditor (Innovation 6)
"""

from cybereval.services.leakage_engine import LeakageDetectorEngine


def test_clean_split_no_leakage():
    scenarios = [
        {
            "scenario_code": "CE-01",
            "narrative": "Spearphishing email with malicious macro attachment executing powershell.",
            "split": "train",
            "category": "attack_chain",
            "evidence_items": [],
        },
        {
            "scenario_code": "CE-02",
            "narrative": "Kubernetes cluster API server unauthorized RBAC privilege escalation via service account token.",
            "split": "test",
            "category": "threat_modeling",
            "evidence_items": [],
        },
    ]

    report = LeakageDetectorEngine.audit_splits(scenarios)
    assert report["integrity_passed"] is True
    assert report["leakage_violations_count"] == 0


def test_held_out_leakage_detected():
    # Near identical scenarios placed across train and held_out
    narrative = "Attacker exploited Apache Struts CVE-2017-5638 through Content-Type header injection executing whoami command."
    scenarios = [
        {
            "scenario_code": "CE-TRAIN-01",
            "narrative": narrative,
            "split": "train",
            "category": "vulnerability_analysis",
            "evidence_items": [],
        },
        {
            "scenario_code": "CE-TEST-01",
            "narrative": narrative,
            "split": "held_out",
            "category": "vulnerability_analysis",
            "evidence_items": [],
        },
    ]

    report = LeakageDetectorEngine.audit_splits(scenarios)
    assert report["integrity_passed"] is False
    assert report["leakage_violations_count"] >= 1
    assert any("held-out" in v["violation"].lower() for v in report["leakage_violations"])
