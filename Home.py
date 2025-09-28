import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# --- CONFIGURATION ---
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1fodJWGccSaDmlSEDkJblZoQE-lcifxpnOg5RYf3ovTg/edit?gid=0#gid=0"
USERS_WORKSHEET_NAME = "Logininfo"
FEATURES_WORKSHEET_NAME = "Features"

# --- GESTION DE LA CONNEXION GOOGLE SHEETS ---
@st.cache_resource
def get_gsheet_client():
    """Crée et retourne un client gspread authentifié."""
    try:
        service_account_info = {
            "type": st.secrets["GCP_TYPE"], "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"], "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n').strip(),
            "client_email": st.secrets["GCP_CLIENT_EMAIL"], "client_id": st.secrets["GCP_CLIENT_ID"],
            "auth_uri": st.secrets["GCP_AUTH_URI"], "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_CERT_URL"], "client_x509_cert_url": st.secrets["GCP_CLIENT_CERT_URL"]
        }
        return gspread.service_account_from_dict(service_account_info)
    except Exception as e:
        st.error(f"❌ Erreur de connexion à Google Sheets. Vérifiez vos secrets. Détails: {e}")
        return None

# --- INITIALISATION DE L'ÉTAT DE SESSION ---
if 'features' not in st.session_state: st.session_state.features = {"À développer": [], "En cours": [], "Réalisé": []}
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_user" not in st.session_state: st.session_state.current_user = ""
if "users" not in st.session_state: st.session_state.users = {}
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False

# --- FONCTIONS DE GESTION DES DONNÉES ---
def load_users_from_gsheet():
    """Charge les utilisateurs depuis Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc: return {}
        spreadsheet = gc.open_by_url(USERS_SHEET_URL)
        worksheet = spreadsheet.worksheet(USERS_WORKSHEET_NAME)
        records = worksheet.get_all_records()
        return {str(r.get("email", "")).strip().lower(): {"password": str(r.get("password", "")), "name": str(r.get("name", ""))} for r in records if r.get("email")}
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des utilisateurs: {e}")
        return {}

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
        st.error(f"La feuille '{FEATURES_WORKSHEET_NAME}' est introuvable.")
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
        all_features = [
            {**feature, 'status': status}
            for status, features_list in st.session_state.features.items()
            for feature in features_list
        ]
        if all_features:
            df = pd.DataFrame(all_features)[['id', 'title', 'description', 'priority', 'status', 'date_ajout']]
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        else:
            worksheet.clear()
            worksheet.update_row(1, ['id', 'title', 'description', 'priority', 'status', 'date_ajout'])
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde : {e}")

# --- STYLES CSS ---
st.markdown("""
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    
    /* MODIFICATION : Styles pour le message de bienvenue centré */
    .welcome-message {
        text-align: center;
        margin: 10px 0;
    }
    .welcome-text {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 0;
    }
    .user-name {
        font-size: 18px;
        font-weight: bold;
        color: #1f77b4; /* Bleu Streamlit */
        margin-top: 0;
    }
    /* Adapte la couleur du nom au mode sombre */
    html[data-theme='dark'] .user-name {
        color: #5dade2;
    }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT INITIAL DES UTILISATEURS ---
if not st.session_state.users:
    st.session_state.users = load_users_from_gsheet()

# --- PAGE DE CONNEXION ---
if not st.session_state.logged_in:
    st.set_page_config(page_title="TG-Hire IA - Connexion", layout="centered")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("tgcc.png", use_container_width=True)
        with st.form("login_form"):
            st.subheader("Connexion")
            email = st.text_input("Adresse Email").lower().strip()
            password = st.text_input("Mot de Passe", type="password")
            if st.form_submit_button("Se Connecter", use_container_width=True):
                if email in st.session_state.users and st.session_state.users[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = st.session_state.users[email]["name"]
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")
    st.stop()

# --- PAGE PRINCIPALE (APRÈS CONNEXION) ---
else:
    if not st.session_state.data_loaded:
        with st.spinner("Chargement des fonctionnalités..."):
            st.session_state.features = load_features_from_gsheet()
        st.session_state.data_loaded = True

    st.set_page_config(page_title="TG-Hire IA - Roadmap", layout="wide", initial_sidebar_state="expanded")

    # --- BARRE LATÉRALE (MODIFIÉE) ---
    with st.sidebar:
        st.image("tgcc.png", use_container_width=True)
        st.markdown("---")
        # MODIFICATION : Utilisation du nouveau style CSS pour le message de bienvenue
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
            st.session_state.data_loaded = False
            st.rerun()

    # --- CONTENU PRINCIPAL ---
    st.title("📊 Roadmap Fonctionnelle")
    st.markdown("---")

    # --- TABLEAU KANBAN (MODIFIÉ) ---
    col1, col2, col3 = st.columns(3)
    statuses = {"À développer": "📝", "En cours": "⏳", "Réalisé": "✅"}
    priority_colors = {"Haute": "🔴", "Moyenne": "🟠", "Basse": "🟢"}

    for status, emoji in statuses.items():
        if status == "À développer": col = col1
        elif status == "En cours": col = col2
        else: col = col3

        with col:
            st.header(f"{emoji} {status}")
            if st.session_state.features.get(status):
                for feature in st.session_state.features[status]:
                    # MODIFICATION : Utilisation de st.expander pour des cartes pliables
                    with st.expander(f"{priority_colors.get(feature['priority'], '⚪️')} **{feature['title']}**"):
                        st.markdown(f"*{feature['description']}*")
                        st.caption(f"Ajouté le : {feature.get('date_ajout', 'N/A')}")
            else:
                st.info(f"Aucune tâche dans '{status}'.")

    # --- TAUX DE RÉALISATION ---
    st.markdown("---")
    realise_count = len(st.session_state.features.get("Réalisé", []))
    total_count = sum(len(features) for features in st.session_state.features.values())

    if total_count > 0:
        completion_rate = realise_count / total_count
        st.subheader(f"Taux de Réalisation : {completion_rate:.1%}")
        st.progress(completion_rate)
    else:
        st.subheader("Taux de Réalisation : N/A")
        st.progress(0)

    # --- GESTION DES FONCTIONNALITÉS ---
    with st.expander("⚙️ Gérer les fonctionnalités", expanded=False):
        # ... (le code de gestion reste identique)
        form_tab1, form_tab2, form_tab3 = st.tabs(["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"])
        # (votre code pour ajouter, modifier, supprimer reste ici)

    st.caption("TG-Hire IA - Roadmap Fonctionnelle v2.2")