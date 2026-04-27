from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# 1. Data Scraping Models
class Project(BaseModel):
    id: str  # Use link as ID if not available
    title: str
    description: str
    status: Optional[str] = None
    publish_date: Optional[str] = None
    budget: Optional[str] = None
    duration: Optional[str] = None
    skills: Optional[str] = None
    url: str

class Job(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None      # Full Time / Part Time
    work_type: Optional[str] = None     # On-site / Remote / Hybrid
    publish_date: Optional[str] = None
    budget: Optional[str] = None
    skills: Optional[str] = None
    url: str

# 2. Core AI & Matching Logic Models
class MatchRequest(BaseModel):
    cv_content: str
    job_desc: str

class MatchResponse(BaseModel):
    match_score: int

class OptimizeATSRequest(BaseModel):
    cv_text: str

class OptimizeATSResponse(BaseModel):
    feedback: str
    ats_score: int

class ProposalRequest(BaseModel):
    user_profile: str
    project_details: str

class ProposalResponse(BaseModel):
    proposal_text: str

# 3. CV Generation & Management Models

class PersonalDetails(BaseModel):
    full_name: str = Field(alias="Full Name")
    phone_number: str = Field(alias="Phone Number")
    professional_title: str = Field(alias="Professional Title")
    email_address: str = Field(alias="Email Address")
    location: str = Field(alias="Location")
    portfolio_linkedin: str = Field(alias="Portfolio / LinkedIn URL")
    professional_summary: str = Field(alias="Professional Summary")

class ExperienceItem(BaseModel):
    currently_work_here: bool = Field(alias="I currently work here")
    job_title: str = Field(alias="Job Title")
    company: str = Field(alias="Company")
    start_date: str = Field(alias="Start Date")
    end_date: str = Field(alias="End Date")
    description: str = Field(alias="Description")

class EducationItem(BaseModel):
    school_university: str = Field(alias="School / University")
    degree_qualification: str = Field(alias="Degree / Qualification")
    year_of_graduation: str = Field(alias="Year of Graduation")
    additional_details: str = Field(alias="Additional Details")

class CVSchema(BaseModel):
    personal_details: PersonalDetails = Field(alias="Personal Details")
    experience: List[ExperienceItem] = Field(alias="Experience")
    education: List[EducationItem] = Field(alias="Education")
    skills: List[str] = Field(alias="Skills")

    class Config:
        populate_by_name = True

class CVProfileRequest(BaseModel):
    user_data: str

class CVProfileResponse(BaseModel):
    cv_schema: CVSchema

class CVJobRequest(BaseModel):
    target_job: str
    base_cv: CVSchema

class CVJobResponse(BaseModel):
    optimized_cv: CVSchema

class CVExtractedResponse(BaseModel):
    extracted_text: str

class CVBuildOldRequest(BaseModel):
    raw_text: str

class AIKeywordsRequest(BaseModel):
    cv_so_far: CVSchema

class AIKeywordsResponse(BaseModel):
    recommended_keywords: List[str]

# 4. Interaction Models
class UserInteractRequest(BaseModel):
    cv: CVSchema
    user_query: str

class UserInteractResponse(BaseModel):
    modified_cv: CVSchema
    ai_message: Optional[str] = None
