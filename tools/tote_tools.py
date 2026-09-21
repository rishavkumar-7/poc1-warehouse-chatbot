from db.connector import run_query
from lineage.lineage import wrap


def get_tote_requirements(shipment_id: str) -> dict:
    """
    Use case 4: Tote requirement lookup.

    Input:  shipment_id (str), required.
    Does:   counts `totes` rows by status for the given shipment.
    Output: {"required": int, "completed": int, "remaining": int}
            required = sum of all tote rows regardless of status;
            remaining = required - completed.
    """
    sql = "SELECT status, COUNT(*) as cnt FROM totes WHERE shipment_id = :shipment_id GROUP BY status"
    rows = run_query(sql, {"shipment_id": shipment_id})
    counts = {r["status"]: r["cnt"] for r in rows}

    required = sum(counts.values())
    completed = counts.get("completed", 0)
    answer = {"required": required, "completed": completed, "remaining": required - completed}

    return wrap(answer, "query", "totes", sql + f" | shipment_id={shipment_id}")
