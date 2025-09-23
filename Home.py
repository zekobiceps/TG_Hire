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
st.caption("🤖 TG-Hire IA | Version 1")

st.divider()
st.header("Roadmap des Fonctionnalités")

# Initialisation des fonctionnalités dans session_state
if "roadmap" not in st.session_state:
    st.session_state.roadmap = {
        "À développer": ["Fonctionnalité 1", "Fonctionnalité 2"],
        "En cours de développement": ["Fonctionnalité 3"],
        "Réalisé": ["Fonctionnalité 4", "Fonctionnalité 5"]
    }

# Kanban avec 3 colonnes
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("À développer")
    for func in st.session_state.roadmap["À développer"]:
        st.write(func)
        if st.button("Déplacer à En cours", key=f"to_progress_{func}"):
            st.session_state.roadmap["À développer"].remove(func)
            st.session_state.roadmap["En cours de développement"].append(func)
            st.rerun()

with col2:
    st.subheader("En cours de développement")
    for func in st.session_state.roadmap["En cours de développement"]:
        st.write(func)
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("Retour à À développer", key=f"to_todo_{func}"):
                st.session_state.roadmap["En cours de développement"].remove(func)
                st.session_state.roadmap["À développer"].append(func)
                st.rerun()
        with col_right:
            if st.button("Déplacer à Réalisé", key=f"to_done_{func}"):
                st.session_state.roadmap["En cours de développement"].remove(func)
                st.session_state.roadmap["Réalisé"].append(func)
                st.rerun()

with col3:
    st.subheader("Réalisé")
    for func in st.session_state.roadmap["Réalisé"]:
        st.write(func)
        if st.button("Retour à En cours", key=f"to_progress_from_done_{func}"):
            st.session_state.roadmap["Réalisé"].remove(func)
            st.session_state.roadmap["En cours de développement"].append(func)
            st.rerun()

# Ajout d'une nouvelle fonctionnalité
st.divider()
new_func = st.text_input("Ajouter une nouvelle fonctionnalité")
if st.button("Ajouter"):
    if new_func:
        st.session_state.roadmap["À développer"].append(new_func)
        st.rerun()