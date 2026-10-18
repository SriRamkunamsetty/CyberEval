"""
CyberEval - Model Providers API Router
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cybereval.core.database import get_db
from cybereval.models.evaluation import ModelProvider
from cybereval.schemas.evaluation import ModelProviderRead

router = APIRouter(prefix="/models", tags=["Model Providers"])


@router.get("/providers", response_model=List[ModelProviderRead])
async def list_model_providers(db: AsyncSession = Depends(get_db)):
    """List all registered LLM providers and baseline models."""
    stmt = select(ModelProvider).where(ModelProvider.is_active == True).order_by(ModelProvider.name.asc())
    res = await db.execute(stmt)
    return res.scalars().all()
