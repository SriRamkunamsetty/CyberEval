"""
CyberEval - Benchmark Audit & Leakage Detection API Router (Innovation 6)
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.dataset import DatasetVersion, Scenario
from cybereval.services.leakage_engine import LeakageDetectorEngine

router = APIRouter(prefix="/audit", tags=["Benchmark Integrity & Leakage"])


@router.get("/leakage/{dataset_version_id}")
async def audit_dataset_leakage(dataset_version_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Audits scenarios in a dataset version for near-duplicates and cross-split test contamination.
    """
    v_stmt = (
        select(DatasetVersion)
        .options(
            selectinload(DatasetVersion.scenarios).selectinload(Scenario.evidence_items),
        )
        .where(DatasetVersion.id == dataset_version_id)
    )
    v_res = await db.execute(v_stmt)
    version = v_res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    scen_dicts = [
        {
            "scenario_code": s.scenario_code,
            "title": s.title,
            "category": s.category,
            "narrative": s.narrative,
            "split": s.split,
            "counterfactual_pair_id": s.counterfactual_pair_id,
            "evidence_items": [{"raw_payload": e.raw_payload} for e in s.evidence_items],
        }
        for s in version.scenarios
    ]

    report = LeakageDetectorEngine.audit_splits(scenarios=scen_dicts)
    return report
