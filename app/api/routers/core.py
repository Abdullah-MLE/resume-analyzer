from fastapi import APIRouter, HTTPException
from app.api.models import (
    MatchRequest, MatchResponse,
    ProposalRequest, ProposalResponse
)
from app.services import cv_service

router = APIRouter(prefix="/API", tags=["Core AI"])

@router.post("/match", response_model=MatchResponse)
async def match_cv_job(payload: MatchRequest):
    """Calculates compatibility between CV and Job"""
    # Logic to be implemented later
    return MatchResponse(match_score=0)

@router.post("/proposel", response_model=ProposalResponse)
async def generate_proposal(payload: ProposalRequest):
    """Generates a professional project proposal"""
    try:
        proposal = await cv_service.generate_project_proposal(payload.user_profile, payload.project_details)
        return ProposalResponse(proposal_text=proposal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
