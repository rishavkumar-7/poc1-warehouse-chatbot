"""
NOTE: `from google.adk import Agent` and the exact Agent(...) constructor kwargs
depend on the installed google-adk version. Verify the import path and constructor
signature against `pip show google-adk` / the ADK docs before running — the ADK API
surface has changed across releases. The registration pattern below (collect plain
Python functions, pass them as `tools=`) is the stable part of this design.
"""
from config import settings
from agent.prompts import SYSTEM_INSTRUCTION

from tools.order_tools import get_pending_orders
from tools.picker_tools import get_picker_location_and_task, get_idle_users
from tools.shipment_tools import get_shipment_status
from tools.tote_tools import get_tote_requirements
from estimation.pd_estimate import estimate_pd_completion
from estimation.spd_cutoff import estimate_spd_fedex_cutoff

# Use cases 1-4 -> retrieval tools; use cases 5-6 -> estimation engine.
ALL_TOOLS = [
    get_pending_orders,
    get_picker_location_and_task,
    get_idle_users,
    get_shipment_status,
    get_tote_requirements,
    estimate_pd_completion,
    estimate_spd_fedex_cutoff,
]


def build_agent():
    """
    Input:  none (reads GEMINI_MODEL_NAME from config.settings).
    Does:   instantiates the ADK Agent with the system instruction and the full
            tool list above.
    Output: a configured Agent instance. Built once at API startup and reused
            across requests (see api/main.py).
    """
    from google.adk import Agent  # deferred import: only required once ADK is installed

    return Agent(
        name="warehouse_operations_assistant",
        model=settings.GEMINI_MODEL_NAME,
        instruction=SYSTEM_INSTRUCTION,
        tools=ALL_TOOLS,
    )

APP_NAME = "warehouse_ops_assistant"


def build_runner():
    from google.adk.runners import InMemoryRunner

    agent = build_agent()
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    return runner, APP_NAME