"""
Automated check behind the "documented lineage for every answer" exit criterion.
Every function in tools/ and estimation/ must return the Section 0 envelope.
"""
from tools.order_tools import get_pending_orders
from tools.picker_tools import get_picker_location_and_task, get_idle_users
from tools.shipment_tools import get_shipment_status
from tools.tote_tools import get_tote_requirements
from estimation.pd_estimate import estimate_pd_completion
from estimation.spd_cutoff import estimate_spd_fedex_cutoff

FUNCS_WITH_ARGS = [
    (get_pending_orders, ("SHP789",)),
    (get_picker_location_and_task, ("U123",)),
    (get_idle_users, ()),
    (get_shipment_status, ("SHP789",)),
    (get_tote_requirements, ("SHP789",)),
    (estimate_pd_completion, ("SHP789",)),
    (estimate_spd_fedex_cutoff, ("SHP800",)),
]


def test_every_result_has_lineage_envelope():
    for func, args in FUNCS_WITH_ARGS:
        result = func(*args)
        assert "answer" in result, f"{func.__name__} missing 'answer'"
        assert "lineage" in result, f"{func.__name__} missing 'lineage'"
        assert result["lineage"]["source"], f"{func.__name__} has empty lineage source"
        assert result["lineage"]["type"] in ("query", "calculation"), (
            f"{func.__name__} has invalid lineage type"
        )
        assert result["lineage"]["detail"], f"{func.__name__} has empty lineage detail"
        assert result["lineage"]["generated_at"], f"{func.__name__} missing timestamp"
