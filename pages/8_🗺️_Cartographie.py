import sys
import os
import importlib.util
import streamlit as st

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🗺️ Cartographie des compétences")

# -------------------- Data --------------------
SOURCING_MATRIX_DATA = {
    "Quadrant 1": ["Compétence A", "Compétence B"],
    "Quadrant 2": ["Compétence C", "Compétence D"],
    "Quadrant 3": ["Compétence E", "Compétence F"],
    "Quadrant 4": ["Compétence G", "Compétence H"],
}

quadrant_choisi = st.selectbox("Quadrant:", list(SOURCING_MATRIX_DATA.keys()), key="carto_quadrant")

if quadrant_choisi:
    st.subheader(f"📊 Compétences dans {quadrant_choisi}")
    for comp in SOURCING_MATRIX_DATA[quadrant_choisi]:
        st.write(f"- {comp}")

if st.button("➕ Ajouter compétence", key="add_comp"):
    new_comp = st.text_input("Nouvelle compétence:", key="new_comp")
    if new_comp:
        SOURCING_MATRIX_DATA[quadrant_choisi].append(new_comp)
        st.success(f"✅ Compétence '{new_comp}' ajoutée")
        st.rerun()
