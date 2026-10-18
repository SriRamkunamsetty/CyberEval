"""
CyberEval - Review & Adjudication Schemas (Module H & Innovation 3)
Contracts for expert double-blind review, Cohen's kappa agreement, and adjudication.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ReviewDecisionBase(BaseModel):
    reviewer_id: str
    claim_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    rubric_ratings: Dict[str, float] = Field(
        default_factory=lambda: {
            "factual_correctness": 1.0,
            "evidence_grounding": 1.0,
            "attack_chain_validity": 1.0,
            "completeness": 1.0,
            "remediation_quality": 1.0,
            "uncertainty_calibration": 1.0,
        }
    )
    overall_verdict: str = "ACCEPT"  # ACCEPT, QUALIFIED, REJECT
    notes: str = ""
    dispute_raised: bool = False


class ReviewDecisionCreate(ReviewDecisionBase):
    task_id: str


class ReviewDecisionRead(ReviewDecisionBase):
    id: str
    task_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewTaskBase(BaseModel):
    model_response_id: str
    assigned_reviewer_id: str
    is_double_blind: bool = True


class ReviewTaskCreate(ReviewTaskBase):
    pass


class ReviewTaskRead(ReviewTaskBase):
    id: str
    status: str
    created_at: datetime
    decisions: List[ReviewDecisionRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class AdjudicationCreate(BaseModel):
    model_response_id: str
    adjudicator_id: str
    dispute_reason: str
    final_verdict: str  # UPHELD_AUTOMATED, UPHELD_REVIEWER_A, UPHELD_REVIEWER_B, CUSTOM
    final_score: float
    rationale: str
    reference_answer_correction_proposed: bool = False
    proposed_correction_payload: Optional[Dict[str, Any]] = None


class AdjudicationRead(AdjudicationCreate):
    id: str
    is_applied_to_dataset: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InterRaterAgreementResponse(BaseModel):
    dataset_version_id: str
    total_double_reviewed_tasks: int
    observed_agreement_pct: float
    expected_agreement_pct: float
    cohens_kappa: float
    interpretation: str  # "Slight", "Fair", "Moderate", "Substantial", "Almost Perfect"
    ambiguous_scenarios_flagged: List[Dict[str, Any]]
    disagreements_by_dimension: Dict[str, int]
