import streamlit as st

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()
    
import streamlit as st
from utils import *
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👥 Préparation d'Entretien")

st.title("👥 Préparation d'Entretien")
st.write("Cette page sera dédiée à la préparation des entretiens de recrutement.")
st.info("Fonctionnalité en cours de développement...")