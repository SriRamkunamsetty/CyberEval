"""
CyberEval - Dataset & Scenario Pydantic Schemas
Strict data contracts for input validation and output serialization.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class EvidenceItemBase(BaseModel):
    evidence_code: str = Field(..., example="EV-01")
    evidence_type: str = Field(..., example="sysmon")
    timestamp_observed: Optional[str] = None
    raw_payload: Dict[str, Any]
    provenance: str = "synthetic-telemetry"
    is_critical: bool = True


class EvidenceItemCreate(EvidenceItemBase):
    pass


class EvidenceItemRead(EvidenceItemBase):
    id: str
    scenario_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReferenceAnswerBase(BaseModel):
    required_claims: List[Dict[str, Any]] = Field(default_factory=list)
    acceptable_alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    forbidden_conclusions: List[Dict[str, Any]] = Field(default_factory=list)
    critical_attack_path: List[Dict[str, Any]] = Field(default_factory=list)
    valid_attck_mappings: List[Dict[str, Any]] = Field(default_factory=list)
    essential_remediation: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty_requirements: Dict[str, Any] = Field(default_factory=dict)
    reviewer_rationale: str


class ReferenceAnswerCreate(ReferenceAnswerBase):
    pass


class ReferenceAnswerRead(ReferenceAnswerBase):
    id: str
    scenario_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScenarioBase(BaseModel):
    scenario_code: str = Field(..., example="CE-AC-001")
    title: str = Field(..., example="Living-off-the-Land Lateral Movement via WMI")
    category: str = Field(..., example="attack_chain")
    difficulty: str = Field("medium", example="medium")
    narrative: str
    tags: List[str] = Field(default_factory=list)
    split: str = "test"
    counterfactual_pair_id: Optional[str] = None
    is_counterfactual_variant: bool = False
    counterfactual_delta_description: Optional[str] = None


class ScenarioCreate(ScenarioBase):
    evidence_items: List[EvidenceItemCreate] = Field(default_factory=list)
    reference_answer: ReferenceAnswerCreate


class ScenarioRead(ScenarioBase):
    id: str
    dataset_version_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScenarioDetailRead(ScenarioRead):
    evidence_items: List[EvidenceItemRead] = Field(default_factory=list)
    reference_answer: Optional[ReferenceAnswerRead] = None
    model_config = ConfigDict(from_attributes=True)


class DatasetVersionBase(BaseModel):
    version_tag: str = Field(..., example="1.0.0")
    changelog: Optional[str] = None
    is_frozen: bool = True


class DatasetVersionCreate(DatasetVersionBase):
    scenarios: List[ScenarioCreate] = Field(default_factory=list)


class DatasetVersionRead(DatasetVersionBase):
    id: str
    dataset_id: str
    checksum: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DatasetBase(BaseModel):
    name: str = Field(..., example="cybereval-core-v1")
    description: str
    author: str = "CyberEval Team"
    license: str = "Apache-2.0"


class DatasetCreate(DatasetBase):
    initial_version: Optional[DatasetVersionCreate] = None


class DatasetRead(DatasetBase):
    id: str
    is_active: bool
    created_at: datetime
    versions: List[DatasetVersionRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
