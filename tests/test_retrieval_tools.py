from tools.order_tools import get_pending_orders
from tools.picker_tools import get_picker_location_and_task, get_idle_users
from tools.shipment_tools import get_shipment_status
from tools.tote_tools import get_tote_requirements


def test_get_pending_orders_for_shipment():
    result = get_pending_orders("SHP789")
    assert result["answer"]["total_pending"] == 2
    assert result["answer"]["by_priority"]["high"] == 1
    assert result["lineage"]["source"] == "orders"


def test_get_picker_location_and_task_active_user():
    result = get_picker_location_and_task("U123")
    assert result["answer"]["current_zone"] == "Zone-A"
    assert result["answer"]["task_id"] == "T1"
    assert result["answer"]["task_status"] == "pending"


def test_get_picker_location_and_task_idle_user():
    result = get_picker_location_and_task("U124")
    assert result["answer"]["status"] == "idle"


def test_get_picker_location_and_task_unknown_user():
    result = get_picker_location_and_task("U999")
    assert result["answer"]["found"] is False


def test_get_idle_users():
    result = get_idle_users()
    idle_ids = [u["user_id"] for u in result["answer"]["idle_users"]]
    assert "U124" in idle_ids
    assert "U123" not in idle_ids


def test_get_shipment_status():
    result = get_shipment_status("SHP789")
    assert result["answer"]["order_counts"]["pending"] == 2
    assert result["answer"]["order_counts"]["processed"] == 1
    assert result["answer"]["tote_counts"]["required"] == 2
    assert result["answer"]["active_tasks"] == 1


def test_get_shipment_status_unknown_shipment():
    result = get_shipment_status("SHP_DOES_NOT_EXIST")
    assert result["answer"]["found"] is False


def test_get_tote_requirements():
    result = get_tote_requirements("SHP789")
    assert result["answer"]["total_needed"] == 3
    assert result["answer"]["completed"] == 1
    assert result["answer"]["remaining"] == 2