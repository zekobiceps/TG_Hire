import streamlit as st
from utils import *
from datetime import datetime

# Initialisation de l'état de session
init_session_state()

# Stockage temporaire des utilisateurs (à remplacer par une base sécurisée)
USERS = {
    "user1@example.com": "password123",
    "user2@example.com": "securepass"
}

# Vérification de l'état de connexion
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Page de login
if not st.session_state.logged_in:
    st.set_page_config(
        page_title="TG-Hire IA - Assistant Recrutement",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("🤖 TG-Hire IA - Assistant Recrutement")
    st.write("Veuillez vous connecter pour accéder à l'outil.")
    
    email = st.text_input("Adresse Email", key="login_email")
    password = st.text_input("Mot de Passe", type="password", key="login_password")
    
    if st.button("Se Connecter"):
        if email in USERS and USERS[email] == password:
            st.session_state.logged_in = True
            st.success("Connexion réussie !")
            st.rerun()
        else:
            st.error("Email ou mot de passe incorrect.")
else:
    # Page d'accueil après connexion
    st.set_page_config(
        page_title="TG-Hire IA - Assistant Recrutement",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("🤖 TG-Hire IA - Assistant Recrutement")
    st.write("Bienvenue dans votre assistant de recrutement.")

    st.sidebar.success("Choisissez une page ci-dessus.")

    # --- TABLEAU KANBAN DES FONCTIONNALITÉS ---
    st.markdown("---")
    st.subheader("📊 Tableau de Bord des Fonctionnalités")
    
    # Définition des fonctionnalités
    features = {
        "À développer": [
            "Intégration avec LinkedIn API",
            "Système de notifications en temps réel",
            "Analyse de sentiment des entretiens",
            "Tableau de bord analytics avancé",
            "Export automatique vers ATS"
        ],
        "En cours": [
            "Optimisation de l'IA de matching",
            "Interface mobile responsive",
            "Synchronisation cloud"
        ],
        "Réalisé": [
            "Système d'authentification",
            "Analyse basique de CV",
            "Classement par similarité cosinus",
            "Export PDF/Word des briefs",
            "Matrice KSA interactive"
        ]
    }
    
    # Création des colonnes Kanban
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📋 À développer")
        st.markdown("---")
        for feature in features["À développer"]:
            with st.container():
                st.markdown(f"""
                <div style="
                    background: #ffebee; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin: 5px 0; 
                    border-left: 4px solid #f44336;
                ">
                📌 {feature}
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🔄 En cours")
        st.markdown("---")
        for feature in features["En cours"]:
            with st.container():
                st.markdown(f"""
                <div style="
                    background: #fff3e0; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin: 5px 0; 
                    border-left: 4px solid #ff9800;
                ">
                ⚡ {feature}
                </div>
                """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("### ✅ Réalisé")
        st.markdown("---")
        for feature in features["Réalisé"]:
            with st.container():
                st.markdown(f"""
                <div style="
                    background: #e8f5e8; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin: 5px 0; 
                    border-left: 4px solid #4caf50;
                ">
                ✅ {feature}
                </div>
                """, unsafe_allow_html=True)
    
    # Statistiques rapides
    st.markdown("---")
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        st.metric("Fonctionnalités totales", 
                 len(features["À développer"]) + len(features["En cours"]) + len(features["Réalisé"]))
    
    with col_stats2:
        st.metric("Taux de réalisation", 
                 f"{(len(features['Réalisé']) / (len(features['À développer']) + len(features['En cours']) + len(features['Réalisé'])) * 100):.1f}%")
    
    with col_stats3:
        st.metric("En développement", len(features["En cours"]))
    
    st.divider()
    st.caption("🤖 TG-Hire IA | Made with ❤️")

    # Bouton de déconnexion dans la sidebar
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.rerun()

    # Protéger les pages dans pages/ (arrête l'exécution si non connecté)
    if not st.session_state.logged_in:
        st.stop()