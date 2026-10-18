"""
CyberEval - Regression & Release Gating Schemas (Module G & Innovation 4)
Contracts for comparing candidate models against baselines and gating releases in CI/CD.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ScenarioDiff(BaseModel):
    scenario_code: str
    scenario_title: str
    category: str
    baseline_score: float
    candidate_score: float
    score_delta: float
    status: str  # "IMPROVED", "STABLE", "REGRESSED"
    baseline_unsupported_claims: int
    candidate_unsupported_claims: int
    critical_gate_failed: bool
    reasons: List[str] = Field(default_factory=list)


class RegressionComparisonRequest(BaseModel):
    candidate_run_id: str
    baseline_run_id: str
    policy_name: Optional[str] = None  # if None, default policy used


class RegressionComparisonResponse(BaseModel):
    candidate_run_id: str
    baseline_run_id: str
    candidate_model: str
    baseline_model: str
    overall_score_delta: float
    factual_correctness_delta: float
    evidence_grounding_delta: float
    attack_chain_validity_delta: float
    unsupported_claim_rate_delta: float
    scenarios_regressed_count: int
    scenarios_improved_count: int
    scenarios_stable_count: int
    new_unsupported_claims_count: int
    is_gate_passed: bool
    gate_verdict: str  # "RELEASE_APPROVED", "BLOCKED_BY_REGRESSION", "BLOCKED_BY_CRITICAL_GATES"
    blocked_reasons: List[str]
    scenario_diffs: List[ScenarioDiff]


class ReleaseGatePolicyBase(BaseModel):
    name: str = Field(..., example="strict-enterprise-gate")
    description: str
    max_tolerated_score_drop: float = 0.03
    max_unsupported_claim_rate: float = 0.10
    max_regressed_scenarios: int = 1
    require_zero_hallucination_traps: bool = True
    is_active: bool = True


class ReleaseGatePolicyCreate(ReleaseGatePolicyBase):
    pass


class ReleaseGatePolicyRead(ReleaseGatePolicyBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
