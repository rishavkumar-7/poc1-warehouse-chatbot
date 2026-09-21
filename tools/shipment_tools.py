from db.connector import run_query
from lineage.lineage import wrap


def get_shipment_status(shipment_id: str) -> dict:
    """
    Use case 3: Shipment status.

    Input:  shipment_id (str), required.
    Does:   pulls the shipment row, then counts orders by status, totes by status,
            and pending tasks, as three separate grouped queries.
    Output: {"shipment_id", "ship_type", "carrier", "status",
             "order_counts": {...}, "tote_counts": {...}, "active_tasks": int}
    """
    shipment_sql = (
        "SELECT shipment_id, ship_type, carrier, status FROM shipments "
        "WHERE shipment_id = :shipment_id"
    )
    shipment_rows = run_query(shipment_sql, {"shipment_id": shipment_id})
    if not shipment_rows:
        return wrap(
            {"shipment_id": shipment_id, "found": False},
            "query",
            "shipments",
            shipment_sql,
        )
    shipment = shipment_rows[0]

    order_sql = (
        "SELECT status, COUNT(*) as cnt FROM orders "
        "WHERE shipment_id = :shipment_id GROUP BY status"
    )
    order_rows = run_query(order_sql, {"shipment_id": shipment_id})
    order_counts = {r["status"]: r["cnt"] for r in order_rows}

    tote_sql = (
        "SELECT status, COUNT(*) as cnt FROM totes "
        "WHERE shipment_id = :shipment_id GROUP BY status"
    )
    tote_rows = run_query(tote_sql, {"shipment_id": shipment_id})
    tote_counts = {r["status"]: r["cnt"] for r in tote_rows}

    active_task_sql = (
        "SELECT COUNT(*) as cnt FROM tasks "
        "WHERE shipment_id = :shipment_id AND status = 'pending'"
    )
    active_tasks_rows = run_query(active_task_sql, {"shipment_id": shipment_id})
    active_tasks = active_tasks_rows[0]["cnt"] if active_tasks_rows else 0

    answer = {
        "shipment_id": shipment["shipment_id"],
        "ship_type": shipment["ship_type"],
        "carrier": shipment["carrier"],
        "status": shipment["status"],
        "order_counts": order_counts,
        "tote_counts": tote_counts,
        "active_tasks": active_tasks,
    }
    detail = f"{shipment_sql} | {order_sql} | {tote_sql} | {active_task_sql} | shipment_id={shipment_id}"
    return wrap(answer, "query", "shipments, orders, totes, tasks", detail)
