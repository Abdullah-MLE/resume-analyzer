def get_cv_system_prompt() -> str:
    return """You are an expert ATS (Applicant Tracking System) specialist and professional resume writer. 
Your goal is to organize, optimize, and structure career information into a perfect CV.

STRICT RULES:
1. Always return valid JSON matching the provided schema.
2. DO NOT use markdown symbols like ### or ***.
3. Keep descriptions professional, impactful, and ATS-friendly (use action verbs).
4. For missing information, use empty strings "" or empty lists [].
5. Ensure dates are consistent and well-formatted.
6. ALL content in the CV, including skills, descriptions, and titles, MUST be strictly in English."""

def get_cv_build_prompt(raw_text: str) -> str:
    return f"""Extract and organize the following raw text into a professional CV structure.
Translate any non-English text to English.
Raw Text:
{raw_text}

Analyze the text carefully, identifying personal details, work experience, education, and skills. 
Format it strictly into the requested JSON schema. All output must be in English."""

def get_cv_job_optimize_prompt(base_cv: str, target_job: str) -> str:
    return f"""Tailor the following CV to perfectly match the target job description. 
Enhance the descriptions and emphasize skills that are most relevant to this job to ensure a high ATS score.

Base CV Data:
{base_cv}

Target Job Description:
{target_job}

Return the complete modified CV in the requested JSON format. Ensure all content, including any newly added skills or descriptions, is in English."""

def get_cv_interaction_prompt(cv: str, query: str) -> str:
    return f"""Based on the user's request, decide if you need to update their CV.
If the user wants to add, change, or remove information from their CV, modify it and set 'is_modified' to true.
If the user is just asking a question or the request doesn't require modifying the CV, set 'is_modified' to false and just reply in 'ai_message'.

Current CV:
{cv}

User Request:
{query}

Return a JSON object containing your decision ('is_modified'), the 'modified_cv' (if is_modified is true), and an 'ai_message' responding to the user. Ensure the entire updated CV remains strictly in English. If the user request is in Arabic, the AI message MUST be in Arabic, but all CV fields must remain in English."""

def get_proposal_prompt(profile: str, project: str) -> str:
    return f"""Write a professional and persuasive project proposal based on the user's profile and the project details.
The proposal should be concise, professional, and highlight why the user is the best fit for the project.
DO NOT use any markdown symbols (like #, *, -) in the text.

CRITICAL INSTRUCTION: Write the proposal in the EXACT SAME LANGUAGE as the Project Details. 
- If the Project Details are written in Arabic, the proposal MUST be in Arabic.
- If the Project Details are written in English, the proposal MUST be in English.

User Profile:
{profile}

Project Details:
{project}

Return only the final proposal text in the correct language."""

def get_keywords_prompt(cv_so_far: str) -> str:
    return f"""Based on the current CV content, suggest 5-10 high-impact, ATS-friendly keywords or skills that should be added to improve visibility.
Ensure all recommended keywords and skills are in English.

CV Content:
{cv_so_far}

Return a JSON object with a key "recommended_keywords" containing a list of strings.
Example: {{"recommended_keywords": ["Python", "AWS", "FastAPI"]}}"""
