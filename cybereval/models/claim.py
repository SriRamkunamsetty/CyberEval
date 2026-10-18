"""
CyberEval - Claim & Evidence Link Models (Innovation 1: Claim-to-Evidence Graph)
Represents granular claims decomposed from model answers and their graph edges to verified scenario evidence.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cybereval.core.database import Base, TimestampMixin


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    model_response_id: Mapped[str] = mapped_column(ForeignKey("model_responses.id"), index=True)
    claim_index: Mapped[int] = mapped_column(Integer, default=0)
    statement: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(50), default="inference")
    # types: observation, inference, hypothesis, recommendation, attck_mapping, attribution

    # Support status evaluated by automated engine or verified by human
    status: Mapped[str] = mapped_column(String(30), default="UNSUPPORTED", index=True)
    # statuses: SUPPORTED, UNSUPPORTED, CONTRADICTED, AMBIGUOUS

    is_hallucination_trap_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    forbidden_conclusion_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    confidence_expressed: Mapped[str] = mapped_column(String(30), default="high")
    # high, moderate, cautious, abstained

    evidence_gap_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human reviewer overrides
    reviewer_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    reviewer_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    model_response: Mapped["ModelResponse"] = relationship("ModelResponse", back_populates="claims")
    evidence_links: Mapped[List["ClaimEvidenceLink"]] = relationship(
        "ClaimEvidenceLink", back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimEvidenceLink(Base, TimestampMixin):
    __tablename__ = "claim_evidence_links"

    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evidence_code: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "EV-01"
    link_type: Mapped[str] = mapped_column(String(30), default="supports")  # supports, contradicts, mentions
    entailment_score: Mapped[float] = mapped_column(Float, default=1.0)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_human_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    claim: Mapped["Claim"] = relationship("Claim", back_populates="evidence_links")
