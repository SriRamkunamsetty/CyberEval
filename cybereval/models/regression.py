"""
CyberEval - Regression & Release Gating Models (Module G & Innovation 4)
Maintains audit trail of baseline comparisons, regression deltas, and automated CI/CD release decisions.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from cybereval.core.database import Base, TimestampMixin


class RegressionResult(Base, TimestampMixin):
    __tablename__ = "regression_results"

    candidate_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    baseline_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    
    # Deltas (Candidate - Baseline)
    overall_score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    factual_correctness_delta: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_grounding_delta: Mapped[float] = mapped_column(Float, default=0.0)
    attack_chain_validity_delta: Mapped[float] = mapped_column(Float, default=0.0)
    unsupported_claim_rate_delta: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Flip statistics
    scenarios_regressed_count: Mapped[int] = mapped_column(Integer, default=0)
    scenarios_improved_count: Mapped[int] = mapped_column(Integer, default=0)
    new_unsupported_claims_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Decision Gate
    is_gate_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    gate_verdict: Mapped[str] = mapped_column(String(50), default="RELEASE_APPROVED")
    # "RELEASE_APPROVED", "BLOCKED_BY_REGRESSION", "BLOCKED_BY_CRITICAL_GATES"
    
    blocked_reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    scenario_diffs: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # [{"scenario_code": "CE-AC-001", "baseline_score": 0.85, "candidate_score": 0.50, "status": "REGRESSED"}]


class ReleaseGatePolicy(Base, TimestampMixin):
    __tablename__ = "release_gate_policies"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    max_tolerated_score_drop: Mapped[float] = mapped_column(Float, default=0.03)  # max 3% score drop
    max_unsupported_claim_rate: Mapped[float] = mapped_column(Float, default=0.10)  # max 10% ungrounded claims
    max_regressed_scenarios: Mapped[int] = mapped_column(Integer, default=1)  # max 1 regressed scenario allowed
    require_zero_hallucination_traps: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
