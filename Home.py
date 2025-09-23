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

def move_card(column_from, column_to, card_title):
    """Fonction pour déplacer une carte entre colonnes"""
    for card in st.session_state.kanban_data[column_from]:
        if card["title"] == card_title:
            st.session_state.kanban_data[column_from].remove(card)
            card["status"] = "En cours" if column_to == "En cours de développement" else column_to
            st.session_state.kanban_data[column_to].append(card)
            st.rerun()
            break

# Colonne 1: À développer
with col1:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("📋 À développer")
    for card in st.session_state.kanban_data["À développer"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        col_btn = st.columns(1)
        with col_btn[0]:
            if st.button("➡️ En cours", key=f"move_to_progress_{card['title']}"):
                move_card("À développer", "En cours de développement", card["title"])
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Colonne 2: En cours de développement
with col2:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("🔄 En cours de développement")
    for card in st.session_state.kanban_data["En cours de développement"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        col_btn = st.columns(2)
        with col_btn[0]:
            if st.button("⬅️ À développer", key=f"move_to_todo_{card['title']}"):
                move_card("En cours de développement", "À développer", card["title"])
        with col_btn[1]:
            if st.button("➡️ Réalisé", key=f"move_to_done_{card['title']}"):
                move_card("En cours de développement", "Réalisé", card["title"])
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Colonne 3: Réalisé
with col3:
    st.markdown('<div class="kanban-column">', unsafe_allow_html=True)
    st.subheader("✅ Réalisé")
    for card in st.session_state.kanban_data["Réalisé"]:
        st.markdown(f'<div class="kanban-card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{card["title"]}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p>{card["description"]}</p>', unsafe_allow_html=True)
        if st.button("⬅️ En cours", key=f"move_back_progress_{card['title']}"):
            move_card("Réalisé", "En cours de développement", card["title"])
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Section pour ajouter une nouvelle fonctionnalité
st.divider()
st.subheader("➕ Ajouter une Nouvelle Fonctionnalité")
new_title = st.text_input("Titre de la fonctionnalité")
new_description = st.text_area("Description", height=60)
if st.button("Ajouter à 'À développer'", type="primary"):
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

# Bouton pour réinitialiser la roadmap (optionnel)
if st.button("🔄 Réinitialiser la Roadmap"):
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
    st.rerun()

# Footer
st.divider()
st.caption("🤖 TG-Hire IA | Version 1")