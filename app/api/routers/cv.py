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
    """Converts old CV file into structured schema"""
    try:
        raw_text = cv_service.extract_text_from_base64_file(payload.file_base64, payload.file_name)
        if not raw_text:
            raise HTTPException(status_code=400, detail="Could not extract text from the provided file.")
            
        cv = await cv_service.build_cv_from_text(raw_text)
        return CVProfileResponse(cv_schema=cv)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/Build/Profile_cv", response_model=CVProfileResponse)
async def build_profile_cv(payload: CVProfileRequest):
    """Generates a CV schema based on a user profile ID"""
    try:
        from app.services.db_services import fetch_full_user_profile
        profile_data = fetch_full_user_profile(payload.user_id)
        if not profile_data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        # Format profile_data into a text prompt for the AI
        user_data_text = f"Full Name: {profile_data.get('full_name', '')}\n"
        user_data_text += f"Professional Title: {profile_data.get('professional_title', '')}\n"
        user_data_text += f"Bio: {profile_data.get('bio', '')}\n"
        user_data_text += f"Location: {profile_data.get('location', '')}\n"
        user_data_text += f"Phone: {profile_data.get('phone_number', '')}\n"
        user_data_text += f"Portfolio: {profile_data.get('portfolio_url', '')}\n"
        user_data_text += f"Specialization: {profile_data.get('specialization', '')}\n"
        
        user_data_text += "\nExperience:\n"
        for exp in profile_data.get('experience_list', []):
            user_data_text += f"- {exp.get('job_title')} at {exp.get('company')} ({exp.get('start_date')} to {exp.get('end_date') or 'Present'}): {exp.get('description', '')}\n"
            
        user_data_text += "\nEducation:\n"
        for edu in profile_data.get('education_list', []):
            user_data_text += f"- {edu.get('degree')} at {edu.get('school')} ({edu.get('graduation_year')}): {edu.get('description', '')}\n"
            
        user_data_text += "\nSkills: " + ", ".join(profile_data.get('skills_list', []))

        cv = await cv_service.build_cv_from_text(user_data_text)
        return CVProfileResponse(cv_schema=cv)
    except HTTPException:
        raise
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
        decision = await cv_service.interact_with_cv(payload.cv, payload.user_query)
        
        final_cv = decision.modified_cv if decision.is_modified and decision.modified_cv else payload.cv
        
        return UserInteractResponse(
            modified_cv=final_cv,
            ai_message=decision.ai_message
        )
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
