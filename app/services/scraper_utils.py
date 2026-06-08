import os
import random
import time
import requests
from urllib.parse import urlparse
from typing import List, Dict, Optional, Callable
from app.core.logger import get_logger

logger = get_logger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 15  # seconds
SLEEP_BETWEEN_REQUESTS = 2.5  # seconds — polite delay per same-site request
MAX_WORKERS_PER_SITE = 3  # keep low to avoid bans (was 10)

_PROXY_CACHE = []
_LAST_CACHE_TIME = 0


def _short_url(url: str) -> str:
    """Shorten a URL for logging: 'https://mostaql.com/project/123456' → 'mostaql.com/.../123456'"""
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        parts = path.split("/")
        if len(parts) > 2:
            return f"{parsed.netloc}/.../{parts[-1]}"
        return f"{parsed.netloc}{path}"
    except Exception:
        return url[:60]


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

    if not _PROXY_CACHE or (current_time - _LAST_CACHE_TIME > 300):
        if os.path.exists(proxy_file):
            try:
                with open(proxy_file, "r") as f:
                    _PROXY_CACHE = [line.strip() for line in f if line.strip()]
                    _LAST_CACHE_TIME = current_time
                    logger.info(f"Loaded {len(_PROXY_CACHE)} proxies")
            except Exception as e:
                logger.error(f"Error reading proxy file: {e}")

    if _PROXY_CACHE:
        proxy_url = random.choice(_PROXY_CACHE)
        return {"http": proxy_url, "https": proxy_url}

    return None


def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT, params: Optional[Dict] = None) -> Optional[str]:
    """Fetch HTML from a URL with proxy rotation and retries."""
    short = _short_url(url)
    max_retries = 3
    for attempt in range(max_retries):
        proxies = get_random_proxy()
        try:
            r = requests.get(url, headers=HEADERS, params=params, proxies=proxies, timeout=timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            logger.debug(f"OK {short} ({len(r.text)} chars)")
            return r.text
        except Exception as e:
            # Only log the short error type, not the full stack
            err_type = type(e).__name__
            if attempt < max_retries - 1:
                logger.debug(f"Retry {attempt+1}/{max_retries} {short}: {err_type}")
                time.sleep(2)
            else:
                logger.warning(f"FAIL {short} after {max_retries} tries: {err_type}")
                return None
    return None


from app.services.db_services import get_existing_urls


def orchestrate_scraping(
    page_urls: List[str],
    extract_links_func: Callable[[str, int], List[str]],
    extract_details_func: Callable[[str], Optional[Dict[str, str]]],
    per_page_limit: int,
    table_name: str = None,
    save_func: Callable[[Dict], bool] = None,
    source_platform: str = "Unknown",
) -> List[Dict[str, str]]:
    """Orchestrate scraping for one platform.

    Uses SEQUENTIAL requests with polite delays to avoid bans
    when using free proxies.
    """
    all_links: List[str] = []

    # 1. Gather links from listing pages
    for page_url in page_urls:
        links = extract_links_func(page_url, per_page_limit)
        if not links:
            break
        for L in links:
            if L not in all_links:
                all_links.append(L)
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    if not all_links:
        logger.info(f"  {source_platform}: 0 links found")
        return []

    # 2. Filter out already-saved URLs
    new_links = all_links
    if table_name and all_links:
        existing_urls = get_existing_urls(all_links, table_name)
        new_links = [link for link in all_links if link not in existing_urls]

    skipped = len(all_links) - len(new_links)
    logger.info(f"  {source_platform}: {len(all_links)} links, {skipped} already saved, {len(new_links)} new")

    if not new_links:
        return []

    # 3. Extract details — SEQUENTIALLY with delay (avoids bans with free proxies)
    projects: List[Dict[str, str]] = []
    for i, link in enumerate(new_links):
        try:
            data = extract_details_func(link)
            if data:
                if "source_platform" not in data:
                    data["source_platform"] = source_platform
                projects.append(data)
                if save_func:
                    save_func(data)
        except Exception as exc:
            logger.warning(f"  {source_platform}: Error on item {i+1}: {type(exc).__name__}")

        # Polite delay between requests to the same site
        if i < len(new_links) - 1:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    logger.info(f"  {source_platform}: {len(projects)} items saved")
    return projects
