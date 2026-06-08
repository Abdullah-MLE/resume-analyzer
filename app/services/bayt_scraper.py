from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright
import os
import random

BASE_URL = "https://www.bayt.com"
DEFAULT_URL = "https://www.bayt.com/en/egypt/jobs/"

def _get_page_html(url: str, browser, proxy_config=None) -> Optional[str]:
    """Open a URL with the shared Playwright browser and return HTML after JS renders."""
    try:
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.evaluate("window.scrollBy(0, 2000)")
        page.wait_for_timeout(1500)
        html = page.content()
        context.close()
        return html
    except Exception as e:
        return None

def _extract_card_details(card) -> Optional[Dict[str, str]]:
    """Parse one <li data-js-job> card and map to standard Job schema."""
    title_tag = card.select_one('a[data-js-aid="jobID"]')
    if not title_tag:
        return None

    title = title_tag.get_text(" ", strip=True)
    href = title_tag.get("href", "")
    if href.startswith("/"): href = BASE_URL + href

    company_tag = card.select_one("a.t-default.t-bold")
    company = company_tag.get_text(" ", strip=True) if company_tag else ""

    location_div = card.select_one("div.t-mute.t-small")
    location = ""
    if location_div:
        parts = [sp.get_text(" ", strip=True) for sp in location_div.find_all("span") if sp.get_text(strip=True)]
        location = ", ".join(parts)

    descr_div = card.select_one("div.jb-descr")
    description = ""
    if descr_div:
        text = descr_div.get_text(" ", strip=True)
        if "Summary:" in text: text = text.split("Summary:", 1)[-1].strip()
        description = text

    experience = ""
    exp_dt = card.select_one("dt.jb-label-careerlevel")
    if exp_dt: experience = exp_dt.get_text(" ", strip=True).strip()

    date_span = card.select_one('span[data-automation-id="job-active-date"]')
    publish_date = date_span.get_text(" ", strip=True) if date_span else ""

    job_type_tags = [dt.get_text(" ", strip=True) for dt in card.select("div.jb-tags dt") if dt.get_text(strip=True)]
    job_type = ", ".join(job_type_tags)

    details_parts = []
    if company: details_parts.append(f"Company: {company}")
    if location: details_parts.append(f"Location: {location}")
    if description: details_parts.append(description)

    return {
        "id": href,
        "title": title,
        "company": company,
        "description": " | ".join(details_parts),
        "location": location,
        "job_type": job_type,
        "work_type": "",
        "publish_date": publish_date,
        "budget": "",
        "skills": experience,
        "url": href,
    }

def _scrape_listing_page(url: str, browser) -> List[Dict[str, str]]:
    html = _get_page_html(url, browser)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li[data-js-job]")
    results = []
    for card in cards:
        data = _extract_card_details(card)
        if data: results.append(data)
    return results

def _build_url(base: str, page: int) -> str:
    if page <= 1: return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}page={page}"

from app.services.db_services import save_job, get_existing_urls
from app.services.scraper_utils import get_random_proxy

def fetch_bayt_jobs(pages: int = 1, list_url: str = DEFAULT_URL) -> List[Dict[str, str]]:
    """
    Fetches Bayt jobs using a headless Chromium browser via Playwright.
    Pages are scraped sequentially to keep resource usage manageable.
    """
    all_jobs: List[Dict[str, str]] = []
    with sync_playwright() as p:
        proxy_info = get_random_proxy()
        proxy_config = None
        if proxy_info and "http" in proxy_info:
            proxy_config = {"server": proxy_info["http"]}
                
        browser = p.chromium.launch(headless=True, proxy=proxy_config)
        for page_num in range(1, pages + 1):
            url = _build_url(list_url, page_num)
            results = _scrape_listing_page(url, browser)
            
            # Check DB
            all_urls = [r["url"] for r in results if r.get("url")]
            existing_urls = get_existing_urls(all_urls, "opportunities_job")
            
            for item in results:
                if item["url"] not in existing_urls:
                    item["source_platform"] = "Bayt"
                    all_jobs.append(item)
                    save_job(item)
                    
        browser.close()
    return all_jobs
