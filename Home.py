import streamlit as st
from utils import *
from datetime import datetime

# Initialisation de l'état de session
init_session_state()

# Stockage temporaire des utilisateurs (à remplacer par une base sécurisée)
USERS = {
    "zakaria.fassih@tgcc.ma": "password123",
    "test@test.ma": "password123"
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

    st.divider()
    st.caption("🤖 TG-Hire IA | Version 1")

    # Bouton de déconnexion dans la sidebar
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.rerun()

    # Protéger les pages dans pages/ (arrête l'exécution si non connecté)
    if not st.session_state.logged_in:
        st.stop()