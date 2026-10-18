"""
CyberEval - Review & Adjudication API Endpoints (Module H & Innovation 3)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.review import ReviewTask, ReviewDecision, Adjudication
from cybereval.models.evaluation import ModelResponse
from cybereval.models.dataset import Scenario
from cybereval.schemas.review import (
    ReviewTaskRead,
    ReviewTaskCreate,
    ReviewDecisionRead,
    ReviewDecisionCreate,
    AdjudicationRead,
    AdjudicationCreate,
    InterRaterAgreementResponse,
)
from cybereval.services.agreement_engine import AgreementEngine

router = APIRouter(prefix="/reviews", tags=["Human Review & Adjudication"])


@router.get("/tasks", response_model=List[ReviewTaskRead])
async def list_review_tasks(db: AsyncSession = Depends(get_db)):
    """List pending and completed expert review tasks."""
    stmt = select(ReviewTask).options(selectinload(ReviewTask.decisions)).order_by(ReviewTask.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/tasks", response_model=ReviewTaskRead, status_code=status.HTTP_201_CREATED)
async def create_review_task(payload: ReviewTaskCreate, db: AsyncSession = Depends(get_db)):
    """Assign a model response to a security analyst for expert review."""
    task = ReviewTask(
        model_response_id=payload.model_response_id,
        assigned_reviewer_id=payload.assigned_reviewer_id,
        is_double_blind=payload.is_double_blind,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/decisions", response_model=ReviewDecisionRead, status_code=status.HTTP_201_CREATED)
async def submit_review_decision(payload: ReviewDecisionCreate, db: AsyncSession = Depends(get_db)):
    """Submit an expert review decision with claim-level validation and rubric ratings."""
    task_res = await db.execute(select(ReviewTask).where(ReviewTask.id == payload.task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")

    decision = ReviewDecision(
        task_id=payload.task_id,
        reviewer_id=payload.reviewer_id,
        claim_decisions=payload.claim_decisions,
        rubric_ratings=payload.rubric_ratings,
        overall_verdict=payload.overall_verdict,
        notes=payload.notes,
        dispute_raised=payload.dispute_raised,
    )
    db.add(decision)
    task.status = "completed" if not payload.dispute_raised else "disputed"
    await db.commit()
    await db.refresh(decision)
    return decision


@router.post("/adjudications", response_model=AdjudicationRead, status_code=status.HTTP_201_CREATED)
async def submit_adjudication(payload: AdjudicationCreate, db: AsyncSession = Depends(get_db)):
    """Submit final adjudication ruling to resolve reviewer disputes."""
    adjudication = Adjudication(
        model_response_id=payload.model_response_id,
        adjudicator_id=payload.adjudicator_id,
        dispute_reason=payload.dispute_reason,
        final_verdict=payload.final_verdict,
        final_score=payload.final_score,
        rationale=payload.rationale,
        reference_answer_correction_proposed=payload.reference_answer_correction_proposed,
        proposed_correction_payload=payload.proposed_correction_payload,
    )
    db.add(adjudication)
    await db.commit()
    await db.refresh(adjudication)
    return adjudication


@router.get("/agreement/{dataset_version_id}", response_model=InterRaterAgreementResponse)
async def get_inter_rater_agreement(dataset_version_id: str, db: AsyncSession = Depends(get_db)):
    """
    Computes Cohen's Kappa across all double-blind reviewed tasks for a dataset version.
    Identifies high-disagreement ambiguous scenarios and rubric weaknesses.
    """
    # Query tasks that have >= 2 decisions
    stmt = (
        select(ReviewTask)
        .options(selectinload(ReviewTask.decisions))
        .join(ModelResponse, ReviewTask.model_response_id == ModelResponse.id)
        .join(Scenario, ModelResponse.scenario_id == Scenario.id)
        .where(Scenario.dataset_version_id == dataset_version_id)
    )
    res = await db.execute(stmt)
    tasks = res.scalars().all()

    paired_decisions = []
    for t in tasks:
        if len(t.decisions) >= 2:
            dec_a = {
                "overall_verdict": t.decisions[0].overall_verdict,
                "notes": t.decisions[0].notes,
                "rubric_ratings": t.decisions[0].rubric_ratings,
            }
            dec_b = {
                "overall_verdict": t.decisions[1].overall_verdict,
                "notes": t.decisions[1].notes,
                "rubric_ratings": t.decisions[1].rubric_ratings,
            }
            scen_ctx = {"scenario_code": "CE-SCENARIO", "title": "Reviewed Scenario"}
            paired_decisions.append((dec_a, dec_b, scen_ctx))

    agreement = AgreementEngine.compute_inter_rater_agreement(
        dataset_version_id=dataset_version_id,
        paired_decisions=paired_decisions,
    )
    return agreement
