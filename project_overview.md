# SuperCareer AI & ATS - Project Overview

Welcome to the **SuperCareer AI & ATS** project! This is a complete system designed to automatically scrape job opportunities and freelance projects, store them in a database, and use Artificial Intelligence (AI) to analyze resumes (CVs) and match them with jobs.

---

## 1. Project Goal
The main goal of this project is to build an **automated freelance and job recruitment assistant**. It has two main capabilities:
1. **Web Scraping:** Automatically scan job boards and freelance websites in the region, collect new jobs/projects, and save them.
2. **AI Resume Assistant:** Provide API endpoints to create professional CVs, optimize CVs to match specific job descriptions, calculate compatibility scores, and generate custom job proposals.

---

## 2. High-Level Architecture

The project is split into three main layers:
*   **Database (Supabase):** Stores the scraped jobs, freelance projects, and skills.
*   **Web Scrapers (Background Services):** Run continuously in the background to scrape jobs and projects from popular websites.
*   **FastAPI backend (API Service):** Serves endpoints for CV parsing, matching, keyword suggestions, proposal generation, and manual scraping triggers.

```
+-------------------------------------------------------------+
|                        API Service                          |
|                       (FastAPI App)                         |
+------------------------------+------------------------------+
                               |
                               | (Saves / Checks data)
                               v
+-------------------------------------------------------------+
|                         Database                            |
|                        (Supabase)                           |
+------------------------------^------------------------------+
                               |
                               | (Scrapes & Saves jobs)
                               |
+------------------------------+------------------------------+
|                       Scraper Service                       |
|                   (Intelligent Scheduler)                   |
+-------------------------------------------------------------+
```

---

## 3. Detailed Component Breakdown

### A. FastAPI Backend (`/app/api` & `/app/main.py`)
This is the entry point of the web server. It provides endpoints grouped under three main areas:

1.  **Core AI (`/API`):**
    *   `POST /API/match`: Calculates the compatibility between a CV and a job description.
    *   `POST /API/proposel`: Generates a professional, custom project proposal for a freelance job using the user's profile.
2.  **CV Generation and Optimization (`/API/CV`):**
    *   `POST /API/CV/Build/old_cv` & `/Build/Profile_cv`: Converts raw user text or profile data into a structured JSON CV schema.
    *   `POST /API/CV/Build/Job_cv`: Optimizes a CV to make it a perfect fit for a target job.
    *   `POST /API/CV/optimiz/ATS`: Evaluates the ATS (Applicant Tracking System) compatibility score of a CV.
    *   `POST /API/CV/optimiz/user_interaction`: Allows the user to ask the AI to make specific edits to the CV (e.g., "Add my experience as a writer").
    *   `POST /API/CV/AI_Recommended_Keywords`: Recommends 5 to 10 high-impact keywords to add to the CV to get better ATS rankings.
3.  **Manual Scraping (`/API/Scraping`):**
    *   Provides routes to manually trigger scraping cycles for specific websites (Mostaql, FreelanceYard, Elharefa, Wuzzuf, Bayt, Forasna).

---

### B. Web Scrapers & Scheduler (`/app/services`)
The scraping system is managed by an intelligent loop (`scheduler.py`) that handles six platforms:

*   **Freelance Platforms:**
    *   **Mostaql:** Scrapes project titles, budgets, descriptions, durations, and required skills.
    *   **FreelanceYard:** Scrapes projects.
    *   **Elharefa:** Scrapes projects.
*   **Job Boards:**
    *   **Wuzzuf:** Scrapes jobs (titles, companies, descriptions, locations, job/work types, and skills).
    *   **Bayt:** Scrapes jobs (uses a headless browser powered by Playwright to bypass protections).
    *   **Forasna:** Scrapes jobs.

#### ⚙️ The Intelligent Scheduler:
The scheduler does not run on a static timer. Instead, it adapts dynamically:
1.  **Base Interval:** It runs every 15 minutes by default.
2.  **No New Data Multiplier:** If a cycle runs and finds **0 new items**, it multiplies the wait time by `1.5` (up to a maximum of 60 minutes) to save server power and avoid getting blocked. Once new data is found, the wait time resets back to 15 minutes.
3.  **Night Mode:** It has Egyptian timezone detection (`Africa/Cairo`). Between **12:00 AM (midnight) and 6:00 AM**, the scheduler goes into Night Mode and sleeps for **120 minutes** (2 hours) per cycle since new jobs are rarely posted during these hours.
4.  **Deduplication:** Before saving a scraped project or job, the scraper checks Supabase to see if the URL is already in the database. If it exists, it skips it to prevent duplicates.
5.  **Proxy Rotation (`scraper_utils.py`):** Uses a list of proxies from `.env` or `free-proxy-list.txt` to make requests, preventing the scrapers from being banned.

---

### C. Database Layer (`/app/core/database.py` & `/app/services/db_services.py`)
The database uses **Supabase**. It has a schema to track opportunities and skills:
*   `opportunities_freelanceproject`: Stores freelance work (title, description, budget, platform, source url, posted date).
*   `opportunities_job`: Stores full-time or part-time employment positions (title, company, description, location, platform, source url).
*   `accounts_skill`: A global table of unique skills (e.g., "Python", "React", "SQL").
*   `opportunities_freelanceproject_required_skills` & `opportunities_job_required_skills`: Junction tables that link skills to the scraped projects and jobs.

---

### D. AI & Matching Engine
The project uses two types of AI models:

1.  **Google Gemini (via Vertex AI or Gemini API key):**
    *   Used for generating text structures, optimizing CV content, generating project proposals, and recommending keywords.
    *   Managed by a custom `GeminiWrapper` helper that handles retries, fallback models (like `gemini-2.5-flash-lite`, `gemini-2.0-flash-lite`, and `gemini-2.5-flash`), and structured JSON output matching Pydantic schemas.
2.  **SentenceTransformer (ML Model):**
    *   Loads the `paraphrase-multilingual-MiniLM-L12-v2` model in memory.
    *   Used to compute semantic similarity scores between a user's CV and a job description.

---

## 4. How to Run the Project

### Using Docker (Recommended)
This is the easiest way because it sets up all environments, PyTorch, and Playwright automatically.

1.  Configure the `.env` file (copy `.env.example` to `.env` and fill in API keys).
2.  Run the command:
    ```bash
    docker-compose up -d --build
    ```
    This starts two containers:
    *   `ats_api`: The FastAPI web server running on port `8080` (accessible at `http://localhost:8080`).
    *   `ats_scraper`: The background scraper running its loop continuously.

### Running Locally without Docker
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Install Playwright browser binaries (required for scraper):
    ```bash
    playwright install chromium
    ```
3.  Set environment variables:
    *   To run the API and scraper together: `SERVICE_TYPE=both`
    *   To run only the API: `SERVICE_TYPE=api`
    *   To run only the Scraper: `SERVICE_TYPE=scraper`
4.  Start the application:
    ```bash
    python -m app.main
    ```
