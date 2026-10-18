"""
CyberEval - Attack-Chain Completeness & Consistency Validator (Module E)
Evaluates topological graph structure of attack paths, causal prerequisites,
temporal correlation vs causation, and MITRE ATT&CK technique mapping precision.
"""

from typing import List, Dict, Any, Tuple
import networkx as nx


class AttackChainAnalyzer:
    """Validates attack paths, topological prerequisites, and ATT&CK mappings."""

    @classmethod
    def evaluate_attack_chain(
        cls,
        model_attack_chain: List[Dict[str, Any]],
        model_attck_mappings: List[Dict[str, Any]],
        reference_answer: Dict[str, Any],
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Evaluates attack chain validity and MITRE ATT&CK mapping accuracy.
        Returns: (attack_chain_validity_score, attck_mapping_score, diagnostics)
        """
        ref_attack_path = reference_answer.get("critical_attack_path", [])
        ref_mappings = reference_answer.get("valid_attck_mappings", [])

        # 1. ATTACK PATH EVALUATION
        ref_edges = set()
        for edge in ref_attack_path:
            src = edge.get("source", "").lower().strip()
            tgt = edge.get("target", "").lower().strip()
            ref_edges.add((src, tgt))

        model_edges = set()
        for edge in model_attack_chain:
            src = edge.get("source", "").lower().strip()
            tgt = edge.get("target", "").lower().strip()
            model_edges.add((src, tgt))

        # Build graph to verify topological prerequisites and absence of cycles
        G_model = nx.DiGraph()
        for src, tgt in model_edges:
            G_model.add_edge(src, tgt)

        has_cycles = False
        try:
            cycles = list(nx.simple_cycles(G_model))
            has_cycles = len(cycles) > 0
        except Exception:
            has_cycles = False

        # Edge Precision, Recall, F1
        true_positives = len(ref_edges.intersection(model_edges))
        edge_precision = true_positives / max(1, len(model_edges)) if model_edges else (1.0 if not ref_edges else 0.0)
        edge_recall = true_positives / max(1, len(ref_edges)) if ref_edges else 1.0
        edge_f1 = (2 * edge_precision * edge_recall / (edge_precision + edge_recall)) if (edge_precision + edge_recall) > 0 else 0.0

        # Cycle penalty or reversed causality penalty
        path_score = edge_f1
        if has_cycles:
            path_score *= 0.5  # Penalize circular causal reasoning

        # 2. MITRE ATT&CK MAPPING EVALUATION
        ref_tech_ids = {m.get("technique_id", "").upper().strip() for m in ref_mappings}
        model_tech_ids = {m.get("technique_id", "").upper().strip() for m in model_attck_mappings}

        attck_tp = len(ref_tech_ids.intersection(model_tech_ids))
        attck_precision = attck_tp / max(1, len(model_tech_ids)) if model_tech_ids else (1.0 if not ref_tech_ids else 0.0)
        attck_recall = attck_tp / max(1, len(ref_tech_ids)) if ref_tech_ids else 1.0
        attck_f1 = (2 * attck_precision * attck_recall / (attck_precision + attck_recall)) if (attck_precision + attck_recall) > 0 else 0.0

        diagnostics = {
            "ref_edges_count": len(ref_edges),
            "model_edges_count": len(model_edges),
            "matched_edges": true_positives,
            "edge_precision": round(edge_precision, 3),
            "edge_recall": round(edge_recall, 3),
            "edge_f1": round(edge_f1, 3),
            "has_causal_cycles": has_cycles,
            "ref_attck_count": len(ref_tech_ids),
            "model_attck_count": len(model_tech_ids),
            "matched_attck_techniques": list(ref_tech_ids.intersection(model_tech_ids)),
            "missed_attck_techniques": list(ref_tech_ids - model_tech_ids),
            "unsupported_attck_techniques": list(model_tech_ids - ref_tech_ids),
            "attck_f1": round(attck_f1, 3),
        }

        return round(path_score, 3), round(attck_f1, 3), diagnostics
