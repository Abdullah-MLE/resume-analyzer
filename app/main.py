from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.api.routers.core import router as core_router
from app.api.routers.cv import router as cv_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mocking ML model loading
    print("Loading Mock ML models...")
    app.state.model = "Mocked_Model"
    print("Mock Models loaded successfully.")
    
    yield
    
    app.state.model = None

app = FastAPI(
    title="SuperCareer AI / Tansiq AI API",
    description="Recruitment and CV Optimization Platform. (Mocked)",
    version="1.0.0",
    lifespan=lifespan
)

# Include all the new routers
app.include_router(core_router)
app.include_router(cv_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
