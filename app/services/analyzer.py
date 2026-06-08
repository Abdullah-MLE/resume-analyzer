import re
from typing import List, Tuple
from sentence_transformers import util
from app.core.constants import SKILLS, ACTION_VERBS, STRONG_VERBS, SECTIONS_MAP

def calculate_similarity(model, cv_text: str, job_description: str) -> float:
    if not job_description.strip():
        return 0.0
    embeddings1 = model.encode(cv_text, convert_to_tensor=True)
    embeddings2 = model.encode(job_description, convert_to_tensor=True)
    cosine_scores = util.cos_sim(embeddings1, embeddings2)
    return float(cosine_scores[0][0].item())

def calculate_ats_score(resume_text: str) -> Tuple[int, List[str]]:
    text = resume_text.lower()
    score = 0
    matched = []

    # 1. Skill matching
    for skill in SKILLS:
        if skill in text:
            matched.append(skill)
            score += 6
    score = min(score, 40)

    # 2. Length
    word_count = len(text.split())
    if word_count > 500:
        score += 20
    elif word_count > 300:
        score += 15
    elif word_count > 200:
        score += 10
    elif word_count > 100:
        score += 5

    # 3. Sections
    sections = ["skills", "projects", "experience", "education"]
    section_points = sum(6 for sec in sections if sec in text)
    score += min(section_points, 25)

    # 4. Action verbs
    verb_points = sum(3 for v in ACTION_VERBS if v in text)
    score += min(verb_points, 15)

    return min(score, 100), matched

def analyze_resume(resume_text: str) -> List[str]:
    suggestions = []
    
    # 1. Check for Metrics (Numbers/Percentages)
    metrics = re.findall(r'\d+%|\d+\s?k|\$\d+|increased|decreased|improved', resume_text.lower())
    if len(metrics) < 3:
        suggestions.append("Quantify your achievements. Use numbers (e.g., 'Improved accuracy by 15%') to show impact.")

    # 2. Section Detection with Synonyms
    for section, keywords in SECTIONS_MAP.items():
        if not any(key in resume_text.lower() for key in keywords):
            suggestions.append(f"Missing or unclear '{section.capitalize()}' section. Use standard headings.")

    # 3. Bullet Point Detection
    bullet_points = re.findall(r'^[•\-\*]\s|^\d+\.\s', resume_text, re.MULTILINE)
    if len(bullet_points) < 5:
        suggestions.append("Use bullet points for better readability and ATS parsing.")

    # 4. Action Verbs vs Passive Voice
    found_verbs = [v for v in STRONG_VERBS if v in resume_text.lower()]
    if len(found_verbs) < 3:
        suggestions.append("Incorporate stronger action verbs like 'orchestrated' or 'automated' to describe your role.")

    # 5. Length and Density
    words = resume_text.split()
    if len(words) < 200:
        suggestions.append("Your resume is too short. Try to add more detailed descriptions of projects and experience.")
    elif len(words) > 800:
        suggestions.append("Your resume is too long. Aim for a concise 1-2 page document (approx 400-600 words).")
    
    # 6. Contact Info Check
    if not re.search(r'[\w\.-]+@[\w\.-]+', resume_text):
        suggestions.append("Missing email address. Ensure your contact information is clearly visible.")
    
    if "linkedin.com" not in resume_text.lower():
        suggestions.append("Add your LinkedIn profile URL to increase professional visibility.")

    return suggestions
