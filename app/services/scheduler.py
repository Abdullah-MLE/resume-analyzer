import asyncio
from datetime import datetime
from app.core.logger import get_logger

from app.services.mostaql_scraper import fetch_mostaql_projects
from app.services.freelanceyard_scraper import fetch_freelanceyard_projects
from app.services.elharefa_scraper import fetch_elharefa_projects
from app.services.wuzzuf_scraper import fetch_wuzzuf_jobs
from app.services.bayt_scraper import fetch_bayt_jobs
from app.services.forasna_scraper import fetch_forasna_jobs

logger = get_logger()

# Scheduler Configuration
BASE_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 60
MULTIPLIER_IF_NO_DATA = 1.5
NIGHT_INTERVAL_MINUTES = 120 # 2 hours
NIGHT_START_HOUR = 0  # 12:00 AM
NIGHT_END_HOUR = 6    # 6:00 AM

# Global state to stop the scheduler cleanly
_is_running = False

async def run_scrapers():
    """Run all scrapers sequentially or concurrently and return the total number of new items found."""
    total_new_items = 0
    
    logger.info("Starting a new scraping cycle...")
    
    # We can run them sequentially to avoid killing the server/CPU, 
    # since each scraper uses concurrent.futures internally.
    try:
        mostaql_data = await asyncio.to_thread(fetch_mostaql_projects, pages=1, per_page_limit=25)
        total_new_items += len(mostaql_data)
        logger.info(f"[Mostaql] +{len(mostaql_data)}")

        freelanceyard_data = await asyncio.to_thread(fetch_freelanceyard_projects, pages=1, per_page_limit=25)
        total_new_items += len(freelanceyard_data)
        logger.info(f"[FreelanceYard] +{len(freelanceyard_data)}")

        elharefa_data = await asyncio.to_thread(fetch_elharefa_projects, pages=1, per_page_limit=25)
        total_new_items += len(elharefa_data)
        logger.info(f"[Elharefa] +{len(elharefa_data)}")

        wuzzuf_data = await asyncio.to_thread(fetch_wuzzuf_jobs, pages=1)
        total_new_items += len(wuzzuf_data)
        logger.info(f"[Wuzzuf] +{len(wuzzuf_data)}")

        bayt_data = await asyncio.to_thread(fetch_bayt_jobs, pages=1)
        total_new_items += len(bayt_data)
        logger.info(f"[Bayt] +{len(bayt_data)}")

        forasna_data = await asyncio.to_thread(fetch_forasna_jobs, pages=1)
        total_new_items += len(forasna_data)
        logger.info(f"[Forasna] +{len(forasna_data)}")
        
    except Exception as e:
        logger.error(f"Error during scraping cycle: {e}")
        
    return total_new_items

async def intelligent_scraper_loop():
    global _is_running
    _is_running = True
    current_interval = BASE_INTERVAL_MINUTES

    logger.info("Intelligent Scraper Loop started.")
    print("🤖 [Scraper] System started. Check 'scraper.log' for details.")

    # Small delay before starting the first cycle to allow the server to fully start
    await asyncio.sleep(10)

    while _is_running:
        now = datetime.now()
        
        # Night mode override
        if NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR:
            sleep_time_minutes = NIGHT_INTERVAL_MINUTES
            logger.info(f"Night mode active. Sleeping for {sleep_time_minutes} minutes.")
            print(f"🌙 [Scraper] Night mode. Next run in {sleep_time_minutes} min.")
        else:
            # Run Scrapers
            print("⏳ [Scraper] Cycle started...")
            new_items_count = await run_scrapers()
            
            if new_items_count > 0:
                current_interval = BASE_INTERVAL_MINUTES
                logger.info(f"Cycle Done: {new_items_count} new. Next: {current_interval}m.")
                print(f"✅ [Scraper] Cycle finished. Found {new_items_count} new items. Next in {current_interval} min.")
            else:
                current_interval = min(current_interval * MULTIPLIER_IF_NO_DATA, MAX_INTERVAL_MINUTES)
                logger.info(f"Cycle Done: 0 new. Next: {current_interval:.1f}m.")
                print(f"💤 [Scraper] Cycle finished. No new items. Next in {current_interval:.1f} min.")
                
            sleep_time_minutes = current_interval

        # Sleep, but break it into chunks so we can exit cleanly if _is_running becomes False
        sleep_seconds = sleep_time_minutes * 60
        chunk_size = 5
        for _ in range(int(sleep_seconds / chunk_size)):
            if not _is_running:
                break
            await asyncio.sleep(chunk_size)
            
    logger.info("Intelligent Scraper Loop stopped.")
    print("🛑 [Scraper] System stopped.")

def stop_scheduler():
    global _is_running
    _is_running = False
