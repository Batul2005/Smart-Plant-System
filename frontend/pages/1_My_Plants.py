"""
pages/1_My_Plants.py
---------------------
Plant management: add new plants, view existing ones, update or delete.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from backend import models
from backend.plant_species import get_species_list, get_species_info

st.set_page_config(page_title="My Plants", page_icon="🌱", layout="wide")

if st.session_state.get("user") is None:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.user
st.title("🌱 My Plants")

with st.sidebar:
    st.markdown(f"### 👤 {user['name']}")
    if st.button("Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

tab_view, tab_add = st.tabs(["My Plants", "➕ Add New Plant"])

with tab_add:
    st.subheader("Add a new plant")
    col1, col2 = st.columns(2)
    with col1:
        plant_name = st.text_input("Plant nickname", placeholder="e.g. Window Rose")
    with col2:
        species = st.selectbox("Species", get_species_list())

    info = get_species_info(species)
    with st.expander(f"ℹ️ {species} care requirements", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Water", f"{info['water_requirement']['ideal']}{info['water_requirement']['unit'].replace('% soil moisture','%')}")
        c2.metric("Sunlight", f"{info['sunlight_requirement']['ideal']}%")
        c3.metric("Temp", f"{info['temperature_range']['ideal']}°C")
        c4.metric("Humidity", f"{info['humidity_range']['ideal']}%")
        st.caption(info["description"])

    if st.button("Add Plant", type="primary"):
        if not plant_name.strip():
            st.error("Please give your plant a nickname.")
        else:
            plant = models.add_plant(user["user_id"], plant_name.strip(), species)
            st.success(f"🌿 {plant_name} ({species}) added successfully!")
            st.rerun()

with tab_view:
    plants = models.get_plants_for_user(user["user_id"])

    if not plants:
        st.info("No plants yet — add one in the 'Add New Plant' tab.")
    else:
        for plant in plants:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                status_emoji = "💀" if not plant["is_alive"] else "🌿"
                c1.markdown(f"**{status_emoji} {plant['plant_name']}**  \n*{plant['species']}*")
                c2.markdown(f"**Stage:**  \n{plant['growth_stage']}")
                c3.markdown(f"**Planted:**  \n{plant['planted_date'][:10]}")
                with c4:
                    b1, b2 = st.columns(2)
                    if b1.button("📊 View", key=f"dash_{plant['plant_id']}", use_container_width=True):
                        st.session_state.selected_plant_id = plant["plant_id"]
                        st.switch_page("pages/2_Dashboard.py")
                    if b2.button("🗑️", key=f"del_{plant['plant_id']}", use_container_width=True,
                                 help="Delete this plant"):
                        models.delete_plant(plant["plant_id"])
                        st.rerun()
