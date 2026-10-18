"""
CyberEval - Evaluation Run & Score Schemas
Contracts for launching benchmark runs, retrieving dimension scores, and inspecting model responses.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ModelProviderBase(BaseModel):
    name: str = Field(..., example="baseline-expert")
    display_name: str = Field(..., example="CyberEval Baseline Expert (Ground Truth)")
    provider_type: str = Field(..., example="built_in")  # built_in, openai, anthropic, gemini, ollama
    model_identifier: str = Field(..., example="baseline-ground-truth-v1")
    is_active: bool = True


class ModelProviderCreate(ModelProviderBase):
    pass


class ModelProviderRead(ModelProviderBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvaluationConfigBase(BaseModel):
    name: str = Field(..., example="Standard Security Reasoning Benchmark")
    description: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    system_prompt: str = Field(
        default=(
            "You are an expert cybersecurity forensic analyst. "
            "Analyze the provided incident narrative and structured evidence logs. "
            "Identify the attack stages, MITRE ATT&CK techniques, evidence attribution, "
            "defensive recommendations, and uncertainty qualifications. "
            "Do NOT speculate or assert facts not directly grounded in the logs."
        )
    )
    output_schema_version: str = "v1"
    repeat_runs: int = 1
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "factual_correctness": 0.30,
            "evidence_grounding": 0.25,
            "attack_chain_validity": 0.20,
            "completeness": 0.10,
            "remediation_quality": 0.10,
            "format_compliance": 0.05,
        }
    )
    gate_thresholds: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_unsupported_claim_rate": 0.15,
            "max_critical_omission_rate": 0.10,
            "min_weighted_score": 0.70,
            "allow_forbidden_conclusions": False,
        }
    )


class EvaluationConfigCreate(EvaluationConfigBase):
    pass


class EvaluationConfigRead(EvaluationConfigBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScoreRead(BaseModel):
    id: str
    model_response_id: str
    factual_correctness: float
    evidence_grounding: float
    attack_chain_validity: float
    completeness: float
    remediation_quality: float
    format_compliance: float
    uncertainty_calibration: float
    weighted_score: float
    critical_gates_passed: bool
    gate_failure_reasons: List[str]
    details: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ModelResponseRead(BaseModel):
    id: str
    evaluation_run_id: str
    scenario_id: str
    iteration_index: int
    rendered_prompt: str
    raw_completion: str
    parsed_json: Optional[Dict[str, Any]] = None
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    is_error: bool
    scores: Optional[ScoreRead] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvaluationRunCreate(BaseModel):
    dataset_version_id: str
    model_name: str
    config_id: Optional[str] = None
    run_label: str = "benchmark-run"
    scenario_subset_codes: Optional[List[str]] = None  # None evaluates all scenarios in version
    custom_config_override: Optional[EvaluationConfigCreate] = None


class EvaluationRunRead(BaseModel):
    id: str
    dataset_version_id: str
    config_id: str
    model_name: str
    run_label: str
    status: str
    overall_score: Optional[float] = None
    factual_correctness: Optional[float] = None
    evidence_grounding: Optional[float] = None
    attack_chain_validity: Optional[float] = None
    completeness: Optional[float] = None
    remediation_quality: Optional[float] = None
    format_compliance: Optional[float] = None
    uncertainty_calibration: Optional[float] = None
    unsupported_claim_rate: Optional[float] = None
    critical_omission_rate: Optional[float] = None
    critical_gates_passed: bool
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    std_error: Optional[float] = None
    reproducibility_hash: str
    execution_time_seconds: Optional[float] = None
    total_tokens_consumed: int
    error_message: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvaluationRunDetailRead(EvaluationRunRead):
    responses: List[ModelResponseRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
