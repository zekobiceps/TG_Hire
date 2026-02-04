import streamlit as st
from utils import display_commit_info, require_login

st.set_page_config(
    page_title="Gestion des Stagiaires",
    page_icon="🎓",
    layout="wide"
)

# Vérification de la connexion
require_login()

st.title("🎓 Gestion des Stagiaires")
display_commit_info()

st.info("🚧 Cette page est en cours de réalisation.")
