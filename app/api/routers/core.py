from typing import List
from fastapi import APIRouter, HTTPException
from app.api.models import (
    MatchRequest, MatchResponse,
    ProposalRequest, ProposalResponse,
    MatchedProjectResponse, MatchedJobResponse
)
from app.services import cv_service
from app.core.logger import get_logger

logger = get_logger("api.core")

router = APIRouter(prefix="/API", tags=["Core AI"])

@router.post("/match", response_model=MatchResponse)
async def match_cv_job(payload: MatchRequest):
    """Calculates compatibility between CV text and Job description
    using real cosine similarity on SentenceTransformer embeddings."""
    try:
        from app.services.embedding_service import generate_embedding, compute_cosine_similarity

        logger.info("[Match] Computing real cosine similarity ...")
        cv_emb = generate_embedding(payload.cv_content)
        job_emb = generate_embedding(payload.job_desc)
        score = compute_cosine_similarity(cv_emb, job_emb)
        match_score = max(0, min(100, int(score * 100)))
        logger.info(f"[Match] Score = {match_score}%")
        return MatchResponse(match_score=match_score)
    except Exception as e:
        logger.error(f"[Match] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposel", response_model=ProposalResponse)
async def generate_proposal(payload: ProposalRequest):
    """Generates a professional project proposal"""
    try:
        proposal = await cv_service.generate_project_proposal(payload.user_profile, payload.project_details)
        return ProposalResponse(proposal_text=proposal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matches/projects/{user_id}", response_model=List[MatchedProjectResponse])
async def get_user_matched_projects(user_id: int):
    """Returns the matched freelance projects for a user based on DB records."""
    from app.services.db_services import get_matched_projects_for_user
    try:
        projects = get_matched_projects_for_user(user_id)
        if not projects:
            raise HTTPException(status_code=404, detail="Please fill out your profile")
        return projects
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Matches] Projects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/matches/jobs/{user_id}", response_model=List[MatchedJobResponse])
async def get_user_matched_jobs(user_id: int):
    """Returns the matched jobs for a user based on DB records."""
    from app.services.db_services import get_matched_jobs_for_user
    try:
        jobs = get_matched_jobs_for_user(user_id)
        if not jobs:
            raise HTTPException(status_code=404, detail="Please choose or create a base CV")
        return jobs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Matches] Jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
#  Manual Tools
# ═══════════════════════════════════════════════════════════════

@router.post("/tools/embed", tags=["Tools"])
async def trigger_embedding():
    """Manually generate embeddings for all items missing them.
    
    This does NOT run matching — only embedding generation.
    Useful after manually adding data to the database.
    """
    import asyncio
    try:
        logger.info("[Tools] Manual embedding triggered.")
        from app.services.embedding_service import run_embedding_pipeline
        result = await asyncio.to_thread(run_embedding_pipeline)
        summary = {
            "status": "completed",
            "new_embeddings": {
                "jobs": len(result["new_jobs"]),
                "projects": len(result["new_projects"]),
                "cvs": len(result["new_cvs"]),
                "profiles": len(result["new_profiles"]),
            }
        }
        logger.info(f"[Tools] Embedding result: {summary}")
        return summary
    except Exception as e:
        logger.error(f"[Tools] Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/match", tags=["Tools"])
async def trigger_matching():
    """Manually run the full embedding + matching pipeline.
    
    This first generates embeddings for all items missing them,
    then computes match scores and saves results to the database.
    """
    import asyncio
    try:
        logger.info("[Tools] Manual matching pipeline triggered.")
        from app.services.matching_service import run_matching_pipeline
        result = await asyncio.to_thread(run_matching_pipeline)
        logger.info(f"[Tools] Matching result: {result}")
        return {"status": "completed", **result}
    except Exception as e:
        logger.error(f"[Tools] Matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/scrape", tags=["Tools"])
async def trigger_scraping():
    """Manually trigger one scraping cycle (all platforms)."""
    import asyncio
    try:
        logger.info("[Tools] Manual scraping triggered.")
        from app.services.scheduler import run_scrapers
        new_items = await run_scrapers()
        logger.info(f"[Tools] Scraping done — {new_items} new items.")
        return {"status": "completed", "new_items": new_items}
    except Exception as e:
        logger.error(f"[Tools] Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
