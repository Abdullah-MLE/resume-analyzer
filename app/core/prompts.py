def get_cv_system_prompt() -> str:
    return """You are an expert ATS (Applicant Tracking System) specialist and professional resume writer. 
Your goal is to organize, optimize, and structure career information into a perfect CV.

STRICT RULES:
1. Always return valid JSON matching the provided schema.
2. DO NOT use markdown symbols like ### or ***.
3. Keep descriptions professional, impactful, and ATS-friendly (use action verbs).
4. For missing information, use empty strings "" or empty lists [].
5. Ensure dates are consistent and well-formatted."""

def get_cv_build_prompt(raw_text: str) -> str:
    return f"""Extract and organize the following raw text into a professional CV structure.
Raw Text:
{raw_text}

Analyze the text carefully, identifying personal details, work experience, education, and skills. 
Format it strictly into the requested JSON schema."""

def get_cv_job_optimize_prompt(base_cv: str, target_job: str) -> str:
    return f"""Tailor the following CV to perfectly match the target job description. 
Enhance the descriptions and emphasize skills that are most relevant to this job to ensure a high ATS score.

Base CV Data:
{base_cv}

Target Job Description:
{target_job}

Return the complete modified CV in the requested JSON format."""

def get_cv_interaction_prompt(cv: str, query: str) -> str:
    return f"""Update the following CV based on the user's specific request.

Current CV:
{cv}

User Request:
{query}

Return the updated CV in the requested JSON format."""

def get_proposal_prompt(profile: str, project: str) -> str:
    return f"""Write a professional and persuasive project proposal based on the user's profile and the project details.
The proposal should be concise, professional, and highlight why the user is the best fit for the project.
DO NOT use any markdown symbols (like #, *, -) in the text.

User Profile:
{profile}

Project Details:
{project}

Return only the final proposal text."""

def get_keywords_prompt(cv_so_far: str) -> str:
    return f"""Based on the current CV content, suggest 5-10 high-impact, ATS-friendly keywords or skills that should be added to improve visibility.

CV Content:
{cv_so_far}

Return a JSON object with a key "recommended_keywords" containing a list of strings.
Example: {{"recommended_keywords": ["Python", "AWS", "FastAPI"]}}"""
