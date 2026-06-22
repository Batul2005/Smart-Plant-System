"""
pages/4_Disease_Scan.py
-------------------------
Upload a leaf/plant photo for OpenCV-based health analysis (color +
texture). See disease_detection/detect.py for the honest explanation of
why this uses classical CV rather than a pretrained deep learning model.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import tempfile

from backend import models
from disease_detection.detect import analyze_leaf_image

st.set_page_config(page_title="Disease Scan", page_icon="🩺", layout="wide")

if st.session_state.get("user") is None:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.markdown(f"### 👤 {user['name']}")
    if st.button("Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

plants = models.get_plants_for_user(user["user_id"])
if not plants:
    st.info("No plants yet. Add one from the **My Plants** page.")
    st.stop()

plant_names = {p["plant_id"]: f"{p['plant_name']} ({p['species']})" for p in plants}
default_id = st.session_state.get("selected_plant_id") or plants[0]["plant_id"]
if default_id not in plant_names:
    default_id = plants[0]["plant_id"]

selected_id = st.sidebar.selectbox(
    "Select plant", options=list(plant_names.keys()),
    format_func=lambda pid: plant_names[pid],
    index=list(plant_names.keys()).index(default_id),
)
plant = models.get_plant_by_id(selected_id)

st.title(f"🩺 Disease Scan — {plant['plant_name']}")
st.caption(
    "Uses classical computer vision (OpenCV, HSV color analysis + Laplacian texture variance) "
    "to screen leaf color and surface irregularities — a real, working CV pipeline rather than "
    "a pretrained deep-learning model with unverified weights."
)

uploaded = st.file_uploader("Upload a clear photo of the plant's leaves", type=["jpg", "jpeg", "png"])

col_img, col_result = st.columns([1, 1])

if uploaded:
    with col_img:
        st.image(uploaded, caption="Uploaded image", use_container_width=True)

    suffix = os.path.splitext(uploaded.name)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    try:
        with st.spinner("Analyzing leaf color and texture..."):
            result = analyze_leaf_image(tmp_path)
    finally:
        os.unlink(tmp_path)

    models.store_disease_scan(selected_id, result["diagnosis"], result["confidence"], result["treatment"])

    with col_result:
        diagnosis_colors = {
            "Healthy": "🟢",
            "Yellowing leaves (possible chlorosis)": "🟡",
            "Dry / browning leaves": "🟠",
            "Possible disease (leaf spotting detected)": "🔴",
            "No leaf detected": "⚪",
        }
        icon = diagnosis_colors.get(result["diagnosis"], "🔵")

        st.markdown(f"### {icon} {result['diagnosis']}")
        st.progress(result["confidence"], text=f"Confidence: {result['confidence']*100:.0f}%")
        st.markdown(f"**Suggested action:** {result['treatment']}")

        with st.expander("🔬 Raw analysis details"):
            st.json(result["details"])
else:
    with col_img:
        st.info("Upload an image to begin analysis. For best results, use good lighting and "
                "fill the frame with leaves against a plain background.")

st.divider()

st.subheader("📜 Scan History")
scans = models.get_disease_scan_history(selected_id)
if not scans:
    st.caption("No scans yet for this plant.")
else:
    for scan in scans:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{scan['diagnosis']}**  \n{scan['treatment']}")
            c2.metric("Confidence", f"{scan['confidence']*100:.0f}%")
            st.caption(scan["scanned_at"])
