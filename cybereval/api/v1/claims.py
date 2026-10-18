"""
CyberEval - Claim & Evidence Graph API Endpoints (Innovation 1: Claim-to-Evidence Graph)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.evaluation import ModelResponse
from cybereval.models.dataset import Scenario
from cybereval.models.claim import Claim, ClaimEvidenceLink
from cybereval.schemas.claim import ClaimRead, ClaimGraphResponse
from cybereval.services.claim_graph import ClaimEvidenceGraphEngine

router = APIRouter(prefix="/claims", tags=["Claims & Evidence Graph"])


@router.get("/response/{model_response_id}", response_model=List[ClaimRead])
async def list_response_claims(model_response_id: str, db: AsyncSession = Depends(get_db)):
    """List extracted claims and their evidence links for a model response."""
    stmt = (
        select(Claim)
        .options(selectinload(Claim.evidence_links))
        .where(Claim.model_response_id == model_response_id)
        .order_by(Claim.claim_index.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/graph/{model_response_id}", response_model=ClaimGraphResponse)
async def get_claim_evidence_graph(model_response_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves interactive Claim-to-Evidence graph representation for a model response.
    Returns nodes (claims, evidence logs, hallucination traps) and directed bipartite edges.
    """
    stmt = (
        select(ModelResponse)
        .options(
            selectinload(ModelResponse.claims).selectinload(Claim.evidence_links),
            selectinload(ModelResponse.scores),
        )
        .where(ModelResponse.id == model_response_id)
    )
    res = await db.execute(stmt)
    m_resp = res.scalar_one_or_none()
    if not m_resp:
        raise HTTPException(status_code=404, detail="Model response not found")

    # Fetch scenario, evidence, and reference answer
    scen_stmt = (
        select(Scenario)
        .options(
            selectinload(Scenario.evidence_items),
            selectinload(Scenario.reference_answer),
        )
        .where(Scenario.id == m_resp.scenario_id)
    )
    scen_res = await db.execute(scen_stmt)
    scenario = scen_res.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Build claim dicts
    annotated_claims = []
    for c in m_resp.claims:
        annotated_claims.append({
            "claim_index": c.claim_index,
            "statement": c.statement,
            "claim_type": c.claim_type,
            "status": c.status,
            "is_hallucination_trap_hit": c.is_hallucination_trap_hit,
            "forbidden_conclusion_id": c.forbidden_conclusion_id,
            "confidence_expressed": c.confidence_expressed,
            "evidence_gap_description": c.evidence_gap_description,
            "recommended_correction": c.recommended_correction,
            "evidence_links": [
                {
                    "evidence_code": l.evidence_code,
                    "link_type": l.link_type,
                    "entailment_score": l.entailment_score,
                }
                for l in c.evidence_links
            ],
        })

    ev_items_dict = [
        {
            "evidence_code": e.evidence_code,
            "evidence_type": e.evidence_type,
            "raw_payload": e.raw_payload,
            "is_critical": e.is_critical,
        }
        for e in scenario.evidence_items
    ]

    ref_dict = {
        "forbidden_conclusions": scenario.reference_answer.forbidden_conclusions if scenario.reference_answer else [],
    }

    graph = ClaimEvidenceGraphEngine.build_claim_evidence_graph(
        scenario_code=scenario.scenario_code,
        model_response_id=m_resp.id,
        annotated_claims=annotated_claims,
        evidence_items=ev_items_dict,
        reference_answer=ref_dict,
    )
    return graph
