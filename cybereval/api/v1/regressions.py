"""
CyberEval - Regression & Release Gating API Endpoints (Module G & Innovation 4)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.evaluation import EvaluationRun, ModelResponse, Score
from cybereval.models.dataset import Scenario
from cybereval.models.regression import ReleaseGatePolicy, RegressionResult
from cybereval.schemas.regression import (
    RegressionComparisonRequest,
    RegressionComparisonResponse,
    ReleaseGatePolicyRead,
    ReleaseGatePolicyCreate,
)
from cybereval.services.regression_engine import RegressionEngine

router = APIRouter(prefix="/regressions", tags=["Regression Testing & Release Gates"])


@router.post("/compare", response_model=RegressionComparisonResponse)
async def compare_runs(payload: RegressionComparisonRequest, db: AsyncSession = Depends(get_db)):
    """
    Compares candidate model run against baseline run.
    Identifies regressed scenarios, metric deltas, new ungrounded claims, and enforces release gates.
    """
    # 1. Fetch Candidate Run
    c_stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.responses).selectinload(ModelResponse.scores),
        )
        .where(EvaluationRun.id == payload.candidate_run_id)
    )
    c_res = await db.execute(c_stmt)
    cand_run = c_res.scalar_one_or_none()
    if not cand_run:
        raise HTTPException(status_code=404, detail="Candidate evaluation run not found")

    # 2. Fetch Baseline Run
    b_stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.responses).selectinload(ModelResponse.scores),
        )
        .where(EvaluationRun.id == payload.baseline_run_id)
    )
    b_res = await db.execute(b_stmt)
    base_run = b_res.scalar_one_or_none()
    if not base_run:
        raise HTTPException(status_code=404, detail="Baseline evaluation run not found")

    # 3. Resolve Policy
    policy_dict = None
    if payload.policy_name:
        p_res = await db.execute(select(ReleaseGatePolicy).where(ReleaseGatePolicy.name == payload.policy_name))
        pol_obj = p_res.scalar_one_or_none()
        if pol_obj:
            policy_dict = {
                "max_tolerated_score_drop": pol_obj.max_tolerated_score_drop,
                "max_unsupported_claim_rate": pol_obj.max_unsupported_claim_rate,
                "max_regressed_scenarios": pol_obj.max_regressed_scenarios,
                "require_zero_hallucination_traps": pol_obj.require_zero_hallucination_traps,
            }

    # Fetch scenarios for title mapping
    scenario_ids = list(set([r.scenario_id for r in cand_run.responses]))
    scen_res = await db.execute(select(Scenario).where(Scenario.id.in_(scenario_ids)))
    scen_map = {s.id: s for s in scen_res.scalars().all()}

    cand_resp_dicts = []
    for r in cand_run.responses:
        sc = scen_map.get(r.scenario_id)
        sc_data = {
            "weighted_score": r.scores.weighted_score if r.scores else 0.0,
            "critical_gates_passed": r.scores.critical_gates_passed if r.scores else True,
            "gate_failure_reasons": r.scores.gate_failure_reasons if r.scores else [],
            "details": r.scores.details if r.scores else {},
        }
        cand_resp_dicts.append({
            "scenario_id": r.scenario_id,
            "scenario_code": sc.scenario_code if sc else "CE-SCENARIO",
            "scenario_title": sc.title if sc else "Scenario",
            "category": sc.category if sc else "attack_chain",
            "scores": sc_data,
        })

    base_resp_dicts = []
    for r in base_run.responses:
        sc = scen_map.get(r.scenario_id)
        sc_data = {
            "weighted_score": r.scores.weighted_score if r.scores else 0.0,
            "critical_gates_passed": r.scores.critical_gates_passed if r.scores else True,
            "gate_failure_reasons": r.scores.gate_failure_reasons if r.scores else [],
            "details": r.scores.details if r.scores else {},
        }
        base_resp_dicts.append({
            "scenario_id": r.scenario_id,
            "scores": sc_data,
        })

    cand_run_dict = {
        "id": cand_run.id,
        "model_name": cand_run.model_name,
        "overall_score": cand_run.overall_score,
        "factual_correctness": cand_run.factual_correctness,
        "evidence_grounding": cand_run.evidence_grounding,
        "attack_chain_validity": cand_run.attack_chain_validity,
        "unsupported_claim_rate": cand_run.unsupported_claim_rate,
        "critical_gates_passed": cand_run.critical_gates_passed,
    }
    base_run_dict = {
        "id": base_run.id,
        "model_name": base_run.model_name,
        "overall_score": base_run.overall_score,
        "factual_correctness": base_run.factual_correctness,
        "evidence_grounding": base_run.evidence_grounding,
        "attack_chain_validity": base_run.attack_chain_validity,
        "unsupported_claim_rate": base_run.unsupported_claim_rate,
        "critical_gates_passed": base_run.critical_gates_passed,
    }

    comparison = RegressionEngine.compare_runs(
        candidate_run=cand_run_dict,
        baseline_run=base_run_dict,
        candidate_responses=cand_resp_dicts,
        baseline_responses=base_resp_dicts,
        policy=policy_dict,
    )

    # Persist regression result
    reg_result = RegressionResult(
        candidate_run_id=cand_run.id,
        baseline_run_id=base_run.id,
        overall_score_delta=comparison.overall_score_delta,
        factual_correctness_delta=comparison.factual_correctness_delta,
        evidence_grounding_delta=comparison.evidence_grounding_delta,
        attack_chain_validity_delta=comparison.attack_chain_validity_delta,
        unsupported_claim_rate_delta=comparison.unsupported_claim_rate_delta,
        scenarios_regressed_count=comparison.scenarios_regressed_count,
        scenarios_improved_count=comparison.scenarios_improved_count,
        new_unsupported_claims_count=comparison.new_unsupported_claims_count,
        is_gate_passed=comparison.is_gate_passed,
        gate_verdict=comparison.gate_verdict,
        blocked_reasons=comparison.blocked_reasons,
        scenario_diffs=[d.model_dump() for d in comparison.scenario_diffs],
    )
    db.add(reg_result)
    await db.commit()

    return comparison


@router.get("/policies", response_model=List[ReleaseGatePolicyRead])
async def list_release_policies(db: AsyncSession = Depends(get_db)):
    """List registered release gate policies."""
    stmt = select(ReleaseGatePolicy).order_by(ReleaseGatePolicy.name.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/policies", response_model=ReleaseGatePolicyRead, status_code=status.HTTP_201_CREATED)
async def create_release_policy(payload: ReleaseGatePolicyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new release gate policy."""
    policy = ReleaseGatePolicy(
        name=payload.name,
        description=payload.description,
        max_tolerated_score_drop=payload.max_tolerated_score_drop,
        max_unsupported_claim_rate=payload.max_unsupported_claim_rate,
        max_regressed_scenarios=payload.max_regressed_scenarios,
        require_zero_hallucination_traps=payload.require_zero_hallucination_traps,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy
