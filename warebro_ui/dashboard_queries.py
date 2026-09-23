"""
Dashboard data layer for WareBro.

DESIGN NOTE: dashboard tiles deliberately do NOT go through the ADK agent /
Gemini. They're deterministic aggregate counts, so routing them through the
LLM would add latency, cost, and a failure point for no benefit. This module
talks to the database the same way tools/*.py does (import run_query from
db.connector — never raw SQLAlchemy here), just without the lineage wrapper,
since a dashboard tile doesn't need a "source" footnote the way a chat
answer does.

The one exception: get_shipments_at_risk() reuses the REAL
estimate_spd_fedex_cutoff() from estimation/spd_cutoff.py directly, so the
dashboard's risk numbers are always identical to what the chatbot itself
would tell you for the same shipment — no second implementation of that
math to drift out of sync.

"Approval" proxy note: the schema (db/schema.sql) has no approval/waved-
review concept beyond orders.waved (BOOL). get_awaiting_wave_count() treats
"pending AND not yet waved" as a stand-in for "waiting for approval" until
a real approval field exists — flagged clearly in the UI, not silently
relabeled.
"""
from datetime import datetime, timedelta, timezone

from db.connector import run_query
from config import settings
from estimation.spd_cutoff import estimate_spd_fedex_cutoff


def get_headline_counts() -> dict:
    """
    Does: 5 small aggregate queries for the top metric row.
    Output: {"idle_pickers", "active_pickers", "pending_shipments",
             "high_priority_pending_orders", "orders_awaiting_wave"}
    """
    def scalar(sql, params=None):
        rows = run_query(sql, params or {})
        return rows[0]["cnt"] if rows else 0

    return {
        "idle_pickers": scalar(
            "SELECT COUNT(*) as cnt FROM users WHERE status = 'idle'"
        ),
        "active_pickers": scalar(
            "SELECT COUNT(*) as cnt FROM users WHERE status = 'active'"
        ),
        "pending_shipments": scalar(
            "SELECT COUNT(*) as cnt FROM shipments WHERE status = 'in_progress'"
        ),
        "high_priority_pending_orders": scalar(
            "SELECT COUNT(*) as cnt FROM orders WHERE status = 'pending' AND priority = 'high'"
        ),
        # Proxy for "waiting for approval" — see module docstring.
        "orders_awaiting_wave": scalar(
            "SELECT COUNT(*) as cnt FROM orders WHERE status = 'pending' AND waved = FALSE"
        ),
    }


def get_pending_orders_by_priority() -> dict:
    """Output: {"high": int, "normal": int, "low": int} — zero-filled."""
    sql = "SELECT priority, COUNT(*) as cnt FROM orders WHERE status = 'pending' GROUP BY priority"
    rows = run_query(sql)
    counts = {"high": 0, "normal": 0, "low": 0}
    for r in rows:
        counts[r["priority"]] = r["cnt"]
    return counts


def get_pickers_by_zone() -> dict:
    """Output: {zone_name: active_picker_count} for active, assigned pickers."""
    sql = """
        SELECT current_zone, COUNT(*) as cnt FROM users
        WHERE status = 'active' AND current_zone IS NOT NULL
        GROUP BY current_zone
        ORDER BY current_zone
    """
    rows = run_query(sql)
    return {r["current_zone"]: r["cnt"] for r in rows}


def get_tote_status_breakdown() -> dict:
    """Output: {"required": int, "picked": int, "completed": int} across ALL shipments."""
    sql = "SELECT status, COUNT(*) as cnt FROM totes GROUP BY status"
    rows = run_query(sql)
    counts = {"required": 0, "picked": 0, "completed": 0}
    for r in rows:
        if r["status"] in counts:
            counts[r["status"]] = r["cnt"]
    return counts


def get_recent_throughput_overall(window_minutes: int = None) -> dict:
    """
    Does: counts ALL tasks completed warehouse-wide within the trailing window
    (same window config as estimation/throughput.py, just not scoped to one
    shipment).
    Output: {"completed_count": int, "window_minutes": int, "tasks_per_minute": float}
    """
    window_minutes = window_minutes or settings.THROUGHPUT_WINDOW_MINUTES
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    sql = "SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed' AND completed_at >= :cutoff"
    rows = run_query(sql, {"cutoff": cutoff})
    completed = rows[0]["cnt"] if rows else 0
    return {
        "completed_count": completed,
        "window_minutes": window_minutes,
        "tasks_per_minute": round(completed / window_minutes, 3) if window_minutes else 0.0,
    }


def get_shipments_at_risk(limit: int = 15) -> list[dict]:
    """
    Does: finds in-progress SPD/FedEx shipments, then runs the REAL
    estimate_spd_fedex_cutoff() from the estimation engine on each — same
    function the chatbot itself calls, so these numbers can never disagree
    with what a user gets by asking the chat directly.

    Input:  limit (int) — cap on how many shipments to evaluate, since this
            runs one query per shipment and isn't meant for hundreds at once
            on a dashboard refresh.
    Output: list of {"shipment_id", "risk", "estimated_completion_time",
             "cutoff_time"} — sorted so will_miss/at_risk surface first.
    """
    sql = """
        SELECT shipment_id FROM shipments
        WHERE ship_type = 'SPD' AND carrier = 'FedEx' AND status = 'in_progress'
        LIMIT :limit
    """
    rows = run_query(sql, {"limit": limit})

    RISK_ORDER = {"will_miss": 0, "at_risk": 1, "unknown": 2, "on_track": 3}
    results = []
    for r in rows:
        est = estimate_spd_fedex_cutoff(r["shipment_id"])
        answer = est["answer"]
        results.append({
            "shipment_id": r["shipment_id"],
            "risk": answer.get("risk", "unknown"),
            "estimated_completion_time": answer.get("estimated_completion_time"),
            "cutoff_time": answer.get("cutoff_time"),
        })
    results.sort(key=lambda x: RISK_ORDER.get(x["risk"], 9))
    return results


def get_all_dashboard_data(risk_limit: int = 15) -> dict:
    """Single entry point the UI calls once per refresh — bundles every panel's data."""
    return {
        "headline": get_headline_counts(),
        "orders_by_priority": get_pending_orders_by_priority(),
        "pickers_by_zone": get_pickers_by_zone(),
        "tote_status": get_tote_status_breakdown(),
        "throughput": get_recent_throughput_overall(),
        "shipments_at_risk": get_shipments_at_risk(limit=risk_limit),
        "generated_at": datetime.now(timezone.utc),
    }