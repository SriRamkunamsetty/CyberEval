"""
CyberEval - Reviewer Decisions & Adjudication Models (Module H)
Supports double-blind review, inter-rater reliability, dispute escalation, and benchmark correction.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cybereval.core.database import Base, TimestampMixin


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"

    model_response_id: Mapped[str] = mapped_column(ForeignKey("model_responses.id"), index=True)
    assigned_reviewer_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, in_review, completed, disputed
    is_double_blind: Mapped[bool] = mapped_column(Boolean, default=True)

    decisions: Mapped[List["ReviewDecision"]] = relationship(
        "ReviewDecision", back_populates="task", cascade="all, delete-orphan"
    )


class ReviewDecision(Base, TimestampMixin):
    __tablename__ = "review_decisions"

    task_id: Mapped[str] = mapped_column(ForeignKey("review_tasks.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(String(100), index=True)
    
    # Claim-level decisions: [{"claim_id": "...", "status": "SUPPORTED|UNSUPPORTED|CONTRADICTED", "rationale": "..."}]
    claim_decisions: Mapped[List[dict]] = mapped_column(JSON, default=list)
    
    # Rubric scores given by reviewer (0.0 to 1.0)
    rubric_ratings: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "factual_correctness": 1.0,
            "evidence_grounding": 1.0,
            "attack_chain_validity": 1.0,
            "completeness": 1.0,
            "remediation_quality": 1.0,
            "uncertainty_calibration": 1.0,
        },
    )
    
    overall_verdict: Mapped[str] = mapped_column(String(30), default="ACCEPT")  # ACCEPT, QUALIFIED, REJECT
    notes: Mapped[str] = mapped_column(Text, default="")
    dispute_raised: Mapped[bool] = mapped_column(Boolean, default=False)

    task: Mapped["ReviewTask"] = relationship("ReviewTask", back_populates="decisions")


class Adjudication(Base, TimestampMixin):
    __tablename__ = "adjudications"

    model_response_id: Mapped[str] = mapped_column(ForeignKey("model_responses.id"), index=True)
    adjudicator_id: Mapped[str] = mapped_column(String(100), index=True)
    dispute_reason: Mapped[str] = mapped_column(Text)
    final_verdict: Mapped[str] = mapped_column(String(30))  # UPHELD_AUTOMATED, UPHELD_REVIEWER_A, UPHELD_REVIEWER_B, CUSTOM
    final_score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    
    # Does this adjudication warrant creating a new dataset version with corrected reference answer?
    reference_answer_correction_proposed: Mapped[bool] = mapped_column(Boolean, default=False)
    proposed_correction_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_applied_to_dataset: Mapped[bool] = mapped_column(Boolean, default=False)
