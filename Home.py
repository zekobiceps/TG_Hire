import streamlit as st
import pandas as pd
from utils import *
from datetime import datetime
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.success("Choisissez une page ci-dessus.")

# CSS inspiré de Notion pour supprimer les espaces inutiles et styliser les cartes
st.markdown("""
<style>
.stApp, .stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}
.stColumns {
    margin-top: 0 !important;
}
.notion-column {
    background-color: #f7f9fa;
    border: 1px solid #e0e2e4;
    border-radius: 8px;
    padding: 8px;
    margin: 0 4px;
    min-height: 400px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.notion-card {
    background-color: white;
    border: 1px solid #e0e2e4;
    border-radius: 6px;
    padding: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.notion-card h4 {
    margin: 0;
    color: #1a1a1a;
    font-size: 16px;
    font-weight: 500;
}
.notion-card p {
    margin: 0;
    color: #4a4a4a;
    font-size: 14px;
}
.notion-card .status {
    margin: 0;
    font-size: 12px;
    color: #6b7280;
}
.status-to-do { color: #ef4444; } /* Rouge pour À développer */
.status-in-progress { color: #f59e0b; } /* Orange pour En cours */
.status-done { color: #10b981; } /* Vert pour Réalisé */
.block-container {
    padding-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)

st.header("🚀 Roadmap des Fonctionnalités")

# Initialisation des données dans session_state avec last_modified
if "roadmap_data" not in st.session_state:
    st.session_state.roadmap_data = [
        {"title": "Onglets de sourcing (Boolean, X-Ray)", "description": "Génération de requêtes et liens LinkedIn/Google.", "status": "Réalisé", "last_modified": "2025-09-20 10:00"},
        {"title": "Générateur InMail", "description": "Messages personnalisés avec IA.", "status": "Réalisé", "last_modified": "2025-09-21 14:30"},
        {"title": "Base de données SQLite", "description": "Stockage persistant des briefs avec UI de gestion.", "status": "En cours de développement", "last_modified": "2025-09-22 09:15"},
        {"title": "Export CSV des briefs", "description": "Génération de rapports pour Excel.", "status": "À développer", "last_modified": "2025-09-23 11:00"},
        {"title": "Système de login avancé", "description": "Intégration OAuth ou JWT pour multi-utilisateurs.", "status": "À développer", "last_modified": "2025-09-23 12:00"}
    ]

# Mettre à jour ou initialiser last_modified
for item in st.session_state.roadmap_data:
    if "last_modified" not in item:
        item["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M")

# Organiser les données par statut et trier chronologiquement
to_do = sorted([item for item in st.session_state.roadmap_data if item["status"] == "À développer"], key=lambda x: x["last_modified"], reverse=True)
in_progress = sorted([item for item in st.session_state.roadmap_data if item["status"] == "En cours de développement"], key=lambda x: x["last_modified"], reverse=True)
done = sorted([item for item in st.session_state.roadmap_data if item["status"] == "Réalisé"], key=lambda x: x["last_modified"], reverse=True)

# Interface avec 3 colonnes inspirée de Notion
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="notion-column">', unsafe_allow_html=True)
    st.subheader("📋 À développer")
    for item in to_do:
        st.markdown(f'<div class="notion-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{item["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{item["description"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="status status-to-do">Statut: {item["status"]}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="notion-column">', unsafe_allow_html=True)
    st.subheader("🔄 En cours de développement")
    for item in in_progress:
        st.markdown(f'<div class="notion-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{item["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{item["description"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="status status-in-progress">Statut: {item["status"]}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="notion-column">', unsafe_allow_html=True)
    st.subheader("✅ Réalisé")
    for item in done:
        st.markdown(f'<div class="notion-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{item["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{item["description"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="status status-done">Statut: {item["status"]}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Menu en bas pour gérer les fonctionnalités
st.divider()
st.subheader("🛠️ Gestion des Fonctionnalités")

# Sélection d'une fonctionnalité
selected_title = st.selectbox("Sélectionner une fonctionnalité", [item["title"] for item in st.session_state.roadmap_data], index=None)

if selected_title:
    # Trouver l'élément sélectionné
    selected_item = next((item for item in st.session_state.roadmap_data if item["title"] == selected_title), None)
    if selected_item:
        # Modifier le titre et la description
        new_title = st.text_input("Titre", value=selected_item["title"])
        new_description = st.text_area("Description", value=selected_item["description"], height=60)

        # Changer le statut
        statuses = ["À développer", "En cours de développement", "Réalisé"]
        new_status = st.selectbox("Statut", statuses, index=statuses.index(selected_item["status"]))

        col_btn = st.columns(3)
        with col_btn[0]:
            if st.button("Enregistrer les Modifications"):
                selected_item["title"] = new_title
                selected_item["description"] = new_description
                selected_item["status"] = new_status
                selected_item["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.success("✅ Modifications enregistrées !")
                st.rerun()

        with col_btn[1]:
            if st.button("Supprimer"):
                st.session_state.roadmap_data.remove(selected_item)
                st.success("✅ Fonctionnalité supprimée !")
                st.rerun()

# Section pour ajouter une nouvelle fonctionnalité
st.subheader("➕ Ajouter une Nouvelle Fonctionnalité")
new_title = st.text_input("Titre de la nouvelle fonctionnalité")
new_description = st.text_area("Description", height=60)
new_status = st.selectbox("Statut initial", ["À développer", "En cours de développement", "Réalisé"])
if st.button("Ajouter"):
    if new_title and new_description:
        st.session_state.roadmap_data.append({
            "title": new_title,
            "description": new_description,
            "status": new_status,
            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success("✅ Fonctionnalité ajoutée !")
        st.rerun()
    else:
        st.error("Veuillez remplir le titre et la description.")

# Footer
st.divider()
st.caption("🤖 TG-Hire IA | Version 1")