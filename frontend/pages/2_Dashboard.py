"""
pages/2_Dashboard.py
---------------------
The core dashboard: health gauge, sensor trend graphs, growth stage
tracker, weather history, AI recommendations, and simulation controls
(advance time / manually water the plant).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from backend import models
from backend.health_engine import calculate_health
from backend.simulation import run_cycle, get_latest_sensor_reading
from backend.plant_species import GROWTH_STAGES
from utils.recommendation import generate_recommendations

st.set_page_config(page_title="Plant Dashboard", page_icon="📊", layout="wide")

if st.session_state.get("user") is None:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.markdown(f"### 👤 {user['name']}")
    if st.button("Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.divider()

plants = models.get_plants_for_user(user["user_id"])
if not plants:
    st.info("No plants yet. Add one from the **My Plants** page.")
    st.stop()

plant_names = {p["plant_id"]: f"{p['plant_name']} ({p['species']})" for p in plants}
default_id = st.session_state.get("selected_plant_id") or plants[0]["plant_id"]
if default_id not in plant_names:
    default_id = plants[0]["plant_id"]

selected_id = st.sidebar.selectbox(
    "Select plant",
    options=list(plant_names.keys()),
    format_func=lambda pid: plant_names[pid],
    index=list(plant_names.keys()).index(default_id),
)
st.session_state.selected_plant_id = selected_id

plant = models.get_plant_by_id(selected_id)
st.title(f"📊 {plant['plant_name']} — {plant['species']}")

if not plant["is_alive"]:
    st.error("💀 This plant has died. You can still review its history below, or add a new plant.")

# ---------- Simulation controls ----------
with st.expander("⏩ Simulation controls", expanded=plant["is_alive"]):
    c1, c2, c3 = st.columns(3)
    if c1.button("Advance 1 day", disabled=not plant["is_alive"], use_container_width=True):
        result = run_cycle(selected_id)
        for alert in result["alerts"]:
            st.toast(f"🔔 {alert}", icon="⚠️")
        st.rerun()
    if c2.button("💧 Water the plant", disabled=not plant["is_alive"], use_container_width=True):
        last = get_latest_sensor_reading(selected_id)
        result = run_cycle(selected_id, manual_overrides={"water_level": min(100, last["water_level"] + 35)})
        st.rerun()
    if c3.button("🌱 Add fertilizer", disabled=not plant["is_alive"], use_container_width=True):
        last = get_latest_sensor_reading(selected_id)
        result = run_cycle(selected_id, manual_overrides={"fertilizer": min(100, last["fertilizer"] + 30)})
        st.rerun()

# ---------- Current state ----------
reading = get_latest_sensor_reading(selected_id)
health = calculate_health(
    plant["species"], reading["water_level"], reading["sunlight"],
    reading["temperature"], reading["humidity"], reading["fertilizer"],
)

status_colors = {"Healthy": "#16a34a", "Moderate": "#ca8a04", "Critical": "#dc2626", "Dead": "#4b5563"}
color = status_colors.get(health["status"], "#6b7280")

col_gauge, col_metrics = st.columns([1, 2])

with col_gauge:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health["overall_score"],
        title={"text": f"Health: {health['status']}"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 15], "color": "#fecaca"},
                {"range": [15, 50], "color": "#fed7aa"},
                {"range": [50, 75], "color": "#fef08a"},
                {"range": [75, 100], "color": "#bbf7d0"},
            ],
        },
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

with col_metrics:
    m1, m2, m3 = st.columns(3)
    m1.metric("💧 Water Level", f"{reading['water_level']:.0f}%")
    m2.metric("☀️ Sunlight", f"{reading['sunlight']:.0f}%")
    m3.metric("🌡️ Temperature", f"{reading['temperature']:.0f}°C")
    m4, m5, m6 = st.columns(3)
    m4.metric("💨 Humidity", f"{reading['humidity']:.0f}%")
    m5.metric("🌱 Fertilizer", f"{reading['fertilizer']:.0f}%")
    weather_icons = {"Sunny": "☀️", "Cloudy": "☁️", "Rainy": "🌧️", "Stormy": "⛈️"}
    m6.metric("Weather", f"{weather_icons.get(reading.get('weather'), '')} {reading.get('weather', 'N/A')}")

    # Growth stage progress bar
    stage_idx = GROWTH_STAGES.index(plant["growth_stage"]) if plant["growth_stage"] in GROWTH_STAGES else 0
    progress = stage_idx / (len(GROWTH_STAGES) - 1)
    st.markdown(f"**Growth Stage:** {plant['growth_stage']}")
    st.progress(progress)

# ---------- Recommendations ----------
st.subheader("🤖 AI Recommendations")
recs = generate_recommendations(
    plant["species"], reading["water_level"], reading["sunlight"],
    reading["temperature"], reading["humidity"], reading["fertilizer"],
    health["factor_scores"],
)
for rec in recs:
    st.markdown(f"- {rec}")

st.divider()

# ---------- History charts ----------
history = models.get_sensor_history(selected_id, limit=200)

if len(history) < 2:
    st.info("Run a few simulation cycles above to see trend charts build up over time.")
else:
    df = pd.DataFrame(history)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    df["cycle"] = range(1, len(df) + 1)

    tab1, tab2, tab3, tab4 = st.tabs(["💧 Water & Sunlight", "🌡️ Temp & Humidity", "🌱 Fertilizer", "⛅ Weather History"])

    with tab1:
        fig = px.line(df, x="cycle", y=["water_level", "sunlight"], markers=True,
                       labels={"value": "%", "cycle": "Cycle", "variable": "Metric"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = px.line(df, x="cycle", y=["temperature", "humidity"], markers=True,
                       labels={"value": "Value", "cycle": "Cycle", "variable": "Metric"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = px.bar(df, x="cycle", y="fertilizer", labels={"fertilizer": "Fertilizer %", "cycle": "Cycle"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        weather_counts = df["weather"].value_counts().reset_index()
        weather_counts.columns = ["Weather", "Count"]
        fig = px.pie(weather_counts, names="Weather", values="Count", hole=0.4)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
