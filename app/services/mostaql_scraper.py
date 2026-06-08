from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from app.services.scraper_utils import fetch_html, orchestrate_scraping

def extract_project_links(page_url: str, limit: int = 25) -> List[str]:
    html = fetch_html(page_url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []

    for row in soup.select("tr.project-row"):
        a = row.select_one("h2 a")
        if not a: a = row.find("a", href=lambda href: href and "/project/" in href)
        if a and a.get("href"):
            href = a["href"].strip()
            if href.startswith("//"): href = "https:" + href
            elif href.startswith("/"): href = "https://mostaql.com" + href
            elif not href.startswith("http"): href = "https://mostaql.com/" + href
            links.append(href)
            if len(links) >= limit: break

    if not links:
        for a in soup.select("a[href*='/project/']"):
            href = a["href"].strip()
            if href.startswith("/"): href = "https://mostaql.com" + href
            elif href.startswith("//"): href = "https:" + href
            elif not href.startswith("http"): href = "https://mostaql.com/" + href
            if href not in links: links.append(href)
            if len(links) >= limit: break

    return links[:limit]

def extract_project_details(project_url: str) -> Optional[Dict[str, str]]:
    html = fetch_html(project_url)
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_tag = soup.select_one('span[data-type="page-header-title"]') or soup.select_one('h1.heada__title') or soup.find("h1")
    if title_tag: title = title_tag.get_text(" ", strip=True)

    details = ""
    details_container = soup.select_one("#projectDetailsTab .carda__content") or soup.select_one("#projectDetailsTab") or soup.select_one("div#projectDetailsTab")
    if details_container:
        details = details_container.get_text(" ", strip=True)
    else:
        possible = soup.select_one("div.panel#project-brief, div#project-brief, div.carda__content")
        if possible: details = possible.get_text(" ", strip=True)

    status, publish_date, budget, duration, skills = "", "", "", "", ""
    meta_rows = soup.select("div.meta-rows > div.meta-row") or soup.select("div.meta-row")

    try:
        if len(meta_rows) >= 1:
            val = meta_rows[0].select_one(".meta-value")
            if val: status = val.get_text(" ", strip=True)
        if len(meta_rows) >= 2:
            time_tag = meta_rows[1].select_one("time")
            if time_tag and time_tag.has_attr("datetime"):
                publish_date = time_tag["datetime"].strip()
            else:
                val = meta_rows[1].select_one(".meta-value")
                if val: publish_date = val.get_text(" ", strip=True)
        if len(meta_rows) >= 3:
            val = meta_rows[2].select_one(".meta-value")
            if val: budget = val.get_text(" ", strip=True)
        if len(meta_rows) >= 4:
            val = meta_rows[3].select_one(".meta-value")
            if val: duration = val.get_text(" ", strip=True)
    except Exception: pass

    skills_elems = soup.select("ul.skills li a bdi, ul.skills li a, ul.skills.list-tags li a bdi, ul.skills.list-tags li a")
    skills_list = [s.get_text(" ", strip=True) for s in skills_elems if s.get_text(" ", strip=True)]
    if skills_list:
        seen = set()
        skills = ", ".join([x for x in skills_list if not (x in seen or seen.add(x))])

    if not budget:
        budget_tag = soup.select_one('[data-type="project-budget_range"], div.meta-value[data-type="project-budget_range"]')
        if budget_tag: budget = budget_tag.get_text(" ", strip=True)
    if not duration:
        dur_candidate = soup.find(string=lambda t: t and ("يوم" in t or "أيام" in t))
        if dur_candidate: duration = dur_candidate.strip()

    return {
        "id": project_url,
        "title": title,
        "description": details,
        "status": status,
        "publish_date": publish_date,
        "budget": budget,
        "duration": duration,
        "skills": skills,
        "url": project_url
    }

from app.services.db_services import save_freelance_project

def fetch_mostaql_projects(pages: int = 1, per_page_limit: int = 25) -> List[Dict[str, str]]:
    list_page_url = "https://mostaql.com/projects"
    urls = [f"{list_page_url}?page={p}" if p > 1 else list_page_url for p in range(1, pages + 1)]
    return orchestrate_scraping(
        page_urls=urls, 
        extract_links_func=extract_project_links, 
        extract_details_func=extract_project_details, 
        per_page_limit=per_page_limit,
        table_name="opportunities_freelanceproject",
        save_func=save_freelance_project,
        source_platform="Mostaql"
    )
