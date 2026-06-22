"""
app.py
------
Entrypoint for the Smart Digital Plant Monitoring System Streamlit app.

Run with:
    streamlit run app.py

Handles authentication (login/register) and routes to the main dashboard
once a user is logged in. Plant management, sensor simulation, ML
predictions, disease detection, and notifications are implemented as
Streamlit pages under frontend/pages/.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from database.database import init_db
from backend import models

st.set_page_config(
    page_title="Smart Plant Monitoring System",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ---------- Session state defaults ----------
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_plant_id" not in st.session_state:
    st.session_state.selected_plant_id = None


def login_register_view():
    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <h1>🌿 Smart Digital Plant Monitoring System</h1>
            <p style="color:#6b7280; font-size:1.05rem;">
                A virtual digital twin for your plants — track health, predict growth,
                and get AI-powered care recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Log In", "Create Account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
                if submitted:
                    try:
                        user = models.authenticate_user(email, password)
                        user.pop("password", None)
                        st.session_state.user = user
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

        with tab_register:
            with st.form("register_form"):
                name = st.text_input("Full Name", key="reg_name")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password",
                                          help="At least 6 characters")
                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                if submitted:
                    if len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif not name or not email:
                        st.error("Please fill in all fields.")
                    else:
                        try:
                            user = models.create_user(name, email, password)
                            user.pop("password", None)
                            st.session_state.user = user
                            st.success("Account created! Redirecting...")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

        st.caption("Demo tip: just register with any email — this runs entirely on your local machine.")


def main_app_view():
    user = st.session_state.user

    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(user["email"])
        if st.button("Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.selected_plant_id = None
            st.rerun()
        st.divider()
        st.markdown(
            "**Navigate using the pages above** ⬆️\n\n"
            "- 🌱 My Plants — add/manage plants\n"
            "- 📊 Dashboard — health & sensor charts\n"
            "- 🔮 AI Prediction — ML forecasts\n"
            "- 🩺 Disease Scan — upload a leaf photo\n"
            "- 🔔 Notifications — alert history"
        )

    st.title("🌱 My Plants Overview")

    plants = models.get_plants_for_user(user["user_id"])

    if not plants:
        st.info("You don't have any plants yet. Head to the **My Plants** page (sidebar) to add one!")
        return

    cols = st.columns(3)
    for i, plant in enumerate(plants):
        with cols[i % 3]:
            with st.container(border=True):
                status_emoji = "💀" if not plant["is_alive"] else "🌿"
                st.markdown(f"#### {status_emoji} {plant['plant_name']}")
                st.caption(f"{plant['species']} • {plant['growth_stage']}")
                if st.button("View Dashboard", key=f"view_{plant['plant_id']}", use_container_width=True):
                    st.session_state.selected_plant_id = plant["plant_id"]
                    st.switch_page("pages/2_Dashboard.py")


# ---------- Router ----------
if st.session_state.user is None:
    login_register_view()
else:
    main_app_view()
