"""FastAPI entrypoint for the PatchLens Binary Diffing and Security Analysis API."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import SessionLocal, init_db
from api.routers import analysis, results, samples, system
from api.seed import seed_sample_analyses

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("patchlens.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: initialize SQLite database and pre-seed sample CVE analyses."""
    logger.info("Starting PatchLens API v%s...", settings.version)
    init_db()
    db = SessionLocal()
    try:
        seed_sample_analyses(db)
    except Exception as exc:
        logger.warning("Database sample seeding warning: %s", exc)
    finally:
        db.close()
    yield
    logger.info("Shutting down PatchLens API...")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description=(
        "Automated ELF binary diffing, CFG structural comparison, "
        "and security patch localization platform."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(system.router)
app.include_router(system.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)
app.include_router(results.router, prefix=settings.api_prefix)
app.include_router(samples.router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "service": settings.project_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
