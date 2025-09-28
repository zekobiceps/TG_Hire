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
### AJOUT ###
FEATURES_WORKSHEET_NAME = "Features" # Nom de la feuille pour les tâches

# --- INITIALISATION DE L'ÉTAT DE SESSION ---
if 'features' not in st.session_state:
    st.session_state.features = {"À développer": [], "En cours": [], "Réalisé": []}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "users" not in st.session_state:
    st.session_state.users = {}
### AJOUT ###
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    
### AJOUT : Amélioration de la connexion à Google Sheets ###
@st.cache_resource
def get_gsheet_client():
    """Crée et retourne un client gspread authentifié pour éviter les reconnexions inutiles."""
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
        return gspread.service_account_from_dict(service_account_info)
    except Exception as e:
        st.error(f"❌ Erreur de connexion à Google Sheets. Vérifiez vos secrets. Détails: {e}")
        return None

# --- FONCTIONS ---
def load_users_from_gsheet():
    """Charge les utilisateurs depuis Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc: return {}
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(USERS_WORKSHEET_NAME)
        records = worksheet.get_all_records()
        users = {}
        for record in records:
            email = str(record.get("email", "")).strip().lower()
            password = str(record.get("password", "")).strip()
            name = str(record.get("name", "")).strip()
            if email and password and name:
                users[email] = {"password": password, "name": name}
        return users
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des utilisateurs: {e}")
        return {}

### AJOUT : Fonctions pour charger et sauvegarder les tâches ###
def load_features_from_gsheet():
    """Charge les fonctionnalités depuis la feuille Google Sheets."""
    features_by_status = {"À développer": [], "En cours": [], "Réalisé": []}
    try:
        gc = get_gsheet_client()
        if not gc: return features_by_status
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(FEATURES_WORKSHEET_NAME)
        records = worksheet.get_all_records()
        for record in records:
            record['id'] = int(record['id']) if str(record.get('id')).isdigit() else 0
            status = record.get("status", "À développer")
            if status in features_by_status:
                features_by_status[status].append(record)
        return features_by_status
    except gspread.exceptions.WorksheetNotFound:
         st.error(f"La feuille '{FEATURES_WORKSHEET_NAME}' est introuvable. Veuillez la créer.")
         return features_by_status
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des fonctionnalités : {e}")
        return features_by_status

def save_features_to_gsheet():
    """Sauvegarde toutes les fonctionnalités dans la feuille Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc: return
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(FEATURES_WORKSHEET_NAME)
        all_features = []
        for status, features_list in st.session_state.features.items():
            for feature in features_list:
                feature_copy = feature.copy()
                feature_copy['status'] = status
                all_features.append(feature_copy)

        if all_features:
            df = pd.DataFrame(all_features)
            df = df[['id', 'title', 'description', 'priority', 'status', 'date_ajout']]
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        else:
            worksheet.clear()
            worksheet.update_row(1, ['id', 'title', 'description', 'priority', 'status', 'date_ajout'])
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde des fonctionnalités : {e}")

def debug_session_state():
    """Affiche l'état actuel de la session pour débogage."""
    with st.expander("🔧 Mode Débogage (État de la Session)"):
        st.json(st.session_state)

# --- CHARGEMENT INITIAL DES UTILISATEURS ---
if not st.session_state.users:
    st.session_state.users = load_users_from_gsheet()

# --- STYLES CSS (conservés tels quels) ---
st.markdown("""
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    .feature-card {
        padding: 12px; border-radius: 8px; margin-bottom: 10px;
        border-left: 5px solid; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        background-color: var(--secondary-background-color);
        color: var(--text-color);
    }
    .feature-card p, .feature-card small { color: var(--text-color); opacity: 0.8; }
    .feature-card strong { color: var(--text-color); }
    .priority-Haute { border-left-color: #dc3545; }
    .priority-Moyenne { border-left-color: #ffc107; }
    .priority-Basse { border-left-color: #28a745; }
    /* Styles pour le message de bienvenue */
    .welcome-message { text-align: center; margin: 10px 0; }
    .welcome-text { font-size: 14px; font-weight: bold; margin-bottom: 0; }
    .user-name { font-size: 16px; font-weight: bold; color: #1f77b4; margin-top: 0; }
    html[data-theme='dark'] .user-name { color: #5dade2; }
    </style>
""", unsafe_allow_html=True)

# --- PAGE DE CONNEXION ---
if not st.session_state.logged_in:
    st.set_page_config(page_title="TG-Hire IA - Connexion", layout="centered")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("tgcc.png", use_container_width=True)
        with st.form("login_form"):
            st.subheader("Connexion")
            email = st.text_input("Adresse Email", key="login_email").lower().strip()
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
    ### AJOUT : Logique de chargement des données au début de la session ###
    if not st.session_state.data_loaded:
        with st.spinner("Chargement des fonctionnalités..."):
            st.session_state.features = load_features_from_gsheet()
        st.session_state.data_loaded = True

    st.set_page_config(page_title="TG-Hire IA - Roadmap", layout="wide", initial_sidebar_state="expanded")
    
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.image("tgcc.png", use_container_width=True)
        st.markdown("---")
        st.markdown(f'<div class="welcome-message"><p class="welcome-text">Bienvenue</p><p class="user-name">{st.session_state.current_user}</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            st.session_state.data_loaded = False # MODIFIÉ : Réinitialisation
            st.rerun()
        if st.button("🔧 Activer le Débogage", use_container_width=True):
            debug_session_state()

    # --- CONTENU PRINCIPAL ---
    st.title("📊 Roadmap Fonctionnelle")
    st.markdown("---")

    # --- TABLEAU KANBAN ---
    col1, col2, col3 = st.columns(3)
    statuses = {"À développer": "📝", "En cours": "⏳", "Réalisé": "✅"}

    for status, emoji in statuses.items():
        if status == "À développer": col = col1
        elif status == "En cours": col = col2
        else: col = col3
        
        with col:
            st.header(f"{emoji} {status}")
            if st.session_state.features.get(status):
                for feature in st.session_state.features[status]:
                    st.markdown(f"""
                        <div class="feature-card priority-{feature['priority']}">
                            <strong>{feature['title']}</strong>
                            <p>{feature['description']}</p>
                            <small>Ajouté le : {feature.get('date_ajout', 'N/A')} | Priorité : {feature['priority']}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"Aucune tâche dans '{status}'.")

    st.markdown("---")
    
    # --- GESTION DES FONCTIONNALITÉS ---
    with st.expander("⚙️ Gérer les fonctionnalités (Ajouter, Modifier, Supprimer)", expanded=False):
        total_features = sum(len(features) for features in st.session_state.features.values())
        form_tab1, form_tab2, form_tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])

        # Onglet Ajouter
        with form_tab1:
            with st.form(key="add_feature_form"):
                new_title = st.text_input("Titre")
                new_description = st.text_area("Description", height=100)
                new_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"])
                if st.form_submit_button("Ajouter la fonctionnalité", use_container_width=True):
                    if new_title and new_description:
                        all_ids = [f["id"] for status_list in st.session_state.features.values() for f in status_list]
                        new_id = max(all_ids, default=0) + 1
                        new_feature = {
                            "id": new_id, "title": new_title, "description": new_description,
                            "priority": new_priority, "date_ajout": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.features["À développer"].append(new_feature)
                        save_features_to_gsheet() ### AJOUT ###
                        st.success("✅ Fonctionnalité ajoutée !")
                        st.rerun()
                    else:
                        st.error("Veuillez remplir le titre et la description.")

        # Onglet Modifier
        with form_tab2:
            all_features_flat = [(f, s) for s, fl in st.session_state.features.items() for f in fl]
            if all_features_flat:
                selected_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité",
                    options=[f[0]["id"] for f in all_features_flat],
                    format_func=lambda fid: next(f"{f[0]['title']} ({f[1]})" for f in all_features_flat if f[0]["id"] == fid),
                    index=None, placeholder="Choisissez une tâche..."
                )
                if selected_feature_id:
                    feature_to_edit, old_status = next(((f, s) for f, s in all_features_flat if f["id"] == selected_feature_id), (None, None))
                    if feature_to_edit:
                        with st.form(key="edit_feature_form"):
                            edit_title = st.text_input("Titre", value=feature_to_edit["title"])
                            edit_description = st.text_area("Description", value=feature_to_edit["description"], height=100)
                            edit_status = st.selectbox("Statut", list(statuses.keys()), index=list(statuses.keys()).index(old_status))
                            edit_priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse"], index=["Haute", "Moyenne", "Basse"].index(feature_to_edit["priority"]))
                            if st.form_submit_button("💾 Enregistrer les modifications", use_container_width=True):
                                st.session_state.features[old_status] = [f for f in st.session_state.features[old_status] if f["id"] != selected_feature_id]
                                updated_feature = {**feature_to_edit, "title": edit_title, "description": edit_description, "priority": edit_priority}
                                st.session_state.features[edit_status].append(updated_feature)
                                save_features_to_gsheet() ### AJOUT ###
                                st.success("✅ Fonctionnalité modifiée !")
                                st.rerun()
            else:
                st.info("Aucune fonctionnalité à modifier.")

        # Onglet Supprimer
        with form_tab3:
            all_features_flat = [(f, s) for s, fl in st.session_state.features.items() for f in fl]
            if all_features_flat:
                delete_feature_id = st.selectbox(
                    "Sélectionner une fonctionnalité à supprimer",
                    options=[f[0]["id"] for f in all_features_flat],
                    format_func=lambda fid: next(f"{f[0]['title']} ({f[1]})" for f in all_features_flat if f[0]["id"] == fid),
                    key="delete_select", index=None, placeholder="Choisissez une tâche..."
                )
                if delete_feature_id and st.button("🗑️ Confirmer la suppression", type="primary", use_container_width=True):
                    for status in st.session_state.features:
                        st.session_state.features[status] = [f for f in st.session_state.features[status] if f["id"] != delete_feature_id]
                    save_features_to_gsheet() ### AJOUT ###
                    st.success("✅ Fonctionnalité supprimée !")
                    st.rerun()
            else:
                st.info("Aucune fonctionnalité à supprimer.")

    st.caption("TG-Hire IA - Roadmap Fonctionnelle v2.0 (Persistante)")

# Arrêter l'exécution si l'utilisateur n'est pas connecté pour protéger les autres pages
# (Cette ligne n'est plus nécessaire car la logique est gérée au début)
# if not st.session_state.logged_in:
#    st.stop()