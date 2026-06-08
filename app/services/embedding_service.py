"""
Embedding Service
=================
Generates and stores vector embeddings for jobs, projects, CVs, and user profiles.

Model : paraphrase-multilingual-MiniLM-L12-v2  (384-dim, Arabic + English)
Storage: Supabase pgvector column ``embedding vector(384)``
"""

import threading
import json
import numpy as np
from typing import List, Dict

from app.core.logger import get_logger

logger = get_logger("embedding")

# ── Model singleton ──────────────────────────────────────────
_model = None
_model_lock = threading.Lock()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 32  # keep small → low RAM on CPU-only servers


def get_model():
    """Lazy-load the SentenceTransformer model (thread-safe singleton)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info(f"Loading SentenceTransformer model: {MODEL_NAME} ...")
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(MODEL_NAME)
                logger.info("SentenceTransformer model loaded successfully.")
    return _model


# ── Core embedding functions ─────────────────────────────────
def generate_embedding(text: str) -> List[float]:
    """Encode a single text string → 384-dim float list."""
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    model = get_model()
    with _model_lock:
        vec = model.encode(text, convert_to_tensor=False, show_progress_bar=False)
    return vec.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Encode a batch of texts → list of 384-dim float lists.

    Uses ``normalize_embeddings=True`` so cosine similarity == dot product
    (faster math downstream).
    """
    if not texts:
        return []
    clean = [t if t and t.strip() else " " for t in texts]
    model = get_model()
    with _model_lock:
        vecs = model.encode(
            clean,
            batch_size=BATCH_SIZE,
            convert_to_tensor=False,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
    return [v.tolist() for v in vecs]


def compute_cosine_similarity(emb_a: List[float], emb_b: List[float]) -> float:
    """Cosine similarity between two flat embedding vectors → float in [-1, 1]."""
    a = np.array(emb_a, dtype=np.float32)
    b = np.array(emb_b, dtype=np.float32)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── Text builders ────────────────────────────────────────────
def _build_text_for_job(row: Dict, skills: List[str] = None) -> str:
    parts = []
    if row.get("title"):
        parts.append(row["title"])
    if row.get("description"):
        parts.append(row["description"][:2000])   # cap long descriptions
    if row.get("company"):
        parts.append(f"Company: {row['company']}")
    if row.get("location"):
        parts.append(f"Location: {row['location']}")
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    return " | ".join(parts) or " "


def _build_text_for_project(row: Dict, skills: List[str] = None) -> str:
    parts = []
    if row.get("title"):
        parts.append(row["title"])
    if row.get("description"):
        parts.append(row["description"][:2000])
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    return " | ".join(parts) or " "


def _build_text_for_cv(row: Dict, skills: List[str] = None) -> str:
    parts = []
    if row.get("professional_title"):
        parts.append(row["professional_title"])
    if row.get("professional_summary"):
        parts.append(row["professional_summary"])
    if row.get("content"):
        parts.append(row["content"][:3000])
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    return " | ".join(parts) or " "


def _build_text_for_profile(row: Dict, skills: List[str] = None) -> str:
    parts = []
    if row.get("professional_title"):
        parts.append(row["professional_title"])
    if row.get("specialization"):
        parts.append(row["specialization"])
    if row.get("bio"):
        parts.append(row["bio"])
    if row.get("experience"):
        parts.append(row["experience"][:2000])
    if row.get("education"):
        parts.append(row["education"][:1000])
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    return " | ".join(parts) or " "


# ── Batch embed helpers ──────────────────────────────────────
def _embed_rows(rows, text_builder, skills_map, table_name, label):
    """Generate embeddings for *rows*, update DB. Returns list of embedded IDs."""
    if not rows:
        logger.debug(f"[EMBEDDING] {label}: nothing to embed")
        return []

    logger.info(f"[EMBEDDING] {label}: {len(rows)} items → generating ...")

    texts = [text_builder(r, skills_map.get(r["id"], [])) for r in rows]
    embeddings = generate_embeddings_batch(texts)

    from app.services.db_services import update_embedding
    embedded_ids = []
    for i, row in enumerate(rows):
        if update_embedding(table_name, row["id"], embeddings[i]):
            embedded_ids.append(row["id"])
        else:
            logger.warning(f"[EMBEDDING] {label} id={row['id']}: save failed")

    logger.info(f"[EMBEDDING] {label}: {len(embedded_ids)}/{len(rows)} done")
    return embedded_ids


def embed_new_jobs() -> List[int]:
    """Embed jobs whose ``embedding`` column is NULL."""
    from app.services.db_services import fetch_all, get_skills_map
    rows = fetch_all(
        "opportunities_job",
        "id, title, description, company, location",
        is_null_col="embedding",
    )
    skills_map = get_skills_map("opportunities_job_required_skills", "job_id") if rows else {}
    return _embed_rows(rows, _build_text_for_job, skills_map, "opportunities_job", "jobs")


def embed_new_projects() -> List[int]:
    """Embed freelance projects whose ``embedding`` column is NULL."""
    from app.services.db_services import fetch_all, get_skills_map
    rows = fetch_all(
        "opportunities_freelanceproject",
        "id, title, description",
        is_null_col="embedding",
    )
    skills_map = get_skills_map("opportunities_freelanceproject_required_skills", "freelanceproject_id") if rows else {}
    return _embed_rows(rows, _build_text_for_project, skills_map, "opportunities_freelanceproject", "projects")


def embed_new_cvs() -> List[int]:
    """Embed base CVs whose ``embedding`` column is NULL."""
    from app.services.db_services import fetch_all, get_skills_map
    rows = fetch_all(
        "documents_cv",
        "id, professional_title, professional_summary, content, user_id",
        is_null_col="embedding",
        eq_filters={"is_base": True},
    )
    skills_map = get_skills_map("documents_cv_skills", "cv_id") if rows else {}
    return _embed_rows(rows, _build_text_for_cv, skills_map, "documents_cv", "base CVs")


def embed_new_profiles() -> List[int]:
    """Embed user profiles whose ``embedding`` column is NULL."""
    from app.services.db_services import fetch_all, get_skills_map
    rows = fetch_all(
        "accounts_userprofile",
        "id, professional_title, specialization, experience, education, bio, user_id",
        is_null_col="embedding",
    )
    skills_map = get_skills_map("accounts_userprofile_skills", "userprofile_id") if rows else {}
    return _embed_rows(rows, _build_text_for_profile, skills_map, "accounts_userprofile", "profiles")


# ── Pipeline ─────────────────────────────────────────────────
def run_embedding_pipeline() -> Dict:
    """Generate embeddings for every item that is missing one.

    Returns a dict mapping entity type → list of newly embedded IDs.
    """
    result = {
        "new_jobs": embed_new_jobs(),
        "new_projects": embed_new_projects(),
        "new_cvs": embed_new_cvs(),
        "new_profiles": embed_new_profiles(),
    }

    total = sum(len(v) for v in result.values())
    logger.info(f"[EMBEDDING] Pipeline done — {total} new embeddings")
    return result
