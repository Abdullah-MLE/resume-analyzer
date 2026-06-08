from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app.api.routers.scraping import router as scraping_router
from app.api.routers.core import router as core_router
from app.api.routers.cv import router as cv_router
from app.core.logger import get_logger

logger = get_logger("main")

import asyncio
from app.services.scheduler import intelligent_scraper_loop, stop_scheduler

SERVICE_TYPE = os.getenv("SERVICE_TYPE", "both")  # Can be 'api', 'scraper', or 'both'

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the SentenceTransformer model via centralized embedding_service
    # (singleton — loaded once, reused everywhere)
    if SERVICE_TYPE in ["api", "both"]:
        logger.info("Pre-loading SentenceTransformer model ...")
        from app.services.embedding_service import get_model
        model = get_model()
        app.state.model = model  # keep backward compat for analyzer.py
        logger.info("Model ready.")
    
    scraper_task = None
    # Conditionally start the background scraper
    if SERVICE_TYPE in ["scraper", "both"]:
        logger.info("Starting intelligent scraper loop ...")
        scraper_task = asyncio.create_task(intelligent_scraper_loop())
    
    yield
    
    if SERVICE_TYPE in ["api", "both"]:
        app.state.model = None
        
    if SERVICE_TYPE in ["scraper", "both"]:
        stop_scheduler()
        if scraper_task:
            try:
                await asyncio.wait_for(scraper_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

app = FastAPI(
    title="SuperCareer AI API",
    description="Recruitment and CV Optimization Platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Include all the new routers
app.include_router(scraping_router)
app.include_router(core_router)
app.include_router(cv_router)

if __name__ == "__main__":
    if SERVICE_TYPE == "scraper":
        print("Running in Standalone Scraper Mode (No Web Server)...")
        # Pre-load the model so embedding works during scraping
        from app.services.embedding_service import get_model
        get_model()
        # Run the scraper loop directly, no uvicorn needed
        asyncio.run(intelligent_scraper_loop())
    else:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
