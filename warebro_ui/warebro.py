"""
WareBro — "the brother who answers your warehouse queries."

Third UI, fully isolated from:
  - the ADK dev console (`adk web`)
  - the existing simple chat UI (ui/streamlit_app.py)

Run from the repo root (same convention as the other two — so `db`, `config`,
`estimation` etc. are importable):

    streamlit run warebro_ui/warebro_app.py --server.port 8502

Left side: a live operations dashboard, queried directly from the DB
(no LLM in the loop — see dashboard_queries.py for why).
Right side: the same chatbot experience as ui/streamlit_app.py, calling the
same /chat API endpoint — nothing about the agent/backend changes.

If this file breaks, the other two UIs are completely unaffected — this
folder doesn't touch ui/streamlit_app.py, api/, or agent/ at all.

------------------------------------------------------------------------
IMPORTANT DESIGN NOTE — why chat runs in a two-phase "processing" state:
------------------------------------------------------------------------
The dashboard auto-refreshes by having the browser fire a rerun signal on
a timer. A Streamlit rerun CANCELS whatever script execution is currently
in progress for that session — including a blocking `requests.post()` to
the chat API. A multi-step question (one that makes the agent chain
several tool calls) can easily take longer than a single refresh interval,
so without this guard, a long-running chat request could get silently
killed and restarted every single refresh cycle, forever, with no answer
ever reaching the user.

Fix: when the user submits a message, we don't make the network call in
that same run. We flag "a message is pending", rerun once, and on THAT
rerun we skip re-registering the auto-refresh timer entirely and only
then make the (now uninterruptible-by-timer) blocking call. Once it
returns, we clear the flag and resume normal refreshing.
------------------------------------------------------------------------
"""
import os
from datetime import datetime, timezone

import requests
import streamlit as st

from dashboard_queries import get_all_dashboard_data

API_URL = os.getenv("WAREBRO_API_URL", "http://localhost:8000/chat")
# NOTE: the risk panel alone runs 2 BigQuery queries PER shipment (up to
# RISK_PANEL_LIMIT of them), on top of ~9 more for the other tiles — each
# BigQuery query has real network + job-scheduling overhead, so a full
# dashboard pull commonly takes 20-60+ seconds, not milliseconds. Keep this
# comfortably longer than that.
REFRESH_SECONDS = int(os.getenv("WAREBRO_REFRESH_SECONDS", "45"))
RISK_PANEL_LIMIT = int(os.getenv("WAREBRO_RISK_LIMIT", "5"))
# Multi-tool-call questions can legitimately take a while — give the agent
# real room rather than timing out on something that's just still working.
CHAT_TIMEOUT_SECONDS = int(os.getenv("WAREBRO_CHAT_TIMEOUT", "120"))

st.set_page_config(page_title="WareBro", page_icon="📦", layout="wide")

# ---------------------------------------------------------------- styling --
st.markdown("""
<style>
.wb-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; color: white;
}
.wb-on_track  { background-color: #1f9d55; }
.wb-at_risk   { background-color: #d97706; }
.wb-will_miss { background-color: #dc2626; }
.wb-unknown   { background-color: #6b7280; }
.wb-row {
    padding: 8px 12px; border-radius: 8px; margin-bottom: 6px;
    background-color: rgba(127,127,127,0.08);
    border-left: 3px solid rgba(127,127,127,0.25);
}
.wb-card {
    background-color: rgba(127,127,127,0.05);
    border: 1px solid rgba(127,127,127,0.15);
    border-radius: 14px;
    padding: 18px 20px 8px 20px;
    margin-bottom: 18px;
}
.wb-card h3 { margin-top: 0 !important; }
.wb-caption { color: #888; font-size: 0.8rem; }
.wb-thinking {
    display: inline-block; padding: 8px 14px; border-radius: 10px;
    background-color: rgba(59,130,246,0.12); color: #93c5fd;
    font-size: 0.9rem; font-style: italic;
}
</style>
""", unsafe_allow_html=True)

BADGE_LABEL = {
    "on_track": "On Track",
    "at_risk": "At Risk",
    "will_miss": "Will Miss",
    "unknown": "Unknown",
}

# ---------------------------------------------------------- optional deps --
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

CHAT_PENDING_KEY = "wb_chat_pending_prompt"
chat_is_pending = bool(st.session_state.get(CHAT_PENDING_KEY))

# --------------------------------------------------------- auto-refresh ----
# Deliberately skipped while a chat answer is being generated — see the
# module docstring above for why.
autorefresh_active = False
if not chat_is_pending:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=REFRESH_SECONDS * 1000, key="warebro_autorefresh")
        autorefresh_active = True
    except ImportError:
        pass  # falls back to the manual refresh button below

# ------------------------------------------------------------- top bar -----
top_l, top_r = st.columns([5, 1])
with top_l:
    st.title("📦 WareBro")
    st.caption("Your warehouse, at a glance — ask anything on the right.")
with top_r:
    st.write("")
    if chat_is_pending:
        st.markdown("<span class='wb-caption'>⏸️ Refresh paused — WareBro is thinking</span>",
                    unsafe_allow_html=True)
    elif autorefresh_active:
        st.markdown(f"<span class='wb-caption'>🟢 Live · refreshing every {REFRESH_SECONDS}s</span>",
                    unsafe_allow_html=True)
    else:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
        st.markdown(
            "<span class='wb-caption'>Install <code>streamlit-autorefresh</code> "
            "for automatic live updates.</span>", unsafe_allow_html=True,
        )


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def _cached_dashboard_data(risk_limit: int):
    """
    Caches the full (expensive, ~15-30 BigQuery calls) dashboard pull for
    REFRESH_SECONDS, so chat interactions and other reruns don't silently
    redo every query from scratch.
    """
    return get_all_dashboard_data(risk_limit=risk_limit)


# ------------------------------------------------------------ data pull ----
try:
    with st.spinner("Pulling live warehouse data (first load can take a while — "
                     "each tile is a real BigQuery query)..."):
        data = _cached_dashboard_data(risk_limit=RISK_PANEL_LIMIT)
    db_error = None
except Exception as exc:  # noqa: BLE001 — dashboard must never take the chat down with it
    data = None
    db_error = str(exc)

prev = st.session_state.get("wb_prev_headline")

# =============================================================== LAYOUT ====
dash_col, chat_col = st.columns([2, 1], gap="large")

# --------------------------------------------------------------- DASHBOARD -
with dash_col:
    if db_error:
        st.error(f"Dashboard couldn't reach the database directly: {db_error}\n\n"
                 "(The chat panel on the right is unaffected — it goes through "
                 "the API, not this direct connection.)")
    else:
        h = data["headline"]

        st.markdown(f"<span class='wb-caption'>Last updated "
                    f"{data['generated_at'].strftime('%H:%M:%S UTC')}</span>",
                    unsafe_allow_html=True)

        m1, m2, m3, m4, m5 = st.columns(5)
        metric_defs = [
            (m1, "Idle Pickers", "idle_pickers"),
            (m2, "Active Pickers", "active_pickers"),
            (m3, "Pending Shipments", "pending_shipments"),
            (m4, "High-Priority Orders", "high_priority_pending_orders"),
            (m5, "Awaiting Wave", "orders_awaiting_wave"),
        ]
        for col, label, key in metric_defs:
            delta = None
            if prev is not None:
                d = h[key] - prev.get(key, h[key])
                delta = f"{d:+d}" if d != 0 else None
            col.metric(label, h[key], delta=delta)

        st.session_state["wb_prev_headline"] = h

        st.divider()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("<div class='wb-card'><h3>Pending Orders by Priority</h3>", unsafe_allow_html=True)
            op = data["orders_by_priority"]
            if PLOTLY_AVAILABLE:
                order = ["high", "normal", "low"]
                colors = {"high": "#dc2626", "normal": "#3b82f6", "low": "#6b7280"}
                fig = go.Figure(go.Bar(
                    x=[op.get(k, 0) for k in order],
                    y=[k.capitalize() for k in order],
                    orientation="h",
                    marker_color=[colors[k] for k in order],
                    text=[op.get(k, 0) for k in order],
                    textposition="outside",
                ))
                fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                                   xaxis_title=None, yaxis_title=None,
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.bar_chart(op)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='wb-card'><h3>Active Pickers by Zone</h3>", unsafe_allow_html=True)
            pz = data["pickers_by_zone"]
            if not pz:
                st.caption("No active, zone-assigned pickers right now.")
            elif PLOTLY_AVAILABLE:
                fig = go.Figure(go.Bar(
                    x=list(pz.keys()), y=list(pz.values()),
                    marker_color="#38bdf8",
                    text=list(pz.values()), textposition="outside",
                ))
                fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.bar_chart(pz)
            st.markdown("</div>", unsafe_allow_html=True)

        with c3:
            st.markdown("<div class='wb-card'><h3>Tote Status (All Shipments)</h3>", unsafe_allow_html=True)
            ts = data["tote_status"]
            if PLOTLY_AVAILABLE:
                labels = ["Required", "Picked", "Completed"]
                values = [ts.get("required", 0), ts.get("picked", 0), ts.get("completed", 0)]
                fig = go.Figure(go.Pie(
                    labels=labels, values=values, hole=0.55,
                    marker_colors=["#f59e0b", "#3b82f6", "#1f9d55"],
                    textinfo="label+percent",
                ))
                fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                                   showlegend=False,
                                   paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
            else:
                st.bar_chart(ts)
            st.markdown("</div>", unsafe_allow_html=True)

        t1, t2 = st.columns([1, 2])
        with t1:
            st.markdown("<div class='wb-card'><h3>Recent Throughput</h3>", unsafe_allow_html=True)
            tp = data["throughput"]
            if PLOTLY_AVAILABLE:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=tp["tasks_per_minute"],
                    number={"suffix": " /min"},
                    gauge={
                        "axis": {"range": [0, max(1, tp["tasks_per_minute"] * 2, 1)]},
                        "bar": {"color": "#38bdf8"},
                    },
                ))
                fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=10),
                                   paper_bgcolor="rgba(0,0,0,0)",
                                   font={"color": "#ddd"})
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
                st.caption(f"{tp['completed_count']} tasks completed in the last "
                           f"{tp['window_minutes']} min, warehouse-wide")
            else:
                st.metric(f"Tasks completed (last {tp['window_minutes']} min)", tp["completed_count"])
                st.caption(f"≈ {tp['tasks_per_minute']} tasks/minute warehouse-wide")
            st.markdown("</div>", unsafe_allow_html=True)

        with t2:
            st.markdown("<div class='wb-card'><h3>FedEx / SPD Shipments — Cutoff Risk</h3>",
                        unsafe_allow_html=True)
            st.caption("Uses the same estimation logic the chatbot uses — numbers will always match.")
            risk_list = data["shipments_at_risk"]
            if not risk_list:
                st.caption("No in-progress SPD/FedEx shipments found.")
            else:
                for s in risk_list:
                    badge = BADGE_LABEL.get(s["risk"], s["risk"])
                    eta = s["estimated_completion_time"] or "—"
                    st.markdown(
                        f"<div class='wb-row'>"
                        f"<b>{s['shipment_id']}</b> &nbsp; "
                        f"<span class='wb-badge wb-{s['risk']}'>{badge}</span> "
                        f"&nbsp; <span class='wb-caption'>ETA: {eta}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------------------------- CHAT-
with chat_col:
    st.subheader("💬 Ask WareBro")

    if "wb_history" not in st.session_state:
        st.session_state.wb_history = []

    chat_box = st.container(height=520)
    with chat_box:
        for msg in st.session_state.wb_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("lineage"):
                    with st.expander("Source"):
                        st.json(msg["lineage"])

        if chat_is_pending:
            with st.chat_message("assistant"):
                st.markdown("<span class='wb-thinking'>🧠 WareBro is working on it "
                            "— multi-part questions can take a little while...</span>",
                            unsafe_allow_html=True)

    # --- Phase 1: capture the prompt, don't call the API yet ---
    if not chat_is_pending:
        prompt = st.chat_input("Ask about orders, pickers, shipments, or totes...")
        if prompt:
            st.session_state.wb_history.append({"role": "user", "content": prompt})
            st.session_state[CHAT_PENDING_KEY] = prompt
            st.rerun()  # rerun WITHOUT registering auto-refresh, then do the call below
    else:
        st.chat_input("WareBro is thinking — please wait...", disabled=True)

# --- Phase 2: this only runs on the rerun where auto-refresh was skipped ---
if chat_is_pending:
    pending_prompt = st.session_state[CHAT_PENDING_KEY]
    try:
        response = requests.post(API_URL, json={"message": pending_prompt},
                                  timeout=CHAT_TIMEOUT_SECONDS)
        resp_data = response.json()
        st.session_state.wb_history.append({
            "role": "assistant",
            "content": resp_data.get("answer", ""),
            "lineage": resp_data.get("lineage"),
        })
    except requests.RequestException as exc:
        st.session_state.wb_history.append({
            "role": "assistant",
            "content": f"Couldn't reach the chat API: {exc}",
            "lineage": None,
        })
    del st.session_state[CHAT_PENDING_KEY]
    st.rerun()