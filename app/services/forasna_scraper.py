from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import requests
import concurrent.futures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ar,en;q=0.9",
}
REQUEST_TIMEOUT = 15
BASE_URL = "https://forasna.com"
LIST_URL = "https://forasna.com/%D9%88%D8%B8%D8%A7%D8%A6%D9%81-%D8%AE%D8%A7%D9%84%D9%8A%D8%A9"


def _fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    except Exception as e:
        print(f"[forasna] error fetching {url}: {e}")
        return None


def _extract_job_from_card(card) -> Optional[Dict[str, str]]:
    title_tag = card.select_one("h2.job-title a")
    if not title_tag:
        return None
    title = title_tag.get_text(" ", strip=True)
    href = title_tag.get("href", "")
    if href.startswith("/"):
        href = BASE_URL + href

    company_tag = card.select_one("span.company-name a span")
    company = company_tag.get_text(" ", strip=True) if company_tag else ""

    location_tag = card.select_one("span.location-desktop span")
    location = location_tag.get_text(" ", strip=True) if location_tag else ""

    time_tag = card.select_one("time.job-date")
    publish_date = ""
    if time_tag:
        publish_date = time_tag.get("datetime", "") or time_tag.get_text(" ", strip=True)

    budget = ""
    for detail_div in card.select("div.job-details"):
        label = detail_div.select_one("span.job-details__title")
        if label and "الراتب" in label.get_text():
            value_span = label.find_next_sibling("span")
            if value_span:
                budget = value_span.get_text(" ", strip=True)
            break

    job_type = ""
    experience = ""
    categories = []
    for span in card.select("div.job-details span.with-info-separator, div.job-details a.with-info-separator"):
        title_attr = span.get("title", "")
        text = span.get_text(" ", strip=True)
        if "خبرة" in title_attr or "خبرة" in text:
            experience = text
        elif span.name == "a":
            if not job_type:
                job_type = text
            else:
                categories.append(text)

    skills = ", ".join(categories) if categories else ""

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
        "work_type": job_type, 
        "publish_date": publish_date,
        "budget": budget,
        "skills": skills,
        "url": href,
    }


def _scrape_page(page_url: str) -> List[Dict[str, str]]:
    html = _fetch_html(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.result-wrp")
    results = []
    for card in cards:
        data = _extract_job_from_card(card)
        if data:
            results.append(data)
    return results


from app.services.db_services import save_job, get_existing_urls

def fetch_forasna_jobs(pages: int = 1) -> List[Dict[str, str]]:
    def build_page_url(base: str, page: int) -> str:
        if page <= 1: return base
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}page={page}"

    page_urls = [build_page_url(LIST_URL, p) for p in range(1, pages + 1)]
    all_jobs: List[Dict[str, str]] = []

    max_workers = min(5, pages)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_scrape_page, url): url for url in page_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                results = future.result()
                
                # Check DB
                all_urls = [r["url"] for r in results if r.get("url")]
                existing_urls = get_existing_urls(all_urls, "opportunities_job")
                
                for item in results:
                    if item["url"] not in existing_urls:
                        item["source_platform"] = "Forasna"
                        all_jobs.append(item)
                        save_job(item)
                        
            except Exception as exc:
                print(f"[forasna] error: {exc}")

    return all_jobs
