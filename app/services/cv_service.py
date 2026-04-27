from app.api.models import CVSchema

async def build_cv_from_text(raw_text: str) -> CVSchema:
    return CVSchema(
        name="Mocked User",
        title="Software Engineer",
        summary="A highly skilled mocked user.",
        contact={"email": "mock@example.com"},
        experience=[],
        education=[],
        skills=["Python", "FastAPI"],
        projects=[],
        languages=[],
        certifications=[]
    )

async def optimize_cv_for_job(base_cv: CVSchema, target_job: str) -> CVSchema:
    # Just return the same CV to mock it
    return base_cv

async def interact_with_cv(cv: CVSchema, query: str) -> CVSchema:
    # Just return the same CV to mock it
    return cv

async def generate_project_proposal(profile: str, project: str) -> str:
    return "This is a mocked proposal. I can do this project perfectly."

async def get_recommended_keywords(cv_so_far: CVSchema) -> list[str]:
    return ["Mock", "Keyword", "FastAPI", "Docker"]
