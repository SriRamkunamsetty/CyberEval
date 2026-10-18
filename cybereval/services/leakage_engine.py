"""
CyberEval - Benchmark Integrity & Leakage Auditor (Innovation 6)
Detects near-duplicate scenarios across dataset splits and scenario families using Jaccard and n-gram similarity.
"""

import re
from typing import List, Dict, Any


class LeakageDetectorEngine:
    """Audits benchmark integrity and prevents data leakage across train/test splits."""

    @classmethod
    def audit_splits(
        cls,
        scenarios: List[Dict[str, Any]],
        similarity_threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Audits scenarios for cross-split contamination and near-duplicate leakage.
        """
        leakage_violations = []
        high_similarity_pairs = []

        # Tokenize narratives and evidence payloads
        scenario_token_sets = {}
        for s in scenarios:
            code = s.get("scenario_code", "")
            narrative = s.get("narrative", "")
            ev_text = " ".join([str(e.get("raw_payload", "")) for e in s.get("evidence_items", [])])
            full_text = f"{narrative} {ev_text}".lower()
            tokens = set(re.findall(r"\w{4,}", full_text))
            scenario_token_sets[code] = {
                "tokens": tokens,
                "split": s.get("split", "test"),
                "category": s.get("category", "attack_chain"),
                "title": s.get("title", ""),
                "counterfactual_pair_id": s.get("counterfactual_pair_id"),
            }

        codes = list(scenario_token_sets.keys())
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                c1, c2 = codes[i], codes[j]
                meta1, meta2 = scenario_token_sets[c1], scenario_token_sets[c2]

                # Counterfactual pairs are intentionally related, skip them if tagged as such
                if meta1["counterfactual_pair_id"] and meta1["counterfactual_pair_id"] == meta2["counterfactual_pair_id"]:
                    continue

                set1, set2 = meta1["tokens"], meta2["tokens"]
                if not set1 or not set2:
                    continue

                intersection = len(set1.intersection(set2))
                union = len(set1.union(set2))
                jaccard = intersection / union if union > 0 else 0.0

                if jaccard >= similarity_threshold:
                    pair_info = {
                        "scenario_a": c1,
                        "scenario_b": c2,
                        "split_a": meta1["split"],
                        "split_b": meta2["split"],
                        "similarity_score": round(jaccard, 3),
                    }
                    high_similarity_pairs.append(pair_info)

                    # Cross-split leakage is an integrity violation!
                    if meta1["split"] != meta2["split"] and "held_out" in [meta1["split"], meta2["split"]]:
                        leakage_violations.append({
                            **pair_info,
                            "violation": "Held-out test scenario leaked into training or validation split.",
                        })

        is_integrity_valid = len(leakage_violations) == 0

        return {
            "total_scenarios_audited": len(scenarios),
            "integrity_passed": is_integrity_valid,
            "leakage_violations_count": len(leakage_violations),
            "leakage_violations": leakage_violations,
            "near_duplicate_pairs_count": len(high_similarity_pairs),
            "near_duplicate_pairs": high_similarity_pairs,
        }
