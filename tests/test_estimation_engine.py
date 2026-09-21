from estimation.pd_estimate import estimate_pd_completion
from estimation.spd_cutoff import estimate_spd_fedex_cutoff


def test_estimate_pd_completion_produces_eta_when_throughput_exists():
    result = estimate_pd_completion("SHP789")
    answer = result["answer"]
    assert answer["remaining_tasks"] == 1
    assert answer["throughput_per_minute"] > 0
    assert answer["estimated_completion_time"] is not None
    assert result["lineage"]["type"] == "calculation"


def test_estimate_spd_fedex_cutoff_returns_a_valid_risk_label():
    result = estimate_spd_fedex_cutoff("SHP800")
    assert result["answer"]["risk"] in ("on_track", "at_risk", "will_miss", "unknown")
    assert "cutoff_time" in result["answer"]
