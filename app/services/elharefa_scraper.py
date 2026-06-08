from typing import List, Dict
from app.services.scraper_utils import fetch_html
from app.core.logger import get_logger
import requests

_logger = get_logger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_jobs_api(page_index: int, size: int = 25) -> List[Dict]:
    """Fetch jobs from El Harefa JSON API."""
    url = f"https://api.elharefa.com/jobs?Index={page_index}&Size={size}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("items", [])
    except Exception as e:
        _logger.warning(f"  Elharefa: API error page {page_index}: {type(e).__name__}")
        return []

def map_item(item: Dict) -> Dict[str, str]:
    """Map raw API item to our standard Project schema."""
    title = item.get("title") or ""
    details = item.get("details") or ""
    status = str(item.get("status", "Open"))
    publish_date = item.get("created") or ""

    budget_from = item.get("budgetFrom", "")
    budget_to = item.get("budgetTo", "")
    budget = f"{budget_from} - {budget_to}" if (budget_from or budget_to) else ""

    duration = str(item.get("duration", ""))

    skills_list = [s.get("name") for s in item.get("jobSkills", []) if s.get("name")]
    skills = ", ".join(skills_list)

    permalink = item.get("permaLink") or ""
    url = f"https://www.elharefa.com/ar/job/{permalink}" if permalink else ""

    return {
        "id": str(item.get("id", url)),
        "title": title,
        "description": details,
        "status": status,
        "publish_date": publish_date,
        "budget": budget,
        "duration": duration,
        "skills": skills,
        "url": url
    }

from app.services.db_services import save_freelance_project, get_existing_urls

def fetch_elharefa_projects(pages: int = 1, per_page_limit: int = 25) -> List[Dict[str, str]]:
    """Fetches jobs from El Harefa and returns them as a list of Project dicts."""
    projects: List[Dict[str, str]] = []
    
    for p in range(pages):
        items = fetch_jobs_api(page_index=p, size=per_page_limit)
        if not items:
            break
            
        mapped_items = [map_item(item) for item in items]
        all_urls = [m["url"] for m in mapped_items if m["url"]]
        
        existing_urls = get_existing_urls(all_urls, "opportunities_freelanceproject")
        
        for item in mapped_items:
            if item["url"] not in existing_urls:
                item["source_platform"] = "Elharefa"
                projects.append(item)
                save_freelance_project(item)
                
    return projects
