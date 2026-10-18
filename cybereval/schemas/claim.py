"""
CyberEval - Claim & Evidence Graph Schemas (Innovation 1: Claim-to-Evidence Graph)
Structures for claim extraction, evidence link analysis, and graph visualization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ClaimEvidenceLinkRead(BaseModel):
    id: str
    claim_id: str
    evidence_code: str
    link_type: str  # supports, contradicts, mentions
    entailment_score: float
    explanation: Optional[str] = None
    is_human_verified: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClaimBase(BaseModel):
    claim_index: int
    statement: str
    claim_type: str = "inference"
    status: str = "UNSUPPORTED"
    is_hallucination_trap_hit: bool = False
    forbidden_conclusion_id: Optional[str] = None
    confidence_expressed: str = "high"
    evidence_gap_description: Optional[str] = None
    recommended_correction: Optional[str] = None
    reviewer_status: Optional[str] = None
    reviewer_rationale: Optional[str] = None


class ClaimCreate(ClaimBase):
    evidence_links: List[Dict[str, Any]] = Field(default_factory=list)


class ClaimRead(ClaimBase):
    id: str
    model_response_id: str
    created_at: datetime
    evidence_links: List[ClaimEvidenceLinkRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# Graph Visualization structures for frontend
class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # "claim" or "evidence" or "hallucination_trap"
    status: Optional[str] = None  # "SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "CRITICAL_EVIDENCE"
    category: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str  # "SUPPORTS", "CONTRADICTS", "REQUIRES", "UNSUPPORTED_LEAP"
    weight: float = 1.0


class ClaimGraphResponse(BaseModel):
    scenario_code: str
    model_response_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    grounding_ratio: float
    unsupported_claims_count: int
    hallucination_traps_hit: int
    evidence_utilization_ratio: float
