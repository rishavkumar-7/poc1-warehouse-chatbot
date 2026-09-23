"""
Regenerates db/seed_data.sql itself - same file, same format, same load
command you already use (`envsubst < db/seed_data.sql | bq query ...`).
No new files, no new commands.

Keeps the original known rows (SHP789, SHP800, U123, U124, etc.) exactly as
they were, since tests/manual_test_questions.md references them by name.
Adds ~4,000 additional synthetic rows on top for realistic demo volume.

Usage:
    python3 db/generate_demo_data.py [--seed N]
Then load it exactly like before:
    envsubst < db/seed_data.sql | bq query --use_legacy_sql=false
"""
import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT_FILE = Path(__file__).parent / "seed_data.sql"

FIRST_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
    "Avery", "Quinn", "Drew", "Reese", "Skyler", "Rowan", "Emerson", "Dakota",
]
LAST_NAMES = [
    "Rivera", "Chen", "Patel", "Kim", "Garcia", "Nguyen", "Muller", "Rossi",
    "Silva", "Andersen", "Costa", "Santos", "Novak", "Haddad", "Tanaka",
]
ZONES = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"]
WORKSTREAMS = ["wave1", "wave2", "wave3", "wave4"]
TASK_TYPES = ["pick", "pack", "stage"]

N_EXTRA_USERS = 58          # + the 2 originals = 60
N_EXTRA_SHIPMENTS = 148     # + the 2 originals = 150
ORDERS_PER_SHIPMENT = (5, 20)
TASKS_PER_SHIPMENT = (5, 15)
TOTES_PER_SHIPMENT = (1, 8)


def now():
    return datetime.now(timezone.utc)


def ts(dt):
    return f"TIMESTAMP('{dt.strftime('%Y-%m-%d %H:%M:%S')} UTC')" if dt else "NULL"


def s(val):
    return f"'{val}'" if val is not None else "NULL"


def b(val):
    return "TRUE" if val else "FALSE"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    lines = []
    lines.append("-- Mock data exercising all 6 in-scope use cases.")
    lines.append("-- The first block below is the ORIGINAL known dataset - SHP789, SHP800, U123,")
    lines.append("-- U124 - kept exactly as-is because tests/manual_test_questions.md references")
    lines.append("-- these specific IDs. Everything after that is bulk synthetic data for demo scale.")
    lines.append("-- Regenerate with: python3 db/generate_demo_data.py [--seed N]")
    lines.append("")

    lines.append("INSERT INTO `${project}.${dataset}.users` (user_id, name, current_zone, current_task_id, status) VALUES")
    lines.append("('U123', 'Alex Rivera', 'Zone-A', 'T1', 'active'),")
    lines.append("('U124', 'Sam Chen', NULL, NULL, 'idle');")
    lines.append("")
    lines.append("INSERT INTO `${project}.${dataset}.shipments` (shipment_id, ship_type, carrier, cutoff_time, status) VALUES")
    lines.append("('SHP789', 'PD', NULL, TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR), 'in_progress'),")
    lines.append("('SHP800', 'SPD', 'FedEx', TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR), 'in_progress');")
    lines.append("")
    lines.append("INSERT INTO `${project}.${dataset}.orders` (order_id, shipment_id, status, priority, workstream, waved, created_at) VALUES")
    lines.append("('O1', 'SHP789', 'pending', 'high', 'wave1', TRUE, CURRENT_TIMESTAMP()),")
    lines.append("('O2', 'SHP789', 'pending', 'normal', 'wave1', FALSE, CURRENT_TIMESTAMP()),")
    lines.append("('O3', 'SHP789', 'processed', 'normal', 'wave2', TRUE, CURRENT_TIMESTAMP());")
    lines.append("")
    lines.append("INSERT INTO `${project}.${dataset}.tasks` (task_id, shipment_id, user_id, task_type, status, assigned_at, completed_at) VALUES")
    lines.append("('T1', 'SHP789', 'U123', 'pick', 'pending', CURRENT_TIMESTAMP(), NULL),")
    lines.append("('T2', 'SHP789', 'U123', 'pick', 'completed', TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE), TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)),")
    lines.append("('T3', 'SHP800', 'U123', 'pick', 'pending', CURRENT_TIMESTAMP(), NULL),")
    lines.append("('T4', 'SHP800', 'U123', 'pick', 'completed', TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 MINUTE), TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE));")
    lines.append("")
    lines.append("INSERT INTO `${project}.${dataset}.totes` (tote_id, shipment_id, status) VALUES")
    lines.append("('TT1', 'SHP789', 'required'),")
    lines.append("('TT2', 'SHP789', 'completed'),")
    lines.append("('TT3', 'SHP789', 'required');")
    lines.append("")
    lines.append("-- ==================== Bulk synthetic data below ====================")
    lines.append("")

    users = []
    for i in range(1, N_EXTRA_USERS + 1):
        uid = f"U{1000 + i}"
        active = rng.random() < 0.7
        users.append({"id": uid, "zone": rng.choice(ZONES) if active else None,
                       "status": "active" if active else "idle"})
    rows = [f"({s(u['id'])}, {s(rng.choice(FIRST_NAMES) + ' ' + rng.choice(LAST_NAMES))}, "
            f"{s(u['zone'])}, NULL, {s(u['status'])})" for u in users]
    lines.append("INSERT INTO `${project}.${dataset}.users` (user_id, name, current_zone, current_task_id, status) VALUES")
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    shipments = []
    for i in range(1, N_EXTRA_SHIPMENTS + 1):
        sid = f"SHP{10000 + i}"
        shipments.append({"id": sid, "is_spd": rng.random() < 0.3})
    rows = []
    for sh in shipments:
        cutoff = now() + timedelta(hours=rng.uniform(0.5, 6))
        rows.append(
            f"({s(sh['id'])}, {s('SPD' if sh['is_spd'] else 'PD')}, "
            f"{s('FedEx' if sh['is_spd'] else None)}, {ts(cutoff)}, "
            f"{s('in_progress' if rng.random() < 0.85 else 'complete')})"
        )
    lines.append("INSERT INTO `${project}.${dataset}.shipments` (shipment_id, ship_type, carrier, cutoff_time, status) VALUES")
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    order_rows = []
    counter = 1
    for sh in shipments:
        for _ in range(rng.randint(*ORDERS_PER_SHIPMENT)):
            oid = f"O{100000 + counter}"
            counter += 1
            status = "pending" if rng.random() < 0.4 else "processed"
            priority = rng.choices(["high", "normal", "low"], weights=[20, 60, 20])[0]
            order_rows.append(
                f"({s(oid)}, {s(sh['id'])}, {s(status)}, {s(priority)}, "
                f"{s(rng.choice(WORKSTREAMS))}, {b(rng.random() < 0.6)}, CURRENT_TIMESTAMP())"
            )
    for chunk_start in range(0, len(order_rows), 500):
        chunk = order_rows[chunk_start:chunk_start + 500]
        lines.append("INSERT INTO `${project}.${dataset}.orders` (order_id, shipment_id, status, priority, workstream, waved, created_at) VALUES")
        lines.append(",\n".join(chunk) + ";")
        lines.append("")

    task_rows = []
    counter = 1
    user_ids = [u["id"] for u in users]
    for idx, sh in enumerate(shipments):
        scenario = idx % 3
        for _ in range(rng.randint(*TASKS_PER_SHIPMENT)):
            tid = f"T{100000 + counter}"
            counter += 1
            is_completed = rng.random() < 0.65
            if is_completed:
                minutes_ago = (rng.uniform(1, 25) if scenario == 0 else
                               rng.uniform(20, 55) if scenario == 1 else
                               rng.uniform(90, 240))
                completed = now() - timedelta(minutes=minutes_ago)
                status = "completed"
            else:
                completed = None
                status = "pending"
            assigned = now() - timedelta(minutes=rng.uniform(20, 180))
            task_rows.append(
                f"({s(tid)}, {s(sh['id'])}, {s(rng.choice(user_ids))}, "
                f"{s(rng.choice(TASK_TYPES))}, {s(status)}, {ts(assigned)}, {ts(completed)})"
            )
    for chunk_start in range(0, len(task_rows), 500):
        chunk = task_rows[chunk_start:chunk_start + 500]
        lines.append("INSERT INTO `${project}.${dataset}.tasks` (task_id, shipment_id, user_id, task_type, status, assigned_at, completed_at) VALUES")
        lines.append(",\n".join(chunk) + ";")
        lines.append("")

    tote_rows = []
    counter = 1
    for sh in shipments:
        for _ in range(rng.randint(*TOTES_PER_SHIPMENT)):
            ttid = f"TT{10000 + counter}"
            counter += 1
            status = rng.choices(["required", "picked", "completed"], weights=[30, 20, 50])[0]
            tote_rows.append(f"({s(ttid)}, {s(sh['id'])}, {s(status)})")
    for chunk_start in range(0, len(tote_rows), 500):
        chunk = tote_rows[chunk_start:chunk_start + 500]
        lines.append("INSERT INTO `${project}.${dataset}.totes` (tote_id, shipment_id, status) VALUES")
        lines.append(",\n".join(chunk) + ";")
        lines.append("")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {OUT_FILE}")
    print(f"Users: {2 + len(users)}, Shipments: {2 + len(shipments)}, "
          f"Orders: {3 + len(order_rows)}, Tasks: {4 + len(task_rows)}, Totes: {3 + len(tote_rows)}")
    print(f"Total rows: {2 + len(users) + 2 + len(shipments) + 3 + len(order_rows) + 4 + len(task_rows) + 3 + len(tote_rows)}")


if __name__ == "__main__":
    main()