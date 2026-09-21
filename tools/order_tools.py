from db.connector import run_query
from lineage.lineage import wrap


def get_pending_orders(shipment_id: str = None) -> dict:
    """
    Use case 1: Pending orders inquiry.

    Input:  shipment_id (str, optional) - if omitted, reports across all shipments.
    Does:   queries `orders` for status='pending' (and shipment_id if given), then
            groups the results by priority and workstream in Python.
    Output: {"total_pending": int, "by_priority": {...}, "by_workstream": {...}}
    """
    sql = "SELECT order_id, priority, workstream FROM orders WHERE status = 'pending'"
    params = {}
    if shipment_id:
        sql += " AND shipment_id = :shipment_id"
        params["shipment_id"] = shipment_id

    rows = run_query(sql, params)

    by_priority: dict = {}
    by_workstream: dict = {}
    for row in rows:
        by_priority[row["priority"]] = by_priority.get(row["priority"], 0) + 1
        by_workstream[row["workstream"]] = by_workstream.get(row["workstream"], 0) + 1

    answer = {
        "total_pending": len(rows),
        "by_priority": by_priority,
        "by_workstream": by_workstream,
    }
    detail = sql + (f" | shipment_id={shipment_id}" if shipment_id else " | (all shipments)")
    return wrap(answer, "query", "orders", detail)
