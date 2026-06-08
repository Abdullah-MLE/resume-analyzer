"""
Matching Service
================
Computes cosine-similarity scores between opportunity embeddings and
user embeddings, then stores the results in ``matching_matchresult``.

Flow (called after every scraping cycle):
1. ``run_embedding_pipeline()`` fills in missing embeddings.
2. Match newly embedded **jobs** → all base **CVs**.
3. Match newly embedded **projects** → all user **profiles**.
4. Match newly embedded **CVs** → all existing **jobs**.
5. Match newly embedded **profiles** → all existing **projects**.
"""

import json
import numpy as np
from typing import List, Dict, Set, Tuple
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger("matching")


# ── Helpers ──────────────────────────────────────────────────
def _parse_embedding(raw) -> List[float]:
    """Supabase/pgvector may return the vector as a string or a list."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    return []


def _batch_cosine_similarity(
    embeddings_a: List[List[float]],
    embeddings_b: List[List[float]],
) -> np.ndarray:
    """Return a (len_a × len_b) matrix of cosine similarities (float32)."""
    a = np.array(embeddings_a, dtype=np.float32)
    b = np.array(embeddings_b, dtype=np.float32)

    a_norms = np.linalg.norm(a, axis=1, keepdims=True)
    b_norms = np.linalg.norm(b, axis=1, keepdims=True)
    a_norms = np.maximum(a_norms, 1e-8)
    b_norms = np.maximum(b_norms, 1e-8)

    return np.dot(a / a_norms, (b / b_norms).T)


def _generate_ai_tip(score_pct: float, matched: List[str], missing: List[str]) -> str:
    pct = int(score_pct)
    if pct >= 80:
        return f"Excellent match ({pct}%)! Your profile is highly compatible."
    elif pct >= 60:
        tip = f"Good match ({pct}%). "
        if missing:
            tip += f"Consider adding: {', '.join(missing[:5])}"
        return tip
    elif pct >= 40:
        tip = f"Moderate match ({pct}%). "
        if missing:
            tip += f"You may need: {', '.join(missing[:5])}"
        return tip
    else:
        tip = f"Low match ({pct}%). "
        if missing:
            tip += f"Key missing skills: {', '.join(missing[:5])}"
        return tip


def _get_existing_match_keys() -> Set[Tuple]:
    """Return set of (user_id, job_id, project_id) already stored."""
    from app.services.db_services import fetch_all
    try:
        data = fetch_all("matching_matchresult", "user_id, job_id, project_id")
        return {
            (r["user_id"], r.get("job_id"), r.get("project_id"))
            for r in data
        }
    except Exception as e:
        logger.error(f"[Matching] Error loading existing match keys: {e}")
        return set()


def _save_results_batch(results: List[Dict]) -> int:
    """Insert match results in chunks. Returns saved count."""
    from app.services.db_services import get_supabase
    supabase = get_supabase()
    if not supabase or not results:
        return 0

    saved = 0
    CHUNK = 100
    for i in range(0, len(results), CHUNK):
        chunk = results[i : i + CHUNK]
        try:
            supabase.table("matching_matchresult").insert(chunk).execute()
            saved += len(chunk)
        except Exception as e:
            logger.warning(f"[Matching] Batch insert failed ({e}), falling back to one-by-one ...")
            for record in chunk:
                try:
                    supabase.table("matching_matchresult").insert(record).execute()
                    saved += 1
                except Exception as inner:
                    logger.error(f"[Matching] Single insert failed: {inner}")
    return saved


# ── Core matching functions ──────────────────────────────────
def _match_opportunities_to_users(
    *,
    opp_rows: List[Dict],
    user_rows: List[Dict],
    opp_skills_map: Dict,
    user_skills_map: Dict,
    opp_id_field: str,       # "job_id" or "project_id"
    opp_skill_key: str,      # key in opp_rows to look up in skills_map (usually "id")
    user_skill_key: str,     # key in user_rows to look up in skills_map (usually "id")
    existing_keys: Set[Tuple],
    label: str,
) -> int:
    """Generic matcher: compute similarity matrix, build results, save."""
    if not opp_rows or not user_rows:
        return 0

    logger.info(f"[Matching] {label}: {len(opp_rows)} opportunities × {len(user_rows)} users ...")

    opp_embs = [_parse_embedding(r["embedding"]) for r in opp_rows]
    usr_embs = [_parse_embedding(r["embedding"]) for r in user_rows]

    sim = _batch_cosine_similarity(opp_embs, usr_embs)

    now_iso = datetime.now().isoformat()
    results: List[Dict] = []

    for i, opp in enumerate(opp_rows):
        for j, usr in enumerate(user_rows):
            # Build the unique key for dedup
            if opp_id_field == "job_id":
                key = (usr["user_id"], opp["id"], None)
            else:
                key = (usr["user_id"], None, opp["id"])

            if key in existing_keys:
                continue

            score = float(np.clip(sim[i][j], 0.0, 1.0))
            score_pct = round(score * 100, 2)

            o_skills = set(opp_skills_map.get(opp["id"], []))
            u_skills = set(user_skills_map.get(usr[user_skill_key], []))
            matched = sorted(o_skills & u_skills)
            missing = sorted(o_skills - u_skills)

            record = {
                "user_id": usr["user_id"],
                "job_id": opp["id"] if opp_id_field == "job_id" else None,
                "project_id": opp["id"] if opp_id_field == "project_id" else None,
                "match_score": score_pct,
                "matched_skills": matched,
                "missing_skills": missing,
                "ai_tips": _generate_ai_tip(score_pct, matched, missing),
                "created_at": now_iso,
            }
            results.append(record)
            existing_keys.add(key)  # prevent duplicates within the same batch

    saved = _save_results_batch(results)
    logger.info(f"[Matching] {label}: saved {saved} new match results.")
    return saved


def match_jobs_to_cvs(job_ids: List[int] = None) -> int:
    """Match (optionally specific) jobs → all base CVs with embeddings."""
    from app.services.db_services import fetch_all, fetch_by_ids, get_skills_map

    if job_ids:
        jobs = fetch_by_ids("opportunities_job", "id, embedding", job_ids, not_null_col="embedding")
    else:
        jobs = fetch_all("opportunities_job", "id, embedding", not_null_col="embedding")

    cvs = fetch_all(
        "documents_cv", "id, user_id, embedding",
        not_null_col="embedding", eq_filters={"is_base": True},
    )
    if not jobs or not cvs:
        logger.info("[Matching] Skipping jobs→CVs (no data).")
        return 0

    existing = _get_existing_match_keys()
    job_skills = get_skills_map("opportunities_job_required_skills", "job_id")
    cv_skills = get_skills_map("documents_cv_skills", "cv_id")

    return _match_opportunities_to_users(
        opp_rows=jobs,
        user_rows=cvs,
        opp_skills_map=job_skills,
        user_skills_map=cv_skills,
        opp_id_field="job_id",
        opp_skill_key="id",
        user_skill_key="id",
        existing_keys=existing,
        label="Jobs → CVs",
    )


def match_projects_to_profiles(project_ids: List[int] = None) -> int:
    """Match (optionally specific) projects → all user profiles with embeddings."""
    from app.services.db_services import fetch_all, fetch_by_ids, get_skills_map

    if project_ids:
        projects = fetch_by_ids(
            "opportunities_freelanceproject", "id, embedding",
            project_ids, not_null_col="embedding",
        )
    else:
        projects = fetch_all(
            "opportunities_freelanceproject", "id, embedding",
            not_null_col="embedding",
        )

    profiles = fetch_all("accounts_userprofile", "id, user_id, embedding", not_null_col="embedding")
    if not projects or not profiles:
        logger.info("[Matching] Skipping projects→profiles (no data).")
        return 0

    existing = _get_existing_match_keys()
    proj_skills = get_skills_map("opportunities_freelanceproject_required_skills", "freelanceproject_id")
    prof_skills = get_skills_map("accounts_userprofile_skills", "userprofile_id")

    return _match_opportunities_to_users(
        opp_rows=projects,
        user_rows=profiles,
        opp_skills_map=proj_skills,
        user_skills_map=prof_skills,
        opp_id_field="project_id",
        opp_skill_key="id",
        user_skill_key="id",
        existing_keys=existing,
        label="Projects → Profiles",
    )


def match_cvs_to_all_jobs(cv_ids: List[int]) -> int:
    """Match newly embedded CVs → all existing jobs (reverse direction)."""
    from app.services.db_services import fetch_all, fetch_by_ids, get_skills_map

    if not cv_ids:
        return 0

    cvs = fetch_by_ids("documents_cv", "id, user_id, embedding", cv_ids, not_null_col="embedding")
    jobs = fetch_all("opportunities_job", "id, embedding", not_null_col="embedding")

    if not cvs or not jobs:
        logger.info("[Matching] Skipping CVs→jobs (no data).")
        return 0

    existing = _get_existing_match_keys()
    job_skills = get_skills_map("opportunities_job_required_skills", "job_id")
    cv_skills = get_skills_map("documents_cv_skills", "cv_id")

    # Swap roles: jobs are "opportunities", CVs are "users"
    return _match_opportunities_to_users(
        opp_rows=jobs,
        user_rows=cvs,
        opp_skills_map=job_skills,
        user_skills_map=cv_skills,
        opp_id_field="job_id",
        opp_skill_key="id",
        user_skill_key="id",
        existing_keys=existing,
        label="New CVs → All Jobs",
    )


def match_profiles_to_all_projects(profile_ids: List[int]) -> int:
    """Match newly embedded profiles → all existing projects (reverse direction)."""
    from app.services.db_services import fetch_all, fetch_by_ids, get_skills_map

    if not profile_ids:
        return 0

    profiles = fetch_by_ids(
        "accounts_userprofile", "id, user_id, embedding",
        profile_ids, not_null_col="embedding",
    )
    projects = fetch_all(
        "opportunities_freelanceproject", "id, embedding",
        not_null_col="embedding",
    )

    if not profiles or not projects:
        logger.info("[Matching] Skipping profiles→projects (no data).")
        return 0

    existing = _get_existing_match_keys()
    proj_skills = get_skills_map("opportunities_freelanceproject_required_skills", "freelanceproject_id")
    prof_skills = get_skills_map("accounts_userprofile_skills", "userprofile_id")

    return _match_opportunities_to_users(
        opp_rows=projects,
        user_rows=profiles,
        opp_skills_map=proj_skills,
        user_skills_map=prof_skills,
        opp_id_field="project_id",
        opp_skill_key="id",
        user_skill_key="id",
        existing_keys=existing,
        label="New Profiles → All Projects",
    )


# ── Pipeline ─────────────────────────────────────────────────
def run_matching_pipeline() -> Dict:
    """Full pipeline: embed everything missing → compute all new matches.

    Called by the scheduler after every scraping cycle.
    """
    logger.info("=" * 60)
    logger.info("[Matching Pipeline] Starting full embedding + matching pipeline ...")

    from app.services.embedding_service import run_embedding_pipeline
    emb = run_embedding_pipeline()

    new_job_ids = emb["new_jobs"]
    new_project_ids = emb["new_projects"]
    new_cv_ids = emb["new_cvs"]
    new_profile_ids = emb["new_profiles"]

    total = 0

    # New jobs → all CVs
    if new_job_ids:
        total += match_jobs_to_cvs(new_job_ids)

    # New projects → all profiles
    if new_project_ids:
        total += match_projects_to_profiles(new_project_ids)

    # New CVs → all jobs
    if new_cv_ids:
        total += match_cvs_to_all_jobs(new_cv_ids)

    # New profiles → all projects
    if new_profile_ids:
        total += match_profiles_to_all_projects(new_profile_ids)

    summary = {
        "embeddings": {
            "jobs": len(new_job_ids),
            "projects": len(new_project_ids),
            "cvs": len(new_cv_ids),
            "profiles": len(new_profile_ids),
        },
        "total_new_matches": total,
    }

    logger.info(f"[Matching Pipeline] Done — {total} new matches created.")
    logger.info(f"[Matching Pipeline] Summary: {summary}")
    logger.info("=" * 60)
    return summary
