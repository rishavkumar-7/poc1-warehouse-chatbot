"""
The ONLY file that talks to the database directly.
Every tool/estimation function goes through run_query() here — never raw SQLAlchemy
or google-cloud-bigquery calls anywhere else in the codebase.

Swap path: set DATABASE_URL to point anywhere SQLAlchemy supports (e.g. sqlite for
local tests). Without it, falls back to a BigQuery URI built from config.settings.
"""
import os
from sqlalchemy import create_engine, text

_engine = None  # module-level cache, built once and reused


def _bigquery_uri() -> str:
    from config import settings

    if not settings.GCP_PROJECT_ID:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set and no DATABASE_URL override was provided."
        )
    return f"bigquery://{settings.GCP_PROJECT_ID}/{settings.BQ_DATASET}"


def get_engine():
    """Builds a fresh SQLAlchemy engine. Prefer _get_cached_engine() elsewhere."""
    override = os.getenv("DATABASE_URL")
    if override:
        return create_engine(override)
    return create_engine(_bigquery_uri())


def _get_cached_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def run_query(sql: str, params: dict = None) -> list[dict]:
    """
    Executes a parameterized SQL query and returns a list of row-dicts.

    Input:  sql (str) with :named bind params, params (dict) of bind values.
    Output: list[dict] — one dict per row, column name -> value.
    """
    engine = _get_cached_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]
