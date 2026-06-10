import os
import json
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.prompts import (
    get_cv_system_prompt,
    get_cv_build_prompt,
    get_cv_job_optimize_prompt,
    get_cv_interaction_prompt,
    get_proposal_prompt,
    get_keywords_prompt
)
from app.api.models import CVSchema, ProposalResponse, AIKeywordsResponse
from app.core.logger import get_logger

load_dotenv()

logger = get_logger("langchain-gemini")

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        logger.info("[LangChain] Initializing ChatGoogleGenerativeAI ...")
        # Ensure relative paths in .env are resolved correctly
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and not os.path.isabs(creds_path):
            # Resolve relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            abs_creds_path = os.path.join(base_dir, creds_path)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds_path

        # Determine model
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        project_id = os.environ.get("GCP_PROJECT_ID")
        location = os.environ.get("GCP_LOCATION")
        
        _llm = ChatVertexAI(
            model_name=model_name,
            temperature=0,
            max_retries=3,
            project=project_id,
            location=location
        )
    return _llm

async def build_cv_from_text(raw_text: str) -> CVSchema:
    logger.info(f"[LangChain] build_cv_from_text — input length: {len(raw_text)} chars")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_build_prompt(raw_text)
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(CVSchema)
    
    try:
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        logger.info("[LangChain] build_cv_from_text — SUCCESS")
        return result
    except Exception as e:
        logger.error(f"[LangChain] build_cv_from_text FAILED: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")

async def optimize_cv_for_job(base_cv: CVSchema, target_job: str) -> CVSchema:
    logger.info(f"[LangChain] optimize_cv_for_job — job desc length: {len(target_job)} chars")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_job_optimize_prompt(json.dumps(base_cv.model_dump(by_alias=True)), target_job)
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(CVSchema)
    
    try:
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        logger.info("[LangChain] optimize_cv_for_job — SUCCESS")
        return result
    except Exception as e:
        logger.error(f"[LangChain] optimize_cv_for_job FAILED: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")

async def interact_with_cv(cv: CVSchema, query: str) -> CVSchema:
    logger.info(f"[LangChain] interact_with_cv — query: {query[:100]}")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_interaction_prompt(json.dumps(cv.model_dump(by_alias=True)), query)
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(CVSchema)
    
    try:
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        logger.info("[LangChain] interact_with_cv — SUCCESS")
        return result
    except Exception as e:
        logger.error(f"[LangChain] interact_with_cv FAILED: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")

async def generate_project_proposal(profile: str, project: str) -> str:
    logger.info(f"[LangChain] generate_project_proposal — profile: {len(profile)} chars, project: {len(project)} chars")
    user_prompt = get_proposal_prompt(profile, project)
    
    llm = get_llm()
    
    try:
        result = await llm.ainvoke([
            HumanMessage(content=user_prompt)
        ])
        logger.info("[LangChain] generate_project_proposal — SUCCESS")
        return result.content
    except Exception as e:
        logger.error(f"[LangChain] generate_project_proposal FAILED: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")

async def get_recommended_keywords(cv_so_far: CVSchema) -> list[str]:
    logger.info("[LangChain] get_recommended_keywords — generating ...")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_keywords_prompt(json.dumps(cv_so_far.model_dump(by_alias=True)))
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(AIKeywordsResponse)
    
    try:
        result: AIKeywordsResponse = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        logger.info(f"[LangChain] get_recommended_keywords — SUCCESS — {len(result.recommended_keywords)} keywords")
        return result.recommended_keywords
    except Exception as e:
        logger.error(f"[LangChain] get_recommended_keywords FAILED: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")
