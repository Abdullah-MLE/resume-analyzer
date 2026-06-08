# AI Freelance Hub & ATS System

An integrated system for evaluating resumes (CVs) using ATS standards and automatically scraping job and freelance opportunities from popular job boards.

---

## 🚀 How to Run using Docker (Recommended)

To run the entire project (the API web server and the Scraper background service) in clean, isolated environments, use Docker:

1.  Make sure you have [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed on your machine.
2.  Create your `.env` file by copying `.env.example` and filling in your credentials:
    ```bash
    cp .env.example .env
    ```
3.  Open your command prompt or terminal in the project directory and run:
    ```bash
    docker-compose up -d --build
    ```

This command will build and start two services:
*   **API Service (`ats_api`):** Accessible at `http://localhost:8080` (or local port 8000 internally).
*   **Scraper Service (`ats_scraper`):** Runs in the background to automatically scrape new jobs and projects.

### To stop the project:
```bash
docker-compose down
```

---

## 🌐 Sharing your Local Server (Ngrok)

If you want to make your local server available on the internet (for testing, linking with mobile apps, or sharing with others):

1.  Start your local server (using Docker or Python).
2.  Install [Ngrok](https://ngrok.com/) on your machine.
3.  Open a new terminal window and run:
    ```bash
    ngrok http 8080
    ```
    *(Note: If you run FastAPI directly on python outside Docker, use `ngrok http 8000`)*.

Ngrok will give you a public URL starting with `https://...ngrok-free.app` which forwards requests directly to your local computer.

---

## ⚙️ Running Locally without Docker

If you prefer to run the project without Docker:

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Install browser binaries for Playwright (used for scraping):
    ```bash
    playwright install chromium
    ```
3.  Create a `.env` file in the `resume-analyzer` folder with your credentials.
4.  Run the application using:
    ```bash
    python -m app.main
    ```

You can control what services run by changing the `SERVICE_TYPE` environment variable in your `.env` file:
*   `SERVICE_TYPE=api` runs only the API server.
*   `SERVICE_TYPE=scraper` runs only the background scraper loop.
*   `SERVICE_TYPE=both` runs both services together in the same process.

---

## 📖 API Documentation

Once the API service is running, you can access the interactive API Swagger documentation at:
`http://localhost:8080/docs` (if running via Docker) or `http://localhost:8000/docs` (if running locally).
