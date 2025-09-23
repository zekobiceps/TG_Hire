import streamlit as st
from utils import *
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.success("Choisissez une page ci-dessus.")

# CSS minimal pour le style Kanban (inspiré GitHub : cartes propres, colonnes nettes)
st.markdown("""
<style>
.kanban-column {
    background-color: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 8px;
    margin: 8px;
    min-height: 400px;
}
.kanban-card {
    background-color: white;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.kanban-card h4 {
    margin: 0 0 8px 0;
    color: #24292f;
}
.kanban-card p {
    margin: 0 0 8px 0;
    color: #586069;
    font-size: 14px;
}
.kanban-actions {
    display: flex;
    gap: 4px;
}
</style>
""", unsafe_allow_html=True)

# Suppression du vide en haut
st.markdown("""
<style>
.stApp > header { display: none; }
.stApp { margin-top: -80px; }
</style>
""", unsafe_allow_html=True)

st.divider()
st.header("🚀 Roadmap des Fonctionnalités")

# Initialisation des données Kanban dans session_state (persistance)
if "kanban_data" not in st.session_state:
    st.session_state.kanban_data = {
        "À développer": [
            {"title": "Système de login avancé", "description": "Intégration OAuth ou JWT pour multi-utilisateurs.", "status": "À développer"},
            {"title": "Export CSV des briefs", "description": "Génération de rapports pour Excel.", "status": "À développer"}
        ],
        "En cours de développement": [
            {"title": "Base de données SQLite", "description": "Stockage persistant des briefs avec UI de gestion.", "status": "En cours"}
        ],
        "Réalisé": [
            {"title": "Onglets de sourcing (Boolean, X-Ray)", "description": "Génération de requêtes et liens LinkedIn/Google.", "status": "Réalisé"},
            {"title": "Générateur InMail", "description": "Messages personnalisés avec IA.", "status": "Réalisé"}
        ]
    }

# Interface Kanban avec 3 colonnes
col1, col2, col3 = st.columns(3)

# Ajout de lignes entre colonnes via CSS
st.markdown("""
<style>
.stColumn + .stColumn {
    border-left: 1px solid #e1e4e8;
    padding-left: 8px;
}
</style>
""", unsafe_allow_html=True)

with col1:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("📋 À développer")
    for card in st.session_state.kanban_data["À développer"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("🔄 En cours de développement")
    for card in st.session_state.kanban_data["En cours de développement"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("✅ Réalisé")
    for card in st.session_state.kanban_data["Réalisé"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Menu en bas pour gérer les cartes
st.divider()
st.subheader("🛠️ Gestion des Fonctionnalités")

# Liste de toutes les cartes pour sélection
all_cards = [card["title"] for col in st.session_state.kanban_data.values() for card in col]
selected_card = st.selectbox("Sélectionner une fonctionnalité", all_cards, index=None)

if selected_card:
    # Trouver la carte sélectionnée et sa colonne actuelle
    current_column = None
    card_data = None
    for column, cards in st.session_state.kanban_data.items():
        for card in cards:
            if card["title"] == selected_card:
                current_column = column
                card_data = card
                break
        if current_column:
            break

    if card_data:
        # Modifier le titre et la description
        new_title = st.text_input("Titre", value=card_data["title"])
        new_description = st.text_area("Description", value=card_data["description"], height=60)

        # Déplacer vers une nouvelle colonne
        columns = ["À développer", "En cours de développement", "Réalisé"]
        new_column = st.selectbox("Déplacer vers", columns, index=columns.index(current_column))

        col_btn = st.columns(3)
        with col_btn[0]:
            if st.button("Enregistrer les Modifications"):
                card_data["title"] = new_title
                card_data["description"] = new_description
                st.success("✅ Modifications enregistrées !")
                st.rerun()

        with col_btn[1]:
            if st.button("Déplacer"):
                if new_column != current_column:
                    st.session_state.kanban_data[current_column].remove(card_data)
                    card_data["status"] = new_column
                    st.session_state.kanban_data[new_column].append(card_data)
                    st.success(f"✅ Déplacé vers '{new_column}' !")
                    st.rerun()

        with col_btn[2]:
            if st.button("Supprimer"):
                st.session_state.kanban_data[current_column].remove(card_data)
                st.success("✅ Fonctionnalité supprimée !")
                st.rerun()

# Section pour ajouter une nouvelle fonctionnalité
new_title = st.text_input("Titre de la nouvelle fonctionnalité")
new_description = st.text_area("Description", height=60)
if st.button("Ajouter à 'À développer'"):
    if new_title and new_description:
        st.session_state.kanban_data["À développer"].append({
            "title": new_title,
            "description": new_description,
            "status": "À développer"
        })
        st.success("✅ Fonctionnalité ajoutée !")
        st.rerun()
    else:
        st.error("Veuillez remplir le titre et la description.")

# Footer
st.divider()
st.caption("🤖 TG-Hire IA | Version 1")