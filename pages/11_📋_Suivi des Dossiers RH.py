import streamlit as st
import pandas as pd
import io
import json 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os

# --- IMPORTS POUR GOOGLE API ---
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import gspread
except ImportError:
    st.error("❌ Bibliothèques Google API manquantes. Exécutez : pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib gspread")
    st.stop()

# --- CONFIGURATION GOOGLE SHEETS ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1p8gSC84LZllAaTT6F88xH8nVqZS9jLiOlqiPXHLmJhU/edit"
WORKSHEET_NAME = "HR_Dossiers"
HISTORY_SHEET_NAME = "Relance_History"
SCHEDULED_SHEET_NAME = "Scheduled_Relances"

# Configuration de la page
st.set_page_config(
    page_title="Suivi des Dossiers RH - TGCC",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #1e88e5;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .complete-status {
        background-color: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .incomplete-status {
        background-color: #f8d7da;
        color: #721c24;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 4px;
        padding: 10px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #e3f2fd;
        border-bottom: 2px solid #1e88e5;
    }
    
    /* Optimisation des tableaux */
    .stDataFrame {
        font-size: 0.85rem;
    }
    .stDataFrame table {
        margin: 0 auto;
        max-width: 95%;
    }
    .stDataFrame th {
        text-align: center !important;
        padding: 8px 4px !important;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .stDataFrame td {
        text-align: center !important;
        padding: 6px 4px !important;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Définition des documents RH standard
DOCUMENTS_RH = [
    "Curriculum vitae actualisé",
    "3 copies certifiées conformes des diplômes obtenus et/ou des certificats de scolarité",
    "Copie certifiée conforme des certificats de travail des employeurs précédents",
    "3 derniers bulletins de paie délivrés par l'employeur précédent",
    "Certificat de résidence datant d'au moins 3 mois",
    "Copie certifiée conforme de votre C.I.N.",
    "Extrait d'acte de naissance en français",
    "Copie de la carte C.N.S.S (ou copie de la C.I.N + 2 photos d'identité récentes)",
    "Fiche anthropométrique originale datant d'au moins 3 mois",
    "2 photos d'identité identique datant d'au moins 3 mois (Format standard)",
    "Copie du permis de conduire",
    "Relevé d'Identité Bancaire (RIB) comportant les 24 chiffres",
    "Copie certifiée conforme de l'acte de mariage",
    "Copie de la CIN du conjoint",
    "Extrait d'acte de naissance de chaque enfant",
    "Fiche de renseignement dûment remplie et signée par le salarié",
    "Contrat de travail en double exemplaire à signer et à légaliser",
    "Check-list d'intégration signée par votre N+1/tuteur/la DSI et la DQHSE",
    "Annexes du code de bonne conduite signées par vos soins",
    "Photo au format digital, 600*600 pixels sur fond blanc",
    "Récapitulatif de carrière CNSS (téléchargeable sur l'application MACNSS)"
]

# -------------------- FONCTIONS D'AUTHENTIFICATION GOOGLE --------------------
def get_google_credentials():
    """Crée les identifiants à partir des secrets Streamlit."""
    try:
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets.get("GCP_PRIVATE_KEY_ID", ""),
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'),
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets.get("GCP_CLIENT_ID", ""),
            "auth_uri": st.secrets.get("GCP_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets.get("GCP_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": st.secrets.get("GCP_CLIENT_CERT_URL", "")
        }
        return service_account.Credentials.from_service_account_info(service_account_info)
    except Exception as e:
        st.error(f"❌ Erreur de format des secrets Google: {e}")
        return None

def get_gsheet_client():
    """Authentification pour Google Sheets."""
    try:
        creds = get_google_credentials()
        if creds:
            scoped_creds = creds.with_scopes([
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ])
            gc = gspread.Client(auth=scoped_creds)
            return gc
    except Exception as e:
        st.error(f"❌ Erreur d'authentification Google Sheets: {str(e)}")
    return None

# -------------------- FONCTIONS GOOGLE SHEETS --------------------
@st.cache_data(ttl=60)  # Cache pendant 1 minute
def load_data_from_gsheet():
    """Charge les données depuis Google Sheets"""
    try:
        gc = get_gsheet_client()
        if not gc:
            return pd.DataFrame()
        
        sheet = gc.open_by_url(GOOGLE_SHEET_URL).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        
        if not data:
            # Créer les en-têtes si la feuille est vide
            headers = ['Nom', 'Prénom', 'Poste', 'Service', 'Téléphone', 'Email', 'Date_integration', 
                      'Documents_manquants', 'Statut', 'Derniere_relance', 'Nombre_relances',
                      'Date_creation', 'Date_modification']
            sheet.clear()
            sheet.append_row(headers)
            return pd.DataFrame(columns=headers)
        
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données Google Sheets: {e}")
        return pd.DataFrame()

def save_data_to_gsheet(df):
    """Sauvegarde les données dans Google Sheets"""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
        
        sheet = gc.open_by_url(GOOGLE_SHEET_URL).worksheet(WORKSHEET_NAME)
        
        # Vider la feuille et réécrire toutes les données
        sheet.clear()
        
        # Ajouter les en-têtes
        headers = list(df.columns)
        sheet.append_row(headers)
        
        # Ajouter les données
        if len(df) > 0:
            values = df.fillna('').values.tolist()
            sheet.append_rows(values)
        
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde Google Sheets: {e}")
        return False


def _load_df_from_worksheet(worksheet_name, default_headers=None):
    """Charge un DataFrame depuis une worksheet spécifique. Si la worksheet n'existe pas,
    renvoie un DataFrame vide avec les en-têtes fournis (si fournis).
    """
    try:
        gc = get_gsheet_client()
        if not gc:
            return pd.DataFrame(columns=default_headers) if default_headers else pd.DataFrame()

        sheet = gc.open_by_url(GOOGLE_SHEET_URL)
        try:
            ws = sheet.worksheet(worksheet_name)
        except Exception:
            # Worksheet manquante
            return pd.DataFrame(columns=default_headers) if default_headers else pd.DataFrame()

        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=default_headers) if default_headers else pd.DataFrame()

        return pd.DataFrame(data)
    except Exception as e:
        # Ne pas interrompre l'app: afficher en console et renvoyer vide
        print(f"Erreur chargement worksheet {worksheet_name}: {e}")
        return pd.DataFrame(columns=default_headers) if default_headers else pd.DataFrame()


def _save_df_to_worksheet(df, worksheet_name):
    """Sauvegarde un DataFrame dans une worksheet spécifique; crée la worksheet si nécessaire."""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False

        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        try:
            ws = sh.worksheet(worksheet_name)
            ws.clear()
        except Exception:
            # créer la worksheet si elle n'existe pas
            rows = max(10, len(df) + 10)
            cols = max(1, len(df.columns))
            ws = sh.add_worksheet(title=worksheet_name, rows=str(rows), cols=str(cols))

        headers = list(df.columns)
        ws.append_row(headers)
        if len(df) > 0:
            ws.append_rows(df.fillna('').values.tolist())
        return True
    except Exception as e:
        print(f"Erreur sauvegarde worksheet {worksheet_name}: {e}")
        return False


def load_relance_history_from_gsheet():
    headers = ['Date', 'Collaborateur', 'Email', 'Documents_relances', 'Statut_envoi', 'Email_body']
    return _load_df_from_worksheet(HISTORY_SHEET_NAME, default_headers=headers)


def save_relance_history_to_gsheet(df):
    return _save_df_to_worksheet(df, HISTORY_SHEET_NAME)


def load_scheduled_relances_from_gsheet():
    headers = ['Date_programmee', 'Collaborateur', 'Email', 'Documents_relances', 'Date_limite', 'Statut', 'Actor_email', 'CC', 'Email_body']
    return _load_df_from_worksheet(SCHEDULED_SHEET_NAME, default_headers=headers)


def save_scheduled_relances_to_gsheet(df):
    return _save_df_to_worksheet(df, SCHEDULED_SHEET_NAME)


def add_row_to_gsheet(new_row_data):
    """Ajoute une nouvelle ligne à Google Sheets"""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
        
        sheet = gc.open_by_url(GOOGLE_SHEET_URL).worksheet(WORKSHEET_NAME)
        sheet.append_row(new_row_data)
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de l'ajout de ligne Google Sheets: {e}")
        return False

def update_row_in_gsheet(row_index, updated_data):
    """Met à jour une ligne spécifique dans Google Sheets"""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
        
        sheet = gc.open_by_url(GOOGLE_SHEET_URL).worksheet(WORKSHEET_NAME)
        
        # row_index + 2 car : +1 pour l'index Python (0-based) vers Google Sheets (1-based), +1 pour ignorer l'en-tête
        for col_idx, value in enumerate(updated_data, start=1):
            # Convertir les valeurs NaN en chaînes vides
            cell_value = '' if pd.isna(value) else str(value)
            sheet.update_cell(row_index + 2, col_idx, cell_value)
        
        return True
    except Exception as e:
        # Log l'erreur sans afficher le message transitoire
        print(f"Erreur Google Sheets (masquée): {e}")
        return False
# --- Normalisation centralisée (définie une seule fois) ---
def normalize_hr_database(df):
    """Normalise les colonnes et types du DataFrame HR pour éviter les problèmes
    si l'en-tête de la feuille change entre 'Service' et 'Affectation'."""
    if df is None:
        return df
    if isinstance(df, pd.DataFrame) and df.empty:
        return df
    # Supporter à la fois 'Service' et 'Affectation'
    try:
        cols = list(df.columns)
    except Exception:
        return df
    if 'Affectation' in df.columns and 'Service' not in df.columns:
        df['Service'] = df['Affectation']
    if 'Service' in df.columns and 'Affectation' not in df.columns:
        df['Affectation'] = df['Service']
    # Nombre_relances en int
    if 'Nombre_relances' in df.columns:
        if isinstance(df['Nombre_relances'], pd.Series):
            df['Nombre_relances'] = pd.to_numeric(df['Nombre_relances'], errors='coerce')
            df['Nombre_relances'] = df['Nombre_relances'].fillna(0).astype(int)
        else:
            df['Nombre_relances'] = 0
    else:
        df['Nombre_relances'] = 0
    # Documents_manquants assurer string JSON
    if 'Documents_manquants' in df.columns:
        if isinstance(df['Documents_manquants'], pd.Series):
            df['Documents_manquants'] = df['Documents_manquants'].fillna('[]').astype(str)
        else:
            df['Documents_manquants'] = '[]'
    else:
        df['Documents_manquants'] = '[]'
    return df

# Initialisation des données en session
if 'hr_database' not in st.session_state:
    st.session_state.hr_database = load_data_from_gsheet()
    # Normaliser les colonnes/types immédiatement
    st.session_state.hr_database = normalize_hr_database(st.session_state.hr_database)

# (Le message de succès après rechargement est affiché localement près du bouton Recharger)

if 'relance_history' not in st.session_state:
    # Charger depuis Google Sheets si disponible
    loaded_hist = load_relance_history_from_gsheet()
    if loaded_hist is not None and len(loaded_hist) > 0:
        st.session_state.relance_history = loaded_hist
    else:
        st.session_state.relance_history = pd.DataFrame(columns=[
            'Date', 'Collaborateur', 'Email', 'Documents_relances', 'Statut_envoi', 'Email_body'
        ])

if 'scheduled_relances' not in st.session_state:
    loaded_sched = load_scheduled_relances_from_gsheet()
    if loaded_sched is not None and len(loaded_sched) > 0:
        st.session_state.scheduled_relances = loaded_sched
    else:
        st.session_state.scheduled_relances = pd.DataFrame(columns=[
            'Date_programmee', 'Collaborateur', 'Email', 'Documents_relances', 'Date_limite', 'Statut', 'Actor_email', 'CC', 'Email_body'
        ])

    # Debug helper removed as requested

# Fonctions utilitaires
def save_data():
    """Sauvegarde les données dans Google Sheets"""
    return save_data_to_gsheet(st.session_state.hr_database)

def load_data():
    """Recharge les données depuis Google Sheets"""
    try:
        # Lire directement depuis la worksheet (bypass du cache) puis normaliser
        raw = _load_df_from_worksheet(WORKSHEET_NAME)
        if raw is None:
            return False
        st.session_state.hr_database = normalize_hr_database(raw)
        return True
    except Exception as e:
        st.error(f"Erreur lors du rechargement: {e}")
        return False


def safe_rerun():
    """Fallback-safe rerun helper for Streamlit.
    Some Streamlit builds may not expose `st.experimental_rerun`. This wrapper
    tries available rerun functions and otherwise sets a session flag and stops
    the script to allow the front-end to refresh on next interaction.
    """
    try:
        if hasattr(st, 'experimental_rerun'):
            return st.experimental_rerun()
        # Older/newer variants
        if hasattr(st, 'rerun'):
            return st.rerun()
        # Fallback: indicate success and stop execution so the UI can refresh
        st.session_state['_last_reload_successful'] = True
        try:
            return st.stop()
        except Exception:
            return None
    except Exception:
        # Ensure we at least set the flag if rerun isn't available
        st.session_state['_last_reload_successful'] = True
        try:
            st.stop()
        except Exception:
            pass

def calculate_completion_percentage():
    """Calcule le pourcentage de dossiers complets"""
    if len(st.session_state.hr_database) == 0:
        return 0
    complete_count = len(st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'Complet'])
    return (complete_count / len(st.session_state.hr_database)) * 100

def get_missing_documents_count(documents_json):
    """Compte le nombre de documents manquants"""
    try:
        docs = json.loads(documents_json)
        return len(docs)
    except:
        return 0

def send_email_reminder(
    recipient_email,
    recipient_name,
    missing_docs,
    delay_date=None,
    custom_body=None,
    actor_email=None,
    cc_emails=None
):
    """Envoie un email de relance via SMTP.

    - actor_name / actor_email : informations facultatives de la personne qui déclenche l'envoi
      (utilisées pour Reply-To et pour afficher "Envoyé par" dans le corps).
    - cc_emails : chaîne séparée par des virgules ou liste d'emails à mettre en copie.
    """
    try:
        # Configuration SMTP - utiliser les secrets Streamlit
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        # Valeur par défaut pratique si l'utilisateur n'a pas encore ajouté le secret
        default_sender = "recrutement@tgcc.ma"
        sender_email = st.secrets.get("SENDER_EMAIL", default_sender)
        sender_password = st.secrets.get("SENDER_PASSWORD", "")
        
        if not sender_email or not sender_password:
            st.error("❌ Configuration email manquante. Veuillez configurer SENDER_EMAIL et SENDER_PASSWORD dans les secrets.")
            return False

        # Préparer la liste des CC
        cc_list = []
        if cc_emails:
            if isinstance(cc_emails, str):
                # séparer par virgule et nettoyer
                cc_list = [e.strip() for e in cc_emails.split(',') if e.strip()]
            elif isinstance(cc_emails, (list, tuple)):
                cc_list = [e.strip() for e in cc_emails if str(e).strip()]

        # Utiliser le corps personnalisé s'il est fourni, sinon utiliser le template par défaut
        if custom_body:
            body = custom_body
        else:
            # Créer le corps du message avec le template par défaut
            docs_list = '\n'.join([f"• {doc}" for doc in missing_docs])
            body = f"""Bonjour {recipient_name},

Merci de noter que votre dossier administratif RH demeure incomplet à ce jour.
Merci de remettre les éléments suivants afin de le compléter:

{docs_list}

Les documents doivent être envoyés via le pointeur chantier dans une enveloppe fermée, en mentionnant CONFIDENTIEL et A L'ATTENTION DE M.L'EQUIPE RECRUTEMENT.

Merci de noter que le dernier délai pour compléter votre dossier c'est le {delay_date if delay_date else (datetime.now() + timedelta(days=14)).strftime('%d/%m/%Y')}

Comptant sur votre précieuse collaboration.

Cordialement"""

        # Préfixer par qui envoie si un Reply-To est fourni (on utilise l'email)
        if actor_email:
            sender_info = actor_email
            body = f"Envoyé par : {sender_info}\n\n" + body

        # Créer le message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        if cc_list:
            message['Cc'] = ', '.join(cc_list)
        message['Subject'] = "URGENT: Complément du dossier administrative RH"

        # Reply-To vers la personne qui effectue l'envoi (facultatif)
        if actor_email:
            message.add_header('Reply-To', actor_email)

        message.attach(MIMEText(body, 'plain', 'utf-8'))

        # Destinataires effectifs
        recipients = [recipient_email] + cc_list

        # Envoyer l'email via SMTP
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Activer la sécurité
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, message.as_string())

        return True
    except Exception as e:
        st.error(f"Erreur lors de l'envoi de l'email via SMTP: {e}")
        return False

# Titre principal
st.markdown('<h1 class="main-header">📋 Suivi des Dossiers RH</h1>', unsafe_allow_html=True)
st.markdown("---")

# Créer les onglets
tab1, tab2, tab3 = st.tabs([
    "📊 Suivi Global",
    "👤 Gestion Collaborateur", 
    "📧 Relances Automatiques"
])

    # ============================
# ONGLET 1: SUIVI GLOBAL
# ============================
with tab1:
    st.header("📊 Vue d'ensemble des dossiers RH")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_collaborateurs = len(st.session_state.hr_database)
        st.metric("👥 Total Collaborateurs", total_collaborateurs)
    
    with col2:
        complete_count = len(st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'Complet'])
        st.metric("✅ Dossiers Complets", complete_count)
    
    with col3:
        incomplete_count = total_collaborateurs - complete_count
        st.metric("⏳ Dossiers En Cours", incomplete_count)
    
    with col4:
        completion_rate = calculate_completion_percentage()
        st.metric("📈 Taux de Complétude", f"{completion_rate:.1f}%")
    
    # Ne pas afficher la ligne de pourcentage demandée (supprimée)
    
    # Graphiques
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Graphique en secteurs - Répartition des statuts
        status_counts = st.session_state.hr_database['Statut'].value_counts()
        fig_pie = px.pie(
            values=status_counts.values, 
            names=status_counts.index,
            title="Répartition des Statuts",
            color_discrete_map={'Complet': '#28a745', 'En cours': '#ffc107'}
        )
        st.plotly_chart(fig_pie, width="stretch")
    
    with col_chart2:
        # Graphique en barres - Par affectation
        # Construire une colonne d'affichage 'Affectation_display' pour regrouper correctement
        tmp_hr = st.session_state.hr_database.copy()
        if 'Affectation' in tmp_hr.columns:
            tmp_hr['Affectation_display'] = tmp_hr['Affectation']
        else:
            tmp_hr['Affectation_display'] = tmp_hr['Service'] if 'Service' in tmp_hr.columns else ''
        service_stats = tmp_hr.groupby(['Affectation_display', 'Statut']).size().unstack(fill_value=0)

        # Guard: si aucune donnée disponible
        if service_stats.empty:
            st.info("Aucune donnée par service disponible pour l'instant.")
        else:
            df_service = service_stats.reset_index()
            # Déterminer les colonnes y disponibles (évite ShapeError si une colonne manque)
            desired_cols = ['Complet', 'En cours']
            y_cols = [c for c in desired_cols if c in service_stats.columns]

            if not y_cols:
                st.info("Aucune colonne de statut standard ('Complet'/'En cours') trouvée pour les services.")
            else:
                try:
                    # Déterminer la colonne d'axe X : préférer 'Affectation_display' puis 'Service'
                    if 'Affectation_display' in df_service.columns:
                        xcol = 'Affectation_display'
                    elif 'Service' in df_service.columns:
                        xcol = 'Service'
                    else:
                        # fallback sur la première colonne (sécurité)
                        xcol = df_service.columns[0]

                    fig_bar = px.bar(
                        df_service,
                        x=xcol,
                        y=y_cols,
                        title="Statuts par Affectation",
                        color_discrete_map={'Complet': '#28a745', 'En cours': '#ffc107'}
                    )
                    # Ajouter les labels de valeur par pile
                    # Ne pas afficher les valeurs numériques sur les barres (demande utilisateur)
                    # Filtrer les affectations sans valeur (somme des statuts = 0) et trier
                    for stc in ['Complet', 'En cours']:
                        if stc not in df_service.columns:
                            df_service[stc] = 0

                    # Retirer les affectations où il n'y a aucune entrée
                    df_service = df_service[df_service[['Complet', 'En cours']].sum(axis=0) > 0]

                    # Trier par nombre de dossiers 'En cours' décroissant pour montrer d'abord les chantiers les plus problématiques
                    if 'En cours' in df_service.columns:
                        df_service = df_service.sort_values('En cours', ascending=False)

                    fig_bar.update_layout(xaxis_title='Affectation', uniformtext_minsize=8, uniformtext_mode='hide')
                    st.plotly_chart(fig_bar, width="stretch")
                except Exception as e:
                    st.error(f"Erreur affichage graphique par service: {e}")
    
    st.markdown("---")

    # Nouveaux graphiques demandés :
    col_doc1, col_doc2 = st.columns(2)
    with col_doc1:
        st.subheader("📄 Documents les plus souvent manquants")
        # Aggrégation des documents manquants
        docs_counter = {}
        for v in st.session_state.hr_database['Documents_manquants'].fillna(''):
            try:
                docs = json.loads(v)
            except:
                docs = []
            for d in docs:
                docs_counter[d] = docs_counter.get(d, 0) + 1

        if docs_counter:
            docs_df = pd.DataFrame(list(docs_counter.items()), columns=['Document', 'Count']).sort_values('Count', ascending=False)
            top_n = docs_df.head(10)
            fig_docs = px.bar(top_n, x='Document', y='Count', title='Top 10 des documents manquants', text='Count')
            # Nettoyer les libellés génériques
            fig_docs.update_traces(texttemplate='%{text}', textposition='outside')
            fig_docs.update_layout(xaxis_title='', yaxis_title='', uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig_docs, width="stretch")

        # Déplacer le graphique 'Distribution des relances' dans la colonne de droite (col_doc2)
        with col_doc2:
            st.subheader("📊 Distribution des relances")
            try:
                counts = st.session_state.hr_database['Nombre_relances'].fillna(0).astype(int)
            except Exception:
                counts = pd.Series(dtype=int)

            c0 = int((counts == 0).sum())
            c1 = int((counts == 1).sum())
            c2 = int((counts == 2).sum())
            c3 = int((counts >= 3).sum())

            rel_df = pd.DataFrame({'Relances': ['0', '1', '2', '3+'], 'Count': [c0, c1, c2, c3]})
            fig_rel = px.bar(rel_df, x='Relances', y='Count', title='Distribution des relances (0 / 1 / 2 / 3+)', text='Count')
            fig_rel.update_traces(texttemplate='%{text}', textposition='outside')
            fig_rel.update_layout(
                xaxis={'type': 'category', 'categoryorder': 'array', 'categoryarray': ['0', '1', '2', '3+']},
                yaxis={'tickformat': '.0f', 'dtick': 1},
                xaxis_title='',
                yaxis_title='',
                uniformtext_minsize=8, uniformtext_mode='hide'
            )
            st.plotly_chart(fig_rel, width="stretch")

    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)

    with col_filter1:
        status_filter = st.selectbox("Filtrer par Statut", ["Tous", "Complet", "En cours"])

    with col_filter2:
        # Préférer la colonne 'Affectation' si elle existe (contient les noms des chantiers).
        if 'Affectation' in st.session_state.hr_database.columns:
            raw_services = st.session_state.hr_database['Affectation'].dropna().astype(str).unique().tolist()
        elif 'Service' in st.session_state.hr_database.columns:
            raw_services = st.session_state.hr_database['Service'].dropna().astype(str).unique().tolist()
        else:
            raw_services = []
        # Nettoyer et trier pour une UI plus propre
        raw_services = [s for s in raw_services if str(s).strip() != '']
        raw_services = sorted(raw_services)
        services = ["Tous"] + raw_services
        service_filter = st.selectbox("Filtrer par Affectation", services)

    with col_filter3:
        relance_filter = st.selectbox("Filtrer par Relances", ["Toutes", "0 relance", "1 relance", "2+ relances"])
    
    with col_filter4:
        sort_by = st.selectbox("Trier par", [
            "Nom", "Date d'intégration", "Nombre de documents manquants", "Dernière relance"
        ])
    
    # Application des filtres
    filtered_df = st.session_state.hr_database.copy()
    
    if status_filter != "Tous":
        filtered_df = filtered_df[filtered_df['Statut'] == status_filter]
    
    if service_filter != "Tous":
        # Filtrer en privilégiant 'Affectation' si disponible
        if 'Affectation' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Affectation'] == service_filter]
        else:
            filtered_df = filtered_df[filtered_df['Service'] == service_filter]
    
    if relance_filter != "Toutes":
        if relance_filter == "0 relance":
            filtered_df = filtered_df[filtered_df['Nombre_relances'] == 0]
        elif relance_filter == "1 relance":
            filtered_df = filtered_df[filtered_df['Nombre_relances'] == 1]
        elif relance_filter == "2+ relances":
            filtered_df = filtered_df[filtered_df['Nombre_relances'] >= 2]
    
    # Ajouter le nombre de documents manquants pour l'affichage
    filtered_df['Nb_docs_manquants'] = filtered_df['Documents_manquants'].apply(get_missing_documents_count)
    
    # Tableau principal
    st.subheader("📋 Liste des Collaborateurs")
    
    if len(filtered_df) > 0:
        # Préparer les données pour l'affichage
        # Prioriser la colonne 'Affectation' si elle existe, sinon utiliser 'Service'
        if 'Affectation' in filtered_df.columns:
            filtered_df['Affectation_display'] = filtered_df['Affectation']
        else:
            # si seulement 'Service' existe, l'utiliser
            filtered_df['Affectation_display'] = filtered_df['Service'] if 'Service' in filtered_df.columns else ''

        # S'assurer que toutes les colonnes attendues existent dans le DataFrame (évite KeyError)
        expected_cols = ['Nom', 'Prénom', 'Poste', 'Affectation_display', 'Téléphone', 'Email', 'Date_integration', 'Statut', 'Nb_docs_manquants', 'Derniere_relance', 'Nombre_relances']
        for c in expected_cols:
            if c not in filtered_df.columns:
                filtered_df[c] = ''

        display_df = filtered_df[expected_cols].copy()
        
        display_df.columns = ['Nom', 'Prénom', 'Poste', 'Affectation', 'Téléphone', 'Email', 
                 'Date Intégration', 'Statut', 'Docs Manquants', 
                 'Dernière Relance', 'Nb Relances']
        
        # Affichage avec formatage conditionnel
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True
        )
        
        # Détails des documents manquants — afficher les expanders en grille 6 colonnes
        with st.expander("📄 Détail des documents manquants"):
            # Rassembler les lignes avec documents manquants
            rows_with_docs = []
            for idx, row in filtered_df.iterrows():
                if row.get('Statut', '') == 'En cours':
                    try:
                        missing_docs = json.loads(row.get('Documents_manquants', '[]'))
                    except Exception:
                        missing_docs = []
                    if missing_docs:
                        rows_with_docs.append((idx, row, missing_docs))

            if not rows_with_docs:
                st.info("Aucun document manquant détecté pour les collaborateurs filtrés.")
            else:
                cols = st.columns(6)
                # Distribuer les expanders en round-robin dans les 6 colonnes
                for i, (idx, row, missing_docs) in enumerate(rows_with_docs):
                    col = cols[i % 6]
                    title = f"{row.get('Prénom','')} {row.get('Nom','')} — {row.get('Poste','')} ({len(missing_docs)} docs)"
                    with col:
                        with st.expander(title, expanded=False):
                            for doc in missing_docs:
                                st.write(f"• {doc}")
    else:
        st.info("Aucun collaborateur ne correspond aux filtres sélectionnés.")
    
    # Boutons d'action
    col_action1, col_action2 = st.columns(2)
    
    # Retirer le bouton de sauvegarde de l'onglet principal (inutile)
    with col_action1:
        st.write("")
    
    with col_action2:
        if st.button("🔄 Recharger depuis Google Sheets", width="stretch"):
            with st.spinner("Rechargement en cours..."):
                # Vider le cache pour forcer le rechargement
                st.cache_data.clear()
                try:
                    raw = _load_df_from_worksheet(WORKSHEET_NAME)
                    if raw is None:
                        st.error("❌ Impossible de lire la feuille Google Sheets.")
                    else:
                        st.session_state.hr_database = normalize_hr_database(raw)
                        # Signaler le succès après le rerun
                        st.session_state['_last_reload_successful'] = True
                        # Forcer un rerun afin que l'UI reflète immédiatement les nouvelles données
                        # Utiliser safe_rerun() pour gérer différentes versions de Streamlit
                        safe_rerun()
                except Exception as e:
                    st.error(f"Erreur lors du rechargement direct: {e}")
        # Afficher le message de succès localement juste sous le bouton (une seule fois)
        if st.session_state.get('_last_reload_successful', False):
            st.success("✅ Données rechargées depuis Google Sheets!")
            # Effacer le flag immédiatement pour n'afficher le message qu'une seule fois
            st.session_state['_last_reload_successful'] = False

# ============================
# ONGLET 2: GESTION COLLABORATEUR
# ============================
with tab2:
    st.header("👤 Ajout / Mise à jour d'un Collaborateur")
    
    # Choix: Nouveau collaborateur ou mise à jour (label simplifié)
    action_type = st.radio(
        "",
        ["➕ Ajouter un nouveau collaborateur", "✏️ Mettre à jour un collaborateur existant"],
        horizontal=True
    )
    
    if action_type == "➕ Ajouter un nouveau collaborateur":
        # Formulaire pour nouveau collaborateur
        with st.form("nouveau_collaborateur"):
            st.subheader("📝 Informations du nouveau collaborateur")
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                nom = st.text_input("Nom *", placeholder="Ex: ALAMI")
                prenom = st.text_input("Prénom *", placeholder="Ex: Ahmed")
                email = st.text_input("Email *", placeholder="Ex: ahmed.alami@tgcc.ma")
            
            with col_info2:
                poste = st.text_input("Poste *", placeholder="Ex: Ingénieur IT")
                affectation = st.text_input("Affectation *", placeholder="Ex: Service IT")
                telephone = st.text_input("Téléphone", placeholder="Ex: +212600000000")
                date_integration = st.date_input("Date d'intégration")
            
            st.subheader("📋 Documents RH - Cochez les documents FOURNIS")
            st.info("ℹ️ Cochez uniquement les documents que le collaborateur a DÉJÀ fournis")
            
            # Checklist des documents en deux colonnes
            provided_docs = []
            cols_docs = st.columns(2)
            for i, doc in enumerate(DOCUMENTS_RH):
                col = cols_docs[i % 2]
                with col:
                    if st.checkbox(f"{doc}", key=f"new_{i}"):
                        provided_docs.append(doc)
            
            # Calculer les documents manquants (ceux non cochés)
            missing_docs = [doc for doc in DOCUMENTS_RH if doc not in provided_docs]
            
            # Bouton de soumission
            submitted = st.form_submit_button("➕ Ajouter le collaborateur", type="primary", width="stretch")
            
            if submitted:
                if nom and prenom and email and poste and affectation:
                    # Déterminer le statut
                    statut = "Complet" if len(missing_docs) == 0 else "En cours"
                    
                    # Timestamps
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Créer la nouvelle entrée
                    nouvelle_ligne = pd.DataFrame({
                        'Nom': [nom.upper()],
                        'Prénom': [prenom.title()],
                        'Poste': [poste],
                        'Service': [affectation],
                        'Téléphone': [telephone],
                        'Email': [email.lower()],
                        'Date_integration': [str(date_integration)],
                        'Documents_manquants': [json.dumps(missing_docs)],
                        'Statut': [statut],
                        'Derniere_relance': [''],
                        'Nombre_relances': [0],
                        'Date_creation': [now],
                        'Date_modification': [now]
                    })
                    
                    # Ajouter à la base de données locale
                    st.session_state.hr_database = pd.concat([st.session_state.hr_database, nouvelle_ligne], ignore_index=True)
                    
                    # Ajouter directement à Google Sheets
                    new_row_data = [
                        nom.upper(), prenom.title(), poste, affectation, telephone, email.lower(),
                        str(date_integration), json.dumps(missing_docs), statut,
                        '', 0, now, now
                    ]
                    
                    with st.spinner("Ajout à Google Sheets..."):
                        if add_row_to_gsheet(new_row_data):
                            st.success(f"✅ {prenom} {nom} ajouté(e) dans Google Sheets!")
                            # Vider le cache pour forcer le rechargement
                            st.cache_data.clear()
                        else:
                            st.warning("⚠️ Ajouté localement, mais erreur Google Sheets. Utilisez 'Sauvegarder' manuellement.")
                    
                    st.success(f"📊 Statut: **{statut}** ({len(missing_docs)} documents manquants)")
                    
                    if len(missing_docs) > 0:
                        st.info("📄 Documents manquants:")
                        for doc in missing_docs:
                            st.write(f"  • {doc}")
                    
                        # previously: st.rerun() — removed to avoid automatic tab switching
                else:
                    st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
    
    else:
        # Mise à jour d'un collaborateur existant
        st.subheader("✏️ Mise à jour d'un collaborateur")
        
        if len(st.session_state.hr_database) > 0:
            # Sélection du collaborateur
            collaborateurs = st.session_state.hr_database.apply(lambda x: f"{x['Prénom']} {x['Nom']} ({x['Poste']})", axis=1).tolist()
            selected_collab = st.selectbox("Choisir le collaborateur à mettre à jour:", collaborateurs)
            
            if selected_collab:
                # Trouver l'index du collaborateur sélectionné
                selected_idx = collaborateurs.index(selected_collab)
                collab_data = st.session_state.hr_database.iloc[selected_idx]
                
                # Afficher le statut actuel, et si complet ajouter le message de dossier complet sur la même ligne
                if isinstance(collab_data, pd.Series) and collab_data.get('Statut', None) == 'Complet':
                    st.info(f"📊 Statut actuel: **{collab_data['Statut']}** — ✅ Dossier complet - Aucun document manquant!")
                else:
                    st.info(f"📊 Statut actuel: **{collab_data['Statut']}**")
                
                # Afficher les documents actuellement manquants
                try:
                    current_missing = json.loads(str(collab_data['Documents_manquants']))
                except:
                    current_missing = []
                
                if current_missing:
                    st.warning(f"📄 Documents actuellement manquants ({len(current_missing)}):")
                    for doc in current_missing:
                        st.write(f"  • {doc}")
                else:
                    st.success("✅ Dossier complet - Aucun document manquant!")
                
                # Formulaire de mise à jour
                with st.form("mise_a_jour"):
                    st.subheader("📋 Mise à jour des documents fournis")
                    st.info("ℹ️ Cochez les documents qui ont été FOURNIS")

                    # Téléphone retiré de la mise à jour des documents (conforme à la demande)

                    # Checklist avec état actuel (inverse de la logique précédente) en deux colonnes
                    provided_docs = []
                    cols_docs_update = st.columns(2)
                    for i, doc in enumerate(DOCUMENTS_RH):
                        is_currently_provided = doc not in current_missing  # Inverse de la logique
                        col = cols_docs_update[i % 2]
                        with col:
                            if st.checkbox(f"{doc}", value=is_currently_provided, key=f"update_{i}"):
                                provided_docs.append(doc)
                    
                    # Calculer les documents manquants (ceux non cochés)
                    new_missing_docs = [doc for doc in DOCUMENTS_RH if doc not in provided_docs]
                    
                    # Bouton de mise à jour
                    update_submitted = st.form_submit_button("🔄 Mettre à jour", type="primary", width="stretch")
                    
                    if update_submitted:
                        # Déterminer le nouveau statut
                        nouveau_statut = "Complet" if len(new_missing_docs) == 0 else "En cours"
                        
                        # Timestamp de modification
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Mettre à jour la base de données locale
                        st.session_state.hr_database.loc[selected_idx, 'Documents_manquants'] = json.dumps(new_missing_docs)
                        st.session_state.hr_database.loc[selected_idx, 'Statut'] = nouveau_statut
                        st.session_state.hr_database.loc[selected_idx, 'Date_modification'] = now
                        
                        # Mettre à jour Google Sheets
                        updated_row = st.session_state.hr_database.iloc[selected_idx].fillna('').tolist()
                        
                        with st.spinner("Mise à jour dans Google Sheets..."):
                            if update_row_in_gsheet(selected_idx, updated_row):
                                st.success("✅ Mis à jour dans Google Sheets!")
                                # Vider le cache pour forcer le rechargement
                                st.cache_data.clear()
                            else:
                                st.warning("⚠️ Mis à jour localement, mais erreur Google Sheets. Utilisez 'Sauvegarder' manuellement.")
                        
                        # Afficher le résultat
                        if nouveau_statut == "Complet":
                            st.success(f"🎉 Félicitations! Le dossier de {collab_data['Prénom']} {collab_data['Nom']} est maintenant COMPLET!")
                        else:
                            st.info(f"📊 Dossier mis à jour. Statut: **{nouveau_statut}** ({len(new_missing_docs)} documents encore manquants)")
                            if new_missing_docs:
                                st.write("📄 Documents encore manquants:")
                                for doc in new_missing_docs:
                                    st.write(f"  • {doc}")
                        
                        # pas de rerun ici pour éviter de changer d'onglet
        else:
            st.info("📭 Aucun collaborateur dans la base de données. Ajoutez d'abord un collaborateur.")

# ============================
# ONGLET 3: RELANCES AUTOMATIQUES
# ============================
with tab3:
    st.header("📧 Système de Relances Automatiques")
    
    # Configuration SMTP
    
    # Sélection des collaborateurs à relancer
    st.subheader("👥 Collaborateurs avec documents manquants")
    
    # Filtrer les collaborateurs avec des documents manquants
    incomplete_collabs = st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'En cours'].copy()
    
    if len(incomplete_collabs) > 0:
        # Tableau des collaborateurs à relancer
        display_incomplete = incomplete_collabs[['Nom', 'Prénom', 'Poste', 'Email', 'Date_integration', 'Derniere_relance', 'Nombre_relances']].copy()
        display_incomplete['Nb_docs_manquants'] = incomplete_collabs['Documents_manquants'].apply(get_missing_documents_count)
        
        display_incomplete.columns = ['Nom', 'Prénom', 'Poste', 'Email', 'Date Intégration', 'Dernière Relance', 'Nb Relances', 'Docs Manquants']
        
        st.dataframe(display_incomplete, width="stretch", hide_index=True)
        
        # Formulaire de relance
        st.subheader("📨 Envoyer une relance")
        
        # Sélection du collaborateur (en dehors du formulaire pour actualisation dynamique)
        collab_options = incomplete_collabs.apply(lambda x: f"{x['Prénom']} {x['Nom']} ({x['Email']})", axis=1).tolist()
        selected_collab_relance = st.selectbox("Choisir le collaborateur:", collab_options, key="collab_selectbox")
        
        if selected_collab_relance:
            # Trouver les données du collaborateur sélectionné
            selected_idx_relance = collab_options.index(selected_collab_relance)
            collab_relance_data = incomplete_collabs.iloc[selected_idx_relance]
            
            # Afficher les documents manquants
            try:
                missing_docs_relance = json.loads(collab_relance_data['Documents_manquants'])
            except:
                missing_docs_relance = []
            
            # Section expandable pour les documents manquants
            with st.expander(f"📄 Documents manquants pour {collab_relance_data['Prénom']} {collab_relance_data['Nom']} ({len(missing_docs_relance)} documents)", expanded=True):
                for doc in missing_docs_relance:
                    st.write(f"• {doc}")
            
            # Calculer les dates selon le type de relance
            delay_date_now = (datetime.now() + timedelta(days=14)).strftime('%d/%m/%Y')
            send_date_1week = (datetime.now() + timedelta(days=7))
            delay_date_1week = (send_date_1week + timedelta(days=14)).strftime('%d/%m/%Y')
            send_date_2weeks = (datetime.now() + timedelta(days=14))
            delay_date_2weeks = (send_date_2weeks + timedelta(days=14)).strftime('%d/%m/%Y')
            
            # Section: informations de l'émetteur (Email et CC sur la même ligne)
            col_actor, col_cc = st.columns([1,1])
            with col_actor:
                actor_email = st.text_input("Email de l'émetteur (optionnel, utilisé en Reply-To)", value=st.session_state.get('actor_email', ''))
            with col_cc:
                cc_emails = st.text_input("CC (emails séparés par des virgules, optionnel)", value=st.session_state.get('cc_emails', ''))

            st.markdown("---")

            # Section template email avec possibilité d'édition
            with st.expander("📧 Éditer le modèle d'email", expanded=False):
                docs_list_preview = '\n'.join([f"• {doc}" for doc in missing_docs_relance])
                
                default_email_body = f"""Bonjour {collab_relance_data['Prénom']},

Merci de noter que votre dossier administratif RH demeure incomplet à ce jour.
Merci de remettre les éléments suivants afin de le compléter:

{docs_list_preview}

Les documents doivent être envoyés via le pointeur chantier dans une enveloppe fermée, en mentionnant CONFIDENTIEL et A L'ATTENTION DE M.L'EQUIPE RECRUTEMENT.

Merci de noter que le dernier délai pour compléter votre dossier c'est le {delay_date_now}

Comptant sur votre précieuse collaboration.

Cordialement"""
                
                # Zone de texte éditable pour le corps du message
                custom_email_body = st.text_area(
                    "Corps du message (modifiable):",
                    value=default_email_body,
                    height=300,
                    key=f"email_body_{selected_idx_relance}"
                )
                
                st.info("💡 Vous pouvez modifier le texte ci-dessus. La date limite sera automatiquement mise à jour selon le type de relance choisi.")

            with st.form("relance_form"):
                
                # Options de relance
                st.subheader("⏰ Type de relance")
                relance_type = st.radio(
                    "",
                    ["📧 Envoyer maintenant", "⏰ Programmer dans 1 semaine", "⏰ Programmer dans 2 semaines"],
                    horizontal=True
                )
                
                # Choix d'heure pour la relance programmée (par défaut 09:00)
                send_time = st.time_input("Heure d'envoi (pour relances programmées)", value=datetime.strptime("09:00", "%H:%M").time())

                # Affichage compact des informations selon le type de relance
                if relance_type == "📧 Envoyer maintenant":
                    st.write(f"Date limite dans l'email: {delay_date_now}")
                    final_delay_date = delay_date_now
                elif relance_type == "⏰ Programmer dans 1 semaine":
                    st.write(f"Relance programmée: {send_date_1week.strftime('%d/%m/%Y')} — Date limite: {delay_date_1week} à {send_time.strftime('%H:%M')}")
                    final_delay_date = delay_date_1week
                else:  # 2 semaines
                    st.write(f"Relance programmée: {send_date_2weeks.strftime('%d/%m/%Y')} — Date limite: {delay_date_2weeks} à {send_time.strftime('%H:%M')}")
                    final_delay_date = delay_date_2weeks
                
                # Bouton d'envoi
                send_button = st.form_submit_button("📧 Envoyer/Programmer la relance", type="primary", width="stretch")
                
                if send_button:
                    with st.spinner("📤 Traitement de la relance en cours..."):
                        if relance_type == "📧 Envoyer maintenant":
                            # Envoi immédiat
                            # Utiliser le corps d'email personnalisé avec la date limite mise à jour
                            final_email_body = custom_email_body.replace(delay_date_now, final_delay_date)
                            
                            success = send_email_reminder(
                                collab_relance_data['Email'],
                                collab_relance_data['Prénom'],
                                missing_docs_relance,
                                final_delay_date,
                                final_email_body,
                                actor_email=actor_email,
                                cc_emails=cc_emails
                            )
                            
                            if success:
                                # Mettre à jour les données de relance
                                original_idx = st.session_state.hr_database[
                                    (st.session_state.hr_database['Nom'] == collab_relance_data['Nom']) &
                                    (st.session_state.hr_database['Prénom'] == collab_relance_data['Prénom'])
                                ].index[0]
                                
                                st.session_state.hr_database.loc[original_idx, 'Derniere_relance'] = datetime.now().strftime('%Y-%m-%d')
                                # Ensure Nombre_relances is treated as numeric before incrementing
                                current_relances = st.session_state.hr_database.loc[original_idx, 'Nombre_relances']
                                try:
                                    # Convert to float first to handle potential float-like strings, then to int
                                    val = float(current_relances) if current_relances is not None else 0
                                    st.session_state.hr_database.loc[original_idx, 'Nombre_relances'] = int(val) + 1
                                except (ValueError, TypeError):
                                    st.session_state.hr_database.loc[original_idx, 'Nombre_relances'] = 1
                                
                                # Ajouter à l'historique
                                nouvelle_relance = pd.DataFrame({
                                    'Date': [datetime.now().strftime('%Y-%m-%d %H:%M')],
                                    'Collaborateur': [f"{collab_relance_data['Prénom']} {collab_relance_data['Nom']}"],
                                    'Email': [collab_relance_data['Email']],
                                    'Documents_relances': [json.dumps(missing_docs_relance)],
                                    'Statut_envoi': ['Envoyé immédiatement'],
                                    'Email_body': [final_email_body]
                                })
                                
                                st.session_state.relance_history = pd.concat([st.session_state.relance_history, nouvelle_relance], ignore_index=True)
                                # Persister historique dans Google Sheets
                                try:
                                    save_relance_history_to_gsheet(st.session_state.relance_history)
                                except Exception:
                                    pass

                                st.success(f"✅ Email envoyé avec succès à {collab_relance_data['Prénom']} {collab_relance_data['Nom']}!")
                                # Ne pas forcer le rerun pour éviter changement d'onglet
                            else:
                                st.error("❌ Erreur lors de l'envoi de l'email via l'API Gmail.")
                        else:
                            # Relance programmée
                            # Construire la date programmée avec l'heure choisie
                            if relance_type == "⏰ Programmer dans 1 semaine":
                                base_dt = datetime.now() + timedelta(days=7)
                            else:
                                base_dt = datetime.now() + timedelta(days=14)
                            # Remplacer l'heure par celle choisie
                            date_programmee_dt = base_dt.replace(hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0)
                            date_programmee = date_programmee_dt.strftime('%Y-%m-%d %H:%M')
                            
                            # Construire le corps final (avec date mise à jour) et l'enregistrer
                            scheduled_body = custom_email_body.replace(delay_date_now, final_delay_date)
                            relance_programmee = pd.DataFrame({
                                'Date_programmee': [date_programmee],
                                'Collaborateur': [f"{collab_relance_data['Prénom']} {collab_relance_data['Nom']}"],
                                'Email': [collab_relance_data['Email']],
                                'Documents_relances': [json.dumps(missing_docs_relance)],
                                'Date_limite': [final_delay_date],
                                'Statut': ['Programmée'],
                                'Actor_email': [actor_email],
                                'CC': [cc_emails],
                                'Email_body': [scheduled_body]
                            })
                            
                            st.session_state.scheduled_relances = pd.concat([st.session_state.scheduled_relances, relance_programmee], ignore_index=True)
                            # Persister relances programmées
                            try:
                                save_scheduled_relances_to_gsheet(st.session_state.scheduled_relances)
                            except Exception:
                                pass

                            st.success(f"✅ Relance programmée pour le {date_programmee} pour {collab_relance_data['Prénom']} {collab_relance_data['Nom']}!")
    
    else:
        st.success("🎉 Aucune relance nécessaire! Tous les dossiers sont complets.")
    
    # Historique des relances
    st.markdown("---")
    st.subheader("📈 Historique et Programmation des Relances")
    
    # Onglets pour séparer l'historique et les relances programmées
    hist_tab1, hist_tab2 = st.tabs(["📧 Relances Envoyées", "⏰ Relances Programmées"])
    
    with hist_tab1:
        if len(st.session_state.relance_history) > 0:
            # Affichage de l'historique
            history_display = st.session_state.relance_history.copy()
            history_display = history_display.sort_values('Date', ascending=False)
            # Pretty-print Documents_relances JSON -> 'doc1, doc2'
            if 'Documents_relances' in history_display.columns:
                def _pretty_docs(x):
                    try:
                        arr = json.loads(x) if isinstance(x, str) and x.strip()!='' else []
                        return ', '.join(arr)
                    except Exception:
                        return str(x)
                history_display['Documents_relances'] = history_display['Documents_relances'].apply(_pretty_docs)
            st.dataframe(history_display, width="stretch", hide_index=True)
            
            # Statistiques des relances
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                total_relances = len(st.session_state.relance_history)
                st.metric("📧 Total Relances", total_relances)
            
            with col_stat2:
                relances_today = len(st.session_state.relance_history[
                    st.session_state.relance_history['Date'].str.startswith(datetime.now().strftime('%Y-%m-%d'))
                ])
                st.metric("📅 Relances Aujourd'hui", relances_today)
            
            with col_stat3:
                avg_relances = st.session_state.hr_database[st.session_state.hr_database['Nombre_relances'] > 0]['Nombre_relances'].mean()
                if pd.notna(avg_relances):
                    # afficher sans décimales inutiles (ex: 0.5 -> 1 si on veut entier, ou 0.5 affiché proprement)
                    # on affiche 1 décimale mais s'il s'agit d'un .0 on affiche sans décimale
                    if float(avg_relances).is_integer():
                        st.metric("📊 Moyenne Relances/Collab", f"{int(avg_relances)}")
                    else:
                        st.metric("📊 Moyenne Relances/Collab", f"{avg_relances:.1f}")
                else:
                    st.metric("📊 Moyenne Relances/Collab", "0")
        
        else:
            st.info("📭 Aucune relance envoyée pour le moment.")
    
    with hist_tab2:
        if len(st.session_state.scheduled_relances) > 0:
            # Affichage des relances programmées
            scheduled_display = st.session_state.scheduled_relances.copy()
            scheduled_display = scheduled_display.sort_values('Date_programmee', ascending=True)
            # Pretty-print Documents_relances
            if 'Documents_relances' in scheduled_display.columns:
                def _pretty_docs_sched(x):
                    try:
                        arr = json.loads(x) if isinstance(x, str) and x.strip()!='' else []
                        return ', '.join(arr)
                    except Exception:
                        return str(x)
                scheduled_display['Documents_relances'] = scheduled_display['Documents_relances'].apply(_pretty_docs_sched)
            st.dataframe(scheduled_display, width="stretch", hide_index=True)

            st.markdown("---")
            st.subheader("Gérer les relances programmées")
            # Permettre la suppression d'une relance programmée individuelle
            options = scheduled_display.apply(lambda r: f"{r['Date_programmee']} — {r['Collaborateur']} — {r.get('Email','')}", axis=1).tolist()
            to_delete = st.selectbox("Sélectionnez une relance programmée à supprimer:", options)
            if st.button("🗑️ Supprimer la relance sélectionnée"):
                try:
                    idx = options.index(to_delete)
                    # Retirer de la session_state et persister
                    st.session_state.scheduled_relances = st.session_state.scheduled_relances.drop(st.session_state.scheduled_relances.index[idx]).reset_index(drop=True)
                    try:
                        save_scheduled_relances_to_gsheet(st.session_state.scheduled_relances)
                    except Exception:
                        pass
                    st.success("✅ Relance programmée supprimée.")
                except Exception as e:
                    st.error(f"Erreur suppression: {e}")
        else:
            st.info("📅 Aucune relance programmée pour le moment.")

# Footer
st.markdown("---")
st.markdown("**💼 Système de Suivi des Dossiers RH - TGCC** | Version 1.0")

# (Outils admin supprimés par demande de l'utilisateur)
