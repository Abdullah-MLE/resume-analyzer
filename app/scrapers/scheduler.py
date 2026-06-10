import asyncio
from datetime import datetime
from app.core.logger import get_logger

from app.scrapers.mostaql_scraper import fetch_mostaql_projects
from app.scrapers.freelanceyard_scraper import fetch_freelanceyard_projects
from app.scrapers.elharefa_scraper import fetch_elharefa_projects
from app.scrapers.wuzzuf_scraper import fetch_wuzzuf_jobs
from app.scrapers.bayt_scraper import fetch_bayt_jobs
from app.scrapers.forasna_scraper import fetch_forasna_jobs

logger = get_logger("scheduler")

# Scheduler Configuration
BASE_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 60
MULTIPLIER_IF_NO_DATA = 1.5
NIGHT_INTERVAL_MINUTES = 120  # 2 hours

NIGHT_START_HOUR = 0
NIGHT_END_HOUR = 6

# Global state to stop the scheduler cleanly
_is_running = False

# ── All scrapers defined in one list for easy management ─────
SCRAPERS = [
    {"name": "Mostaql",       "func": fetch_mostaql_projects,       "kwargs": {"pages": 1, "per_page_limit": 25}},
    {"name": "FreelanceYard", "func": fetch_freelanceyard_projects,  "kwargs": {"pages": 1, "per_page_limit": 25}},
    {"name": "Elharefa",      "func": fetch_elharefa_projects,       "kwargs": {"pages": 1, "per_page_limit": 25}},
    {"name": "Wuzzuf",        "func": fetch_wuzzuf_jobs,             "kwargs": {"pages": 1}},
    {"name": "Bayt",          "func": fetch_bayt_jobs,               "kwargs": {"pages": 1}},
    {"name": "Forasna",       "func": fetch_forasna_jobs,            "kwargs": {"pages": 1}},
]


async def run_scrapers():
    """Run all scrapers one-by-one. Each scraper is isolated —
    if one crashes the others still run."""
    total_new_items = 0

    logger.info("━" * 50)
    logger.info("[SCRAPING] Cycle started")
    logger.info("━" * 50)

    for scraper in SCRAPERS:
        name = scraper["name"]
        try:
            logger.info(f"[SCRAPING] ▶ {name} ...")
            data = await asyncio.to_thread(scraper["func"], **scraper["kwargs"])
            count = len(data) if data else 0
            total_new_items += count
            logger.info(f"[SCRAPING] ✓ {name} — {count} new items")
        except Exception as e:
            # ── THIS IS THE KEY FIX ──
            # One scraper crashing does NOT stop the others.
            logger.error(f"[SCRAPING] ✗ {name} — SKIPPED (error: {e})")

    logger.info("━" * 50)
    logger.info(f"[SCRAPING] Cycle done — {total_new_items} total new items")
    logger.info("━" * 50)
    return total_new_items


async def intelligent_scraper_loop():
    global _is_running
    _is_running = True
    current_interval = BASE_INTERVAL_MINUTES

    logger.info("System started. Waiting 10s for server to be ready ...")
    await asyncio.sleep(10)

    from zoneinfo import ZoneInfo
    egypt_timezone = ZoneInfo("Africa/Cairo")

    while _is_running:
        now = datetime.now(egypt_timezone)

        # Night mode
        is_night = False
        if NIGHT_START_HOUR < NIGHT_END_HOUR:
            is_night = NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR
        else:
            is_night = now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR

        if is_night:
            sleep_time_minutes = NIGHT_INTERVAL_MINUTES
            logger.info(f"🌙 Night mode — sleeping {sleep_time_minutes} min")
        else:
            # ────────────────── SCRAPING ──────────────────
            new_items_count = await run_scrapers()

            if new_items_count > 0:
                current_interval = BASE_INTERVAL_MINUTES
            else:
                current_interval = min(current_interval * MULTIPLIER_IF_NO_DATA, MAX_INTERVAL_MINUTES)

            # ────────────────── EMBEDDING + MATCHING ──────
            try:
                logger.info("━" * 50)
                logger.info("[EMBEDDING] Starting pipeline ...")
                logger.info("━" * 50)
                from app.services.matching_service import run_matching_pipeline
                result = await asyncio.to_thread(run_matching_pipeline)
                total_matches = result.get("total_new_matches", 0)
                emb = result.get("embeddings", {})
                logger.info("━" * 50)
                logger.info(
                    f"[PIPELINE DONE] "
                    f"Embedded: {emb.get('jobs',0)} jobs, {emb.get('projects',0)} projects, "
                    f"{emb.get('cvs',0)} CVs, {emb.get('profiles',0)} profiles | "
                    f"New matches: {total_matches}"
                )
                logger.info("━" * 50)
            except Exception as e:
                logger.error(f"[PIPELINE ERROR] {e}")

            sleep_time_minutes = current_interval
            logger.info(f"💤 Next cycle in {sleep_time_minutes:.0f} min")

        # Sleep in chunks so we can exit cleanly
        sleep_seconds = sleep_time_minutes * 60
        chunk_size = 5
        for _ in range(int(sleep_seconds / chunk_size)):
            if not _is_running:
                break
            await asyncio.sleep(chunk_size)

    logger.info("System stopped.")


def stop_scheduler():
    global _is_running
    _is_running = False
