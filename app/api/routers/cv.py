from fastapi import APIRouter, File, UploadFile, HTTPException
from app.api.models import (
    CVProfileRequest, CVProfileResponse,
    CVJobRequest, CVJobResponse,
    CVExtractedResponse, CVBuildOldRequest,
    OptimizeATSRequest, OptimizeATSResponse,
    UserInteractRequest, UserInteractResponse,
    AIKeywordsRequest, AIKeywordsResponse,
    CVSchema
)
from app.services import cv_service

router = APIRouter(prefix="/API/CV", tags=["CV Generation and Optimization"])

@router.post("/Build/old_cv", response_model=CVProfileResponse)
async def build_old_cv(payload: CVBuildOldRequest):
    """Converts old CV text into structured schema"""
    try:
        cv = await cv_service.build_cv_from_text(payload.raw_text)
        return CVProfileResponse(cv_schema=cv)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/Build/Profile_cv", response_model=CVProfileResponse)
async def build_profile_cv(payload: CVProfileRequest):
    """Generates a CV schema based on user data"""
    try:
        cv = await cv_service.build_cv_from_text(payload.user_data)
        return CVProfileResponse(cv_schema=cv)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/Build/Job_cv", response_model=CVJobResponse)
async def build_job_cv(payload: CVJobRequest):
    """Optimizes a CV schema for a target job"""
    try:
        cv = await cv_service.optimize_cv_for_job(payload.base_cv, payload.target_job)
        return CVJobResponse(optimized_cv=cv)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimiz/ATS", response_model=OptimizeATSResponse)
async def optimize_ats(payload: OptimizeATSRequest):
    """Analyzes CV for ATS compatibility (Placeholder for logic)"""
    import json
    import random
    
    # Convert CVSchema into text format for AI/processing
    cv_text = json.dumps(payload.cv.model_dump(by_alias=True), indent=2)
    
    # Placeholder logic (could pass cv_text to an AI model)
    score = random.randint(60, 95)
    return OptimizeATSResponse(
        feedback=f"ATS Score logic to be implemented. Received CV with length: {len(cv_text)} chars.",
        ats_score=score
    )

@router.post("/optimiz/user_interaction", response_model=UserInteractResponse)
async def user_interact(payload: UserInteractRequest):
    """Modifies CV based on user requests"""
    try:
        result = await cv_service.interact_with_cv(payload.cv, payload.user_query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/AI_Recommended_Keywords", response_model=AIKeywordsResponse)
async def recommend_keywords(payload: AIKeywordsRequest):
    """Suggests ATS keywords based on CV content"""
    try:
        keywords = await cv_service.get_recommended_keywords(payload.cv_so_far)
        return AIKeywordsResponse(recommended_keywords=keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
