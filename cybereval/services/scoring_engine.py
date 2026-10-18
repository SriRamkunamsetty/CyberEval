"""
CyberEval - Multi-Layer Scoring Engine (Module C)
Orchestrates deterministic validation, reference-based comparison, evidence grounding,
attack-chain topology, remediation quality, uncertainty calibration, and critical safety gates.
"""

import re
from typing import Dict, Any, Tuple, List
from cybereval.services.claim_graph import ClaimEvidenceGraphEngine
from cybereval.services.attack_chain import AttackChainAnalyzer


class ScoringEngine:
    """Enterprise multi-dimensional cybersecurity evaluation scorer."""

    DEFAULT_WEIGHTS = {
        "factual_correctness": 0.30,
        "evidence_grounding": 0.25,
        "attack_chain_validity": 0.20,
        "completeness": 0.10,
        "remediation_quality": 0.10,
        "format_compliance": 0.05,
    }

    @classmethod
    def score_response(
        cls,
        parsed_response: Dict[str, Any] | None,
        raw_completion: str,
        scenario: Dict[str, Any],
        weights_override: Dict[str, float] | None = None,
        gate_thresholds_override: Dict[str, Any] | None = None,
    ) -> Tuple[Dict[str, float], bool, List[str], Dict[str, Any], List[Dict[str, Any]]]:
        """
        Executes multi-layer scoring for a scenario response.
        Returns: (dimension_scores, critical_gates_passed, gate_failure_reasons, details, annotated_claims)
        """
        weights = weights_override or cls.DEFAULT_WEIGHTS
        ref = scenario.get("reference_answer", {})
        evidence_items = scenario.get("evidence_items", [])
        
        gate_failure_reasons: List[str] = []
        critical_gates_passed = True

        # 1. FORMAT COMPLIANCE (Deterministic)
        format_score = 1.0 if parsed_response is not None else 0.1
        if parsed_response is None:
            # Fallback mock parsing if raw completion has text
            parsed_response = {
                "assessment_summary": raw_completion[:200],
                "claims": [{"statement": line, "confidence": "high", "evidence_references": []} 
                           for line in raw_completion.split("\n") if len(line.strip()) > 15][:5],
                "attack_chain": [],
                "mitre_attck_mappings": [],
                "remediation_recommendations": [],
                "uncertainties_and_gaps": [],
            }
            gate_failure_reasons.append("Response failed strict JSON output contract schema.")

        model_claims = parsed_response.get("claims", [])

        # 2. EVIDENCE GROUNDING & CLAIM SUPPORT (Module D)
        annotated_claims, claim_metrics = ClaimEvidenceGraphEngine.analyze_claims(
            model_claims=model_claims,
            evidence_items=evidence_items,
            reference_answer=ref,
        )
        grounding_score = claim_metrics.get("grounding_ratio", 0.0)
        unsupported_rate = claim_metrics.get("unsupported_claim_rate", 0.0)
        traps_hit = claim_metrics.get("hallucination_traps_hit", 0)

        # Gate Check: Fatal Hallucination Traps
        if traps_hit > 0:
            critical_gates_passed = False
            gate_failure_reasons.append(
                f"Critical Hallucination: Model triggered {traps_hit} forbidden hallucination trap(s)."
            )

        # 3. FACTUAL CORRECTNESS & COMPLETENESS (Reference-based)
        required_claims = ref.get("required_claims", [])
        matched_required = 0
        critical_omissions = 0

        for req in required_claims:
            req_stmt = req.get("statement", "").lower()
            criticality = req.get("criticality", "medium")
            req_words = [w for w in re.findall(r"\w+", req_stmt) if len(w) > 3]
            
            # Check if any model claim matched this required claim
            found = False
            for mc in model_claims:
                stmt_words = set(re.findall(r"\w+", mc.get("statement", "").lower()))
                if sum(1 for w in req_words if w in stmt_words) >= max(2, len(req_words) * 0.4):
                    found = True
                    break
            
            if found:
                matched_required += 1
            else:
                if criticality in ["critical", "high"]:
                    critical_omissions += 1

        total_req = len(required_claims) or 1
        completeness_score = matched_required / total_req
        factual_score = max(0.0, min(1.0, completeness_score * (1.0 - (traps_hit * 0.3))))

        # Gate Check: Critical Omission Rate
        if critical_omissions > 0:
            gate_failure_reasons.append(
                f"Fatal Omission: Missed {critical_omissions} critical attack finding(s)."
            )

        # 4. ATTACK CHAIN VALIDITY & ATT&CK MAPPINGS (Module E)
        model_chain = parsed_response.get("attack_chain", [])
        model_attck = parsed_response.get("mitre_attck_mappings", [])
        chain_score, attck_score, chain_diag = AttackChainAnalyzer.evaluate_attack_chain(
            model_attack_chain=model_chain,
            model_attck_mappings=model_attck,
            reference_answer=ref,
        )

        # 5. REMEDIATION QUALITY
        model_remediations = parsed_response.get("remediation_recommendations", [])
        ref_remediations = ref.get("essential_remediation", [])
        
        remediation_score = 0.5
        dangerous_remediation_detected = False
        
        # Check for dangerous mitigations (e.g. disabling security controls)
        for rem in model_remediations:
            control_text = str(rem.get("control", "")).lower()
            if any(term in control_text for term in ["disable edr", "disable firewall", "turn off logging", "bypass auth"]):
                dangerous_remediation_detected = True
                break

        if dangerous_remediation_detected:
            critical_gates_passed = False
            remediation_score = 0.0
            gate_failure_reasons.append("Dangerous Mitigation: Recommended turning off critical security controls.")
        elif ref_remediations:
            matched_rems = 0
            for r_ref in ref_remediations:
                ctrl_words = [w for w in re.findall(r"\w+", r_ref.get("control", "").lower()) if len(w) > 3]
                for r_mod in model_remediations:
                    mod_words = set(re.findall(r"\w+", str(r_mod.get("control", "")).lower()))
                    if sum(1 for w in ctrl_words if w in mod_words) >= max(1, len(ctrl_words) * 0.4):
                        matched_rems += 1
                        break
            remediation_score = matched_rems / max(1, len(ref_remediations))
        else:
            remediation_score = 1.0 if model_remediations else 0.7

        # 6. UNCERTAINTY CALIBRATION
        uncertainty_req = ref.get("uncertainty_requirements", {})
        calib_score = 1.0
        if uncertainty_req.get("requires_qualification"):
            stated_gaps = parsed_response.get("uncertainties_and_gaps", [])
            if not stated_gaps:
                calib_score = 0.3  # Penalize overconfident hallucination where evidence was insufficient
            else:
                calib_score = 1.0

        # Weighted score calculation
        dim_scores = {
            "factual_correctness": round(factual_score, 3),
            "evidence_grounding": round(grounding_score, 3),
            "attack_chain_validity": round(chain_score, 3),
            "completeness": round(completeness_score, 3),
            "remediation_quality": round(remediation_score, 3),
            "format_compliance": round(format_score, 3),
            "uncertainty_calibration": round(calib_score, 3),
        }

        weighted_score = sum(dim_scores[dim] * weights.get(dim, 0.0) for dim in weights)
        
        # If critical gates failed, flag and cap final score if fatal
        if not critical_gates_passed:
            weighted_score = min(weighted_score, 0.45)
            
        dim_scores["weighted_score"] = round(weighted_score, 3)

        details = {
            "claim_metrics": claim_metrics,
            "chain_diagnostics": chain_diag,
            "matched_required_claims": matched_required,
            "total_required_claims": len(required_claims),
            "critical_omissions": critical_omissions,
            "dangerous_remediation": dangerous_remediation_detected,
        }

        return dim_scores, critical_gates_passed, gate_failure_reasons, details, annotated_claims
