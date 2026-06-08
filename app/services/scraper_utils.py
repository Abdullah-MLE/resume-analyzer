import os
import random
import time
import requests
import concurrent.futures
from typing import List, Dict, Optional, Callable
from app.core.logger import get_logger

logger = get_logger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 15  # seconds
SLEEP_BETWEEN_REQUESTS = 1.0  # seconds

_PROXY_CACHE = []
_LAST_CACHE_TIME = 0

def get_random_proxy() -> Optional[Dict[str, str]]:
    """Returns a random proxy from .env or free-proxy-list.txt."""
    global _PROXY_CACHE, _LAST_CACHE_TIME
    
    # Priority 1: .env variable
    proxies_env = os.getenv("PROXIES", "")
    if proxies_env:
        proxy_list = [p.strip() for p in proxies_env.split(",") if p.strip()]
        if proxy_list:
            proxy_url = random.choice(proxy_list)
            return {"http": proxy_url, "https": proxy_url}
    
    # Priority 2: free-proxy-list.txt
    proxy_file = "free-proxy-list.txt"
    current_time = time.time()
    
    # Refresh cache every 5 minutes or if empty
    if not _PROXY_CACHE or (current_time - _LAST_CACHE_TIME > 300):
        if os.path.exists(proxy_file):
            try:
                with open(proxy_file, "r") as f:
                    _PROXY_CACHE = [line.strip() for line in f if line.strip()]
                    _LAST_CACHE_TIME = current_time
                    logger.info(f"[Proxy] Loaded {len(_PROXY_CACHE)} proxies from {proxy_file}")
            except Exception as e:
                logger.error(f"[Proxy] Error reading {proxy_file}: {e}")
    
    if _PROXY_CACHE:
        proxy_url = random.choice(_PROXY_CACHE)
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    return None

def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT, params: Optional[Dict] = None) -> Optional[str]:
    """Fetch HTML from a URL with proxy rotation and retries."""
    max_retries = 3
    for attempt in range(max_retries):
        proxies = get_random_proxy()
        try:
            logger.debug(f"[HTTP] GET {url} (attempt {attempt + 1}/{max_retries})")
            r = requests.get(url, headers=HEADERS, params=params, proxies=proxies, timeout=timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            logger.info(f"[HTTP] OK {url} — {len(r.text)} chars")
            return r.text
        except Exception as e:
            logger.warning(f"[HTTP] FAIL {url} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"[HTTP] All retries exhausted for {url}")
                return None
            time.sleep(2) # Wait before next retry
    return None

from app.services.db_services import get_existing_urls

def orchestrate_scraping(
    page_urls: List[str], 
    extract_links_func: Callable[[str, int], List[str]], 
    extract_details_func: Callable[[str], Optional[Dict[str, str]]], 
    per_page_limit: int,
    table_name: str = None,
    save_func: Callable[[Dict], bool] = None,
    source_platform: str = "Unknown"
) -> List[Dict[str, str]]:
    """Orchestrate the full scraping pipeline for a platform."""
    logger.info(f"[Scraper:{source_platform}] Starting — {len(page_urls)} pages, limit={per_page_limit}")
    
    all_links: List[str] = []
    
    # 1. Gather Links
    for page_url in page_urls:
        links = extract_links_func(page_url, per_page_limit)
        if not links:
            logger.info(f"[Scraper:{source_platform}] No links found on {page_url}")
            break
        for L in links:
            if L not in all_links: 
                all_links.append(L)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    logger.info(f"[Scraper:{source_platform}] Gathered {len(all_links)} total links")

    # 2. Check Database for Existing URLs
    new_links = all_links
    if table_name and all_links:
        existing_urls = get_existing_urls(all_links, table_name)
        new_links = [link for link in all_links if link not in existing_urls]
        logger.info(f"[Scraper:{source_platform}] {len(all_links) - len(new_links)} already in DB, {len(new_links)} new")

    # 3. Extract Details and Save in Parallel
    projects: List[Dict[str, str]] = []
    max_workers = min(10, len(new_links) if new_links else 1)
    
    if new_links:
        logger.info(f"[Scraper:{source_platform}] Extracting details for {len(new_links)} items (workers={max_workers}) ...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(extract_details_func, link): link for link in new_links}
            for future in concurrent.futures.as_completed(future_to_url):
                link = future_to_url[future]
                try:
                    data = future.result()
                    if data:
                        if "source_platform" not in data:
                            data["source_platform"] = source_platform
                        projects.append(data)
                        if save_func:
                            save_func(data)
                    else:
                        logger.debug(f"[Scraper:{source_platform}] No data extracted from {link}")
                except Exception as exc:
                    logger.warning(f"[Scraper:{source_platform}] Error extracting {link}: {exc}")

    logger.info(f"[Scraper:{source_platform}] Done — {len(projects)} items extracted and saved.")
    return projects
