import random
from typing import List, Tuple

def calculate_similarity(model, cv_text: str, job_description: str) -> float:
    if not job_description.strip():
        return 0.0
    return round(random.uniform(0.6, 0.95), 2)

def calculate_ats_score(resume_text: str) -> Tuple[int, List[str]]:
    score = random.randint(60, 95)
    matched = ["Python", "Docker", "FastAPI"] if score > 70 else ["Python"]
    return score, matched

def analyze_resume(resume_text: str) -> List[str]:
    return [
        "Quantify your achievements with metrics.",
        "Add more action verbs.",
        "Ensure your contact info is up to date."
    ]
