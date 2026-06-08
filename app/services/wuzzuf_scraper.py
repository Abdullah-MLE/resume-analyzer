from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from app.services.scraper_utils import fetch_html, orchestrate_scraping

BASE_URL = "https://wuzzuf.net"
DEFAULT_URL = "https://wuzzuf.net/a/IT-Software-Development-Jobs-in-Egypt?ref=browse-jobs"

def _extract_links_from_page(page_url: str, limit: int = 25) -> List[str]:
    """Extract job links from a Wuzzuf listing page."""
    html = fetch_html(page_url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/jobs/p/" in href:
            if href.startswith("/"): href = BASE_URL + href
            elif not href.startswith("http"): href = BASE_URL + "/" + href
            if href not in links: links.append(href)
            if len(links) >= limit: break
    return links[:limit]

def _extract_card_details(card) -> Optional[Dict[str, str]]:
    """Extract all fields from a single Wuzzuf job card."""
    title_tag = card.select_one("h2 a")
    if not title_tag: return None

    title = title_tag.get_text(" ", strip=True)
    href = title_tag.get("href", "")
    if href.startswith("/"): href = BASE_URL + href

    company_tag = card.find("a", href=lambda h: h and "/jobs/careers/" in h)
    company = company_tag.get_text(" ", strip=True).rstrip(" -").strip() if company_tag else ""

    location_span = card.find("span", class_="css-16x61xq")
    location = location_span.get_text(" ", strip=True) if location_span else ""

    publish_date = ""
    for el in card.find_all(["span", "div", "time"]):
        text = el.get_text(" ", strip=True)
        if "ago" in text and len(text) < 30:
            publish_date = text
            break

    job_type, work_type = "", ""
    for span in card.find_all("span"):
        cls = " ".join(span.get("class", []))
        text = span.get_text(" ", strip=True)
        if "css-uc9rga" in cls: job_type = text
        elif "css-uofntu" in cls: work_type = text

    experience = ""
    for el in card.find_all(["span", "div"]):
        text = el.get_text(" ", strip=True)
        if "Yrs of Exp" in text or "Entry Level" in text or "Student" in text:
            experience = text.lstrip("·").strip()
            break

    skills_links = card.find_all("a", href=lambda h: h and "/a/" in h)
    skills_list = []
    for a in skills_links:
        text = a.get_text(" ", strip=True).lstrip("·").strip()
        if text and text not in (job_type, work_type, experience, company) and len(text) < 60:
            skills_list.append(text)
    skills = ", ".join(skills_list)

    details_parts = []
    if company: details_parts.append(f"Company: {company}")
    if location: details_parts.append(f"Location: {location}")
    if experience: details_parts.append(f"Experience: {experience}")
    description = " | ".join(details_parts)

    return {
        "id": href,
        "title": title,
        "company": company,
        "description": description,
        "location": location,
        "job_type": job_type,
        "work_type": work_type,
        "publish_date": publish_date,
        "budget": "",
        "skills": skills,
        "url": href,
    }

def _scrape_listing_page(page_url: str, _limit: int = 25) -> List[Dict[str, str]]:
    """Scrape all job cards from a Wuzzuf listing page (no per-job requests needed)."""
    html = fetch_html(page_url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.css-ghe2tq")
    results = []
    for card in cards:
        data = _extract_card_details(card)
        if data: results.append(data)
    return results

from app.services.db_services import save_job, get_existing_urls
from app.core.logger import get_logger

_wuzzuf_logger = get_logger("scraper")

def fetch_wuzzuf_jobs(pages: int = 1, list_url: str = DEFAULT_URL) -> List[Dict[str, str]]:
    """
    Fetches Wuzzuf jobs from the listing pages directly via card extraction.
    Sequential to keep logs clean and avoid bans.
    """
    def build_url(page: int) -> str:
        if page == 0: return list_url
        sep = "&" if "?" in list_url else "?"
        return f"{list_url}{sep}page={page}"

    results = []
    for p in range(pages):
        url = build_url(p)
        try:
            page_results = _scrape_listing_page(url)
            if not page_results:
                continue

            # Check DB
            all_urls = [r["url"] for r in page_results if r.get("url")]
            existing_urls = get_existing_urls(all_urls, "opportunities_job")

            for item in page_results:
                if item["url"] not in existing_urls:
                    item["source_platform"] = "Wuzzuf"
                    results.append(item)
                    save_job(item)

        except Exception as exc:
            _wuzzuf_logger.warning(f"  Wuzzuf: page {p} error: {type(exc).__name__}")

    return results

