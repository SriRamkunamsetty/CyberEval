"""
CyberEval - Evaluation Run & Score Models
Manages model configurations, run execution logs, model responses, and dimension scores.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from cybereval.core.database import Base, TimestampMixin


class ModelProvider(Base, TimestampMixin):
    __tablename__ = "model_providers"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g. "openai-gpt4o", "baseline-expert"
    display_name: Mapped[str] = mapped_column(String(100))
    provider_type: Mapped[str] = mapped_column(String(50))  # built_in, openai, anthropic, gemini, ollama
    model_identifier: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EvaluationConfig(Base, TimestampMixin):
    __tablename__ = "evaluation_configs"

    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    system_prompt: Mapped[str] = mapped_column(Text)
    output_schema_version: Mapped[str] = mapped_column(String(20), default="v1")
    repeat_runs: Mapped[int] = mapped_column(Integer, default=1)
    
    # Scorer weights and gate thresholds
    weights: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "factual_correctness": 0.30,
            "evidence_grounding": 0.25,
            "attack_chain_validity": 0.20,
            "completeness": 0.10,
            "remediation_quality": 0.10,
            "format_compliance": 0.05,
        },
    )
    gate_thresholds: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "max_unsupported_claim_rate": 0.15,
            "max_critical_omission_rate": 0.10,
            "min_weighted_score": 0.70,
            "allow_forbidden_conclusions": False,
        },
    )


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    config_id: Mapped[str] = mapped_column(ForeignKey("evaluation_configs.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(100), index=True)
    run_label: Mapped[str] = mapped_column(String(100), default="default")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, running, completed, failed
    
    # Summary Metrics
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    factual_correctness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_grounding: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attack_chain_validity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    remediation_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    format_compliance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    uncertainty_calibration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    unsupported_claim_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_omission_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_gates_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Statistical reliability (Innovation 5)
    ci_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    std_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    reproducibility_hash: Mapped[str] = mapped_column(String(64))
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tokens_consumed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    responses: Mapped[List["ModelResponse"]] = relationship(
        "ModelResponse", back_populates="evaluation_run", cascade="all, delete-orphan"
    )


class ModelResponse(Base, TimestampMixin):
    __tablename__ = "model_responses"

    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    iteration_index: Mapped[int] = mapped_column(Integer, default=0)
    
    rendered_prompt: Mapped[str] = mapped_column(Text)
    raw_completion: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)

    evaluation_run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="responses")
    scores: Mapped[Optional["Score"]] = relationship(
        "Score", back_populates="model_response", uselist=False, cascade="all, delete-orphan"
    )
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="model_response", cascade="all, delete-orphan"
    )


class Score(Base, TimestampMixin):
    __tablename__ = "scores"

    model_response_id: Mapped[str] = mapped_column(ForeignKey("model_responses.id"), unique=True, index=True)
    
    # 6 Primary Evaluation Dimensions
    factual_correctness: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_grounding: Mapped[float] = mapped_column(Float, default=0.0)
    attack_chain_validity: Mapped[float] = mapped_column(Float, default=0.0)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    remediation_quality: Mapped[float] = mapped_column(Float, default=0.0)
    format_compliance: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty_calibration: Mapped[float] = mapped_column(Float, default=0.0)

    # Weighted aggregate
    weighted_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Critical gate status
    critical_gates_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    gate_failure_reasons: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Granular scoring diagnostics
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    model_response: Mapped["ModelResponse"] = relationship("ModelResponse", back_populates="scores")
