import streamlit as st
from utils import *
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 TG-Hire IA - Assistant Recrutement")
st.write("Bienvenue dans votre assistant de recrutement.")

st.sidebar.success("Choisissez une page ci-dessus.")

st.divider()
st.caption("🤖 TG-Hire IA | Made with ❤️")
