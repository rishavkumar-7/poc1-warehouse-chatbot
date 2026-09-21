"""
Deliberately trivial. This module must never be the source of a wrong answer —
only of missing/incomplete attribution. Every tools/*.py and estimation/*.py
function ends by calling wrap() before returning.
"""
from datetime import datetime, timezone


def wrap(answer, lineage_type: str, source: str, detail: str) -> dict:
    """
    Input:  answer (any) - the actual value to return to the caller
            lineage_type (str) - "query" or "calculation"
            source (str) - table name(s) or formula name
            detail (str) - the exact SQL run, or formula + inputs used
    Output: the standard envelope dict, see Section 0 of the technical spec.
    """
    return {
        "answer": answer,
        "lineage": {
            "type": lineage_type,
            "source": source,
            "detail": detail,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
