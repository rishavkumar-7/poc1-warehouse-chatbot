from datetime import datetime, timedelta, timezone
from config import settings
from estimation.pd_estimate import _remaining_pending_tasks
from estimation.throughput import get_recent_throughput
from lineage.lineage import wrap


def _parse_cutoff_today(cutoff_hhmm: str) -> datetime:
    now = datetime.now(timezone.utc)
    hour, minute = map(int, cutoff_hhmm.split(":"))
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def estimate_spd_fedex_cutoff(shipment_id: str) -> dict:
    """
    Use case 6: SPD/FedEx picking completion estimate vs. carrier cutoff.

    Input:  shipment_id (str), required; expected ship_type='SPD', carrier='FedEx'.
    Does:   same remaining-work / throughput calculation as estimate_pd_completion,
            then compares the resulting ETA to config.settings.SPD_FEDEX_CUTOFF_TIME.
    Output: {"estimated_completion_time", "cutoff_time", "risk"}
            risk thresholds (config.settings.AT_RISK_BUFFER_MINUTES, default 30 min):
              on_track  -> ETA is more than the buffer before cutoff
              at_risk   -> ETA is within the buffer of cutoff
              will_miss -> ETA is after cutoff
            NOTE: these thresholds are placeholders pending business sign-off —
            see tests/known_limitations.md.
    """
    remaining = _remaining_pending_tasks(shipment_id)
    throughput = get_recent_throughput(shipment_id)
    cutoff_time = _parse_cutoff_today(settings.SPD_FEDEX_CUTOFF_TIME)

    if throughput == 0:
        answer = {
            "estimated_completion_time": None,
            "cutoff_time": cutoff_time.isoformat(),
            "risk": "unknown",
            "reason": "no recent activity",
        }
        detail = f"remaining={remaining}, throughput=0 -> cannot estimate"
        return wrap(answer, "calculation", "tasks (remaining) + throughput + configured cutoff", detail)

    minutes_remaining = remaining / throughput
    eta = datetime.now(timezone.utc) + timedelta(minutes=minutes_remaining)
    buffer = timedelta(minutes=settings.AT_RISK_BUFFER_MINUTES)

    if eta <= cutoff_time - buffer:
        risk = "on_track"
    elif eta <= cutoff_time:
        risk = "at_risk"
    else:
        risk = "will_miss"

    answer = {
        "estimated_completion_time": eta.isoformat(),
        "cutoff_time": cutoff_time.isoformat(),
        "risk": risk,
    }
    detail = (
        f"ETA {eta.isoformat()} vs cutoff {cutoff_time.isoformat()} "
        f"(buffer={settings.AT_RISK_BUFFER_MINUTES}min) -> {risk}"
    )
    return wrap(answer, "calculation", "tasks (remaining) + throughput + configured cutoff", detail)
