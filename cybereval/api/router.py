"""
CyberEval - Master API Router
Aggregates all API v1 domain routers.
"""

from fastapi import APIRouter
from cybereval.api.v1.datasets import router as datasets_router
from cybereval.api.v1.evaluations import router as evaluations_router
from cybereval.api.v1.claims import router as claims_router
from cybereval.api.v1.reviews import router as reviews_router
from cybereval.api.v1.regressions import router as regressions_router
from cybereval.api.v1.reports import router as reports_router
from cybereval.api.v1.models import router as models_router
from cybereval.api.v1.audit import router as audit_router

api_router = APIRouter()

api_router.include_router(datasets_router)
api_router.include_router(evaluations_router)
api_router.include_router(claims_router)
api_router.include_router(reviews_router)
api_router.include_router(regressions_router)
api_router.include_router(reports_router)
api_router.include_router(models_router)
api_router.include_router(audit_router)
