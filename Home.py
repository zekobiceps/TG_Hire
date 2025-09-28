import streamlit as st
import os
import sys
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# Optionnel: Ajouter le répertoire racine au chemin de recherche
# sys.path.append(os.path.dirname(__file__))
# from utils import *

# --- CONFIGURATION ---
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fodJWGccSaDmlSEDkJblZoQE-lcifxpnOg5RYf3ovTg/edit?gid=0#gid=0"
USERS_WORKSHEET_NAME = "Logininfo"

# --- INITIALISATION DE L'ÉTAT DE SESSION ---
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

# --- FONCTIONS ---
def load_users_from_gsheet():
    """Charge les utilisateurs depuis Google Sheets en utilisant les secrets Streamlit."""
    try:
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n').strip(), 
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets["GCP_CLIENT_ID"],
            "auth_uri": st.secrets["GCP_AUTH_URI"],
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_CERT_URL"],
            "client_x509_cert_url": st.secrets["GCP_CLIENT_CERT_URL"]
        }
        
        gc = gspread.service_account_from_dict(service_account_info)
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(USERS_WORKSHEET_NAME)
        
        records = worksheet.get_all_records()
        
        users = {}
        for record in records:
            email = record.get("email", "").strip().lower()
            password = record.get("password", "").strip()
            name = record.get("name", "").strip()
            if email and password and name:
                users[email] = {"password": password, "name": name}
        
        return users
    except KeyError as e:
        st.error(f"❌ Clé de secret manquante : {e}. Vérifiez les secrets GCP dans Streamlit Cloud.")
        return {}
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des utilisateurs depuis Google Sheets : {e}")
        return {}

def debug_session_state():
    """Affiche l'état actuel de la session pour débogage."""
    with st.expander("🔧 Mode Débogage (État de la Session)"):
        st.json(st.session_state)

# --- CHARGEMENT INITIAL ---
if not st.session_state.users:
    st.session_state.users = load_users_from_gsheet()

# --- STYLES CSS ---
st.markdown("""
    <style>
    /* Cacher les éléments par défaut de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Style pour les cartes de fonctionnalités (Kanban) */
    .feature-card {
        background: #ffffff;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #6c757d;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.3s ease-in-out;
    }
    .feature-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .feature-card p {
        margin: 5px 0 0 0;
        color: #495057;
    }
    .feature-card small {
        color: #6c757d;
    }
    .priority-Haute { border-left-color: #dc3545; }
    .priority-Moyenne { border-left-color: #ffc107; }
    .priority-Basse { border-left-color: #28a745; }
    
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


# --- PAGE DE CONNEXION ---
if not st.session_state.logged_in:
    st.set_page_config(
        page_title="TG-Hire IA - Connexion",
        page_icon="📊",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.image("tgcc.png", use_container_width=True)
        
        with st.form("login_form"):
            st.subheader("Connexion")
            email = st.text_input("Adresse Email", key="login_email")
            password = st.text_input("Mot de Passe", type="password", key="login_password")
            
            if st.form_submit_button("Se Connecter", use_container_width=True):
                if email in st.session_state.users and st.session_state.users[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = st.session_state.users[email]["name"]
                    st.success("Connexion réussie !")
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")

# --- PAGE PRINCIPALE (APRÈS CONNEXION) ---
else:
    st.set_page_config(
        page_title="TG-Hire IA - Roadmap Fonctionnelle",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.image("tgcc.png", use_container_width=True)
        st.markdown("---")
        
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
            
        if st.button("🔧 Activer le Débogage", use_container_width=True):
            debug_session_state()

    # --- CONTENU PRINCIPAL ---
    st.title("📊 Roadmap Fonctionnelle")
    st.markdown("---")

    # --- TABLEAU KANBAN ---
    col1, col2, col3 = st.columns(3)

    # Colonne 1: À développer
    with col1:
        st.header("📝 À développer")
        for feature in st.session_state.features["À développer"]:
            st.markdown(f"""
                <div class="feature-card priority-{feature['priority']}">
                    <strong>{feature['title']}</strong>
                    <p>{feature['description']}</p>
                    <small>Ajouté le : {feature['date_ajout']} | Priorité : {feature['priority']}</small>
                </div>
            """, unsafe_allow_html=True)

    # Colonne 2: En cours
    with col2:
        st.header("⏳ En cours")
        if st.session_state.features["En cours"]:
            for feature in st.session_state.features["En cours"]:
                st.markdown(f"""
                    <div class="feature-card priority-{feature['priority']}">
                        <strong>{feature['title']}</strong>
                        <p>{feature['description']}</p>
                        <small>Ajouté le : {feature['date_ajout']} | Priorité : {feature['priority']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune tâche en cours.")

    # Colonne 3: Réalisé
    with col3:
        st.header("✅ Réalisé")
        if st.session_state.features["Réalisé"]:
            for feature in st.session_state.features["Réalisé"]:
                st.markdown(f"""
                    <div class="feature-card priority-{feature['priority']}">
                        <strong>{feature['title']}</strong>
                        <p>{feature['description']}</p>
                        <small>Ajouté le : {feature['date_ajout']} | Priorité : {feature['priority']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune tâche réalisée.")

    st.markdown("---")
    
    # --- GESTION DES FONCTIONNALITÉS ---
    with st.expander("⚙️ Gérer les fonctionnalités (Ajouter, Modifier, Supprimer)", expanded=False):
        
        # Obtenir le nombre total de fonctionnalités pour les vérifications
        total_features = sum(len(features) for features in st.session_state.features.values())
        
        form_tab1, form_tab2, form_tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])

        # Onglet Ajouter
        with form_tab1:
            with st.form(key="add_feature_form"):
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    new_title = st.text_input("Titre", key="new_title")
                    new_description = st.text_area("Description", key="new_description", height=100)
                with col_form2:
                    new_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"], key="new_priority")
                
                if st.form_submit_button("Ajouter la fonctionnalité", use_container_width=True):
                    if new_title and new_description:
                        max_id = max((f["id"] for status in st.session_state.features.values() for f in status), default=0)
                        new_feature = {
                            "id": max_id + 1,
                            "title": new_title,
                            "description": new_description,
                            "priority": new_priority,
                            "date_ajout": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.features["À développer"].append(new_feature)
                        st.success("✅ Fonctionnalité ajoutée !")
                        st.rerun()
                    else:
                        st.error("Veuillez remplir le titre et la description.")

        # Onglet Modifier
        with form_tab2:
            if total_features > 0:
                all_features = [(f["id"], f"{f['title']} ({status})") for status, features in st.session_state.features.items() for f in features]
                
                selected_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à modifier",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), ""),
                    key="edit_select"
                )
                
                if selected_feature_id:
                    # Trouver la fonctionnalité et son statut actuel
                    selected_feature, old_status = next(
                        ((f, s) for s, fs in st.session_state.features.items() for f in fs if f["id"] == selected_feature_id), 
                        (None, None)
                    )
                    
                    if selected_feature:
                        with st.form(key="edit_feature_form"):
                            col_edit1, col_edit2 = st.columns(2)
                            with col_edit1:
                                edit_title = st.text_input("Titre", value=selected_feature["title"])
                                edit_description = st.text_area("Description", value=selected_feature["description"], height=100)
                            with col_edit2:
                                edit_status = st.selectbox("Statut", ["À développer", "En cours", "Réalisé"], 
                                                           index=["À développer", "En cours", "Réalisé"].index(old_status))
                                edit_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"], 
                                                             index=["Haute", "Moyenne", "Basse"].index(selected_feature["priority"]))
                            
                            if st.form_submit_button("💾 Enregistrer les modifications", use_container_width=True):
                                # Supprimer l'ancienne version
                                st.session_state.features[old_status] = [f for f in st.session_state.features[old_status] if f["id"] != selected_feature_id]
                                
                                # Ajouter la version mise à jour
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
        
        # Onglet Supprimer
        with form_tab3:
            if total_features > 0:
                all_features = [(f["id"], f"{f['title']} ({status})") for status, features in st.session_state.features.items() for f in features]
                
                delete_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à supprimer",
                    options=[f[0] for f in all_features],
                    format_func=lambda x: next((f[1] for f in all_features if f[0] == x), ""),
                    key="delete_select"
                )
                
                if delete_feature_id and st.button("🗑️ Confirmer la suppression", type="primary", use_container_width=True):
                    for status in st.session_state.features:
                        st.session_state.features[status] = [f for f in st.session_state.features[status] if f["id"] != delete_feature_id]
                    st.success("✅ Fonctionnalité supprimée !")
                    st.rerun()
            else:
                st.info("Aucune fonctionnalité à supprimer.")

    st.caption("TG-Hire IA - Roadmap Fonctionnelle v1.1 (Kanban View)")

# Arrêter l'exécution si l'utilisateur n'est pas connecté pour protéger les autres pages
if not st.session_state.logged_in:
    st.stop()