from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path

import streamlit as st

from queue_system import QueueManager


STATE_PATH = Path(__file__).with_name("state.json")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def load_manager() -> QueueManager:
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            qm = QueueManager.from_snapshot(data)
        except Exception:
            qm = QueueManager()
    else:
        qm = QueueManager()
    qm.ensure_today(date.today())
    return qm


def save_manager(qm: QueueManager) -> None:
    STATE_PATH.write_text(json.dumps(qm.snapshot(), indent=2), encoding="utf-8")


st.set_page_config(page_title="Queue Prototype", layout="wide")
st.title("Digital Queue Prototype")
st.caption("Two queues (priority + regular), daily reset, no database.")

if "qm" not in st.session_state:
    st.session_state.qm = load_manager()

qm: QueueManager = st.session_state.qm
qm.ensure_today(date.today())

with st.sidebar:
    st.subheader("Settings")
    minutes = st.number_input(
        "Service minutes per customer",
        min_value=1,
        max_value=30,
        value=qm.service_minutes_per_customer,
        step=1,
    )
    if minutes != qm.service_minutes_per_customer:
        # recreate manager with same state but different service time
        snap = qm.snapshot()
        snap["service_minutes"] = int(minutes)
        qm = QueueManager.from_snapshot(snap)
        st.session_state.qm = qm
        save_manager(qm)

    st.divider()
    st.subheader("Admin")
    if st.button("Reset (new day / shop closes)", type="secondary"):
        qm.reset(today=date.today())
        save_manager(qm)
        st.success("Reset complete.")

tab_kiosk, tab_staff, tab_display = st.tabs(["Customer kiosk", "Staff", "Public display"])

with tab_kiosk:
    st.subheader("Draw a ticket")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get REGULAR ticket", type="primary", use_container_width=True):
            t = qm.issue_ticket(customer_type="regular", issued_at_iso=now_iso())
            save_manager(qm)
            info = qm.position_and_eta(t.number) or {"ahead": 0, "eta_minutes": 0}
            st.success(f"Your ticket: R-{t.number}")
            st.write(f"Your position in line: **{info['ahead'] + 1}**")
            st.write(f"People ahead: **{info['ahead']}**")
            st.write(f"Estimated wait: **{info['eta_minutes']} minutes**")
    with col2:
        if st.button("Get PRIORITY ticket", type="primary", use_container_width=True):
            t = qm.issue_ticket(customer_type="priority", issued_at_iso=now_iso())
            save_manager(qm)
            info = qm.position_and_eta(t.number) or {"ahead": 0, "eta_minutes": 0}
            st.success(f"Your ticket: P-{t.number}")
            st.write(f"Your position in line: **{info['ahead'] + 1}**")
            st.write(f"People ahead: **{info['ahead']}**")
            st.write(f"Estimated wait: **{info['eta_minutes']} minutes**")

    st.divider()
    st.subheader("Check status (optional)")
    ticket_num = st.number_input("Enter your ticket number", min_value=1, step=1)
    if st.button("Check my position"):
        info = qm.position_and_eta(int(ticket_num))
        if info is None:
            st.warning("Ticket not found in waiting queues (may be served already or invalid).")
        else:
            st.info(
                f"Type: **{info['customer_type']}** | Your position: **{info['ahead'] + 1}** | People ahead: **{info['ahead']}** | ETA: **{info['eta_minutes']} min**"
            )

with tab_staff:
    st.subheader("Call next customer")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Next customer", type="primary", use_container_width=True):
            t = qm.call_next()
            save_manager(qm)
            if t is None:
                st.warning("No customers waiting.")
            else:
                prefix = "P" if t.customer_type == "priority" else "R"
                st.success(f"Now serving: {prefix}-{t.number}")
    with col2:
        t = qm.current_ticket()
        if t is None:
            st.metric("Now serving", "—")
        else:
            prefix = "P" if t.customer_type == "priority" else "R"
            st.metric("Now serving", f"{prefix}-{t.number}")

    counts = qm.waiting_counts()
    with col3:
        st.metric("Waiting (priority)", counts["priority"])
        st.metric("Waiting (regular)", counts["regular"])
        st.metric("Waiting (total)", counts["total"])

with tab_display:
    st.subheader("Public display")
    t = qm.current_ticket()
    counts = qm.waiting_counts()
    waiting = qm.waiting_ticket_numbers()
    next_t = qm.peek_next_ticket()
    after_next_t = qm.peek_after_next_ticket()
    total_eta_minutes = counts["total"] * qm.service_minutes_per_customer
    priority_total_eta_minutes = counts["priority"] * qm.service_minutes_per_customer
    regular_total_eta_minutes = counts["regular"] * qm.service_minutes_per_customer

    col1, col2 = st.columns(2)
    with col1:
        if t is None:
            st.markdown("### Now serving: **—**")
        else:
            prefix = "P" if t.customer_type == "priority" else "R"
            st.markdown(f"### Now serving: **{prefix}-{t.number}**")
        st.write(f"Estimated waiting time (for new ticket): **{total_eta_minutes} min**")
        st.caption(f"Updated: {now_iso()}")

    with col2:
        st.markdown("### Queue status")
        st.write(f"Priority waiting: **{counts['priority']}**")
        st.write(f"Total waiting time (priority queue): **{priority_total_eta_minutes} min**")
        st.write(f"Regular waiting: **{counts['regular']}**")
        st.write(f"Total waiting time (regular queue): **{regular_total_eta_minutes} min**")
        st.write(f"Total waiting: **{counts['total']}**")

    st.divider()
    st.subheader("Queue board")
    q1, q2 = st.columns(2)
    with q1:
        st.markdown("#### Priority queue")
        if waiting["priority"]:
            st.write(", ".join(f"**P-{n}**" for n in waiting["priority"]))
        else:
            st.write("—")
    with q2:
        st.markdown("#### Regular queue")
        if waiting["regular"]:
            st.write(", ".join(f"**R-{n}**" for n in waiting["regular"]))
        else:
            st.write("—")

    st.divider()
    st.subheader("Next customers")
    n1, n2 = st.columns(2)
    with n1:
        if next_t is None:
            st.metric("Next up", "—")
        else:
            pfx = "P" if next_t.customer_type == "priority" else "R"
            st.metric("Next up", f"{pfx}-{next_t.number}")
    with n2:
        if after_next_t is None:
            st.metric("After that", "—")
        else:
            pfx = "P" if after_next_t.customer_type == "priority" else "R"
            st.metric("After that", f"{pfx}-{after_next_t.number}")

    st.divider()
    st.subheader("What should customers expect?")
    st.write(
        "Priority customers are called first. Regular customers wait behind all priority customers plus earlier regular tickets."
    )

