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

# CSS pour supprimer les espaces inutiles et styliser le tableau
st.markdown("""
<style>
.stApp, .stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}
.stDataFrame {
    margin-top: 0 !important;
}
.dataframe {
    border-collapse: collapse;
    width: 100%;
}
.dataframe th, .dataframe td {
    border: 1px solid #e1e4e8;
    padding: 8px;
    text-align: left;
    vertical-align: top;
}
.dataframe th {
    background-color: #f6f8fa;
    color: #24292f;
}
.dataframe tr:hover {
    background-color: #f0f0f0;
}
.block-container {
    padding-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# Roadmap des Fonctionnalités sans divider en haut
st.header("🚀 Roadmap des Fonctionnalités")

# Initialisation des données dans session_state avec dates
if "roadmap_data" not in st.session_state:
    st.session_state.roadmap_data = [
        {"title": "Onglets de sourcing (Boolean, X-Ray)", "description": "Génération de requêtes et liens LinkedIn/Google.", "status": "Réalisé", "date": "2025-09-20 10:00"},
        {"title": "Générateur InMail", "description": "Messages personnalisés avec IA.", "status": "Réalisé", "date": "2025-09-21 14:30"},
        {"title": "Base de données SQLite", "description": "Stockage persistant des briefs avec UI de gestion.", "status": "En cours de développement", "date": "2025-09-22 09:15"},
        {"title": "Export CSV des briefs", "description": "Génération de rapports pour Excel.", "status": "À développer", "date": "2025-09-23 11:00"},
        {"title": "Système de login avancé", "description": "Intégration OAuth ou JWT pour multi-utilisateurs.", "status": "À développer", "date": "2025-09-23 12:00"}
    ]

# Mettre à jour la date lors de la modification
for item in st.session_state.roadmap_data:
    if "last_modified" not in item:
        item["last_modified"] = item["date"]
    else:
        item["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M")

# Conversion en DataFrame avec tri chronologique (du plus récent au plus ancien)
df_roadmap = pd.DataFrame(st.session_state.roadmap_data)
df_roadmap = df_roadmap.sort_values(by="last_modified", ascending=False)

# Affichage du tableau
st.dataframe(df_roadmap[["title", "description", "status", "last_modified"]], use_container_width=True)

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
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success("✅ Fonctionnalité ajoutée !")
        st.rerun()
    else:
        st.error("Veuillez remplir le titre et la description.")

# Footer
st.divider()
st.caption("🤖 TG-Hire IA | Version 1")