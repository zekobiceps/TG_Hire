import streamlit as st

st.set_page_config(
    page_title="Gestion des Stagiaires",
    page_icon="🎓",
    layout="wide"
)

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

st.title("🎓 Gestion des Stagiaires")

st.info("🚧 Cette page est en cours de réalisation.")
