import streamlit as st

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()
    
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

# Initialiser les variables manquantes
defaults = {
    "annonces": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Annonces",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📢 Gestion des annonces")

# -------------------- Ajout d’une annonce --------------------
st.subheader("➕ Ajouter une annonce")

col1, col2 = st.columns(2)
with col1:
    titre = st.text_input("Titre de l’annonce", key="annonce_titre")
    poste = st.text_input("Poste concerné", key="annonce_poste")
with col2:
    entreprise = st.text_input("Entreprise", key="annonce_entreprise")
    localisation = st.text_input("Localisation", key="annonce_loc")

contenu = st.text_area("Contenu de l’annonce", key="annonce_contenu", height=150)

if st.button("💾 Publier l’annonce", type="primary", use_container_width=True, key="btn_publier_annonce"):
    if titre and poste and entreprise and contenu:
        annonce = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "titre": titre,
            "poste": poste,
            "entreprise": entreprise,
            "localisation": localisation,
            "contenu": contenu,
        }
        st.session_state.annonces.append(annonce)
        st.success("✅ Annonce publiée avec succès !")
    else:
        st.warning("⚠️ Merci de remplir tous les champs obligatoires")

st.divider()

# -------------------- Liste des annonces --------------------
st.subheader("📋 Annonces publiées")

if not st.session_state.annonces:
    st.info("Aucune annonce publiée pour le moment.")
else:
    for i, annonce in enumerate(st.session_state.annonces[::-1]):  # affichage dernière en premier
        with st.expander(f"{annonce['date']} - {annonce['titre']} ({annonce['poste']})", expanded=False):
            st.write(f"**Entreprise :** {annonce['entreprise']}")
            st.write(f"**Localisation :** {annonce['localisation'] or 'Non spécifiée'}")
            st.write("**Contenu :**")
            st.text_area("Contenu", annonce["contenu"], height=120, key=f"annonce_contenu_{i}", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"delete_annonce_{i}"):
                    st.session_state.annonces.pop(len(st.session_state.annonces) - 1 - i)
                    st.success("Annonce supprimée.")
                    st.rerun()
            with col2:
                st.download_button(
                    "⬇️ Exporter",
                    data=f"Titre: {annonce['titre']}\nPoste: {annonce['poste']}\nEntreprise: {annonce['entreprise']}\nLocalisation: {annonce['localisation']}\n\n{annonce['contenu']}",
                    file_name=f"annonce_{annonce['poste']}_{i}.txt",
                    mime="text/plain",
                    key=f"download_annonce_{i}"
                )
