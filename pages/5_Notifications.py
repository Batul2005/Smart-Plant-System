"""
pages/5_Notifications.py
--------------------------
Displays the notification feed for the selected plant (and a combined
view across all plants), with the ability to mark alerts as read.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from backend import models
from database.database import get_connection

st.set_page_config(page_title="Notifications", page_icon="🔔", layout="wide")

if st.session_state.get("user") is None:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.markdown(f"### 👤 {user['name']}")
    if st.button("Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.title("🔔 Notifications")

plants = models.get_plants_for_user(user["user_id"])
if not plants:
    st.info("No plants yet. Add one from the **My Plants** page.")
    st.stop()

plant_lookup = {p["plant_id"]: p for p in plants}

with get_connection() as conn:
    plant_ids = list(plant_lookup.keys())
    placeholders = ",".join("?" * len(plant_ids))
    rows = conn.execute(
        f"SELECT * FROM Notifications WHERE plant_id IN ({placeholders}) "
        f"ORDER BY created_at DESC LIMIT 100",
        plant_ids,
    ).fetchall()
    notifications = [dict(r) for r in rows]

if not notifications:
    st.info("No alerts yet. Notifications appear here when water runs low, temperature "
            "exceeds safe limits, or plant health becomes critical.")
else:
    unread_count = sum(1 for n in notifications if not n["is_read"])
    st.caption(f"{unread_count} unread of {len(notifications)} total alerts")

    if st.button("Mark all as read"):
        with get_connection() as conn:
            conn.execute(
                f"UPDATE Notifications SET is_read = 1 WHERE plant_id IN ({placeholders})",
                plant_ids,
            )
        st.rerun()

    severity_icons = {"high": "🟠", "critical": "🔴", "low": "🟡"}

    for n in notifications:
        plant_name = plant_lookup.get(n["plant_id"], {}).get("plant_name", "Unknown plant")
        icon = severity_icons.get(n["severity"], "🔵")
        read_style = "" if not n["is_read"] else " (read)"
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"{icon} **{plant_name}**{read_style}  \n{n['message']}")
            c2.caption(n["created_at"][:16].replace("T", " "))
