from datetime import datetime, timedelta, timezone
from db.connector import run_query
from estimation.throughput import get_recent_throughput
from lineage.lineage import wrap


def _remaining_pending_tasks(shipment_id: str) -> int:
    sql = "SELECT COUNT(*) as cnt FROM tasks WHERE shipment_id = :shipment_id AND status = 'pending'"
    rows = run_query(sql, {"shipment_id": shipment_id})
    return rows[0]["cnt"] if rows else 0


def estimate_pd_completion(shipment_id: str) -> dict:
    """
    Use case 5: PD shipment completion estimate.

    Input:  shipment_id (str), required; expected to have ship_type = 'PD'.
    Does:   remaining pending tasks / recent throughput = minutes remaining;
            converts that into an absolute ETA timestamp.
    Output: {"estimated_completion_time": ISO str or None,
             "remaining_tasks": int, "throughput_per_minute": float}
            If throughput is 0 (no recent completions), returns a null estimate
            with a "reason" instead of raising a divide-by-zero error.
    """
    remaining = _remaining_pending_tasks(shipment_id)
    throughput = get_recent_throughput(shipment_id)

    if throughput == 0:
        answer = {
            "estimated_completion_time": None,
            "remaining_tasks": remaining,
            "throughput_per_minute": 0.0,
            "reason": "no recent activity",
        }
        detail = f"remaining={remaining}, throughput=0 -> cannot estimate"
    else:
        minutes_remaining = remaining / throughput
        eta = datetime.now(timezone.utc) + timedelta(minutes=minutes_remaining)
        answer = {
            "estimated_completion_time": eta.isoformat(),
            "remaining_tasks": remaining,
            "throughput_per_minute": round(throughput, 3),
        }
        detail = (
            f"{remaining} remaining / {round(throughput, 3)} tasks-per-min "
            f"= {round(minutes_remaining, 1)} min -> ETA {eta.isoformat()}"
        )

    return wrap(answer, "calculation", "tasks (remaining) + throughput", detail)
