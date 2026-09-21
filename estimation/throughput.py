from datetime import datetime, timedelta
from db.connector import run_query
from config import settings


def get_recent_throughput(shipment_id: str, window_minutes: int = None) -> float:
    """
    Internal input to the estimation functions — NOT user-facing, so it returns a
    plain float rather than a lineage-wrapped envelope.

    Input:  shipment_id (str), window_minutes (int, optional, defaults to
            config.settings.THROUGHPUT_WINDOW_MINUTES).
    Does:   counts `tasks` completed for this shipment within the trailing window.
    Output: tasks completed per minute (float). Returns 0.0 if nothing completed
            in the window (caller must handle this — see estimation/pd_estimate.py).
    """
    window_minutes = window_minutes or settings.THROUGHPUT_WINDOW_MINUTES
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    sql = """
        SELECT COUNT(*) as cnt FROM tasks
        WHERE shipment_id = :shipment_id
          AND status = 'completed'
          AND completed_at >= :cutoff
    """
    # Pass a native datetime, not a formatted string, so the DBAPI driver applies
    # the same conversion it used when the column values were inserted.
    rows = run_query(sql, {"shipment_id": shipment_id, "cutoff": cutoff})
    completed_count = rows[0]["cnt"] if rows else 0

    return completed_count / window_minutes if window_minutes else 0.0
