from db.connector import run_query
from lineage.lineage import wrap


def get_picker_location_and_task(user_id: str) -> dict:
    """
    Use case 2: Picker location and current task.

    Input:  user_id (str), required.
    Does:   left-joins `users` to `tasks` on current_task_id = task_id.
    Output: {"user_id", "current_zone", "task_id", "task_status"}
            or {"user_id", "status": "idle", "current_zone"} if current_task_id is NULL
            or {"user_id", "found": False} if the user doesn't exist.
    """
    sql = """
        SELECT u.user_id AS user_id, u.current_zone AS current_zone,
               u.current_task_id AS current_task_id, t.status AS task_status
        FROM users u
        LEFT JOIN tasks t ON u.current_task_id = t.task_id
        WHERE u.user_id = :user_id
    """
    rows = run_query(sql, {"user_id": user_id})
    detail = sql.strip() + f" | user_id={user_id}"

    if not rows:
        return wrap({"user_id": user_id, "found": False}, "query", "users JOIN tasks", detail)

    row = rows[0]
    if row["current_task_id"] is None:
        answer = {"user_id": row["user_id"], "status": "idle", "current_zone": row["current_zone"]}
    else:
        answer = {
            "user_id": row["user_id"],
            "current_zone": row["current_zone"],
            "task_id": row["current_task_id"],
            "task_status": row["task_status"],
        }
    return wrap(answer, "query", "users JOIN tasks", detail)


def get_idle_users() -> dict:
    """
    Supports the "is any user out of tasks?" check from the original brief.

    Input:  none.
    Does:   queries `users` where status='idle' or current_task_id IS NULL.
    Output: {"idle_users": [{"user_id": ..., "name": ...}, ...]}
    """
    sql = "SELECT user_id, name FROM users WHERE status = 'idle' OR current_task_id IS NULL"
    rows = run_query(sql)
    return wrap({"idle_users": rows}, "query", "users", sql)
