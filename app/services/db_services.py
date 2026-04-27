from typing import Dict, List, Optional
from datetime import datetime
from app.core.database import get_supabase
from app.core.logger import get_logger

logger = get_logger()

def insert_skills_and_get_ids(skills_str: str) -> List[int]:
    """
    Takes a comma-separated string of skills, inserts missing ones into accounts_skill,
    and returns a list of skill IDs.
    """
    if not skills_str:
        return []
    
    supabase = get_supabase()
    if not supabase:
        return []

    # Split by comma and clean
    skill_names = [s.strip() for s in skills_str.split(",") if s.strip()]
    if not skill_names:
        return []

    skill_ids = []
    
    for name in skill_names:
        # Check if skill exists
        response = supabase.table("accounts_skill").select("id").ilike("name", name).execute()
        
        if response.data:
            skill_ids.append(response.data[0]['id'])
        else:
            # Insert new skill
            # Handle potential race conditions by ignoring duplicates if they occur
            try:
                insert_response = supabase.table("accounts_skill").insert({"name": name}).execute()
                if insert_response.data:
                    skill_ids.append(insert_response.data[0]['id'])
            except Exception as e:
                logger.error(f"[db_services] Error inserting skill {name}: {e}")
                
    return skill_ids

import urllib.parse

def save_freelance_project(project_data: Dict) -> bool:
    """
    Saves a freelance project and its skills to Supabase.
    """
    supabase = get_supabase()
    if not supabase:
        return False
        
    try:
        url = urllib.parse.unquote(project_data.get("url", ""))[:200] if project_data.get("url") else ""
        
        record = {
            "title": project_data.get("title", "")[:200],
            "description": project_data.get("description", ""),
            "budget": project_data.get("budget", "")[:200],
            "platform_name": project_data.get("source_platform", "Freelance Platform")[:200],
            "source_url": url,
            "posted_date": datetime.now().isoformat(),
            "scraped_at": datetime.now().isoformat(),
            "duration": project_data.get("duration", "")[:200],
            "status": project_data.get("status", "Open")[:200]
        }
        
        # Insert project
        response = supabase.table("opportunities_freelanceproject").insert(record).execute()
        if not response.data:
            return False
            
        project_id = response.data[0]['id']
        
        # Handle Skills
        skills_str = project_data.get("skills", "")
        skill_ids = insert_skills_and_get_ids(skills_str)
        
        # Link skills
        for skill_id in skill_ids:
            try:
                supabase.table("opportunities_freelanceproject_required_skills").insert({
                    "freelanceproject_id": project_id,
                    "skill_id": skill_id
                }).execute()
            except Exception as e:
                logger.error(f"[db_services] Error inserting into opportunities_freelanceproject_required_skills: {e}")
            
        return True
    except Exception as e:
        logger.error(f"[db_services] Error saving freelance project {project_data.get('url')}: {e}")
        return False

def save_job(job_data: Dict) -> bool:
    """
    Saves a job and its skills to Supabase.
    """
    supabase = get_supabase()
    if not supabase:
        return False
        
    try:
        url = urllib.parse.unquote(job_data.get("url", ""))[:200] if job_data.get("url") else ""
        
        # Prepare the job record
        record = {
            "title": job_data.get("title", "")[:200],
            "company": job_data.get("company", "")[:200],
            "description": job_data.get("description", ""),
            "location": job_data.get("location", "")[:200],
            "source_platform": job_data.get("source_platform", "Job Board")[:200],
            "source_url": url,
            "posted_date": datetime.now().date().isoformat(),  # Ensure posted_date is provided
            "scraped_at": datetime.now().isoformat()
        }
        
        # Insert job
        response = supabase.table("opportunities_job").insert(record).execute()
        if not response.data:
            return False
            
        job_id = response.data[0]['id']
        
        # Handle Skills
        skills_str = job_data.get("skills", "")
        skill_ids = insert_skills_and_get_ids(skills_str)
        
        # Link skills
        for skill_id in skill_ids:
            try:
                supabase.table("opportunities_job_required_skills").insert({
                    "job_id": job_id,
                    "skill_id": skill_id
                }).execute()
            except Exception as e:
                logger.error(f"[db_services] Error inserting into opportunities_job_required_skills: {e}")
            
        return True
    except Exception as e:
        logger.error(f"[db_services] Error saving job {job_data.get('url')}: {e}")
        return False

def get_existing_urls(urls: List[str], table_name: str) -> List[str]:
    """
    Checks Supabase for existing source_urls in a given table.
    Returns a list of URLs that are already in the database.
    """
    supabase = get_supabase()
    if not supabase or not urls:
        return []
        
    try:
        # Supabase API limits filtering to a certain number of items in an 'in' clause, 
        # but 25-50 (per page) should be totally fine.
        response = supabase.table(table_name).select("source_url").in_("source_url", urls).execute()
        return [item['source_url'] for item in response.data]
    except Exception as e:
        logger.error(f"[db_services] Error checking existing URLs in {table_name}: {e}")
        return []
