from fastapi import APIRouter
from typing import List
from app.api.models import Project, Job

from app.services.mostaql_scraper import fetch_mostaql_projects
from app.services.freelanceyard_scraper import fetch_freelanceyard_projects
from app.services.elharefa_scraper import fetch_elharefa_projects
from app.services.wuzzuf_scraper import fetch_wuzzuf_jobs
from app.services.bayt_scraper import fetch_bayt_jobs
from app.services.forasna_scraper import fetch_forasna_jobs

router = APIRouter(prefix="/API/Scraping", tags=["Scraping"])

@router.get("/projects/Mostqil", response_model=List[Project])
def scrape_mostqil():
    """Fetches the latest projects from Mostqil"""
    data = fetch_mostaql_projects(pages=1, per_page_limit=25)
    return data

@router.get("/projects/Freelance", response_model=List[Project])
def scrape_freelance():
    """Fetches the latest projects from FreelanceYard"""
    data = fetch_freelanceyard_projects(pages=1, per_page_limit=25)
    return data

@router.get("/projects/Elharefa", response_model=List[Project])
def scrape_elharefa():
    """Fetches the latest projects from El Harefa"""
    data = fetch_elharefa_projects(pages=1, per_page_limit=25)
    return data


@router.get("/Jobs/Wazuf", response_model=List[Job])
def scrape_wuzzuf():
    """Fetches the latest jobs from Wuzzuf"""
    data = fetch_wuzzuf_jobs(pages=1)
    return data

@router.get("/Jobs/Bayt", response_model=List[Job])
def scrape_bayt():
    """Fetches the latest jobs from Bayt using a headless browser"""
    data = fetch_bayt_jobs(pages=1)
    return data

@router.get("/Jobs/Forasna", response_model=List[Job])
def scrape_forasna():
    """Fetches the latest jobs from Forasna"""
    data = fetch_forasna_jobs(pages=1)
    return data
