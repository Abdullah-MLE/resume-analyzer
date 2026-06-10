import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.scrapers.scheduler import run_scrapers

async def manual_run():
    print("🚀 [Manual Run] Starting scrapers manually (ignoring night mode)...")
    try:
        new_items = await run_scrapers()
        print(f"✅ [Manual Run] Finished successfully! Found {new_items} new items.")
    except Exception as e:
        print(f"❌ [Manual Run] Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(manual_run())
