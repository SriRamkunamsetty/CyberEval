"""
CyberEval - Evaluation Execution & Run Management API Endpoints
"""

import hashlib
import json
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.dataset import DatasetVersion, Scenario, EvidenceItem, ReferenceAnswer
from cybereval.models.evaluation import EvaluationConfig, EvaluationRun, ModelResponse, Score
from cybereval.models.claim import Claim, ClaimEvidenceLink
from cybereval.schemas.evaluation import (
    EvaluationRunCreate,
    EvaluationRunRead,
    EvaluationRunDetailRead,
    EvaluationConfigRead,
    EvaluationConfigCreate,
)
from cybereval.services.model_adapter import ModelAdapterService
from cybereval.services.scoring_engine import ScoringEngine
from cybereval.services.statistical import StatisticalEngine

router = APIRouter(prefix="/evaluations", tags=["Evaluation Runs"])


@router.post("", response_model=EvaluationRunRead, status_code=status.HTTP_201_CREATED)
async def start_evaluation_run(
    payload: EvaluationRunCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes an end-to-end evaluation run against benchmark scenarios.
    Performs model generation, deterministic scoring, claim extraction, and statistical bootstrap.
    """
    # 1. Fetch Dataset Version
    v_stmt = (
        select(DatasetVersion)
        .options(
            selectinload(DatasetVersion.scenarios).selectinload(Scenario.evidence_items),
            selectinload(DatasetVersion.scenarios).selectinload(Scenario.reference_answer),
        )
        .where(DatasetVersion.id == payload.dataset_version_id)
    )
    v_res = await db.execute(v_stmt)
    version = v_res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    scenarios = version.scenarios
    if payload.scenario_subset_codes:
        scenarios = [s for s in scenarios if s.scenario_code in payload.scenario_subset_codes]

    if not scenarios:
        raise HTTPException(status_code=400, detail="No matching scenarios found to evaluate")

    # 2. Resolve Config
    config: EvaluationConfig | None = None
    if payload.config_id:
        c_res = await db.execute(select(EvaluationConfig).where(EvaluationConfig.id == payload.config_id))
        config = c_res.scalar_one_or_none()

    if not config:
        # Fetch default or create from override
        c_res = await db.execute(select(EvaluationConfig).order_by(EvaluationConfig.created_at.desc()))
        config = c_res.scalars().first()
        if not config:
            config = EvaluationConfig(
                name="Default Rubric",
                system_prompt="Analyze the incident telemetry accurately and ground all claims.",
            )
            db.add(config)
            await db.flush()

    # 3. Create Evaluation Run Record
    reproducibility_payload = f"{version.id}:{payload.model_name}:{config.id}:{time.time()}"
    repro_hash = hashlib.sha256(reproducibility_payload.encode()).hexdigest()

    run = EvaluationRun(
        dataset_version_id=version.id,
        config_id=config.id,
        model_name=payload.model_name,
        run_label=payload.run_label,
        status="running",
        reproducibility_hash=repro_hash,
    )
    db.add(run)
    await db.flush()

    start_exec_time = time.time()
    total_tokens = 0
    all_scores: List[float] = []
    dim_accumulators = {
        "factual_correctness": [],
        "evidence_grounding": [],
        "attack_chain_validity": [],
        "completeness": [],
        "remediation_quality": [],
        "format_compliance": [],
        "uncertainty_calibration": [],
    }
    all_gates_passed = True
    total_claims_count = 0
    unsupported_claims_count = 0
    critical_omissions_count = 0

    # 4. Iterate and Evaluate Each Scenario
    for scenario in scenarios:
        # Prepare context payload for prompt and baseline models
        ev_items_dict = [
            {
                "evidence_code": e.evidence_code,
                "evidence_type": e.evidence_type,
                "timestamp_observed": e.timestamp_observed,
                "raw_payload": e.raw_payload,
                "is_critical": e.is_critical,
            }
            for e in scenario.evidence_items
        ]
        ref_dict = {
            "required_claims": scenario.reference_answer.required_claims if scenario.reference_answer else [],
            "acceptable_alternatives": scenario.reference_answer.acceptable_alternatives if scenario.reference_answer else [],
            "forbidden_conclusions": scenario.reference_answer.forbidden_conclusions if scenario.reference_answer else [],
            "critical_attack_path": scenario.reference_answer.critical_attack_path if scenario.reference_answer else [],
            "valid_attck_mappings": scenario.reference_answer.valid_attck_mappings if scenario.reference_answer else [],
            "essential_remediation": scenario.reference_answer.essential_remediation if scenario.reference_answer else [],
            "uncertainty_requirements": scenario.reference_answer.uncertainty_requirements if scenario.reference_answer else {},
        }
        scenario_context = {
            "scenario_code": scenario.scenario_code,
            "title": scenario.title,
            "category": scenario.category,
            "narrative": scenario.narrative,
            "evidence_items": ev_items_dict,
            "reference_answer": ref_dict,
        }

        # Build user prompt
        user_prompt = (
            f"### SCENARIO: {scenario.scenario_code} - {scenario.title}\n"
            f"Category: {scenario.category}\n\n"
            f"### INCIDENT NARRATIVE:\n{scenario.narrative}\n\n"
            f"### FORENSIC EVIDENCE LOGS:\n{json.dumps(ev_items_dict, indent=2)}\n\n"
            f"Please output a valid JSON security assessment with fields: 'assessment_summary', 'claims', "
            f"'attack_chain', 'mitre_attck_mappings', 'remediation_recommendations', and 'uncertainties_and_gaps'."
        )

        # Generate Model Output
        raw_completion, parsed_json, latency_ms, p_tok, c_tok = await ModelAdapterService.generate(
            model_name=payload.model_name,
            system_prompt=config.system_prompt,
            user_prompt=user_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            scenario_context=scenario_context,
        )
        total_tokens += (p_tok + c_tok)

        # Create ModelResponse entity
        m_response = ModelResponse(
            evaluation_run_id=run.id,
            scenario_id=scenario.id,
            iteration_index=0,
            rendered_prompt=user_prompt,
            raw_completion=raw_completion,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            is_error=False,
        )
        db.add(m_response)
        await db.flush()

        # Score Response
        dim_scores, gates_passed, gate_reasons, details, annotated_claims = ScoringEngine.score_response(
            parsed_response=parsed_json,
            raw_completion=raw_completion,
            scenario=scenario_context,
            weights_override=config.weights,
            gate_thresholds_override=config.gate_thresholds,
        )

        if not gates_passed:
            all_gates_passed = False

        all_scores.append(dim_scores["weighted_score"])
        for k in dim_accumulators:
            dim_accumulators[k].append(dim_scores[k])

        claim_meta = details.get("claim_metrics", {})
        total_claims_count += claim_meta.get("total_claims", 0)
        unsupported_claims_count += claim_meta.get("unsupported_claims", 0) + claim_meta.get("contradicted_claims", 0)
        critical_omissions_count += details.get("critical_omissions", 0)

        # Create Score Entity
        score_entity = Score(
            model_response_id=m_response.id,
            factual_correctness=dim_scores["factual_correctness"],
            evidence_grounding=dim_scores["evidence_grounding"],
            attack_chain_validity=dim_scores["attack_chain_validity"],
            completeness=dim_scores["completeness"],
            remediation_quality=dim_scores["remediation_quality"],
            format_compliance=dim_scores["format_compliance"],
            uncertainty_calibration=dim_scores["uncertainty_calibration"],
            weighted_score=dim_scores["weighted_score"],
            critical_gates_passed=gates_passed,
            gate_failure_reasons=gate_reasons,
            details=details,
        )
        db.add(score_entity)

        # Store Claims and Evidence Links
        for c_data in annotated_claims:
            claim_entity = Claim(
                model_response_id=m_response.id,
                claim_index=c_data["claim_index"],
                statement=c_data["statement"],
                claim_type=c_data["claim_type"],
                status=c_data["status"],
                is_hallucination_trap_hit=c_data["is_hallucination_trap_hit"],
                forbidden_conclusion_id=c_data["forbidden_conclusion_id"],
                confidence_expressed=c_data["confidence_expressed"],
                evidence_gap_description=c_data["evidence_gap_description"],
                recommended_correction=c_data["recommended_correction"],
            )
            db.add(claim_entity)
            await db.flush()

            for ev_link in c_data.get("evidence_links", []):
                link_entity = ClaimEvidenceLink(
                    claim_id=claim_entity.id,
                    evidence_code=ev_link["evidence_code"],
                    link_type=ev_link.get("link_type", "supports"),
                    entailment_score=ev_link.get("entailment_score", 1.0),
                    explanation=ev_link.get("explanation"),
                )
                db.add(link_entity)

    # 5. Compute Statistical Bootstrap Confidence Intervals
    ci_lower, ci_upper, std_err, _ = StatisticalEngine.compute_bootstrap_ci(all_scores)

    # 6. Aggregate Run Metrics
    total_exec_time = time.time() - start_exec_time
    avg_weighted = sum(all_scores) / max(1, len(all_scores))
    unsup_rate = unsupported_claims_count / max(1, total_claims_count)
    crit_omiss_rate = critical_omissions_count / max(1, len(scenarios))

    run.status = "completed"
    run.overall_score = round(avg_weighted, 3)
    run.factual_correctness = round(sum(dim_accumulators["factual_correctness"]) / max(1, len(scenarios)), 3)
    run.evidence_grounding = round(sum(dim_accumulators["evidence_grounding"]) / max(1, len(scenarios)), 3)
    run.attack_chain_validity = round(sum(dim_accumulators["attack_chain_validity"]) / max(1, len(scenarios)), 3)
    run.completeness = round(sum(dim_accumulators["completeness"]) / max(1, len(scenarios)), 3)
    run.remediation_quality = round(sum(dim_accumulators["remediation_quality"]) / max(1, len(scenarios)), 3)
    run.format_compliance = round(sum(dim_accumulators["format_compliance"]) / max(1, len(scenarios)), 3)
    run.uncertainty_calibration = round(sum(dim_accumulators["uncertainty_calibration"]) / max(1, len(scenarios)), 3)
    run.unsupported_claim_rate = round(unsup_rate, 3)
    run.critical_omission_rate = round(crit_omiss_rate, 3)
    run.critical_gates_passed = all_gates_passed
    run.ci_lower = ci_lower
    run.ci_upper = ci_upper
    run.std_error = std_err
    run.execution_time_seconds = round(total_exec_time, 2)
    run.total_tokens_consumed = total_tokens

    await db.commit()
    await db.refresh(run)
    return run


@router.get("", response_model=List[EvaluationRunRead])
async def list_evaluation_runs(db: AsyncSession = Depends(get_db)):
    """List completed and pending evaluation runs."""
    stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve summary metrics and configuration for an evaluation run."""
    stmt = select(EvaluationRun).where(EvaluationRun.id == run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run


@router.get("/{run_id}/results", response_model=EvaluationRunDetailRead)
async def get_evaluation_run_results(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve scenario-by-scenario completions and dimension scores for a run."""
    stmt = (
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.responses).selectinload(ModelResponse.scores))
        .where(EvaluationRun.id == run_id)
    )
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run
