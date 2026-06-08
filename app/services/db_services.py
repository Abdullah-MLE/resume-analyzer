from typing import Dict, List, Optional
from datetime import datetime
from app.core.database import get_supabase
from app.core.logger import get_logger

logger = get_logger("db")

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


# ═══════════════════════════════════════════════════════════════
#  Embedding & Matching Helpers
# ═══════════════════════════════════════════════════════════════

def fetch_all(
    table_name: str,
    select_columns: str,
    is_null_col: str = None,
    not_null_col: str = None,
    eq_filters: Dict = None,
    page_size: int = 1000,
) -> List[Dict]:
    """Paginated fetch from any Supabase table.

    Filters:
        is_null_col  – column IS NULL
        not_null_col – column IS NOT NULL
        eq_filters   – {column: value, …} equality filters
    """
    supabase = get_supabase()
    if not supabase:
        return []

    all_data: List[Dict] = []
    offset = 0

    while True:
        try:
            query = supabase.table(table_name).select(select_columns)
            if is_null_col:
                query = query.is_(is_null_col, "null")
            if not_null_col:
                query = query.not_.is_(not_null_col, "null")
            if eq_filters:
                for col, val in eq_filters.items():
                    query = query.eq(col, val)
            response = query.range(offset, offset + page_size - 1).execute()
        except Exception as e:
            logger.error(f"[db_services] fetch_all({table_name}) error at offset {offset}: {e}")
            break

        if not response.data:
            break

        all_data.extend(response.data)
        if len(response.data) < page_size:
            break
        offset += page_size

    return all_data


def fetch_by_ids(
    table_name: str,
    select_columns: str,
    ids: List[int],
    not_null_col: str = None,
    chunk_size: int = 100,
) -> List[Dict]:
    """Fetch rows by a list of IDs (chunked to avoid PostgREST limits)."""
    supabase = get_supabase()
    if not supabase or not ids:
        return []

    all_data: List[Dict] = []
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        try:
            query = supabase.table(table_name).select(select_columns).in_("id", chunk)
            if not_null_col:
                query = query.not_.is_(not_null_col, "null")
            resp = query.execute()
            if resp.data:
                all_data.extend(resp.data)
        except Exception as e:
            logger.error(f"[db_services] fetch_by_ids({table_name}) error: {e}")
    return all_data


def update_embedding(table_name: str, row_id: int, embedding_list: List[float]) -> bool:
    """Write an embedding vector into the ``embedding`` column for one row."""
    supabase = get_supabase()
    if not supabase:
        return False
    try:
        supabase.table(table_name).update(
            {"embedding": embedding_list}
        ).eq("id", row_id).execute()
        return True
    except Exception as e:
        logger.error(f"[db_services] update_embedding({table_name}, id={row_id}): {e}")
        return False


def get_all_skill_names() -> Dict[int, str]:
    """Return {skill_id: skill_name} for every skill in accounts_skill."""
    supabase = get_supabase()
    if not supabase:
        return {}
    try:
        data = fetch_all("accounts_skill", "id, name")
        return {row["id"]: row["name"] for row in data}
    except Exception as e:
        logger.error(f"[db_services] get_all_skill_names error: {e}")
        return {}


def get_skills_map(junction_table: str, fk_column: str) -> Dict[int, List[str]]:
    """Build {item_id: [skill_name, …]} from a junction table.

    Example::

        get_skills_map("opportunities_job_required_skills", "job_id")
        → {12: ["Python", "SQL"], 17: ["React"], …}
    """
    supabase = get_supabase()
    if not supabase:
        return {}
    try:
        skill_names = get_all_skill_names()
        data = fetch_all(junction_table, f"{fk_column}, skill_id")
        result: Dict[int, List[str]] = {}
        for row in data:
            item_id = row[fk_column]
            name = skill_names.get(row["skill_id"], "")
            if name:
                result.setdefault(item_id, []).append(name)
        return result
    except Exception as e:
        logger.error(f"[db_services] get_skills_map({junction_table}) error: {e}")
        return {}

