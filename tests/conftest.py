"""
Seeds an in-memory SQLite database that mirrors db/schema.sql + db/seed_data.sql,
so tools/ and estimation/ can be exercised without real BigQuery access.
BigQuery DDL/DML syntax isn't portable to SQLite, so this fixture builds the
equivalent tables programmatically via SQLAlchemy Core instead of running the
.sql files directly.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime, timedelta
import pytest
from sqlalchemy import MetaData, Table, Column, String, Boolean, DateTime, create_engine

import db.connector as connector


@pytest.fixture(scope="session", autouse=True)
def seeded_engine():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    users = Table(
        "users", metadata,
        Column("user_id", String), Column("name", String),
        Column("current_zone", String), Column("current_task_id", String),
        Column("status", String),
    )
    shipments = Table(
        "shipments", metadata,
        Column("shipment_id", String), Column("ship_type", String),
        Column("carrier", String), Column("cutoff_time", DateTime),
        Column("status", String),
    )
    orders = Table(
        "orders", metadata,
        Column("order_id", String), Column("shipment_id", String),
        Column("status", String), Column("priority", String),
        Column("workstream", String), Column("waved", Boolean),
        Column("created_at", DateTime),
    )
    tasks = Table(
        "tasks", metadata,
        Column("task_id", String), Column("shipment_id", String),
        Column("user_id", String), Column("task_type", String),
        Column("status", String), Column("assigned_at", DateTime),
        Column("completed_at", DateTime),
    )
    totes = Table(
        "totes", metadata,
        Column("tote_id", String), Column("shipment_id", String),
        Column("status", String),
    )

    metadata.create_all(engine)

    now = datetime.utcnow()

    with engine.begin() as conn:
        conn.execute(users.insert(), [
            {"user_id": "U123", "name": "Alex Rivera", "current_zone": "Zone-A",
             "current_task_id": "T1", "status": "active"},
            {"user_id": "U124", "name": "Sam Chen", "current_zone": None,
             "current_task_id": None, "status": "idle"},
        ])
        conn.execute(shipments.insert(), [
            {"shipment_id": "SHP789", "ship_type": "PD", "carrier": None,
             "cutoff_time": now + timedelta(hours=4), "status": "in_progress"},
            {"shipment_id": "SHP800", "ship_type": "SPD", "carrier": "FedEx",
             "cutoff_time": now + timedelta(hours=1), "status": "in_progress"},
        ])
        conn.execute(orders.insert(), [
            {"order_id": "O1", "shipment_id": "SHP789", "status": "pending",
             "priority": "high", "workstream": "wave1", "waved": True, "created_at": now},
            {"order_id": "O2", "shipment_id": "SHP789", "status": "pending",
             "priority": "normal", "workstream": "wave1", "waved": False, "created_at": now},
            {"order_id": "O3", "shipment_id": "SHP789", "status": "processed",
             "priority": "normal", "workstream": "wave2", "waved": True, "created_at": now},
        ])
        conn.execute(tasks.insert(), [
            {"task_id": "T1", "shipment_id": "SHP789", "user_id": "U123", "task_type": "pick",
             "status": "pending", "assigned_at": now, "completed_at": None},
            {"task_id": "T2", "shipment_id": "SHP789", "user_id": "U123", "task_type": "pick",
             "status": "completed", "assigned_at": now - timedelta(minutes=30),
             "completed_at": now - timedelta(minutes=10)},
            {"task_id": "T3", "shipment_id": "SHP800", "user_id": "U123", "task_type": "pick",
             "status": "pending", "assigned_at": now, "completed_at": None},
            {"task_id": "T4", "shipment_id": "SHP800", "user_id": "U123", "task_type": "pick",
             "status": "completed", "assigned_at": now - timedelta(minutes=20),
             "completed_at": now - timedelta(minutes=5)},
        ])
        conn.execute(totes.insert(), [
            {"tote_id": "TT1", "shipment_id": "SHP789", "status": "required"},
            {"tote_id": "TT2", "shipment_id": "SHP789", "status": "completed"},
            {"tote_id": "TT3", "shipment_id": "SHP789", "status": "required"},
        ])

    # Inject directly into connector's module-level cache so run_query() uses
    # this exact seeded engine rather than building a new (empty) one.
    connector._engine = engine
    yield engine
