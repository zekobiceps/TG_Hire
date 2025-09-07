import sys
import os
import importlib.util
import streamlit as st
from datetime import datetime

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Annonces",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📢 Gestion des annonces")

# -------------------- Données --------------------
if "annonces" not in st.session_state:
    st.session_state.annonces = []

# -------------------- Interface --------------------
col1, col2 = st.columns([2, 1])
with col1:
    titre = st.text_input("Titre de l’annonce", key="annonce_titre")
    description = st.text_area("Description de l’annonce", key="annonce_desc", height=200)
with col2:
    date_pub = st.date_input("Date de publication", datetime.today(), key="annonce_date")
    recruteur = st.selectbox("Recruteur", ["Zakaria", "Sara", "Jalal", "Bouchra"], key="annonce_recruteur")

if st.button("➕ Ajouter annonce", type="primary", key="add_annonce"):
    if titre and description:
        annonce = {
            "titre": titre,
            "description": description,
            "date": str(date_pub),
            "recruteur": recruteur
        }
        st.session_state.annonces.append(annonce)
        st.success("✅ Annonce ajoutée")
    else:
        st.warning("⚠️ Veuillez remplir tous les champs")

st.divider()
st.subheader("📋 Liste des annonces")

if st.session_state.annonces:
    for i, annonce in enumerate(st.session_state.annonces):
        with st.expander(f"{annonce['titre']} ({annonce['date']}) - {annonce['recruteur']}", expanded=False):
            st.write(annonce["description"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"del_annonce_{i}"):
                    st.session_state.annonces.pop(i)
                    st.rerun()
            with col2:
                st.write(f"👤 Recruteur : {annonce['recruteur']}")
else:
    st.info("ℹ️ Aucune annonce enregistrée")
