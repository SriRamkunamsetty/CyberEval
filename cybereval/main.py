"""
CyberEval - Application Entry Point
Enterprise Cybersecurity AI Evaluation Platform
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from cybereval.core.config import settings
from cybereval.core.database import init_db, AsyncSessionLocal
from cybereval.core.security import SecurityHeadersMiddleware
from cybereval.core.exceptions import CyberEvalException
from cybereval.services.seed_data import seed_benchmark_data
from cybereval.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown lifespan."""
    # 1. Initialize DB tables
    await init_db()
    
    # 2. Seed initial benchmark data (scenarios, models, gate policies)
    async with AsyncSessionLocal() as session:
        await seed_benchmark_data(session)
        
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CyberEval: Enterprise Benchmark & Quality Assurance Platform for Cybersecurity AI",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# 1. Mandatory Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 3. Global Exception Handler
@app.exception_handler(CyberEvalException)
async def cybereval_exception_handler(request: Request, exc: CyberEvalException):
    return JSONResponse(
        status_code=400,
        content={"error": exc.message, "details": exc.details},
    )

# 4. Mount API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 5. Mount Frontend SPA Static Assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cybereval.main:app", host=settings.HOST, port=settings.PORT, reload=True)
