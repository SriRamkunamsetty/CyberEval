"""
CyberEval - Datasets & Scenarios API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.dataset import Dataset, DatasetVersion, Scenario, EvidenceItem, ReferenceAnswer
from cybereval.schemas.dataset import (
    DatasetRead,
    DatasetCreate,
    DatasetVersionRead,
    DatasetVersionCreate,
    ScenarioRead,
    ScenarioDetailRead,
    ScenarioCreate,
)

router = APIRouter(prefix="/datasets", tags=["Datasets & Scenarios"])


@router.get("", response_model=List[DatasetRead])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all registered benchmark datasets."""
    stmt = select(Dataset).options(selectinload(Dataset.versions)).order_by(Dataset.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new benchmark dataset."""
    existing = await db.execute(select(Dataset).where(Dataset.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Dataset with this name already exists")
    
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        author=payload.author,
        license=payload.license,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve dataset details and versions."""
    stmt = select(Dataset).options(selectinload(Dataset.versions)).where(Dataset.id == dataset_id)
    res = await db.execute(stmt)
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/versions/{version_id}/scenarios", response_model=List[ScenarioRead])
async def list_version_scenarios(
    dataset_id: str,
    version_id: str,
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    split: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List scenarios in a specific dataset version with optional category and split filters."""
    stmt = select(Scenario).where(Scenario.dataset_version_id == version_id)
    if category:
        stmt = stmt.where(Scenario.category == category)
    if difficulty:
        stmt = stmt.where(Scenario.difficulty == difficulty)
    if split:
        stmt = stmt.where(Scenario.split == split)
    stmt = stmt.order_by(Scenario.scenario_code.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailRead)
async def get_scenario_detail(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve complete scenario definition including evidence logs and reference answers."""
    stmt = (
        select(Scenario)
        .options(
            selectinload(Scenario.evidence_items),
            selectinload(Scenario.reference_answer),
        )
        .where(Scenario.id == scenario_id)
    )
    res = await db.execute(stmt)
    scenario = res.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario
