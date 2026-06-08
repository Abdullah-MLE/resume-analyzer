import os
from google import genai
from app.libs.GeminiWrapper.GeminiWrapper import GeminiWrapper
from app.libs.GeminiWrapper.models import InputParams, TextParams
from app.core.prompts import (
    get_cv_system_prompt,
    get_cv_build_prompt,
    get_cv_job_optimize_prompt,
    get_cv_interaction_prompt,
    get_proposal_prompt,
    get_keywords_prompt
)
from app.api.models import CVSchema, ProposalResponse
import json
from dotenv import load_dotenv
from app.core.logger import get_logger

load_dotenv()

logger = get_logger("gemini")

def init_gemini_client():
    """Initialize Gemini client prioritizing Service Account credentials."""
    # Ensure relative paths in .env are resolved correctly
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not os.path.isabs(creds_path):
        # Resolve relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_creds_path = os.path.join(base_dir, creds_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds_path
        creds_path = abs_creds_path

    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    api_key = os.environ.get("GOOGLE_API_KEY")
    
    logger.info(f"[Gemini] Initializing client — credentials: {creds_path}")
    if creds_path and not os.path.exists(creds_path):
        logger.warning(f"[Gemini] Credentials file NOT FOUND at {creds_path}")
    
    if creds_path or project_id:
        logger.info(f"[Gemini] Using Vertex AI — project={project_id}, location={location}")
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
    elif api_key:
        logger.info("[Gemini] Using API Key authentication.")
        return genai.Client(api_key=api_key)
    else:
        logger.info("[Gemini] Using default credentials.")
        return genai.Client()

_gemini_wrapper = None

def get_gemini_wrapper():
    global _gemini_wrapper
    if _gemini_wrapper is None:
        logger.info("[Gemini] Creating GeminiWrapper instance ...")
        _gemini_wrapper = GeminiWrapper(init_gemini_client())
        logger.info("[Gemini] GeminiWrapper ready.")
    return _gemini_wrapper

async def build_cv_from_text(raw_text: str) -> CVSchema:
    logger.info(f"[Gemini] build_cv_from_text — input length: {len(raw_text)} chars")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_build_prompt(raw_text)
    
    result = get_gemini_wrapper().generate_text(
        input_params=InputParams(
            prompt=user_prompt,
            system_instruction=system_prompt
        ),
        text_params=TextParams(
            response_schema=CVSchema,
            response_mime_type="application/json"
        )
    )
    
    if result["success"]:
        logger.info("[Gemini] build_cv_from_text — SUCCESS")
        return result["content"]
    
    logger.error(f"[Gemini] build_cv_from_text FAILED: {result.get('error')}")
    logger.debug(f"[Gemini] Error log: {result.get('error_log')}")
    raise Exception(f"AI Generation Failed: {result['error']}")

async def optimize_cv_for_job(base_cv: CVSchema, target_job: str) -> CVSchema:
    logger.info(f"[Gemini] optimize_cv_for_job — job desc length: {len(target_job)} chars")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_job_optimize_prompt(json.dumps(base_cv.model_dump(by_alias=True)), target_job)
    
    result = get_gemini_wrapper().generate_text(
        input_params=InputParams(
            prompt=user_prompt,
            system_instruction=system_prompt
        ),
        text_params=TextParams(
            response_schema=CVSchema,
            response_mime_type="application/json"
        )
    )
    
    if result["success"]:
        logger.info("[Gemini] optimize_cv_for_job — SUCCESS")
        return result["content"]
    
    logger.error(f"[Gemini] optimize_cv_for_job FAILED: {result.get('error')}")
    logger.debug(f"[Gemini] Error log: {result.get('error_log')}")
    raise Exception(f"AI Generation Failed: {result['error']}")

async def interact_with_cv(cv: CVSchema, query: str) -> CVSchema:
    logger.info(f"[Gemini] interact_with_cv — query: {query[:100]}")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_cv_interaction_prompt(json.dumps(cv.model_dump(by_alias=True)), query)
    
    result = get_gemini_wrapper().generate_text(
        input_params=InputParams(
            prompt=user_prompt,
            system_instruction=system_prompt
        ),
        text_params=TextParams(
            response_schema=CVSchema,
            response_mime_type="application/json"
        )
    )
    
    if result["success"]:
        logger.info("[Gemini] interact_with_cv — SUCCESS")
        return result["content"]
    
    logger.error(f"[Gemini] interact_with_cv FAILED: {result.get('error')}")
    logger.debug(f"[Gemini] Error log: {result.get('error_log')}")
    raise Exception(f"AI Generation Failed: {result['error']}")

async def generate_project_proposal(profile: str, project: str) -> str:
    logger.info(f"[Gemini] generate_project_proposal — profile: {len(profile)} chars, project: {len(project)} chars")
    user_prompt = get_proposal_prompt(profile, project)
    
    result = get_gemini_wrapper().generate_text(
        input_params=InputParams(
            prompt=user_prompt
        )
    )
    
    if result["success"]:
        logger.info("[Gemini] generate_project_proposal — SUCCESS")
        return result["content"]
    
    logger.error(f"[Gemini] generate_project_proposal FAILED: {result.get('error')}")
    logger.debug(f"[Gemini] Error log: {result.get('error_log')}")
    raise Exception(f"AI Generation Failed: {result['error']}")

async def get_recommended_keywords(cv_so_far: CVSchema) -> list[str]:
    logger.info("[Gemini] get_recommended_keywords — generating ...")
    system_prompt = get_cv_system_prompt()
    user_prompt = get_keywords_prompt(json.dumps(cv_so_far.model_dump(by_alias=True)))
    
    from app.api.models import AIKeywordsResponse
    
    result = get_gemini_wrapper().generate_text(
        input_params=InputParams(
            prompt=user_prompt,
            system_instruction=system_prompt
        ),
        text_params=TextParams(
            response_schema=AIKeywordsResponse,
            response_mime_type="application/json"
        )
    )
    
    if result["success"]:
        # The wrapper returns an instance of AIKeywordsResponse
        ai_data: AIKeywordsResponse = result["content"]
        logger.info(f"[Gemini] get_recommended_keywords — SUCCESS — {len(ai_data.recommended_keywords)} keywords")
        return ai_data.recommended_keywords
    
    logger.error(f"[Gemini] get_recommended_keywords FAILED: {result.get('error')}")
    logger.debug(f"[Gemini] Error log: {result.get('error_log')}")
    raise Exception(f"AI Generation Failed: {result['error']}")
