import streamlit as st
import os
import sys
import gspread
from google.oauth2 import service_account

# Ajouter le répertoire racine au chemin de recherche (optionnel si utils.py est dans la racine)
sys.path.append(os.path.dirname(__file__))
from utils import *

from datetime import datetime
import pandas as pd

# URL de la feuille Google Sheets pour les utilisateurs
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fodJWGccSaDmlSEDkJblZoQE-lcifxpnOg5RYf3ovTg/edit?gid=0#gid=0"
USERS_WORKSHEET_NAME = "Logininfo"  # Nom de la feuille mis à jour

# Initialisation robuste de l'état de session
if 'features' not in st.session_state:
    st.session_state.features = {
        "À développer": [
            {
                "id": 1,
                "title": "Interface de connexion sécurisée",
                "description": "Développer une interface de connexion avec authentification",
                "priority": "Haute",
                "date_ajout": "2024-01-01"
            }
        ],
        "En cours": [],
        "Réalisé": []
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "users" not in st.session_state:
    st.session_state.users = {}

# Fonction pour charger les utilisateurs depuis Google Sheets
def load_users_from_gsheet():
    """Charge les utilisateurs (email, password, name) depuis la feuille Google Sheets."""
    try:
        # Construire le dictionnaire d'authentification à partir des secrets
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace("\\n", "\n").strip(),
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets["GCP_CLIENT_ID"],
            "auth_uri": st.secrets["GCP_AUTH_URI"],
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_CERT_URL"],
            "client_x509_cert_url": st.secrets["GCP_CLIENT_CERT_URL"]
        }
        
        # Vérifier si toutes les clés nécessaires sont présentes
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"]
        if not all(key in service_account_info and service_account_info[key] for key in required_keys):
            st.error("❌ Certaines clés de secret GCP sont manquantes. Vérifiez votre secrets.toml.")
            return {}

        gc = gspread.service_account_from_dict(service_account_info)
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(USERS_WORKSHEET_NAME)
        
        # Charger les données (en supposant que la ligne 1 est les en-têtes : A1 = "email", B1 = "password", C1 = "name")
        records = worksheet.get_all_records()
        
        users = {}
        for record in records:
            email = record.get("email", "").strip().lower()
            password = record.get("password", "").strip()
            name = record.get("name", "").strip()
            if email and password and name:
                users[email] = {"password": password, "name": name}
        
        return users
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des utilisateurs depuis Google Sheets : {e}")
        return {}

# Fonction de débogage
def debug_session_state():
    """Affiche l'état actuel de la session pour débogage."""
    with st.expander("🔧 Mode Débogage (État de la Session)"):
        st.json(st.session_state)

# Charger les utilisateurs au démarrage
st.session_state.users = load_users_from_gsheet()

# Appliquer le style CSS minimaliste
st.markdown("""
    <style>
    /* Cacher les éléments par défaut de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Style minimaliste */
    .feature-card {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #6c757d;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Style pour le message de bienvenue */
    .welcome-message {
        text-align: center;
        margin: 10px 0;
    }
    .welcome-text {
        font-size: 14px;
        font-weight: bold;
        margin-bottom: 0;
    }
    .user-name {
        font-size: 16px;
        font-weight: bold;
        color: #1f77b4;
        margin-top: 0;
    }
    </style>
""", unsafe_allow_html=True)

# Page de login
if not st.session_state.logged_in:
    st.set_page_config(
        page_title="TG-Hire IA - Roadmap Fonctionnelle",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Centrer le contenu de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Afficher l'image au centre
        st.image("tgcc.png", width=300, use_container_width=True)
        
        # Formulaire de connexion
        with st.form("login_form"):
            st.subheader("Connexion")
            email = st.text_input("Adresse Email", key="login_email")
            password = st.text_input("Mot de Passe", type="password", key="login_password")
            
            if st.form_submit_button("Se Connecter"):
                if email in st.session_state.users and st.session_state.users[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = st.session_state.users[email]["name"]
                    st.success("Connexion réussie !")
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")

else:
    # Page d'accueil après connexion
    st.set_page_config(
        page_title="TG-Hire IA - Roadmap Fonctionnelle",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar avec logo en haut et message de bienvenue formaté
    with st.sidebar:
        # Logo en haut de la sidebar
        st.image("tgcc.png", width=150, use_container_width=True)
        st.markdown("---")
        
        # Message de bienvenue formaté sur deux lignes
        st.markdown(
            f'<div class="welcome-message">'
            f'<p class="welcome-text">Bienvenue</p>'
            f'<p class="user-name">{st.session_state.current_user}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        if st.button("🚪 Déconnexion", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            st.rerun()

    # Contenu principal - sans logo ni message de bienvenue
    st.title("📊 Roadmap Fonctionnelle")

    # Vérification que les clés existent dans features
    for status in ["À développer", "En cours", "Réalisé"]:
        if status not in st.session_state.features:
            st.session_state.features[status] = []

    # --- TABLEAU KANBAN DES FONCTIONNALITÉS ---
    
    # Création des colonnes Kanban
    col1, col2, col3 = st.columns(3)
    
    # Colonne "À développer"
    with col1:
        st.markdown("### 📋 À développer")
        st.markdown("---")
        if st.session_state.features["À développer"]:
            for feature in st.session_state.features["À développer"]:
                priority_color = {"Haute": "#dc3545", "Moyenne": "#fd7e14", "Basse": "#198754"}
                
                st.markdown(f"""
                <div class="feature-card" style="border-left-color: {priority_color[feature['priority']]}">
                    <div style="font-weight: bold; font-size: 14px;">📌 {feature['title']}</div>
                    <div style="font-size: 12px; color: #495057; margin: 5px 0;">{feature['description']}</div>
                    <div style="font-size: 11px; color: #6c757d;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune fonctionnalité à développer")
    
    # Colonne "En cours"
    with col2:
        st.markdown("### 🔄 En cours")
        st.markdown("---")
        if st.session_state.features["En cours"]:
            for feature in st.session_state.features["En cours"]:
                priority_color = {"Haute": "#dc3545", "Moyenne": "#fd7e14", "Basse": "#198754"}
                
                st.markdown(f"""
                <div class="feature-card" style="border-left-color: {priority_color[feature['priority']]}">
                    <div style="font-weight: bold; font-size: 14px;">⚡ {feature['title']}</div>
                    <div style="font-size: 12px; color: #495057; margin: 5px 0;">{feature['description']}</div>
                    <div style="font-size: 11px; color: #6c757d;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune fonctionnalité en cours")
    
    # Colonne "Réalisé"
    with col3:
        st.markdown("### ✅ Réalisé")
        st.markdown("---")
        if st.session_state.features["Réalisé"]:
            for feature in st.session_state.features["Réalisé"]:
                priority_color = {"Haute": "#dc3545", "Moyenne": "#fd7e14", "Basse": "#198754"}
                
                st.markdown(f"""
                <div class="feature-card" style="border-left-color: {priority_color[feature['priority']]}">
                    <div style="font-weight: bold; font-size: 14px;">✅ {feature['title']}</div>
                    <div style="font-size: 12px; color: #495057; margin: 5px 0;">{feature['description']}</div>
                    <div style="font-size: 11px; color: #6c757d;">Priorité: {feature['priority']} | Ajout: {feature['date_ajout']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune fonctionnalité réalisée")
    
    # --- STATISTIQUES SIMPLES ---
    st.markdown("---")
    
    total_features = sum(len(features) for features in st.session_state.features.values())
    completed_features = len(st.session_state.features["Réalisé"])
    
    col_stats1, col_stats2 = st.columns(2)
    
    with col_stats1:
        st.metric("Fonctionnalités totales", total_features)
    
    with col_stats2:
        completion_rate = (completed_features / total_features * 100) if total_features > 0 else 0
        st.metric("Taux de réalisation", f"{completion_rate:.1f}%")

    # --- ONGLET DE GESTION ---
    with st.expander("🔧 Gestion des fonctionnalités", expanded=False):
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])
        
        with tab1:
            st.subheader("Ajouter une fonctionnalité")
            with st.form(key="add_feature_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_title = st.text_input("Titre *")
                    new_description = st.text_area("Description *", height=80)
                
                with col2:
                    new_status = st.selectbox("Statut *", ["À développer", "En cours", "Réalisé"])
                    new_priority = st.selectbox("Priorité *", ["Haute", "Moyenne", "Basse"])
                
                if st.form_submit_button("💾 Ajouter"):
                    if new_title and new_description:
                        # Trouver le prochain ID disponible
                        all_ids = []
                        for status, features in st.session_state.features.items():
                            for feature in features:
                                all_ids.append(feature["id"])
                        new_id = max(all_ids) + 1 if all_ids else 1
                        
                        new_feature = {
                            "id": new_id,
                            "title": new_title,
                            "description": new_description,
                            "priority": new_priority,
                            "date_ajout": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.features[new_status].append(new_feature)
                        st.success("✅ Fonctionnalité ajoutée !")
                        st.rerun()
                    else:
                        st.error("❌ Champs obligatoires manquants")
        
        with tab2:
            st.subheader("Modifier une fonctionnalité")
            if total_features > 0:
                all_features = []
                for status, features in st.session_state.features.items():
                    for feature in features:
                        all_features.append((feature["id"], f"{feature['title']} ({status})"))
                
                selected_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), "")
                )
                
                if selected_feature_id:
                    selected_feature = None
                    old_status = None
                    for status, features in st.session_state.features.items():
                        for feature in features:
                            if feature["id"] == selected_feature_id:
                                selected_feature = feature
                                old_status = status
                                break
                    
                    if selected_feature:
                        with st.form(key="edit_feature_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edit_title = st.text_input("Titre", value=selected_feature["title"])
                                edit_description = st.text_area("Description", value=selected_feature["description"], height=80)
                            
                            with col2:
                                edit_status = st.selectbox("Statut", ["À développer", "En cours", "Réalisé"], 
                                                         index=["À développer", "En cours", "Réalisé"].index(old_status))
                                edit_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"], 
                                                           index=["Haute", "Moyenne", "Basse"].index(selected_feature["priority"]))
                            
                            if st.form_submit_button("💾 Enregistrer"):
                                st.session_state.features[old_status] = [f for f in st.session_state.features[old_status] if f["id"] != selected_feature_id]
                                
                                updated_feature = {
                                    "id": selected_feature_id,
                                    "title": edit_title,
                                    "description": edit_description,
                                    "priority": edit_priority,
                                    "date_ajout": selected_feature["date_ajout"]
                                }
                                st.session_state.features[edit_status].append(updated_feature)
                                st.success("✅ Fonctionnalité modifiée !")
                                st.rerun()
            else:
                st.info("Aucune fonctionnalité à modifier.")
        
        with tab3:
            st.subheader("Supprimer une fonctionnalité")
            if total_features > 0:
                all_features = []
                for status, features in st.session_state.features.items():
                    for feature in features:
                        all_features.append((feature["id"], f"{feature['title']} ({status})"))
                
                delete_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à supprimer",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), ""),
                    key="delete_select"
                )
                
                if delete_feature_id:
                    if st.button("🗑️ Supprimer", type="secondary", use_container_width=True):
                        for status, features in st.session_state.features.items():
                            st.session_state.features[status] = [f for f in features if f["id"] != delete_feature_id]
                        st.success("✅ Fonctionnalité supprimée !")
                        st.rerun()
            else:
                st.info("Aucune fonctionnalité à supprimer.")

    # Pied de page
    st.markdown("---")
    st.caption("TG-Hire IA - Roadmap Fonctionnelle v1.0")

    # Activer le débogage si nécessaire
    if st.sidebar.button("🔧 Activer le Débogage"):
        debug_session_state()

# Protéger les pages dans pages/ (arrête l'exécution si non connecté)
if not st.session_state.logged_in:
    st.stop()