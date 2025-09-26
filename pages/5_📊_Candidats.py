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

st.title("📊 Suivi des Candidats")

st.title("📊 Suivi des Candidats")
st.write("Cette page sera dédiée au suivi et à la comparaison des candidats.")
st.info("Fonctionnalité en cours de développement...")