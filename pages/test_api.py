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
            headers = ['Nom', 'Prénom', 'Poste', 'Service', 'Email', 'Date_integration', 
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

# Initialisation des données en session
if 'hr_database' not in st.session_state:
    st.session_state.hr_database = load_data_from_gsheet()

if 'relance_history' not in st.session_state:
    st.session_state.relance_history = pd.DataFrame(columns=[
        'Date', 'Collaborateur', 'Email', 'Documents_relances', 'Statut_envoi'
    ])

if 'scheduled_relances' not in st.session_state:
    st.session_state.scheduled_relances = pd.DataFrame(columns=[
        'Date_programmee', 'Collaborateur', 'Email', 'Documents_relances', 'Date_limite', 'Statut'
    ])

# Fonctions utilitaires
def save_data():
    """Sauvegarde les données dans Google Sheets"""
    return save_data_to_gsheet(st.session_state.hr_database)

def load_data():
    """Recharge les données depuis Google Sheets"""
    try:
        st.session_state.hr_database = load_data_from_gsheet()
        return True
    except Exception as e:
        st.error(f"Erreur lors du rechargement: {e}")
        return False

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

def send_email_reminder(recipient_email, recipient_name, missing_docs, delay_date=None, custom_body=None):
    """Envoie un email de relance via SMTP"""
    try:
        # Configuration SMTP - utiliser les secrets Streamlit
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        sender_email = st.secrets.get("SENDER_EMAIL", "")
        sender_password = st.secrets.get("SENDER_PASSWORD", "")
        
        if not sender_email or not sender_password:
            st.error("❌ Configuration email manquante. Veuillez configurer SENDER_EMAIL et SENDER_PASSWORD dans les secrets.")
            return False
        
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
        
        # Créer le message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = "URGENT: Complément du dossier administrative RH"
        message.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Envoyer l'email via SMTP
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Activer la sécurité
            server.login(sender_email, sender_password)
            server.send_message(message)
        
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
    
    # Barre de progression globale
    st.subheader("🎯 Progression Globale")
    progress_bar = st.progress(completion_rate / 100)
    st.write(f"**{completion_rate:.1f}%** des dossiers sont complets")
    
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
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_chart2:
        # Graphique en barres - Par service
        service_stats = st.session_state.hr_database.groupby(['Service', 'Statut']).size().unstack(fill_value=0)

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
                    fig_bar = px.bar(
                        df_service,
                        x='Service',
                        y=y_cols,
                        title="Statuts par Service",
                        color_discrete_map={'Complet': '#28a745', 'En cours': '#ffc107'}
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur affichage graphique par service: {e}")
    
    st.markdown("---")
    
    # Filtres
    st.subheader("🔍 Filtres")
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    
    with col_filter1:
        status_filter = st.selectbox("Filtrer par Statut", ["Tous", "Complet", "En cours"])
    
    with col_filter2:
        services = ["Tous"] + list(st.session_state.hr_database['Service'].unique())
        service_filter = st.selectbox("Filtrer par Service", services)
    
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
        display_df = filtered_df[['Nom', 'Prénom', 'Poste', 'Service', 'Email', 
                                 'Date_integration', 'Statut', 'Nb_docs_manquants', 
                                 'Derniere_relance', 'Nombre_relances']].copy()
        
        display_df.columns = ['Nom', 'Prénom', 'Poste', 'Service', 'Email', 
                             'Date Intégration', 'Statut', 'Docs Manquants', 
                             'Dernière Relance', 'Nb Relances']
        
        # Affichage avec formatage conditionnel
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Détails des documents manquants
        with st.expander("📄 Détail des documents manquants"):
            for idx, row in filtered_df.iterrows():
                if row['Statut'] == 'En cours':
                    try:
                        missing_docs = json.loads(row['Documents_manquants'])
                        if missing_docs:
                            st.write(f"**{row['Prénom']} {row['Nom']}** ({row['Poste']}):")
                            for doc in missing_docs:
                                st.write(f"  • {doc}")
                            st.write("")
                    except:
                        pass
    else:
        st.info("Aucun collaborateur ne correspond aux filtres sélectionnés.")
    
    # Boutons d'action
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        if st.button("💾 Sauvegarder dans Google Sheets", use_container_width=True):
            with st.spinner("Sauvegarde en cours..."):
                if save_data():
                    st.success("✅ Données sauvegardées dans Google Sheets!")
                    # Vider le cache pour forcer le rechargement
                    st.cache_data.clear()
    
    with col_action2:
        if st.button("� Recharger depuis Google Sheets", use_container_width=True):
            with st.spinner("Rechargement en cours..."):
                # Vider le cache pour forcer le rechargement
                st.cache_data.clear()
                if load_data():
                    st.success("✅ Données rechargées depuis Google Sheets!")
                    st.rerun()

# ============================
# ONGLET 2: GESTION COLLABORATEUR
# ============================
with tab2:
    st.header("👤 Ajout / Mise à jour d'un Collaborateur")
    
    # Choix: Nouveau collaborateur ou mise à jour
    action_type = st.radio(
        "Que souhaitez-vous faire ?",
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
                date_integration = st.date_input("Date d'intégration")
            
            st.subheader("📋 Documents RH - Cochez les documents FOURNIS")
            st.info("ℹ️ Cochez uniquement les documents que le collaborateur a DÉJÀ fournis")
            
            # Checklist des documents
            provided_docs = []
            for i, doc in enumerate(DOCUMENTS_RH):
                if st.checkbox(f"{doc}", key=f"new_{i}"):
                    provided_docs.append(doc)
            
            # Calculer les documents manquants (ceux non cochés)
            missing_docs = [doc for doc in DOCUMENTS_RH if doc not in provided_docs]
            
            # Bouton de soumission
            submitted = st.form_submit_button("➕ Ajouter le collaborateur", type="primary", use_container_width=True)
            
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
                        nom.upper(), prenom.title(), poste, affectation, email.lower(),
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
                    
                    st.rerun()
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
                
                st.info(f"📊 Statut actuel: **{collab_data['Statut']}**")
                
                # Afficher les documents actuellement manquants
                try:
                    current_missing = json.loads(collab_data['Documents_manquants'])
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
                    
                    # Checklist avec état actuel (inverse de la logique précédente)
                    provided_docs = []
                    for i, doc in enumerate(DOCUMENTS_RH):
                        is_currently_provided = doc not in current_missing  # Inverse de la logique
                        if st.checkbox(f"{doc}", value=is_currently_provided, key=f"update_{i}"):
                            provided_docs.append(doc)
                    
                    # Calculer les documents manquants (ceux non cochés)
                    new_missing_docs = [doc for doc in DOCUMENTS_RH if doc not in provided_docs]
                    
                    # Bouton de mise à jour
                    update_submitted = st.form_submit_button("🔄 Mettre à jour", type="primary", use_container_width=True)
                    
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
                        
                        st.rerun()
        else:
            st.info("📭 Aucun collaborateur dans la base de données. Ajoutez d'abord un collaborateur.")

# ============================
# ONGLET 3: RELANCES AUTOMATIQUES
# ============================
with tab3:
    st.header("📧 Système de Relances Automatiques")
    
    # Configuration SMTP
    st.info("📧 **Configuration SMTP** : Les emails sont envoyés via SMTP. Assurez-vous que SENDER_EMAIL et SENDER_PASSWORD sont configurés dans les secrets.")
    
    # Sélection des collaborateurs à relancer
    st.subheader("👥 Collaborateurs avec documents manquants")
    
    # Filtrer les collaborateurs avec des documents manquants
    incomplete_collabs = st.session_state.hr_database[st.session_state.hr_database['Statut'] == 'En cours'].copy()
    
    if len(incomplete_collabs) > 0:
        # Tableau des collaborateurs à relancer
        display_incomplete = incomplete_collabs[['Nom', 'Prénom', 'Poste', 'Email', 'Date_integration', 'Derniere_relance', 'Nombre_relances']].copy()
        display_incomplete['Nb_docs_manquants'] = incomplete_collabs['Documents_manquants'].apply(get_missing_documents_count)
        
        display_incomplete.columns = ['Nom', 'Prénom', 'Poste', 'Email', 'Date Intégration', 'Dernière Relance', 'Nb Relances', 'Docs Manquants']
        
        st.dataframe(display_incomplete, use_container_width=True, hide_index=True)
        
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
                    "Choisir le type de relance:",
                    ["📧 Envoyer maintenant", "⏰ Programmer dans 1 semaine", "⏰ Programmer dans 2 semaines"],
                    horizontal=False
                )
                
                # Affichage des informations selon le type de relance
                if relance_type == "📧 Envoyer maintenant":
                    st.info(f"📅 Date limite dans l'email: {delay_date_now}")
                    final_delay_date = delay_date_now
                elif relance_type == "⏰ Programmer dans 1 semaine":
                    st.info(f"📧 La relance sera envoyée le: {send_date_1week.strftime('%d/%m/%Y')}")
                    st.info(f"� Date limite dans l'email: {delay_date_1week}")
                    final_delay_date = delay_date_1week
                else:  # 2 semaines
                    st.info(f"📧 La relance sera envoyée le: {send_date_2weeks.strftime('%d/%m/%Y')}")
                    st.info(f"� Date limite dans l'email: {delay_date_2weeks}")
                    final_delay_date = delay_date_2weeks
                
                # Bouton d'envoi
                send_button = st.form_submit_button("📧 Envoyer/Programmer la relance", type="primary", use_container_width=True)
                
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
                                final_email_body
                            )
                            
                            if success:
                                # Mettre à jour les données de relance
                                original_idx = st.session_state.hr_database[
                                    (st.session_state.hr_database['Nom'] == collab_relance_data['Nom']) &
                                    (st.session_state.hr_database['Prénom'] == collab_relance_data['Prénom'])
                                ].index[0]
                                
                                st.session_state.hr_database.loc[original_idx, 'Derniere_relance'] = datetime.now().strftime('%Y-%m-%d')
                                st.session_state.hr_database.loc[original_idx, 'Nombre_relances'] += 1
                                
                                # Ajouter à l'historique
                                nouvelle_relance = pd.DataFrame({
                                    'Date': [datetime.now().strftime('%Y-%m-%d %H:%M')],
                                    'Collaborateur': [f"{collab_relance_data['Prénom']} {collab_relance_data['Nom']}"],
                                    'Email': [collab_relance_data['Email']],
                                    'Documents_relances': [json.dumps(missing_docs_relance)],
                                    'Statut_envoi': ['Envoyé immédiatement']
                                })
                                
                                st.session_state.relance_history = pd.concat([st.session_state.relance_history, nouvelle_relance], ignore_index=True)
                                
                                st.success(f"✅ Email envoyé avec succès à {collab_relance_data['Prénom']} {collab_relance_data['Nom']}!")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de l'envoi de l'email via l'API Gmail.")
                        else:
                            # Relance programmée
                            if relance_type == "⏰ Programmer dans 1 semaine":
                                date_programmee = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
                            else:  # 2 semaines
                                date_programmee = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d %H:%M')
                            
                            # Ajouter à la liste des relances programmées
                            relance_programmee = pd.DataFrame({
                                'Date_programmee': [date_programmee],
                                'Collaborateur': [f"{collab_relance_data['Prénom']} {collab_relance_data['Nom']}"],
                                'Email': [collab_relance_data['Email']],
                                'Documents_relances': [json.dumps(missing_docs_relance)],
                                'Date_limite': [final_delay_date],
                                'Statut': ['Programmée']
                            })
                            
                            st.session_state.scheduled_relances = pd.concat([st.session_state.scheduled_relances, relance_programmee], ignore_index=True)
                            
                            st.success(f"✅ Relance programmée pour le {date_programmee} pour {collab_relance_data['Prénom']} {collab_relance_data['Nom']}!")
                            st.info("📋 La relance sera envoyée automatiquement à la date programmée.")
    
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
            
            st.dataframe(history_display, use_container_width=True, hide_index=True)
            
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
            
            st.dataframe(scheduled_display, use_container_width=True, hide_index=True)
            
            # Option pour annuler une relance programmée
            if st.button("🗑️ Supprimer toutes les relances programmées", type="secondary"):
                st.session_state.scheduled_relances = pd.DataFrame(columns=[
                    'Date_programmee', 'Collaborateur', 'Email', 'Documents_relances', 'Date_limite', 'Statut'
                ])
                st.success("✅ Toutes les relances programmées ont été supprimées.")
                st.rerun()
        else:
            st.info("📅 Aucune relance programmée pour le moment.")

# Footer
st.markdown("---")
st.markdown("**💼 Système de Suivi des Dossiers RH - TGCC** | Version 1.0")
