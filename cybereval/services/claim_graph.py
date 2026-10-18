"""
CyberEval - Claim-to-Evidence Graph Engine (Module D & Innovation 1)
Constructs directed bipartite graphs linking extracted claims to verified evidence logs,
detects hallucination traps, unsupported inferences, and evidence gaps.
"""

import re
from typing import List, Dict, Any, Tuple
import networkx as nx
from cybereval.schemas.claim import GraphNode, GraphEdge, ClaimGraphResponse


class ClaimEvidenceGraphEngine:
    """Analyzes claims, builds Claim-to-Evidence graphs, and detects ungrounded reasoning."""

    @classmethod
    def analyze_claims(
        cls,
        model_claims: List[Dict[str, Any]],
        evidence_items: List[Dict[str, Any]],
        reference_answer: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluates each claim against scenario evidence and forbidden hallucination traps.
        Returns: (annotated_claims, summary_metrics)
        """
        forbidden_conclusions = reference_answer.get("forbidden_conclusions", [])
        required_claims = reference_answer.get("required_claims", [])
        
        # Build evidence lookup table
        evidence_by_code = {e.get("evidence_code"): e for e in evidence_items}
        all_evidence_codes = set(evidence_by_code.keys())
        
        annotated_claims = []
        supported_count = 0
        unsupported_count = 0
        contradicted_count = 0
        traps_hit = 0
        referenced_evidence_codes = set()

        for idx, claim in enumerate(model_claims):
            stmt = claim.get("statement", "").strip()
            cited_ev = claim.get("evidence_references", [])
            # Also detect cited evidence in text if formatted like EV-01
            found_ev_in_text = re.findall(r"EV-\d+", stmt)
            all_cited = list(set(cited_ev + found_ev_in_text))

            # 1. Check Hallucination Traps (Forbidden Conclusions)
            trap_hit = False
            trap_id = None
            trap_reason = None
            lower_stmt = stmt.lower()
            is_negated = any(neg in lower_stmt for neg in [
                "not ", " no ", "never", "unconfirmed", "unsupported", "insufficient",
                "routine", "not the", "did not", "failed to", "blocked", "prevented"
            ])

            if not is_negated:
                for fc in forbidden_conclusions:
                    fc_stmt = fc.get("statement", "").lower()
                    fc_id = fc.get("claim_id", "FC")
                    fc_reason = fc.get("reason", "Forbidden conclusion not supported by evidence.")
                    
                    fc_keywords = [w for w in re.findall(r"\w+", fc_stmt) if len(w) > 3 and w not in ["this", "that", "from", "with", "have", "were"]]
                    stmt_words = set(re.findall(r"\w+", lower_stmt))
                    matches = sum(1 for w in fc_keywords if w in stmt_words)
                    
                    if len(fc_keywords) > 0 and (matches / len(fc_keywords)) >= 0.60:
                        trap_hit = True
                        trap_id = fc_id
                        trap_reason = fc_reason
                        traps_hit += 1
                        break

            evidence_links = []
            if trap_hit:
                status = "CONTRADICTED"
                contradicted_count += 1
                evidence_gap = f"Critical Hallucination: {trap_reason}"
                recommended_corr = "Do not assert unconfirmed high-impact outcomes; qualify observed activity as inconclusive."
            else:
                # 2. Check Evidence Support
                valid_links = [code for code in all_cited if code in evidence_by_code]
                for code in valid_links:
                    referenced_evidence_codes.add(code)
                    evidence_links.append({
                        "evidence_code": code,
                        "link_type": "supports",
                        "entailment_score": 0.95,
                        "explanation": f"Corroborated by telemetry in {code}",
                    })

                # Check if claim aligns with any required claim
                matches_required = False
                for rc in required_claims:
                    rc_stmt = rc.get("statement", "").lower()
                    rc_keywords = [w for w in re.findall(r"\w+", rc_stmt) if len(w) > 3]
                    stmt_words = set(re.findall(r"\w+", stmt.lower()))
                    if sum(1 for w in rc_keywords if w in stmt_words) >= max(2, len(rc_keywords) * 0.4):
                        matches_required = True
                        # Auto-link required evidence if valid
                        for req_ev in rc.get("required_evidence", []):
                            if req_ev in evidence_by_code and req_ev not in [l["evidence_code"] for l in evidence_links]:
                                referenced_evidence_codes.add(req_ev)
                                evidence_links.append({
                                    "evidence_code": req_ev,
                                    "link_type": "supports",
                                    "entailment_score": 0.90,
                                    "explanation": f"Grounded in verified scenario log {req_ev}",
                                })
                        break

                if evidence_links or matches_required:
                    status = "SUPPORTED"
                    supported_count += 1
                    evidence_gap = None
                    recommended_corr = None
                else:
                    status = "UNSUPPORTED"
                    unsupported_count += 1
                    evidence_gap = "No verified telemetry or log record in the scenario supports this claim."
                    recommended_corr = "Describe the observed events directly without inferring ungrounded outcomes."

            annotated_claims.append({
                "claim_index": idx,
                "statement": stmt,
                "claim_type": claim.get("claim_type", "inference"),
                "status": status,
                "is_hallucination_trap_hit": trap_hit,
                "forbidden_conclusion_id": trap_id,
                "confidence_expressed": claim.get("confidence", "high"),
                "evidence_gap_description": evidence_gap,
                "recommended_correction": recommended_corr,
                "evidence_links": evidence_links,
            })

        total = len(model_claims) or 1
        grounding_ratio = supported_count / total
        unsupported_claim_rate = (unsupported_count + contradicted_count) / total
        critical_evidence_count = sum(1 for e in evidence_items if e.get("is_critical", True)) or 1
        evidence_utilization = len(referenced_evidence_codes) / critical_evidence_count

        summary_metrics = {
            "total_claims": len(model_claims),
            "supported_claims": supported_count,
            "unsupported_claims": unsupported_count,
            "contradicted_claims": contradicted_count,
            "grounding_ratio": round(grounding_ratio, 3),
            "unsupported_claim_rate": round(unsupported_claim_rate, 3),
            "hallucination_traps_hit": traps_hit,
            "evidence_utilization_ratio": round(min(1.0, evidence_utilization), 3),
        }

        return annotated_claims, summary_metrics

    @classmethod
    def build_claim_evidence_graph(
        cls,
        scenario_code: str,
        model_response_id: str,
        annotated_claims: List[Dict[str, Any]],
        evidence_items: List[Dict[str, Any]],
        reference_answer: Dict[str, Any],
    ) -> ClaimGraphResponse:
        """
        Builds graph structure of nodes and edges for visualization in the UI.
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        G = nx.DiGraph()

        # 1. Evidence Nodes
        for ev in evidence_items:
            code = ev.get("evidence_code", "EV")
            node_id = f"ev_{code}"
            ev_type = ev.get("evidence_type", "log")
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=f"[{code}] {ev_type.upper()}",
                    node_type="evidence",
                    status="CRITICAL_EVIDENCE" if ev.get("is_critical", True) else "OBSERVED_EVIDENCE",
                    category=ev_type,
                    details=ev.get("raw_payload", {}),
                )
            )
            G.add_node(node_id, type="evidence")

        # 2. Claim Nodes and Edges
        for c in annotated_claims:
            idx = c.get("claim_index", 0)
            claim_id = f"claim_{idx}"
            stmt = c.get("statement", "")
            short_label = stmt[:45] + "..." if len(stmt) > 45 else stmt
            status = c.get("status", "UNSUPPORTED")
            
            nodes.append(
                GraphNode(
                    id=claim_id,
                    label=f"C{idx + 1}: {short_label}",
                    node_type="claim",
                    status=status,
                    category=c.get("claim_type", "inference"),
                    details={
                        "statement": stmt,
                        "status": status,
                        "gap": c.get("evidence_gap_description"),
                        "correction": c.get("recommended_correction"),
                        "is_trap": c.get("is_hallucination_trap_hit"),
                    },
                )
            )
            G.add_node(claim_id, type="claim")

            # Edges to evidence
            ev_links = c.get("evidence_links", [])
            if ev_links:
                for link in ev_links:
                    ev_code = link.get("evidence_code")
                    ev_node_id = f"ev_{ev_code}"
                    rel = "SUPPORTS" if link.get("link_type") == "supports" else "CONTRADICTS"
                    edges.append(
                        GraphEdge(
                            source=ev_node_id,
                            target=claim_id,
                            relation=rel,
                            weight=link.get("entailment_score", 1.0),
                        )
                    )
                    G.add_edge(ev_node_id, claim_id, relation=rel)
            elif status == "UNSUPPORTED":
                # Create phantom unsupported edge to indicate dangling hypothesis
                edges.append(
                    GraphEdge(
                        source=claim_id,
                        target=claim_id,
                        relation="UNSUPPORTED_LEAP",
                        weight=0.0,
                    )
                )

        # 3. Forbidden Conclusion Traps
        for fc in reference_answer.get("forbidden_conclusions", []):
            fc_id = fc.get("claim_id", "FC")
            trap_node_id = f"trap_{fc_id}"
            nodes.append(
                GraphNode(
                    id=trap_node_id,
                    label=f"TRAP: {fc_id}",
                    node_type="hallucination_trap",
                    status="FORBIDDEN_ZONE",
                    category="trap",
                    details=fc,
                )
            )
            # If any claim hit this trap, connect edge
            for c in annotated_claims:
                if c.get("forbidden_conclusion_id") == fc_id:
                    edges.append(
                        GraphEdge(
                            source=f"claim_{c.get('claim_index', 0)}",
                            target=trap_node_id,
                            relation="FALLS_INTO_TRAP",
                            weight=1.0,
                        )
                    )

        total_claims = max(1, len(annotated_claims))
        supported = sum(1 for c in annotated_claims if c.get("status") == "SUPPORTED")
        unsupported = sum(1 for c in annotated_claims if c.get("status") in ["UNSUPPORTED", "CONTRADICTED"])
        traps = sum(1 for c in annotated_claims if c.get("is_hallucination_trap_hit"))

        return ClaimGraphResponse(
            scenario_code=scenario_code,
            model_response_id=model_response_id,
            nodes=nodes,
            edges=edges,
            grounding_ratio=round(supported / total_claims, 3),
            unsupported_claims_count=unsupported,
            hallucination_traps_hit=traps,
            evidence_utilization_ratio=round(min(1.0, len([e for e in edges if e.relation == "SUPPORTS"]) / max(1, len(evidence_items))), 3),
        )
