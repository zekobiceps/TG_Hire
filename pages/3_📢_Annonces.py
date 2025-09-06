import streamlit as st
from utils import (
    init_session_state,
    generate_annonce,
    generate_accroche_inmail
)

# Initialisation de la session
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📢 Générateur d'Annonces et Accroches")

tab1, tab2, tab3 = st.tabs(["📝 Générer une annonce", "✉️ Accroche InMail", "🌐 Web Scraping"])

# -------------------- Onglet 1 : Générateur d'annonce --------------------
with tab1:
    st.header("📝 Générateur d'Annonces Optimisées")

    col1, col2 = st.columns(2)

    with col1:
        poste_annonce = st.text_input("Titre du poste:", placeholder="Ex: Développeur Fullstack")
        competences_annonce = st.text_area(
            "Compétences clés requises:",
            placeholder="Ex: React, Node.js, MongoDB, AWS",
            height=100
        )

    with col2:
        # Importer depuis le brief si disponible
        if st.session_state.get("poste_intitule"):
            if st.button("📋 Importer depuis le brief"):
                poste_annonce = st.session_state.poste_intitule
                competences_text = ""
                if "Compétences - Modèle KSA" in st.session_state.brief_data:
                    for comp, details in st.session_state.brief_data["Compétences - Modèle KSA"].items():
                        if isinstance(details, dict) and details.get("valeur"):
                            competences_text += f"{comp}, "
                competences_annonce = competences_text

    if st.button("🪄 Générer l'annonce", type="primary") and poste_annonce and competences_annonce:
        annonce = generate_annonce(poste_annonce, competences_annonce)

        if annonce and "Erreur" not in annonce:
            st.success("Annonce générée!")
            st.text_area("Annonce optimisée:", value=annonce, height=300)

            if st.button("📋 Copier l'annonce"):
                st.success("Annonce copiée dans le presse-papiers!")
        else:
            st.error("Erreur lors de la génération de l'annonce")

# -------------------- Onglet 2 : Accroche InMail --------------------
with tab2:
    st.header("✉️ Générateur d'Accroche InMail")

    url_linkedin = st.text_input("URL du profil LinkedIn:", placeholder="Ex: https://www.linkedin.com/in/nom-prenom/")
    poste_accroche = st.text_input("Poste à pourvoir:", placeholder="Ex: Chef de projet digital")

    if st.button("💌 Générer l'accroche", type="primary") and url_linkedin and poste_accroche:
        accroche = generate_accroche_inmail(url_linkedin, poste_accroche)

        if accroche and "Erreur" not in accroche:
            st.success("Accroche générée!")
            st.text_area("Accroche InMail personnalisée:", value=accroche, height=150)

            if st.button("📋 Copier l'accroche"):
                st.success("Accroche copiée dans le presse-papiers!")
        else:
            st.error("Erreur lors de la génération de l'accroche")

# -------------------- Onglet 3 : Web Scraping --------------------
with tab3:
    st.header("🌐 Web Scraping")
    st.info("Fonctionnalité en cours de développement...")
    st.write("Cette section permettra bientôt d'extraire automatiquement des données de profils et d'annonces.")
