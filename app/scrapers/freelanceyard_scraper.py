from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from app.scrapers.scraper_utils import fetch_html, orchestrate_scraping

def extract_project_links(page_url: str, limit: int = 25) -> List[str]:
    html = fetch_html(page_url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/jobs/" in href:
            parts = href.split("/jobs/")
            if len(parts) > 1 and len(parts[1]) > 5:
                if href.startswith("//"): href = "https:" + href
                elif href.startswith("/"): href = "https://freelanceyard.com" + href
                elif not href.startswith("http"): href = "https://freelanceyard.com/" + href
                
                if href not in links: links.append(href)
                if len(links) >= limit: break
    return links[:limit]

def extract_project_details(project_url: str) -> Optional[Dict[str, str]]:
    html = fetch_html(project_url)
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_element = soup.select_one('#job-header h3') or soup.find("h3", class_="font-bold text-indigo-700")
    if title_element: title = title_element.get_text(" ", strip=True)

    details = ""
    details_element = soup.select_one('#job-details .break-words.text-muted')
    if details_element: details = details_element.get_text(" ", strip=True)

    status = "Open"
    publish_date = ""
    for el in soup.find_all('div', class_='text-sm text-gray-400'):
        text = el.get_text(" ", strip=True)
        if 'Posted at:' in text:
            publish_date = text.replace('Posted at:', '').strip()

    def find_label_text(soup, label_text):
        for h5 in soup.find_all('h5'):
            if label_text.lower() in h5.get_text(" ", strip=True).lower():
                parent = h5.find_parent('span') or h5.find_parent('div')
                if parent: return parent.get_text(" ", strip=True).replace(h5.get_text(" ", strip=True), '').strip()
        return ""

    budget = find_label_text(soup, "Client budget")
    deadline = find_label_text(soup, "Deadline")

    skills = ""
    for h5 in soup.find_all('h5'):
        if "Required skills" in h5.get_text(" ", strip=True):
            skills_container = h5.find_next('div', class_='flex flex-wrap gap-2')
            if skills_container:
                skills_list = [span.get_text(" ", strip=True) for span in skills_container.find_all('span')]
                skills = ", ".join(skills_list)
            break

    return {
        "id": project_url,
        "title": title,
        "description": details,
        "status": status,
        "publish_date": publish_date,
        "budget": budget,
        "duration": deadline,
        "skills": skills,
        "url": project_url
    }

from app.services.db_services import save_freelance_project

def fetch_freelanceyard_projects(pages: int = 1, per_page_limit: int = 25) -> List[Dict[str, str]]:
    list_page_url = "https://freelanceyard.com/en/jobs"
    urls = [
        f"{list_page_url}&page={p}" if "?" in list_page_url else f"{list_page_url}?page={p}"
        if p > 1 else list_page_url 
        for p in range(1, pages + 1)
    ]
    return orchestrate_scraping(
        page_urls=urls, 
        extract_links_func=extract_project_links, 
        extract_details_func=extract_project_details, 
        per_page_limit=per_page_limit,
        table_name="opportunities_freelanceproject",
        save_func=save_freelance_project,
        source_platform="FreelanceYard"
    )
