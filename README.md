# AI Freelance Hub & ATS System

This is a system to evaluate resumes (ATS) and scrape freelance jobs automatically.

## 🚀 How to Run Using Docker (Recommended)

To run the whole project (API and Scraper) easily, use Docker:

1. Make sure you have [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.
2. Open your terminal in the project folder and run:

```bash
docker-compose up -d --build
```

This command starts two services:
- **API Service**: Runs on port `8000`.
- **Scraper Service**: Runs in the background to scrape jobs.

*To stop the project, run:*
```bash
docker-compose down
```

---

## 🌐 Share the Local Server Online (Using Ngrok)

If you want to access your API from the internet (for example, to connect it to a mobile app or share it), you can use Ngrok:

1. Make sure your local server is running (via Docker or Python).
2. Open a new terminal and run:

```bash
ngrok http 8000
```

Ngrok will give you a public URL (e.g., `https://...ngrok-free.app`). You can use this link to access your API from anywhere.

