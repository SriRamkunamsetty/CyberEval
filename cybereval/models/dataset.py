"""
CyberEval - Dataset & Scenario ORM Models
Defines benchmarks, scenarios, atomic evidence items, and structured reference answers.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cybereval.core.database import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(100), default="CyberEval Team")
    license: Mapped[str] = mapped_column(String(50), default="Apache-2.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    versions: Mapped[List["DatasetVersion"]] = relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetVersion(Base, TimestampMixin):
    __tablename__ = "dataset_versions"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    version_tag: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "1.0.0"
    checksum: Mapped[str] = mapped_column(String(64))  # SHA256 of all scenarios in version
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="versions")
    scenarios: Mapped[List["Scenario"]] = relationship(
        "Scenario", back_populates="dataset_version", cascade="all, delete-orphan"
    )


class Scenario(Base, TimestampMixin):
    __tablename__ = "scenarios"

    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    scenario_code: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "CE-AC-001"
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), index=True)
    # categories: attack_chain, evidence_attribution, threat_modeling, vulnerability_analysis,
    # incident_reconstruction, attck_mapping, defensive_recommendations, uncertainty_handling
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")  # easy, medium, hard, expert
    narrative: Mapped[str] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    split: Mapped[str] = mapped_column(String(20), default="test")  # train, val, test, held_out

    # Counterfactual pairing (Innovation 2)
    counterfactual_pair_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    is_counterfactual_variant: Mapped[bool] = mapped_column(Boolean, default=False)
    counterfactual_delta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dataset_version: Mapped["DatasetVersion"] = relationship("DatasetVersion", back_populates="scenarios")
    evidence_items: Mapped[List["EvidenceItem"]] = relationship(
        "EvidenceItem", back_populates="scenario", cascade="all, delete-orphan"
    )
    reference_answer: Mapped[Optional["ReferenceAnswer"]] = relationship(
        "ReferenceAnswer", back_populates="scenario", uselist=False, cascade="all, delete-orphan"
    )


class EvidenceItem(Base, TimestampMixin):
    __tablename__ = "evidence_items"

    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    evidence_code: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "EV-01"
    evidence_type: Mapped[str] = mapped_column(String(50))  # sysmon, cloudtrail, zeek, auth, edr, file
    timestamp_observed: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[str] = mapped_column(String(200), default="synthetic-telemetry")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=True)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="evidence_items")


class ReferenceAnswer(Base, TimestampMixin):
    __tablename__ = "reference_answers"

    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), unique=True, index=True)
    
    # Module B Structured Components
    required_claims: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # [{"claim_id": "RC-1", "statement": "...", "criticality": "high", "required_evidence": ["EV-01"]}]

    acceptable_alternatives: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # [{"alternative_to": "RC-1", "statement": "..."}]

    forbidden_conclusions: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # Hallucination traps:
    # [{"claim_id": "FC-1", "statement": "Attacker exfiltrated DB", "reason": "No outbound network log exists"}]

    critical_attack_path: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # Graph edges: [{"source": "Initial Access", "target": "Privilege Escalation", "technique": "T1078"}]

    valid_attck_mappings: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # [{"technique_id": "T1059.001", "tactic": "Execution", "justification": "PowerShell encoded script run"}]

    essential_remediation: Mapped[List[dict]] = mapped_column(JSON, default=list)
    # [{"control": "Revoke AWS IAM Key", "type": "Containment", "criticality": "immediate"}]

    uncertainty_requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"requires_qualification": True, "insufficient_evidence_for": ["Attribution", "Data Exfiltration"]}

    reviewer_rationale: Mapped[str] = mapped_column(Text)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="reference_answer")
