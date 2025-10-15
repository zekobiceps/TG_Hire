import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')
import re
import streamlit.components.v1 as components
import unicodedata
from io import BytesIO
import json
import gspread
from google.oauth2 import service_account
import unicodedata

def _normalize_text(text):
    """A global function to safely normalize text, handling None and NaN values."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ''
    s = str(text)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().strip()

def _norm(x):
    """Robust text normalization for status/keywords matching."""
    return _normalize_text(x)

st.set_page_config(
    page_title="📊 Reporting RH Complet",
    page_icon="📊",
    layout="wide"
)


def _truncate_label(label: str, max_len: int = 20) -> str:
    """Truncate long labels to a max length and append ellipsis.

    Returns a truncated string (if needed). Keep a plain truncation without
    changing accents/characters. Default max_len=20 (adjustable).
    """
    if not isinstance(label, str):
        return label
    if len(label) <= max_len:
        return label
    return label[: max_len - 4].rstrip() + '....'


# Shared title font used for all main charts so typography is consistent
TITLE_FONT = dict(family="Arial, sans-serif", size=16, color="#111111", )


def _parse_mixed_dates(series):
    """Parse a pandas Series that may contain mixed date representations.

    Strategy:
      1. If values are numeric (Excel serial), convert using Excel epoch.
      2. Try pd.to_datetime(..., dayfirst=True) to favor dd/mm/YYYY formats.
      3. Fallback to pd.to_datetime(..., errors='coerce') for other formats.

    Returns a datetime64[ns] Series with NaT for unparseable values.
    """
    s = series.copy()
    try:
        # If the series is numeric (Excel serials), convert per-element where it looks numeric
        if pd.api.types.is_numeric_dtype(s):
            def _maybe_excel(x):
                try:
                    xf = float(x)
                    return pd.Timestamp('1899-12-30') + pd.Timedelta(days=xf)
                except Exception:
                    return pd.NaT

            return s.apply(lambda v: _maybe_excel(v) if pd.notna(v) and str(v).strip().replace('.', '', 1).isdigit() else pd.NaT).combine_first(pd.to_datetime(s, dayfirst=True, errors='coerce'))
    except Exception:
        # fall through to permissive parsing below
        pass

    # First try dayfirst parsing (dd/mm/YYYY common in French contexts)
    parsed = pd.to_datetime(s, dayfirst=True, errors='coerce')
    # If many values still NaT, try fallback parsing
    if parsed.isna().sum() > len(parsed) * 0.25:
        parsed_alt = pd.to_datetime(s, errors='coerce')
        parsed = parsed.combine_first(parsed_alt)

    return parsed


def render_kpi_cards(recrutements, postes, directions, delai_display, delai_help=None):
    """Render a single-row set of KPI cards (inline, bordered with colored left stripe).

    Cards: [Nombre de recrutements] [Postes concernés] [Directions concernées] [Délai moyen]
    Returns an HTML string ready to be inserted with st.markdown(..., unsafe_allow_html=True)
    """

    css = """
<style>
.kpi-row{display:flex;gap:12px;flex-wrap:nowrap;align-items:stretch;margin-bottom:12px}
.kpi-card{flex:1 1 0;background:#fff;border-radius:6px;padding:12px;display:flex;flex-direction:column;justify-content:center;border:1px solid #e6eef6}
.kpi-card .title{font-size:12px;color:#2c3e50;margin-bottom:6px}
.kpi-card .value{font-size:22px;font-weight:700;color:#172b4d}
.kpi-accent{border-left:6px solid #1f77b4}
.kpi-green{border-left-color:#2ca02c}
.kpi-orange{border-left-color:#ff7f0e}
.kpi-purple{border-left-color:#6f42c1}
.kpi-help{font-size:11px;color:#555;margin-top:6px}
@media(max-width:800px){.kpi-row{flex-direction:column}}
</style>
"""

    html = f"""
{css}
<div class='kpi-row'>
    <div class='kpi-card kpi-accent' style='flex:2'>
        <div class='title'>Nombre de recrutements</div>
        <div class='value'>{recrutements:,}</div>
    </div>
    <div class='kpi-card kpi-green'>
        <div class='title'>Postes concernés</div>
        <div class='value'>{postes:,}</div>
    </div>
    <div class='kpi-card kpi-orange'>
        <div class='title'>Directions concernées</div>
        <div class='value'>{directions:,}</div>
    </div>
    <div class='kpi-card kpi-purple'>
        <div class='title'>Délai moyen (jours)</div>
        <div class='value'>{delai_display}</div>
        <div class='kpi-help'>{delai_help or ''}</div>
    </div>
</div>
"""

    return html

    df2 = df.copy()
    df2[start_col] = pd.to_datetime(df2[start_col], errors='coerce')
    df2[end_col] = pd.to_datetime(df2[end_col], errors='coerce')

    # Optionally filter to a specific status (e.g., 'Clôture') if the column exists
    if status_col in df2.columns and status_value is not None:
        df2 = df2[df2[status_col] == status_value].copy()

    # Compute delta in days
    df2['time_to_hire_days'] = (df2[end_col] - df2[start_col]).dt.days

    if drop_negative:
        df2 = df2[df2['time_to_hire_days'].notna() & (df2['time_to_hire_days'] >= 0)].copy()
    else:
        df2 = df2[df2['time_to_hire_days'].notna()].copy()

    if df2.empty:
        overall = None
    else:
        overall = {
            'mean': float(df2['time_to_hire_days'].mean()),
            'median': float(df2['time_to_hire_days'].median()),
            'std': float(df2['time_to_hire_days'].std()),
            'count': int(df2['time_to_hire_days'].count())
        }

    # Grouped aggregates
    by_direction = None
    by_poste = None
    if 'Direction concernée' in df2.columns:
        by_direction = df2.groupby('Direction concernée')['time_to_hire_days'].agg(['count', 'mean', 'median', 'std']).reset_index().sort_values('mean')
    if 'Poste demandé' in df2.columns:
        by_poste = df2.groupby('Poste demandé')['time_to_hire_days'].agg(['count', 'mean', 'median', 'std']).reset_index().sort_values('mean')

    return {
        'start_col': start_col,
        'end_col': end_col,
        'overall': overall,
        'by_direction': by_direction,
        'by_poste': by_poste,
        'df': df2
    }


# CSS pour styliser le bouton Google Sheets en rouge vif
st.markdown("""
<style>
.stButton > button[title="Synchroniser les données depuis Google Sheets"] {
    background-color: #FF4B4B !important;
    color: white !important;
    border: none !important;
    border-radius: 5px !important;
    font-weight: bold !important;
}
.stButton > button[title="Synchroniser les données depuis Google Sheets"]:hover {
    background-color: #FF3333 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Données pour le Kanban
postes_data = [
    # Colonne Sourcing
    {"titre": "Ingénieur Achat", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "A.BOUZOUBAA", "recruteur": "Zakaria", "statut": "Sourcing"},
    {"titre": "Directeur Achats Adjoint", "entite": "TGCC", "lieu": "Siège", "demandeur": "C.BENABDELLAH", "recruteur": "Zakaria", "statut": "Sourcing"},
    {"titre": "INGENIEUR TRAVAUX", "entite": "TGCC", "lieu": "YAMED LOT B", "demandeur": "M.TAZI", "recruteur": "Zakaria", "statut": "Sourcing"},

    # Colonne Shortlisté
    {"titre": "CHEF DE PROJETS", "entite": "TGCC", "lieu": "DESSALMENT JORF", "demandeur": "M.FENNAN", "recruteur": "ZAKARIA", "statut": "Shortlisté"},
    {"titre": "Planificateur", "entite": "TGCC", "lieu": "ASFI-B", "demandeur": "SOUFIANI", "recruteur": "Ghita", "statut": "Shortlisté"},
    {"titre": "RESPONSABLE TRANS INTERCH", "entite": "TG PREFA", "lieu": "OUED SALEH", "demandeur": "FBOUZOUBAA", "recruteur": "Ghita", "statut": "Shortlisté"},

    # Colonne Signature DRH
    {"titre": "PROJETEUR DESSINATEUR", "entite": "TG WOOD", "lieu": "OUED SALEH", "demandeur": "S.MENJRA", "recruteur": "Zakaria", "statut": "Signature DRH"},
    {"titre": "Projeteur", "entite": "TGCC", "lieu": "TSP Safi", "demandeur": "B.MORABET", "recruteur": "Zakaria", "statut": "Signature DRH"},
    {"titre": "Consultant SAP", "entite": "TGCC", "lieu": "Siège", "demandeur": "O.KETTA", "recruteur": "Zakaria", "statut": "Signature DRH"},

    # Colonne Clôture
    {"titre": "Doc Controller", "entite": "TGEM", "lieu": "SIEGE", "demandeur": "A.SANKARI", "recruteur": "Zakaria", "statut": "Clôture"},
    {"titre": "Ingénieur étude/qualité", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "A.MOUTANABI", "recruteur": "Zakaria", "statut": "Clôture"},
    {"titre": "Responsable Cybersecurité", "entite": "TGCC", "lieu": "Siège", "demandeur": "Ghazi", "recruteur": "Zakaria", "statut": "Clôture"},
    {"titre": "CHEF DE CHANTIER", "entite": "TGCC", "demandeur": "M.FENNAN", "recruteur": "Zakaria", "statut": "Clôture"},
    {"titre": "Ing contrôle de la performance", "entite": "TGCC", "lieu": "Siège", "demandeur": "H.BARIGOU", "recruteur": "Ghita", "statut": "Clôture"},
    {"titre": "Ingénieur Systèmes Réseaux", "entite": "TGCC", "lieu": "Siège", "demandeur": "M.JADDOR", "recruteur": "Ghita", "statut": "Clôture"},
    {"titre": "Responsable étude de prix", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "S.Bennani Zitani", "recruteur": "Ghita", "statut": "Clôture"},
    {"titre": "Responsable Travaux", "entite": "TGEM", "lieu": "Zone Rabat", "demandeur": "S.ACHIR", "recruteur": "Zakaria", "statut": "Clôture"},

    # Colonne Désistement
    {"titre": "Conducteur de Travaux", "entite": "TGCC", "lieu": "JORF LASFAR", "demandeur": "M.FENNAN", "recruteur": "Zakaria", "statut": "Désistement"},
    {"titre": "Chef de Chantier", "entite": "TGCC", "lieu": "TOARC", "demandeur": "M.FENNAN", "recruteur": "Zakaria", "statut": "Désistement"},
    {"titre": "Magasinier", "entite": "TG WOOD", "lieu": "Oulad Saleh", "demandeur": "K.TAZI", "recruteur": "Ghita", "statut": "Désistement", "commentaire": "Pas de retour du demandeur"}
]


def create_integration_filters(df_recrutement, prefix=""):
    """Créer des filtres spécifiques pour les intégrations (sans les périodes)"""
    if df_recrutement is None or len(df_recrutement) == 0:
        return {}

    # Organiser les filtres dans deux colonnes dans la sidebar
    filters = {}
    left_col, right_col = st.sidebar.columns(2)

    # Filtre par entité demandeuse (colonne gauche)
    entites = ['Toutes'] + sorted(df_recrutement['Entité demandeuse'].dropna().unique())
    with left_col:
        filters['entite'] = st.selectbox("Entité demandeuse", entites, key=f"{prefix}_entite")

    # Filtre par direction concernée (colonne droite)
    directions = ['Toutes'] + sorted(df_recrutement['Direction concernée'].dropna().unique())
    with right_col:
        filters['direction'] = st.selectbox("Direction concernée", directions, key=f"{prefix}_direction")

    # Pas de filtres de période pour les intégrations
    filters['periode_recrutement'] = 'Toutes'
    filters['periode_demande'] = 'Toutes'

    return filters

def create_global_filters(df_recrutement, prefix="", include_periode_recrutement=True, include_periode_demande=True):
    """Créer des filtres globaux réutilisables pour tous les onglets.

    include_periode_recrutement et include_periode_demande contrôlent si le sélecteur
    de période correspondant est affiché (utile pour n'affecter qu'une section).
    """
    if df_recrutement is None or len(df_recrutement) == 0:
        return {}

    # Organiser les filtres dans deux colonnes dans la sidebar
    filters = {}
    left_col, right_col = st.sidebar.columns(2)

    # Filtre par entité demandeuse (colonne gauche)
    entites = ['Toutes'] + sorted(df_recrutement['Entité demandeuse'].dropna().unique())
    with left_col:
        filters['entite'] = st.selectbox("Entité demandeuse", entites, key=f"{prefix}_entite")

    # Filtre par direction concernée (colonne droite)
    directions = ['Toutes'] + sorted(df_recrutement['Direction concernée'].dropna().unique())
    with right_col:
        filters['direction'] = st.selectbox("Direction concernée", directions, key=f"{prefix}_direction")

    # Ajouter les filtres de période (sans ligne de séparation)
    left_col2, right_col2 = st.sidebar.columns(2)

    # Filtre Période de recrutement (basé sur Date d'entrée effective)
    if include_periode_recrutement:
        with left_col2:
            if 'Date d\'entrée effective du candidat' in df_recrutement.columns:
                df_recrutement['Année_Recrutement'] = df_recrutement['Date d\'entrée effective du candidat'].dt.year
                annees_rec = sorted([y for y in df_recrutement['Année_Recrutement'].dropna().unique() if not pd.isna(y)])
                if annees_rec:
                    filters['periode_recrutement'] = st.selectbox(
                        "Période de recrutement", 
                        ['Toutes'] + [int(a) for a in annees_rec], 
                        index=len(annees_rec), 
                        key=f"{prefix}_periode_rec"
                    )
                else:
                    filters['periode_recrutement'] = 'Toutes'
            else:
                filters['periode_recrutement'] = 'Toutes'
    else:
        # Ne pas afficher le sélecteur, s'assurer que la valeur reste 'Toutes'
        filters['periode_recrutement'] = 'Toutes'

    # Filtre Période de la demande (basé sur Date de réception de la demande)
    date_demande_col = 'Date de réception de la demande aprés validation de la DRH'
    if include_periode_demande:
        with right_col2:
            if date_demande_col in df_recrutement.columns:
                df_recrutement['Année_Demande'] = df_recrutement[date_demande_col].dt.year
                annees_dem = sorted([y for y in df_recrutement['Année_Demande'].dropna().unique() if not pd.isna(y)])
                if annees_dem:
                    filters['periode_demande'] = st.selectbox(
                        "Période de la demande", 
                        ['Toutes'] + [int(a) for a in annees_dem], 
                        index=len(annees_dem), 
                        key=f"{prefix}_periode_dem"
                    )
                else:
                    filters['periode_demande'] = 'Toutes'
            else:
                filters['periode_demande'] = 'Toutes'
    else:
        # Ne pas afficher le sélecteur, s'assurer que la valeur reste 'Toutes'
        filters['periode_demande'] = 'Toutes'

    return filters

def apply_global_filters(df, filters):
    """Appliquer les filtres globaux aux données"""
    df_filtered = df.copy()
    
    if filters.get('entite') != 'Toutes':
        df_filtered = df_filtered[df_filtered['Entité demandeuse'] == filters['entite']]
    
    if filters.get('direction') != 'Toutes':
        df_filtered = df_filtered[df_filtered['Direction concernée'] == filters['direction']]
    
    # Appliquer le filtre période de recrutement
    if filters.get('periode_recrutement') != 'Toutes' and 'Année_Recrutement' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Année_Recrutement'] == filters['periode_recrutement']]
    
    # Appliquer le filtre période de la demande
    if filters.get('periode_demande') != 'Toutes' and 'Année_Demande' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Année_Demande'] == filters['periode_demande']]
    
    return df_filtered


@st.cache_resource
def get_gsheet_client():
    """Crée et retourne un client gspread authentifié en utilisant les secrets Streamlit."""
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


def load_data_from_google_sheets(sheet_url):
    """
    Charger les données depuis Google Sheets avec authentification automatique via les secrets.
    """
    try:
        # Extraire l'ID de la feuille et le GID depuis l'URL
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        gid_match = re.search(r"[?&]gid=(\d+)", sheet_url)
        
        if not sheet_id_match:
            raise ValueError("Impossible d'extraire l'ID du Google Sheet depuis l'URL")
        
        sheet_id = sheet_id_match.group(1)
        gid = gid_match.group(1) if gid_match else '0'
        
        # Utiliser le client authentifié avec les secrets
        gc = get_gsheet_client()
        if gc is None:
            # Fallback vers l'export CSV public si l'authentification échoue
            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            df = pd.read_csv(export_url)
            return df
        
        # Ouvrir la feuille par ID
        sh = gc.open_by_key(sheet_id)
        
        # Sélectionner la worksheet par GID
        try:
            worksheet = sh.get_worksheet_by_id(int(gid))
        except:
            worksheet = sh.sheet1  # Fallback vers la première feuille
        
        # Récupérer toutes les données
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
        
    except Exception as e:
        # Si l'authentification échoue, essayer l'export CSV public
        try:
            sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
            gid_match = re.search(r"[?&]gid=(\d+)", sheet_url)
            
            if sheet_id_match:
                sheet_id = sheet_id_match.group(1)
                gid = gid_match.group(1) if gid_match else '0'
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                df = pd.read_csv(export_url)
                return df
        except:
            pass
        
        raise e


def load_data_from_files(csv_file=None, excel_file=None):
    """Charger et préparer les données depuis les fichiers uploadés ou locaux"""
    df_integration = None
    df_recrutement = None
    try:
        # Charger le CSV (données d'intégration)
        if csv_file is not None:
            df_integration = pd.read_csv(csv_file)
        else:
            # Fallback vers fichier local s'il existe
            local_csv = '2025-10-09T20-31_export.csv'
            if os.path.exists(local_csv):
                df_integration = pd.read_csv(local_csv)

        if df_integration is not None and 'Date Intégration' in df_integration.columns:
            df_integration['Date Intégration'] = pd.to_datetime(df_integration['Date Intégration'])

        # Charger l'Excel (données de recrutement)
        # Si une synchronisation Google Sheets a été réalisée, utiliser ce DataFrame
        try:
            if 'synced_recrutement_df' in st.session_state and st.session_state.synced_recrutement_df is not None:
                df_recrutement = st.session_state.synced_recrutement_df.copy()
            elif excel_file is not None:
                df_recrutement = pd.read_excel(excel_file, sheet_name=0)
            else:
                # Fallback vers fichier local s'il existe
                local_excel = 'Recrutement global PBI All  google sheet (5).xlsx'
                if os.path.exists(local_excel):
                    df_recrutement = pd.read_excel(local_excel, sheet_name=0)
        except Exception as e:
            st.error(f"Erreur lors du chargement des données de recrutement: {e}")

        if df_recrutement is not None:
            # Nettoyer et préparer les données de recrutement
            # Convertir les dates
            date_columns = ['Date de réception de la demande aprés validation de la DRH',
                           'Date d\'entrée effective du candidat',
                           'Date d\'annulation /dépriorisation de la demande',
                           'Date de la 1er réponse du demandeur à l\'équipe RH']
            
            for col in date_columns:
                if col in df_recrutement.columns:
                    try:
                        df_recrutement[col] = _parse_mixed_dates(df_recrutement[col])
                    except Exception:
                        # fallback
                        df_recrutement[col] = pd.to_datetime(df_recrutement[col], errors='coerce')
            
            # Nettoyer les colonnes avec des espaces
            df_recrutement.columns = df_recrutement.columns.str.strip()
            
            # Nettoyer les colonnes numériques pour éviter les erreurs de type
            numeric_columns = ['Nb de candidats pré-selectionnés']
            for col in numeric_columns:
                if col in df_recrutement.columns:
                    df_recrutement[col] = pd.to_numeric(df_recrutement[col], errors='coerce')
                    df_recrutement[col] = df_recrutement[col].fillna(0)

            # Vérification basique des colonnes critiques et message dans les logs
            required_cols = [
                'Statut de la demande', 'Poste demandé', 'Direction concernée',
                'Entité demandeuse', 'Modalité de recrutement'
            ]
            missing = [c for c in required_cols if c not in df_recrutement.columns]
            if missing:
                # Log via st.warning but don't raise — keep app running
                st.warning(f"Colonnes attendues manquantes dans le fichier de recrutement: {missing}")
        
        return df_integration, df_recrutement
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return None, None

def create_integration_timeline(df):
    """Créer un graphique de timeline des intégrations"""
    # Grouper par mois
    df['Mois'] = df['Date Intégration'].dt.to_period('M')
    monthly_stats = df.groupby(['Mois', 'Statut']).size().reset_index(name='Count')
    monthly_stats['Mois_str'] = monthly_stats['Mois'].astype(str)
    
    fig = px.bar(
        monthly_stats, 
        x='Mois_str', 
        y='Count',
        color='Statut',
        title="📈 Évolution des Intégrations par Mois",
        color_discrete_map={'En cours': '#ff6b6b', 'Complet': '#51cf66'}
    )
    
    fig.update_traces(hovertemplate='%{y}<extra></extra>')
    fig.update_layout(
        xaxis_title="Mois",
        yaxis_title="Nombre d'intégrations",
        showlegend=True,
        height=400
    )
    
    return fig

def create_affectation_chart(df):
    """Créer un graphique par affectation"""
    affectation_stats = df['Affectation'].value_counts().head(10)
    
    fig = px.pie(
        values=affectation_stats.values,
        names=affectation_stats.index,
        title="🏢 Répartition par Affectation (Top 10)"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig


def render_plotly_scrollable(fig, max_height=500):
    """Renders a plotly figure inside a scrollable HTML div so the user can scroll when there are many bars."""
    try:
        # Use components.html so the plotly JS is executed correctly in Streamlit
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        # Inject a small CSS block that targets Plotly's title classes inside the
        # generated HTML so we can enforce consistent font and left alignment
        injected_css = """
<style>
/* Ensure the plotly SVG title (gtitle) uses our TITLE_FONT and is left-aligned */
.plotly .gtitle, .plotly .gtitle text { font-family: Arial, sans-serif !important; font-size: 16px !important; fill: #111111 !important; }
.plotly .gtitle { text-anchor: start !important; }
/* Force the plot container to align left inside the Streamlit component */
.streamlit-plotly-wrapper{ display:flex; justify-content:flex-start; }
</style>
"""

        # Wrap the plot HTML in a left-aligned container so the chart isn't centered
        wrapper = f"""
<div class='streamlit-plotly-wrapper' style='width:100%;'>
  {injected_css}
  {html}
</div>
"""
        # components.html supports scrolling and executes scripts
        components.html(wrapper, height=max_height, scrolling=True)
    except Exception:
        # Fallback to default renderer
        st.plotly_chart(fig, use_container_width=True)

def create_recrutements_clotures_tab(df_recrutement, global_filters):
    """Onglet Recrutements Clôturés avec style carte"""
    
    # Filtrer seulement les recrutements clôturés
    df_cloture = df_recrutement[df_recrutement['Statut de la demande'] == 'Clôture'].copy()
    
    if len(df_cloture) == 0:
        st.warning("Aucune donnée de recrutement clôturé disponible")
        return
    
    # Appliquer les filtres globaux
    df_filtered = apply_global_filters(df_cloture, global_filters)

    # Use the HTML KPI cards renderer for a more attractive layout
    recrutements = len(df_filtered)
    postes_uniques = df_filtered['Poste demandé'].nunique()
    directions_uniques = df_filtered['Direction concernée'].nunique()

    # Compute delai display and help
    date_reception_col = 'Date de réception de la demande aprés validation de la DRH'
    date_retour_rh_col = 'Date du 1er retour equipe RH  au demandeur'
    delai_display = "N/A"
    delai_help = "Colonnes manquantes ou pas de durées valides"
    if date_reception_col in df_filtered.columns and date_retour_rh_col in df_filtered.columns:
        try:
            s = pd.to_datetime(df_filtered[date_reception_col], errors='coerce')
            e = pd.to_datetime(df_filtered[date_retour_rh_col], errors='coerce')
            mask = s.notna() & e.notna()
            if mask.sum() > 0:
                durees = (e[mask] - s[mask]).dt.days
                durees = durees[durees > 0]
                if len(durees) > 0:
                    delai_moyen = round(durees.mean(), 1)
                    delai_display = f"{delai_moyen}"
                    delai_help = f"Moyenne calculée sur {len(durees)} demandes"
        except Exception:
            pass

    # Revert to simple metrics (no bordered-card styling) in the Recrutements Clôturés section
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nombre de recrutements", recrutements)
    with col2:
        st.metric("Postes concernés", postes_uniques)
    with col3:
        st.metric("Nombre de Directions concernées", directions_uniques)
    with col4:
        st.metric("Délai moyen recrutement (jours)", delai_display)
    
    # Graphiques en ligne 1
    col1, col2 = st.columns([2,1])
    
    with col1:
        # Évolution des recrutements par mois (comme dans l'image 1)
        if 'Date d\'entrée effective du candidat' in df_filtered.columns:
            # Générer une série complète de mois entre la plus petite et la plus grande date
            df_filtered['Mois_Année'] = df_filtered['Date d\'entrée effective du candidat'].dt.to_period('M').dt.to_timestamp()
            monthly_data = df_filtered.groupby('Mois_Année').size().rename('Count')
            if not monthly_data.empty:
                all_months = pd.date_range(start=monthly_data.index.min(), end=monthly_data.index.max(), freq='MS')
                monthly_data = monthly_data.reindex(all_months, fill_value=0)
                monthly_data = monthly_data.reset_index().rename(columns={'index': 'Mois_Année'})
                monthly_data['Mois_Année'] = monthly_data['Mois_Année'].dt.strftime('%b %Y')

                fig_evolution = px.bar(
                    monthly_data,
                    x='Mois_Année',
                    y='Count',
                    title="Évolution des recrutements",
                    text='Count'
                )
                fig_evolution.update_traces(
                    marker_color='#1f77b4',
                    textposition='outside',
                    texttemplate='%{y}',
                    hovertemplate='%{y}<extra></extra>'
                )
                fig_evolution.update_layout(
                    height=360,
                    margin=dict(t=60, b=30, l=20, r=20),
                    xaxis_title=None,
                    yaxis_title=None,
                    xaxis=dict(
                        tickmode='array',
                        tickvals=monthly_data['Mois_Année'],
                        ticktext=monthly_data['Mois_Année'],
                        tickangle=45
                    )
                )
                st.plotly_chart(fig_evolution, use_container_width=True)
    
    with col2:
        # Répartition par modalité de recrutement (CORRECTION: légende déplacée à l'extérieur)
        if 'Modalité de recrutement' in df_filtered.columns:
            modalite_data = df_filtered['Modalité de recrutement'].value_counts()
            
            fig_modalite = go.Figure(data=[go.Pie(
                labels=modalite_data.index, 
                values=modalite_data.values,
                hole=.5,
                textposition='inside',
                textinfo='percent'
            )])
            fig_modalite.update_layout(
                title="Répartition par Modalité de recrutement",
                height=300,
                # Légende positionnée à droite pour éviter le chevauchement
                legend=dict(
                    orientation="v", 
                    yanchor="middle", 
                    y=0.5, 
                    xanchor="left", 
                    x=1.05
                ),
                # Ajuster les marges pour faire de la place à la légende
                margin=dict(l=20, r=150, t=50, b=20)
            )
            st.plotly_chart(fig_modalite, use_container_width=True)

    # Graphiques en ligne 2
    col3, col4 = st.columns(2)
    
    with col3:
        # Comparaison par direction
        direction_counts = df_filtered['Direction concernée'].value_counts()
        # Convert Series to DataFrame for plotly express compatibility
        df_direction = direction_counts.rename_axis('Direction').reset_index(name='Count')
        df_direction = df_direction.sort_values('Count', ascending=False)
        # Truncate long labels for readability, keep full label in customdata for hover
        df_direction['Label_trunc'] = df_direction['Direction'].apply(lambda s: _truncate_label(s, max_len=24))
        # Ensure a display label exists (truncated + small gap) to be used for axis and ordering
        if 'Label_display' not in df_direction.columns:
            df_direction['Label_display'] = df_direction['Label_trunc'] + '\u00A0\u00A0'
        # Add two non-breaking spaces to create visual gap between label and bar
        df_direction['Label_display'] = df_direction['Label_trunc'] + '\u00A0\u00A0'
        fig_direction = px.bar(
            df_direction,
            x='Count',
            y='Label_display',
            title="Comparaison par direction",
            text='Count',
            orientation='h',
            custom_data=['Direction']
        )
        fig_direction.update_traces(
            marker_color='#ff7f0e',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>'
        )
        try:
            fig_direction.update_layout(title=dict(text="Comparaison par direction", x=0, xanchor='left', font=TITLE_FONT))
        except Exception:
            pass
        # Standardize title styling (left aligned)
        try:
            fig_direction.update_layout(title=dict(text="Comparaison par direction", x=0, xanchor='left', font=TITLE_FONT))
        except Exception:
            pass
        # Largest at top: reverse the category array so descending values appear from top to bottom
        height_dir = max(300, 28 * len(df_direction))
        fig_direction.update_layout(
            height=height_dir,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=160, t=40, b=30, r=20),
            yaxis=dict(automargin=True, tickfont=dict(size=11), ticklabelposition='outside left', categoryorder='array', categoryarray=list(df_direction['Label_display'][::-1]))
        )
        # Use a compact default visible area (320px) and allow scrolling to see rest
        render_plotly_scrollable(fig_direction, max_height=320)

    with col4:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts()
        df_poste = poste_counts.rename_axis('Poste').reset_index(name='Count')
        df_poste = df_poste.sort_values('Count', ascending=False)
        df_poste['Label_trunc'] = df_poste['Poste'].apply(lambda s: _truncate_label(s, max_len=24))
        if 'Label_display' not in df_poste.columns:
            df_poste['Label_display'] = df_poste['Label_trunc'] + '\u00A0\u00A0'
        df_poste['Label_display'] = df_poste['Label_trunc'] + '\u00A0\u00A0'
        fig_poste = px.bar(
            df_poste,
            x='Count',
            y='Label_display',
            title="Comparaison par poste",
            text='Count',
            orientation='h',
            custom_data=['Poste']
        )
        fig_poste.update_traces(
            marker_color='#2ca02c',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>'
        )
        try:
            fig_poste.update_layout(title=dict(text="Comparaison par poste", x=0, xanchor='left', font=TITLE_FONT))
        except Exception:
            pass
        try:
            fig_poste.update_layout(title=dict(text="Comparaison par poste", x=0, xanchor='left', font=TITLE_FONT))
        except Exception:
            pass
        height_poste = max(300, 28 * len(df_poste))
        fig_poste.update_layout(
            height=height_poste,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=160, t=40, b=30, r=20),
            yaxis=dict(automargin=True, tickfont=dict(size=11), ticklabelposition='outside left', categoryorder='array', categoryarray=list(df_poste['Label_display'][::-1]))
        )
        render_plotly_scrollable(fig_poste, max_height=320)


    # Ligne 3 - KPIs de délai et candidats
    col5, col6 = st.columns(2)

    with col5:
        # Nombre de candidats présélectionnés - avec conversion sécurisée
        try:
            # Convertir les valeurs en numérique, remplacer les erreurs par 0
            candidats_series = pd.to_numeric(df_filtered['Nb de candidats pré-selectionnés'], errors='coerce').fillna(0)
            total_candidats = int(candidats_series.sum())
        except (KeyError, ValueError):
            total_candidats = 0
            
        fig_candidats = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = total_candidats,
            title = {'text': "Nombre de candidats présélectionnés"},
            gauge = {'axis': {'range': [None, max(total_candidats * 2, 100)]},
                     'bar': {'color': "green"},
                    }))
        fig_candidats.update_layout(height=300)
        st.plotly_chart(fig_candidats, use_container_width=True)

    # ... KPI row now includes Délai moyen de recrutement (moved up)

def create_demandes_recrutement_tab(df_recrutement, global_filters):
    """Onglet Demandes de Recrutement avec style carte"""
    
    # Appliquer les filtres globaux
    df_filtered = apply_global_filters(df_recrutement, global_filters)
    
    # Colonne de date pour les calculs
    date_col = 'Date de réception de la demande aprés validation de la DRH'
    
    # KPIs principaux - Indicateurs de demandes sur la même ligne
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Nombre de demandes", len(df_filtered))
    
    with col2:
        # Nouvelles Demandes (ce mois-ci)
        today = datetime.now()
        start_of_month = today.replace(day=1)
        if date_col in df_filtered.columns:
            nouvelles_demandes = len(df_filtered[df_filtered[date_col] >= start_of_month])
            st.metric(
                "Nouvelles Demandes (ce mois-ci)", 
                nouvelles_demandes,
                help="Le nombre de demandes reçues durant le mois en cours."
            )
        else:
            st.metric("Nouvelles Demandes (ce mois-ci)", "N/A")
    
    with col3:
        # Demandes Annulées / Dépriorisées
        if 'Statut de la demande' in df_filtered.columns:
            demandes_annulees = len(df_filtered[
                df_filtered['Statut de la demande'].str.contains('annul|déprioris|Annul|Déprioris|ANNUL|DÉPRIORIS', case=False, na=False)
            ])
            st.metric(
                "Demandes Annulées/Dépriorisées", 
                demandes_annulees,
                help="Le nombre de demandes qui ont été stoppées. 'fuite' du pipeline."
            )
        else:
            st.metric("Demandes Annulées/Dépriorisées", "N/A")
    
    with col4:
        # Taux d'annulation
        if 'Statut de la demande' in df_filtered.columns and len(df_filtered) > 0:
            demandes_annulees = len(df_filtered[
                df_filtered['Statut de la demande'].str.contains('annul|déprioris|Annul|Déprioris|ANNUL|DÉPRIORIS', case=False, na=False)
            ])
            taux_annulation = round((demandes_annulees / len(df_filtered)) * 100, 1)
            st.metric(
                "Taux d'annulation", 
                f"{taux_annulation}%",
                help="Pourcentage de demandes annulées ou dépriorisées par rapport au total."
            )
        else:
            st.metric("Taux d'annulation", "N/A")

    # Graphiques principaux
    st.markdown("---")
    col1, col2, col3 = st.columns([1,1,2])
    
    with col1:
        # Répartition par statut de la demande
        statut_counts = df_filtered['Statut de la demande'].value_counts()
        fig_statut = go.Figure(data=[go.Pie(labels=statut_counts.index, values=statut_counts.values, hole=.5)])
        fig_statut.update_layout(
            title=dict(text="Répartition par statut de la demande", x=0, xanchor='left', font=TITLE_FONT),
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_statut, use_container_width=True)
    
    with col2:
        # Comparaison par raison du recrutement
        if 'Raison du recrutement' in df_filtered.columns:
            raison_counts = df_filtered['Raison du recrutement'].value_counts()
            df_raison = raison_counts.rename_axis('Raison').reset_index(name='Count')
            fig_raison = px.bar(
                df_raison,
                x='Raison',
                y='Count',
                title="Comparaison par raison du recrutement",
                text='Count',
                orientation='v'
            )
            fig_raison.update_traces(
                marker_color='grey', 
                textposition='auto',
                hovertemplate='%{y}<extra></extra>'
            )
            fig_raison.update_layout(
                height=300, 
                xaxis_title=None, 
                yaxis_title=None,
                xaxis={'categoryorder':'total descending'},
                title=dict(text="Comparaison par raison du recrutement", x=0, xanchor='left', font=TITLE_FONT)
            )
            st.plotly_chart(fig_raison, use_container_width=True)
    
    with col3:
        # Évolution des demandes
        if date_col in df_filtered.columns:
            # Générer une série complète de mois entre la plus petite et la plus grande date de demande
            df_filtered['Mois_Année_Demande'] = df_filtered[date_col].dt.to_period('M').dt.to_timestamp()
            monthly_demandes = df_filtered.groupby('Mois_Année_Demande').size().rename('Count')
            if not monthly_demandes.empty:
                all_months = pd.date_range(start=monthly_demandes.index.min(), end=monthly_demandes.index.max(), freq='MS')
                monthly_demandes = monthly_demandes.reindex(all_months, fill_value=0)
                monthly_demandes = monthly_demandes.reset_index().rename(columns={'index': 'Mois_Année_Demande'})
                monthly_demandes['Mois_Année_Demande'] = monthly_demandes['Mois_Année_Demande'].dt.strftime('%b %Y')

                fig_evolution_demandes = px.bar(
                    monthly_demandes,
                    x='Mois_Année_Demande',
                    y='Count',
                    title="Évolution des demandes",
                    text='Count'
                )
                fig_evolution_demandes.update_traces(
                    marker_color='#1f77b4',
                    textposition='outside',
                    texttemplate='%{y}',
                    hovertemplate='%{y}<extra></extra>'
                )
                fig_evolution_demandes.update_layout(height=360, margin=dict(t=60, b=30, l=20, r=20), xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig_evolution_demandes, use_container_width=True)
    
    # Deuxième ligne de graphiques
    col4, col5 = st.columns(2)
    
    with col4:
        # Comparaison par direction
        direction_counts = df_filtered['Direction concernée'].value_counts()
        df_direction = direction_counts.rename_axis('Direction').reset_index(name='Count')
        df_direction = df_direction.sort_values('Count', ascending=False)
        # Truncate long labels for readability, keep full label in customdata for hover
        df_direction['Label_trunc'] = df_direction['Direction'].apply(lambda s: _truncate_label(s, max_len=24))
        # Ensure display label exists (truncated + small gap) to be used for axis and ordering
        if 'Label_display' not in df_direction.columns:
            df_direction['Label_display'] = df_direction['Label_trunc'] + '\u00A0\u00A0'
        fig_direction = px.bar(
            df_direction,
            x='Count',
            y='Label_display',
            title="Comparaison par direction",
            text='Count',
            orientation='h',
            custom_data=['Direction']
        )
        # Show values inside bars and full label on hover
        fig_direction.update_traces(
            marker_color='#ff7f0e',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>'
        )
        # Dynamic height so long lists become scrollable on the page
        height_dir = max(300, 28 * len(df_direction))
        # Ensure largest values appear on top by reversing the truncated label array
        category_array_dir = list(df_direction['Label_display'][::-1])
        fig_direction.update_layout(
            height=height_dir,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=160, t=40, b=30, r=20),
            yaxis=dict(automargin=True, tickfont=dict(size=11), ticklabelposition='outside left', categoryorder='array', categoryarray=category_array_dir),
            title=dict(text="Comparaison par direction", x=0, xanchor='left', font=TITLE_FONT)
        )
        # Render inside the column so the two charts are on the same row and the component width matches the column
        render_plotly_scrollable(fig_direction, max_height=320)
    
    with col5:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts()
        df_poste = poste_counts.rename_axis('Poste').reset_index(name='Count')
        df_poste = df_poste.sort_values('Count', ascending=False)
        df_poste['Label_trunc'] = df_poste['Poste'].apply(lambda s: _truncate_label(s, max_len=24))
        if 'Label_display' not in df_poste.columns:
            df_poste['Label_display'] = df_poste['Label_trunc'] + '\u00A0\u00A0'
        df_poste['Label_display'] = df_poste['Label_trunc'] + '\u00A0\u00A0'
        fig_poste = px.bar(
            df_poste,
            x='Count',
            y='Label_display',
            title="Comparaison par poste",
            text='Count',
            orientation='h',
            custom_data=['Poste']
        )
        fig_poste.update_traces(
            marker_color='#2ca02c',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>'
        )
        height_poste = max(300, 28 * len(df_poste))
        category_array_poste = list(df_poste['Label_display'][::-1])
        fig_poste.update_layout(
            height=height_poste,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=160, t=40, b=30, r=20),
            yaxis=dict(automargin=True, tickfont=dict(size=11), ticklabelposition='outside left', categoryorder='array', categoryarray=category_array_poste),
            title=dict(text="Comparaison par poste", x=0, xanchor='left', font=TITLE_FONT)
        )
        render_plotly_scrollable(fig_poste, max_height=320)

def create_integrations_tab(df_recrutement, global_filters):
    """Onglet Intégrations basé sur les bonnes données"""
    st.header("📊 Intégrations")
    
    # Filtrer les données : Statut "En cours" ET candidat ayant accepté (nom présent)
    candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
    date_integration_col = "Date d'entrée prévisionnelle"
    
    # Diagnostic des données disponibles
    total_en_cours = len(df_recrutement[df_recrutement['Statut de la demande'] == 'En cours'])
    avec_candidat = len(df_recrutement[
        (df_recrutement['Statut de la demande'] == 'En cours') &
        (df_recrutement[candidat_col].notna()) &
        (df_recrutement[candidat_col].str.strip() != "")
    ])
    avec_date_prevue = len(df_recrutement[
        (df_recrutement['Statut de la demande'] == 'En cours') &
        (df_recrutement[candidat_col].notna()) &
        (df_recrutement[candidat_col].str.strip() != "") &
        (df_recrutement[date_integration_col].notna())
    ])
    
    # Critères : Statut "En cours" ET candidat avec nom
    df_integrations = df_recrutement[
        (df_recrutement['Statut de la demande'] == 'En cours') &
        (df_recrutement[candidat_col].notna()) &
        (df_recrutement[candidat_col].str.strip() != "")
    ].copy()
    
    # Message de diagnostic
    if total_en_cours > 0:
        st.info(f"📊 Diagnostic: {total_en_cours} demandes 'En cours' • {avec_candidat} avec candidat nommé • {avec_date_prevue} avec date d'entrée prévue")
    
    if len(df_integrations) == 0:
        st.warning("Aucune intégration en cours trouvée")
        st.info("Vérifiez que les demandes ont le statut 'En cours' ET un nom de candidat dans la colonne correspondante.")
        return
    
    # Appliquer les filtres globaux
    df_filtered = apply_global_filters(df_integrations, global_filters)
    
    # KPIs d'intégration
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Intégrations en cours", len(df_filtered))
    with col2:
        # Intégrations avec date prévue
        avec_date = len(df_filtered[df_filtered[date_integration_col].notna()])
        st.metric("📅 Avec date prévue", avec_date)
    with col3:
        # Intégrations en retard (date prévue passée)
        if date_integration_col in df_filtered.columns:
            df_filtered[date_integration_col] = pd.to_datetime(df_filtered[date_integration_col], errors='coerce')
            reporting_date = st.session_state.get('reporting_date', None)
            if reporting_date is None:
                today = datetime.now()
            else:
                if isinstance(reporting_date, datetime):
                    today = reporting_date
                else:
                    today = datetime.combine(reporting_date, datetime.min.time())
            en_retard = len(df_filtered[(df_filtered[date_integration_col].notna()) & 
                                      (df_filtered[date_integration_col] < today)])
            st.metric("⚠️ En retard", en_retard)
        else:
            st.metric("⚠️ En retard", "N/A")
    
    # Graphiques
    col1, col2 = st.columns(2)

    # Graphique par affectation réactivé
    with col1:
        if 'Affectation' in df_filtered.columns:
            # Utiliser la fonction existante create_affectation_chart
            fig_affectation = create_affectation_chart(df_filtered)
            st.plotly_chart(fig_affectation, use_container_width=True)
        else:
            st.warning("Colonne 'Affectation' non trouvée dans les données.")

    with col2:
        # Évolution des dates d'intégration prévues
        if date_integration_col in df_filtered.columns:
            df_filtered['Mois_Integration'] = df_filtered[date_integration_col].dt.to_period('M')
            monthly_integration = df_filtered.groupby('Mois_Integration').size().reset_index(name='Count')
            # Convertir en nom de mois seulement (ex: "Janvier", "Février")
            monthly_integration['Mois_str'] = monthly_integration['Mois_Integration'].dt.strftime('%B').str.capitalize()
            
            fig_evolution_int = px.bar(
                monthly_integration, 
                x='Mois_str', 
                y='Count',
                title="📈 Évolution des Intégrations Prévues",
                text='Count'
            )
            fig_evolution_int.update_traces(
                marker_color='#2ca02c', 
                textposition='outside',
                hovertemplate='%{y}<extra></extra>'
            )
            fig_evolution_int.update_layout(height=400, xaxis_title="Mois", yaxis_title="Nombre")
            st.plotly_chart(fig_evolution_int, use_container_width=True)
    
    # Tableau détaillé des intégrations
    st.subheader("📋 Détail des Intégrations en Cours")
    colonnes_affichage = [
        candidat_col, 
        'Poste demandé ',
        'Entité demandeuse',
        'Direction concernée',
        'Affectation',
        date_integration_col
    ]
    # Filtrer les colonnes qui existent
    colonnes_disponibles = [col for col in colonnes_affichage if col in df_filtered.columns]
    
    if colonnes_disponibles:
        df_display = df_filtered[colonnes_disponibles].copy()
        
        # Formater la date pour enlever l'heure et s'assurer du bon format DD/MM/YYYY
        if date_integration_col in df_display.columns:
            # Essayer d'abord le format DD/MM/YYYY puis MM/DD/YYYY si nécessaire
            def format_date_safely(date_str):
                if pd.isna(date_str) or date_str == '' or date_str == 'N/A' or date_str is pd.NaT:
                    return 'N/A'
                
                parsed_date = pd.to_datetime(date_str, errors='coerce')
                
                if pd.notna(parsed_date):
                    return parsed_date.strftime('%d/%m/%Y')
                else:
                    return 'N/A'
            
            df_display[date_integration_col] = df_display[date_integration_col].apply(format_date_safely)
        
        # Renommer pour affichage plus propre
        df_display = df_display.rename(columns={
            candidat_col: "Candidat",
            'Poste demandé ': "Poste",
            date_integration_col: "Date d'Intégration Prévue"
        })
        
        # Réinitialiser l'index pour enlever les numéros de ligne
        df_display = df_display.reset_index(drop=True)
        
        # Afficher sans index (hide_index=True)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.warning("Colonnes d'affichage non disponibles")


def create_demandes_recrutement_combined_tab(df_recrutement):
    """Onglet combiné Demandes et Recrutement avec cartes expandables comme Home.py"""
    st.header("📊 Demandes & Recrutement")
    
    # CSS pour les cartes style Home.py
    st.markdown("""
    <style>
    .report-card {
        border-radius: 8px;
        background-color: #f8f9fa;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .report-card h4 {
        margin-top: 0;
        margin-bottom: 10px;
        color: #2c3e50;
        font-size: 1.1em;
    }
    .report-card p {
        margin-bottom: 8px;
        font-size: 0.9em;
        color: #5a6c7d;
    }
    .report-card .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        color: white;
        background-color: #007bff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Créer un seul jeu de filtres (4 contrôles): Entité, Direction, Période de la demande, Période de recrutement
    st.sidebar.subheader("🔧 Filtres Globaux")
    shared_filters = create_global_filters(df_recrutement, "combined", include_periode_recrutement=True, include_periode_demande=True)

    # Dériver deux jeux de filtres à partir des filtres partagés pour que chaque section
    # n'applique que la période qui lui est pertinente.
    filters_demandes = {
        'entite': shared_filters.get('entite', 'Toutes'),
        'direction': shared_filters.get('direction', 'Toutes'),
        'periode_demande': shared_filters.get('periode_demande', 'Toutes'),
        # Ne pas filtrer par période de recrutement dans la section Demandes
        'periode_recrutement': 'Toutes'
    }

    filters_clotures = {
        'entite': shared_filters.get('entite', 'Toutes'),
        'direction': shared_filters.get('direction', 'Toutes'),
        'periode_recrutement': shared_filters.get('periode_recrutement', 'Toutes'),
        # Ne pas filtrer par période de demande dans la section Clôtures
        'periode_demande': 'Toutes'
    }

    # Créer deux cartes expandables principales (comme dans Home.py)
    with st.expander("📋 **DEMANDES DE RECRUTEMENT**", expanded=False):
        create_demandes_recrutement_tab(df_recrutement, filters_demandes)
    
    with st.expander("🎯 **RECRUTEMENTS CLÔTURÉS**", expanded=False):
        create_recrutements_clotures_tab(df_recrutement, filters_clotures)


def calculate_weekly_metrics(df_recrutement):
    """Calcule les métriques hebdomadaires basées sur les vraies données"""
    if df_recrutement is None or len(df_recrutement) == 0:
        return {}
    
    # Obtenir la date de reporting (utiliser st.session_state si défini)
    reporting_date = st.session_state.get('reporting_date', None)
    if reporting_date is None:
        today = datetime.now()
    else:
        if isinstance(reporting_date, datetime):
            today = reporting_date
        else:
            today = datetime.combine(reporting_date, datetime.min.time())
    # start_of_week = Monday (00:00) of the reporting_date's week
    start_of_week = datetime(year=today.year, month=today.month, day=today.day) - timedelta(days=today.weekday())  # Lundi de cette semaine à 00:00
    # Définir la semaine précédente (Lundi -> Vendredi). Exemple: si reporting_date=2025-10-15 (mercredi),
    # start_of_week = 2025-10-13 (lundi), previous_monday = 2025-10-06, previous_friday = 2025-10-10.
    previous_monday = start_of_week - timedelta(days=7)   # Lundi de la semaine précédente (00:00)
    previous_friday = start_of_week - timedelta(days=3)   # Vendredi de la semaine précédente (00:00)
    # exclusive upper bound for inclusive-Friday semantics: < previous_friday + 1 day
    previous_friday_exclusive = previous_friday + timedelta(days=1)
    
    # Définir les colonnes attendues avec des alternatives possibles
    date_reception_col = "Date de réception de la demande après validation de la DRH"
    date_integration_col = "Date d'intégration prévisionnelle"
    candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
    statut_col = "Statut de la demande"
    entite_col = "Entité demandeuse"
    
    # Créer une copie pour les calculs
    df = df_recrutement.copy()

    # Toujours exclure les demandes clôturées/annulées du compteur 'avant'
    # (la case UI a été supprimée : les demandes clôturées ne sont pas comptées)
    include_closed = False
    
    # Vérifier les colonnes disponibles
    available_columns = df.columns.tolist()
    
    # Chercher les colonnes similaires si les noms exacts n'existent pas
    def find_similar_column(target_col, available_cols):
        """Trouve une colonne similaire dans la liste disponible"""
        target_lower = target_col.lower()
        for col in available_cols:
            if col.lower() == target_lower:
                return col
        # Chercher des mots-clés
        if "date" in target_lower and "réception" in target_lower:
            for col in available_cols:
                if "date" in col.lower() and ("réception" in col.lower() or "reception" in col.lower() or "demande" in col.lower()):
                    return col
        elif "date" in target_lower and "intégration" in target_lower:
            for col in available_cols:
                if "date" in col.lower() and ("intégration" in col.lower() or "integration" in col.lower() or "entrée" in col.lower()):
                    return col
        elif "candidat" in target_lower and "retenu" in target_lower:
            for col in available_cols:
                if ("candidat" in col.lower() and "retenu" in col.lower()) or ("nom" in col.lower() and "prénom" in col.lower()):
                    return col
        elif "statut" in target_lower:
            for col in available_cols:
                if "statut" in col.lower() or "status" in col.lower():
                    return col
        elif "entité" in target_lower:
            for col in available_cols:
                if "entité" in col.lower() or "entite" in col.lower():
                    return col
        return None
    
    # Trouver les colonnes réelles
    real_date_reception_col = find_similar_column(date_reception_col, available_columns)
    real_date_integration_col = find_similar_column(date_integration_col, available_columns)
    # chercher une colonne d'acceptation du candidat (date d'acceptation de la promesse)
    possible_accept_cols = [
        "Date d'acceptation",
        "Date d'acceptation du candidat",
        "Date d'acceptation de la promesse",
        "Date d'acceptation promesse",
        "Date d'accept",
        "Date d'acceptation de la promesse d'embauche",
        "Date d'acceptation de la promesse d embauche",
        "Date d'acceptation du candidat",
        'Date d\'acceptation',
    ]
    real_accept_col = find_similar_column('Date d\'acceptation du candidat', available_columns)
    # fallback to integration date if no explicit acceptance date
    if real_accept_col is None:
        # try some common alternatives
        for alt in ['Date d\'acceptation', 'Date d\'acceptation de la promesse', "Date d'accept"]:
            c = find_similar_column(alt, available_columns)
            if c:
                real_accept_col = c
                break
    real_candidat_col = find_similar_column(candidat_col, available_columns)
    real_statut_col = find_similar_column(statut_col, available_columns)
    real_entite_col = find_similar_column(entite_col, available_columns)
    # detect Poste demandé column (used for optional entity-specific title filters)
    real_poste_col = find_similar_column('Poste demandé', available_columns) or find_similar_column('Poste', available_columns)
    
    # Si les colonnes essentielles n'existent pas, retourner vide
    if not real_entite_col:
        st.warning(f"⚠️ Colonne 'Entité' non trouvée. Colonnes disponibles: {', '.join(available_columns[:5])}...")
        return {}
    
    if not real_statut_col:
        st.warning(f"⚠️ Colonne 'Statut' non trouvée. Colonnes disponibles: {', '.join(available_columns[:5])}...")
        return {}
    
    # Convertir les dates si les colonnes existent (gardes robustes)
    if real_date_reception_col and real_date_reception_col in df.columns:
        df[real_date_reception_col] = pd.to_datetime(df[real_date_reception_col], errors='coerce')
    else:
        real_date_reception_col = None
    if real_date_integration_col and real_date_integration_col in df.columns:
        df[real_date_integration_col] = pd.to_datetime(df[real_date_integration_col], errors='coerce')
    else:
        real_date_integration_col = None
    if real_accept_col and real_accept_col in df.columns:
        # Use robust mixed-date parser (handles Excel serials and mixed formats)
        try:
            df[real_accept_col] = _parse_mixed_dates(df[real_accept_col])
        except Exception:
            # Last-resort fallback
            df[real_accept_col] = pd.to_datetime(df[real_accept_col], errors='coerce')
    else:
        real_accept_col = None

    # Normalisation et mots-clés de statuts fermés (utiles dans plusieurs blocs)
    closed_keywords = ['cloture', 'clôture', 'annule', 'annulé', 'depriorise', 'dépriorisé', 'desistement', 'désistement', 'annul', 'reject', 'rejett']
    # Optional: entity-specific title inclusion lists. If an entity is present here,
    # only postes matching the provided list will be counted in 'en_cours' for that entity.
    SPECIAL_TITLE_FILTERS = {
        'TGCC': [
            'CHEF DE PROJETS',
            'INGENIEUR TRAVAUX',
            'CONDUCTEUR TRAVAUX SENIOR (ou Ingénieur Junior)',
            'CONDUCTEUR TRAVAUX',
            'INGENIEUR TRAVAUX JUNIOR',
            'RESPONSABLE QUALITE',
            'CHEF DE CHANTIER',
            'METREUR',
            'RESPONSABLE HSE',
            'SUPERVISEUR HSE',
            'ANIMATEUR HSE',
            'DIRECTEUR PROJETS',
            'RESPONSABLE ADMINISTRATIF ET FINANCIER',
            'RESPONSABLE MAINTENANCE',
            'RESPONSABLE ENERGIE INDUSTRIELLE',
            'RESPONSABLE CYBER SECURITE',
            'RESPONSABLE VRD',
            'RESPONSABLE ACCEUIL',
            'RESPONSABLE ETUDES',
            'TECHNICIEN SI',
            'RESPONSABLE GED & ARCHIVAGE',
            'ARCHIVISTE SENIOR',
            'ARCHIVISTE JUNIOR',
            'TOPOGRAPHE'
        ]
    }
    
    # Calculer les métriques par entité
    entites = df[real_entite_col].dropna().unique()
    metrics_by_entity = {}
    
    for entite in entites:
        df_entite = df[df[real_entite_col] == entite]
        # Définitions temporelles par entité (basées sur la semaine précédente Lundi->Vendredi)
        # previous_monday / previous_friday_exclusive sont définis en haut de la fonction

        # 1. Nb postes ouverts avant début semaine
        # Doit compter toutes les lignes dont 'Date de réception ...' est STRICTEMENT antérieure
        # au vendredi de la semaine précédente (i.e. < previous_friday)
        postes_avant = 0
        if real_date_reception_col and real_date_reception_col in df_entite.columns:
            # 'avant' = toutes les demandes antérieures au début de la semaine précédente (previous_monday)
            # Exclure les demandes déjà clôturées/annulées pour éviter de compter de vieux dossiers fermés.
            mask_date_avant = df_entite[real_date_reception_col] < previous_monday
            mask_not_closed = None
            if not include_closed and real_statut_col and real_statut_col in df_entite.columns:
                # Si l'utilisateur a demandé d'exclure les fermés, construire le masque
                mask_not_closed = ~df_entite[real_statut_col].fillna("").astype(str).apply(lambda s: any(k in _norm(s) for k in closed_keywords))
            # Appliquer les deux masques si disponibles (si include_closed True, on n'applique pas le filtre)
            if mask_not_closed is not None:
                mask_avant = mask_date_avant & mask_not_closed
            else:
                mask_avant = mask_date_avant
            postes_avant = int(df_entite[mask_avant].shape[0])
        else:
            postes_avant = 0

        # 2. Nb nouveaux postes ouverts cette semaine = demandes validées par la DRH
        # dans la semaine précédente (du lundi au vendredi inclus).
        nouveaux_postes = 0
        if real_date_reception_col and real_date_reception_col in df_entite.columns:
            mask_nouveaux = (df_entite[real_date_reception_col] >= previous_monday) & (df_entite[real_date_reception_col] < previous_friday_exclusive)
            nouveaux_postes = int(df_entite[mask_nouveaux].shape[0])
        else:
            nouveaux_postes = 0

        # 3. Nb postes pourvus cette semaine: compter les acceptations du candidat
        # dont la date d'acceptation est dans la même fenêtre (previous_monday..previous_friday)
        postes_pourvus = 0
        mask_has_name = None
        if real_candidat_col and real_candidat_col in df_entite.columns:
            mask_has_name = df_entite[real_candidat_col].notna() & (df_entite[real_candidat_col].astype(str).str.strip() != '')

        # préparer un masque de statut 'En cours' si la colonne statut existe (réutilisé plus bas)
        mask_status_en_cours = None
        if real_statut_col and real_statut_col in df_entite.columns:
            mask_status_en_cours = df_entite[real_statut_col].fillna("").astype(str).apply(lambda s: 'en cours' in _norm(s) or 'encours' in _norm(s))

        if real_accept_col and real_accept_col in df_entite.columns:
            mask_accept_prev_week = (df_entite[real_accept_col] >= previous_monday) & (df_entite[real_accept_col] < previous_friday_exclusive)
            if mask_has_name is not None:
                postes_pourvus = int(df_entite[mask_accept_prev_week & mask_has_name].shape[0])
            else:
                postes_pourvus = int(df_entite[mask_accept_prev_week].shape[0])
        else:
            # fallback: try using integration date as proxy for pourvus in the same window
            if real_date_integration_col and real_date_integration_col in df_entite.columns:
                mask_integ_prev_week = (df_entite[real_date_integration_col] >= previous_monday) & (df_entite[real_date_integration_col] < previous_friday_exclusive)
                if mask_has_name is not None:
                    postes_pourvus = int(df_entite[mask_integ_prev_week & mask_has_name].shape[0])
                else:
                    postes_pourvus = int(df_entite[mask_integ_prev_week].shape[0])
            else:
                postes_pourvus = 0

        # 4. Nb postes en cours cette semaine
        # Par défaut on calcule une formule de secours (nouveaux + avant - pourvus)
        postes_en_cours_formula = nouveaux_postes + postes_avant - postes_pourvus
        if postes_en_cours_formula is None:
            postes_en_cours_formula = 0

        # Si la colonne Statut existe, on suit la règle métier stricte demandée :
        # "Postes en cours" = lignes avec statut 'En cours' ET sans valeur dans
        # la colonne 'Nom Prénom du candidat retenu...' (donc pas d'acceptation).
        # Si la colonne Statut est absente, on retombe sur la formule de secours.
        postes_en_cours = int(postes_en_cours_formula)
        postes_en_cours_status = 0
        if mask_status_en_cours is not None:
                mask_has_name_local = None
                if real_candidat_col and real_candidat_col in df_entite.columns:
                    mask_has_name_local = df_entite[real_candidat_col].notna() & (df_entite[real_candidat_col].astype(str).str.strip() != '')

                # Règle stricte demandée : "Postes en cours" = statut 'En cours' ET sans candidat
                if mask_has_name_local is not None:
                    mask_sourcing = mask_status_en_cours & (~mask_has_name_local)
                else:
                    mask_sourcing = mask_status_en_cours

                # Comptage simple et uniforme pour toutes les entités : ne pas appliquer
                # de filtres additionnels (date de réception ou filtre d'intitulé).
                postes_en_cours_status = int(df_entite[mask_sourcing].shape[0])

                # Utiliser ce comptage comme valeur principale 'en_cours'
                postes_en_cours = int(postes_en_cours_status)

        metrics_by_entity[entite] = {
            'avant': postes_avant,
            'nouveaux': nouveaux_postes,
            'pourvus': postes_pourvus,
            'en_cours': postes_en_cours,
            # ajouter info additionnelle utile pour debug/UI
            'en_cours_status_count': postes_en_cours_status
        }
    
    return metrics_by_entity

def create_weekly_report_tab(df_recrutement=None):
    """Onglet Reporting Hebdomadaire (simplifié)

    Cette version affiche les KPI calculés par calculate_weekly_metrics
    en respectant la `st.session_state['reporting_date']` si fournie.
    """
    st.header("📅 Reporting Hebdomadaire : Chiffres Clés de la semaine")

    # Note: les demandes clôturées sont exclues du compteur 'avant' par défaut.
    # La case pour inclure les demandes clôturées a été supprimée.

    # Calculer les métriques
    if df_recrutement is not None and len(df_recrutement) > 0:
        try:
            metrics = calculate_weekly_metrics(df_recrutement)
        except Exception as e:
            st.error(f"⚠️ Erreur lors du calcul des métriques: {e}")
            metrics = {}
    else:
        metrics = {}

    # Exclure certaines entités (Besix et DECO EXCELL) de l'affichage et des totaux
    excluded_entities = set(['BESIX-TGCC', 'DECO EXCELL'])
    metrics_included = {e: m for e, m in metrics.items() if e not in excluded_entities}

    total_avant = sum(m.get('avant', 0) for m in metrics_included.values())
    total_nouveaux = sum(m.get('nouveaux', 0) for m in metrics_included.values())
    total_pourvus = sum(m.get('pourvus', 0) for m in metrics_included.values())
    total_en_cours = sum(m.get('en_cours', 0) for m in metrics_included.values())
    # total lines with statut 'En cours' (may include those with candidate)
    total_en_cours_status = sum(m.get('en_cours_status_count', 0) for m in metrics_included.values())

    # KPI cards (simple)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Postes en cours (sourcing)", total_en_cours)
    with col2:
        st.metric("Postes pourvus cette semaine", total_pourvus)
    with col3:
        st.metric("Nouveaux postes ouverts", total_nouveaux)
    with col4:
        st.metric("Total postes ouverts avant la semaine", total_avant)

    st.markdown("---")

    # Tableau récapitulatif par entité (HTML personnalisé, rendu centralisé)
    st.subheader("📊 Besoins en Cours par Entité")
    if metrics and len(metrics) > 0:
        # Préparer les données pour le HTML
        table_data = []
        for entite, data in metrics_included.items():
            table_data.append({
                'Entité': entite,
                'Nb postes ouverts avant début semaine': data['avant'] if data['avant'] > 0 else '-',
                'Nb nouveaux postes ouverts cette semaine': data['nouveaux'] if data['nouveaux'] > 0 else '-',
                'Nb postes pourvus cette semaine': data['pourvus'] if data['pourvus'] > 0 else '-',
                "Nb postes statut 'En cours' (total)": data.get('en_cours_status_count', 0) if data.get('en_cours_status_count', 0) > 0 else '-',
                'Nb postes en cours cette semaine (sourcing)': data['en_cours'] if data['en_cours'] > 0 else '-'
            })

        # Ajouter la ligne de total
        table_data.append({
            'Entité': '**Total**',
            'Nb postes ouverts avant début semaine': f'**{total_avant}**',
            'Nb nouveaux postes ouverts cette semaine': f'**{total_nouveaux}**',
            'Nb postes pourvus cette semaine': f'**{total_pourvus}**',
            "Nb postes statut 'En cours' (total)": f'**{total_en_cours_status}**',
            'Nb postes en cours cette semaine (sourcing)': f'**{total_en_cours}**'
        })

        # HTML + CSS (repris de la version précédente)
        st.markdown("""
        <style>
        .table-container {
            display: flex;
            justify-content: center;
            width: 100%;
            margin: 15px 0;
        }
        .custom-table {
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            max-width: 900px;
            margin: 0 auto;
        }
        .custom-table th {
            background-color: #DC143C !important; /* Rouge vif */
            color: white !important;
            font-weight: bold !important;
            text-align: center !important;
            padding: 8px 6px !important;
            border: 1px solid white !important;
            font-size: 0.8em;
            line-height: 1.2;
        }
        .custom-table td {
            text-align: center !important;
            padding: 6px 4px !important;
            border: 1px solid #ddd !important;
            background-color: white !important;
            font-size: 0.75em;
            line-height: 1.1;
        }
        .custom-table .entity-cell {
            text-align: left !important;
            padding-left: 10px !important;
            font-weight: 500;
            min-width: 120px;
        }
        .custom-table .total-row {
            background-color: #DC143C !important; /* Rouge vif */
            color: white !important;
            font-weight: bold !important;
            border-top: 2px solid #DC143C !important;
        }
        .custom-table .total-row .entity-cell {
            text-align: left !important;
            padding-left: 10px !important;
            font-weight: bold !important;
        }
        .custom-table .total-row td {
            background-color: #DC143C !important; /* Assurer le fond rouge sur chaque cellule */
            color: white !important; /* Assurer le texte blanc */
            font-size: 0.8em !important;
            font-weight: bold !important;
            border: 1px solid #DC143C !important; /* Bordures rouges */
        }
        .custom-table .total-row .entity-cell {
            text-align: left !important;
            padding-left: 10px !important;
            font-weight: bold !important;
            background-color: #DC143C !important; /* Fond rouge pour la cellule entité */
            color: white !important; /* Texte blanc pour la cellule entité */
        }
        </style>
        """, unsafe_allow_html=True)

        # Construire le tableau HTML
        html_table = '<div class="table-container">'
        html_table += '<table class="custom-table">'
        html_table += '<thead><tr>'
        html_table += '<th>Entité</th>'
        html_table += '<th>Nb postes ouverts avant début semaine</th>'
        html_table += '<th>Nb nouveaux postes ouverts cette semaine</th>'
        html_table += '<th>Nb postes pourvus cette semaine</th>'
        html_table += '<th>Nb postes en cours cette semaine (sourcing)</th>'
        html_table += '</tr></thead>'
        html_table += '<tbody>'

        # Ajouter les lignes de données (toutes sauf la dernière qui est TOTAL)
        data_rows = [row for row in table_data[:-1] if row["Entité"] and row["Entité"].strip()]
        for row in data_rows:
            html_table += '<tr>'
            html_table += f'<td class="entity-cell">{row["Entité"]}</td>'
            html_table += f'<td>{row["Nb postes ouverts avant début semaine"]}</td>'
            html_table += f'<td>{row["Nb nouveaux postes ouverts cette semaine"]}</td>'
            html_table += f'<td>{row["Nb postes pourvus cette semaine"]}</td>'
            html_table += f'<td>{row["Nb postes en cours cette semaine (sourcing)"]}</td>'
            html_table += '</tr>'

        # Ligne TOTAL (la dernière)
        total_row = table_data[-1]
        html_table += '<tr class="total-row">'
        html_table += f'<td class="entity-cell">TOTAL</td>'
        html_table += f'<td>{total_row["Nb postes ouverts avant début semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb nouveaux postes ouverts cette semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb postes pourvus cette semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb postes en cours cette semaine (sourcing)"].replace("**", "")}</td>'
        html_table += '</tr>'
        html_table += '</tbody></table></div>'

        st.markdown(html_table, unsafe_allow_html=True)
    else:
        # Affichage par défaut si pas de metrics
        default_html = """
<div class="table-container">
    <table class="custom-table">
        <thead>
            <tr>
                <th>Entité</th>
                <th>Nb postes ouverts avant début semaine</th>
                <th>Nb nouveaux postes ouverts cette semaine</th>
                <th>Nb postes pourvus cette semaine</th>
                <th>Nb postes en cours cette semaine</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="entity-cell">TGCC</td>
                <td>19</td>
                <td>12</td>
                <td>5</td>
                <td>26</td>
            </tr>
            <tr>
                <td class="entity-cell">TGEM</td>
                <td>2</td>
                <td>2</td>
                <td>0</td>
                <td>4</td>
            </tr>
            <tr class="total-row">
                <td class="entity-cell">TOTAL</td>
                <td>21</td>
                <td>14</td>
                <td>5</td>
                <td>30</td>
            </tr>
        </tbody>
    </table>
</div>
"""
        st.markdown(default_html, unsafe_allow_html=True)

    # Section Debug (expandable): montrer les lignes et pourquoi elles sont comptées
    with st.expander("🔍 Debug - Détails des lignes (ouvrir/fermer)", expanded=False):
        try:
            df_debug = df_recrutement.copy() if df_recrutement is not None else pd.DataFrame()
            if not df_debug.empty:
                cols = df_debug.columns.tolist()

                def find_similar_column(target_col, available_cols):
                    target_lower = target_col.lower()
                    for col in available_cols:
                        if col.lower() == target_lower:
                            return col
                    if "date" in target_lower and "réception" in target_lower:
                        for col in available_cols:
                            if "date" in col.lower() and ("réception" in col.lower() or "reception" in col.lower() or "demande" in col.lower()):
                                return col
                    if "date" in target_lower and "intégration" in target_lower:
                        for col in available_cols:
                            if "date" in col.lower() and ("intégration" in col.lower() or "integration" in col.lower() or "entrée" in col.lower()):
                                return col
                    # Prefer columns explicitly mentioning the candidate / promesse
                    if "candidat" in target_lower or "promesse" in target_lower or "accept" in target_lower:
                        for col in available_cols:
                            lc = col.lower()
                            if ("candidat" in lc and "retenu" in lc) or ("accept" in lc and "candidat" in lc) or ("promesse" in lc and "candidat" in lc):
                                return col
                        # fallback to any column containing 'candidat'
                        for col in available_cols:
                            if 'candidat' in col.lower():
                                return col
                    # As a last resort, match generic 'nom'/'prénom' columns
                    if "candidat" in target_lower and "retenu" in target_lower:
                        for col in available_cols:
                            if ("nom" in col.lower() and "pr" in col.lower()) or ("nom" in col.lower() and "prenom" in col.lower()):
                                return col
                    if "statut" in target_lower:
                        for col in available_cols:
                            if "statut" in col.lower() or "status" in col.lower():
                                return col
                    if "entité" in target_lower or "entite" in target_lower:
                        for col in available_cols:
                            if "entité" in col.lower() or "entite" in col.lower():
                                return col
                    return None

                date_reception_col = "Date de réception de la demande après validation de la DRH"
                date_integration_col = "Date d'intégration prévisionnelle"
                candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"

                real_date_reception_col = find_similar_column(date_reception_col, cols)
                real_date_integration_col = find_similar_column(date_integration_col, cols)
                real_accept_col = None
                for alt in ['Date d\'acceptation du candidat','Date d\'acceptation','Date d\'acceptation de la promesse',"Date d'accept"]:
                    c = find_similar_column(alt, cols)
                    if c:
                        real_accept_col = c
                        break
                real_candidat_col = candidat_col if candidat_col in cols else find_similar_column(candidat_col, cols)
                real_statut_col = find_similar_column('Statut de la demande', cols)
                real_entite_col = find_similar_column('Entité demandeuse', cols) or find_similar_column('Entité', cols)

                rd = st.session_state.get('reporting_date', None)
                if rd is None:
                    today = datetime.now()
                else:
                    today = rd if isinstance(rd, datetime) else datetime.combine(rd, datetime.min.time())
                start_of_week = today - timedelta(days=today.weekday())
                start_of_last_week = start_of_week - timedelta(days=7)

                if real_date_reception_col and real_date_reception_col in df_debug.columns:
                    df_debug[real_date_reception_col] = pd.to_datetime(df_debug[real_date_reception_col], errors='coerce')
                if real_date_integration_col and real_date_integration_col in df_debug.columns:
                    df_debug[real_date_integration_col] = pd.to_datetime(df_debug[real_date_integration_col], errors='coerce')
                if real_accept_col and real_accept_col in df_debug.columns:
                    try:
                        df_debug[real_accept_col] = _parse_mixed_dates(df_debug[real_accept_col])
                    except Exception:
                        df_debug[real_accept_col] = pd.to_datetime(df_debug[real_accept_col], errors='coerce')

                def _local_norm(x):
                    if pd.isna(x) or x is None:
                        return ''
                    s = str(x)
                    s = unicodedata.normalize('NFKD', s)
                    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
                    return s.lower().strip()

                mask_last_week = pd.Series(False, index=df_debug.index)
                mask_this_week = pd.Series(False, index=df_debug.index)
                mask_status_en_cours = pd.Series(False, index=df_debug.index)
                mask_has_name = pd.Series(False, index=df_debug.index)
                mask_accept_this_week = pd.Series(False, index=df_debug.index)
                mask_integration_this_week = pd.Series(False, index=df_debug.index)
                mask_reception_le_today = pd.Series(True, index=df_debug.index)

                if real_date_reception_col and real_date_reception_col in df_debug.columns:
                    mask_last_week = (df_debug[real_date_reception_col] >= start_of_last_week) & (df_debug[real_date_reception_col] < start_of_week)
                    mask_this_week = (df_debug[real_date_reception_col] >= start_of_week) & (df_debug[real_date_reception_col] <= today)
                    mask_reception_le_today = df_debug[real_date_reception_col].notna() & (df_debug[real_date_reception_col] <= today)

                if real_statut_col and real_statut_col in df_debug.columns:
                    mask_status_en_cours = df_debug[real_statut_col].fillna("").astype(str).apply(lambda s: ('en cours' in _local_norm(s)) or ('encours' in _local_norm(s)))

                if real_candidat_col and real_candidat_col in df_debug.columns:
                    mask_has_name = df_debug[real_candidat_col].notna() & (df_debug[real_candidat_col].astype(str).str.strip() != '')

                if real_accept_col and real_accept_col in df_debug.columns:
                    mask_accept_this_week = (df_debug[real_accept_col] >= start_of_week) & (df_debug[real_accept_col] <= today)

                if real_date_integration_col and real_date_integration_col in df_debug.columns:
                    mask_integration_this_week = (df_debug[real_date_integration_col] >= start_of_week) & (df_debug[real_date_integration_col] <= today)

                contributes_avant = mask_last_week
                contributes_nouveaux = mask_this_week
                contributes_pourvus = (mask_has_name & mask_status_en_cours & mask_accept_this_week) | (mask_has_name & mask_status_en_cours & mask_integration_this_week)
                # contrib_en_cours: statut 'En cours'
                contributes_en_cours = mask_status_en_cours

                # For the debug view we want the contributors to exactly reflect the
                # 'Besoins en Cours' table: show only the rows that match the
                # en_cours definition (statut 'En cours').
                any_contrib = contributes_en_cours

                df_selected = df_debug[any_contrib].copy()

                display_cols = []
                if real_entite_col and real_entite_col in df_selected.columns:
                    display_cols.append(real_entite_col)
                if real_candidat_col and real_candidat_col in df_selected.columns:
                    display_cols.append(real_candidat_col)
                if real_statut_col and real_statut_col in df_selected.columns:
                    display_cols.append(real_statut_col)
                if real_date_reception_col and real_date_reception_col in df_selected.columns:
                    display_cols.append(real_date_reception_col)
                if real_accept_col and real_accept_col in df_selected.columns:
                    display_cols.append(real_accept_col)

                df_out = df_selected[display_cols].copy() if display_cols else df_selected.copy()
                # mark if the row matches any SPECIAL_TITLE_FILTERS for its entity (useful for TGCC overrides)
                # compute a boolean flag indicating whether the row's title matches
                # any entry in the SPECIAL_TITLE_FILTERS for that entity.
                # Use safe fallbacks if some variables are not present in this scope.
                try:
                    # try to access SPECIAL_TITLE_FILTERS from the module scope
                    st_special_filters = globals().get('SPECIAL_TITLE_FILTERS', None)
                    # if real_poste_col isn't defined in this block, try to discover a 'Poste' column
                    rp = globals().get('real_poste_col', None)
                    if not rp:
                        # conservative search for a poste-like column name in df_selected
                        for c in df_selected.columns:
                            if 'poste' in c.lower() or 'title' in c.lower():
                                rp = c
                                break

                    def _matches_special_title(row):
                        ent = row.get(real_entite_col, '') if real_entite_col in row.index else (row.get('Entité demandeuse', '') or row.get('Entité', ''))
                        titre = ''
                        if rp and rp in row.index:
                            titre = row.get(rp, '')
                        else:
                            titre = row.get('Poste demandé', '') or row.get('Poste demandé ', '') or ''

                        if not ent or not st_special_filters:
                            return False
                        filter_list = st_special_filters.get(ent, [])
                        if not filter_list:
                            return False
                        tnorm = str(titre).strip().upper()
                        return any(tnorm == s for s in filter_list)

                    df_out['special_title_match'] = df_selected.apply(_matches_special_title, axis=1)
                except Exception:
                    df_out['special_title_match'] = False
                df_out['contrib_avant'] = contributes_avant.loc[df_out.index]
                df_out['contrib_nouveaux'] = contributes_nouveaux.loc[df_out.index]
                df_out['contrib_pourvus'] = contributes_pourvus.loc[df_out.index]
                df_out['contrib_en_cours'] = contributes_en_cours.loc[df_out.index]

                # Ensure the candidate value is present in a predictable column named 'candidate_value'
                try:
                    if real_candidat_col and real_candidat_col in df_selected.columns:
                        df_out['candidate_value'] = df_selected[real_candidat_col].fillna('').astype(str)
                    else:
                        df_out['candidate_value'] = ''
                except Exception:
                    df_out['candidate_value'] = ''

                for dc in [real_date_reception_col, real_accept_col, real_date_integration_col]:
                    if dc and dc in df_out.columns:
                        try:
                            # Safely format each date value in the column using .map
                            df_out[dc] = pd.to_datetime(df_out[dc], errors='coerce')
                            df_out[dc] = df_out[dc].map(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else 'N/A')
                        except Exception:
                            pass

                # Allow user to choose display mode: KPI contributors or all rows with statut 'En cours'
                display_mode = st.radio("Mode d'affichage:", ["Contributeurs 'Postes en cours'", "Toutes lignes statut 'En cours'"], index=0)

                if display_mode == "Toutes lignes statut 'En cours'":
                    if real_statut_col and real_statut_col in df_debug.columns:
                        df_status = df_debug[mask_status_en_cours].copy()
                        # option: masquer par défaut les lignes où un candidat est déjà renseigné
                        show_with_candidate = st.checkbox("Afficher aussi les lignes avec candidat renseigné", value=False)
                        if not show_with_candidate and real_candidat_col and real_candidat_col in df_status.columns:
                            df_status = df_status[ ~ (df_status[real_candidat_col].notna() & (df_status[real_candidat_col].astype(str).str.strip() != '')) ].copy()

                        # show requested columns if available
                        desired_cols = [
                            'Poste demandé', 'Raison du recrutement', 'Entité demandeuse',
                            'Direction concernée', 'Affectation', 'Nom Prénom du demandeur',
                            real_candidat_col  # Ajout de la colonne du candidat
                        ]
                        # Filtrer les colonnes qui sont réellement disponibles et non nulles
                        available_show = [c for c in desired_cols if c and c in df_status.columns]
                        
                        # Si la case n'est pas cochée, on veut voir le demandeur, sinon le candidat
                        if not show_with_candidate:
                            if 'Nom Prénom du demandeur' not in available_show:
                                # Assurons-nous que la colonne du demandeur est là si on ne montre pas les candidats
                                requester_col = find_similar_column('Nom Prénom du demandeur', df_status.columns)
                                if requester_col and requester_col not in available_show:
                                    available_show.append(requester_col)
                        else:
                            # Si on montre les candidats, on peut retirer le demandeur si non souhaité
                            if 'Nom Prénom du demandeur' in available_show and real_candidat_col in available_show:
                                available_show.remove('Nom Prénom du demandeur')
                        if not available_show:
                            # fallback to show key columns we detected earlier
                            available_show = []
                            if real_entite_col and real_entite_col in df_status.columns:
                                available_show.append(real_entite_col)
                            if real_candidat_col and real_candidat_col in df_status.columns:
                                available_show.append(real_candidat_col)
                            if real_statut_col and real_statut_col in df_status.columns:
                                available_show.append(real_statut_col)

                        df_out_status = df_status[available_show].copy() if available_show else df_status.copy()
                        st.info(f"Lignes avec statut 'En cours' détectées (après filtre candidat): {len(df_out_status)}")
                        st.dataframe(df_out_status.reset_index(drop=True), use_container_width=True)
                    else:
                        st.warning("Colonne de statut introuvable — impossible de lister les lignes 'En cours'.")
                else:
                    st.info(f"Lignes contribuant au KPI 'Postes en cours' : {len(df_out)} lignes")
                    # expose original DataFrame index to help trace rows between exports/UI
                    df_out_display = df_out.reset_index().rename(columns={'index': '_orig_index'})
                    # ensure candidate_value is the 4th column (index 3) in the display
                    if 'candidate_value' not in df_out_display.columns:
                        df_out_display['candidate_value'] = ''
                    # reorder to put candidate_value at position 3 if there are enough cols
                    cols_order = list(df_out_display.columns)
                    if 'candidate_value' in cols_order:
                        cols_order = [c for c in cols_order if c != 'candidate_value']
                        insert_at = 3 if len(cols_order) >= 3 else len(cols_order)
                        cols_order.insert(insert_at, 'candidate_value')
                        df_out_display = df_out_display[cols_order]
                    # also show a raw representation of the candidate column (if any) to detect invisible chars
                    if real_candidat_col and real_candidat_col in df_out.columns:
                        try:
                            df_out_display['candidate_raw'] = df_out[real_candidat_col].apply(lambda x: repr(x))
                        except Exception:
                            # fallback silently if repr fails for any value
                            df_out_display['candidate_raw'] = ''
                    st.dataframe(df_out_display, use_container_width=True)
            else:
                st.info('Aucune donnée pour le debug.')
        except Exception as e:
            st.error(f"Erreur lors de la génération du debug: {e}")

    st.markdown("---")

    # 3. Section "Pipeline de Recrutement (Kanban)"
    st.subheader("Pipeline de Recrutement (Kanban)")

    # Construire les données du Kanban à partir du fichier importé (préférence aux données réelles)
    # Détection heuristique des colonnes utiles
    def _find_col(cols, keywords):
        for k in keywords:
            for c in cols:
                if k in c.lower():
                    return c
        return None

    cols = df_recrutement.columns.tolist() if df_recrutement is not None else []
    statut_col = _find_col(cols, ['statut', 'status'])
    poste_col = _find_col(cols, ['poste', 'title', 'post'])
    entite_col = _find_col(cols, ['entité', 'entite', 'entité demandeuse', 'entite demandeuse', 'entité'])
    lieu_col = _find_col(cols, ['lieu', 'affectation', 'site'])
    demandeur_col = _find_col(cols, ['demandeur', 'requester'])
    recruteur_col = _find_col(cols, ['recruteur', 'recruiter'])

    def _normalize_kanban(text):
        if text is None or (isinstance(text, float) and np.isnan(text)):
            return ''
        s = str(text)
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(ch for ch in s if not unicodedata.combining(ch))
        return s.lower().strip()

    # Carte statuts canoniques demandés par l'utilisateur (ordre affichage)
    statuts_kanban = ["Désistement","Sourcing","Shortlisté","Signature DRH","Clôture","Dépriorisé"]

    # Mapping de formes possibles -> statut canonique
    status_map = {
        'desistement': 'Désistement',
        'desisté': 'Désistement',
        'sourcing': 'Sourcing',
        'shortlist': 'Shortlisté',
        'shortlisté': 'Shortlisté',
        'shortlisté': 'Shortlisté',
        'signature drh': 'Signature DRH',
        'signature': 'Signature DRH',
        'cloture': 'Clôture',
        'clôture': 'Clôture',
        'dépriorisé': 'Dépriorisé',
        'depriorise': 'Dépriorisé',
    }

    postes_data = []
    if statut_col and df_recrutement is not None:
        for _, r in df_recrutement.iterrows():
            raw = r.get(statut_col)
            if pd.isna(raw):
                continue
            norm = _normalize_kanban(raw)
            canon = None
            # find mapping by substring
            for key, val in status_map.items():
                if key in norm:
                    canon = val
                    break
            # default fallback: keep original raw string capitalized
            if canon is None:
                # if the normalized text closely matches any canonical target, pick it
                for tgt in statuts_kanban:
                    if _normalize_kanban(tgt) == norm:
                        canon = tgt
                        break
            if canon is None:
                # unrecognized statuses go into 'Sourcing' by default
                canon = 'Sourcing'

            titre = r.get(poste_col, '') if poste_col else r.get('Poste demandé', '')
            postes_data.append({
                'statut': canon,
                'titre': titre or '',
                'entite': r.get(entite_col, '') if entite_col else r.get('Entité demandeuse', ''),
                'lieu': r.get(lieu_col, '') if lieu_col else '',
                'demandeur': r.get(demandeur_col, '') if demandeur_col else '',
                'recruteur': r.get(recruteur_col, '') if recruteur_col else ''
            })

    # Fallback sample data if no real rows found
    if not postes_data:
        postes_data = [
            {"statut": "Sourcing", "titre": "Ingénieur Achat", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "A.BOUZOUBAA", "recruteur": "Zakaria"},
            {"statut": "Sourcing", "titre": "Directeur Achats Adjoint", "entite": "TGCC", "lieu": "Siège", "demandeur": "C.BENABDELLAH", "recruteur": "Zakaria"},
            {"statut": "Sourcing", "titre": "INGENIEUR TRAVAUX", "entite": "TGCC", "lieu": "YAMED LOT B", "demandeur": "M.TAZI", "recruteur": "Zakaria"},
            {"statut": "Shortlisté", "titre": "CHEF DE PROJETS", "entite": "TGCC", "lieu": "DESSALEMENT JORF", "demandeur": "M.FENNAN", "recruteur": "ZAKARIA"},
            {"statut": "Shortlisté", "titre": "Planificateur", "entite": "TGCC", "lieu": "ASFI-B", "demandeur": "SOUFIANI", "recruteur": "Ghita"},
            {"statut": "Shortlisté", "titre": "RESPONSABLE TRANS INTERCH", "entite": "TG PREFA", "lieu": "OUED SALEH", "demandeur": "FBOUZOUBAA", "recruteur": "Ghita"},
            {"statut": "Signature DRH", "titre": "PROJETEUR DESSINATEUR", "entite": "TG WOOD", "lieu": "OUED SALEH", "demandeur": "S.MENJRA", "recruteur": "Zakaria"},
            {"statut": "Signature DRH", "titre": "Projeteur", "entite": "TGCC", "lieu": "TSP Safi", "demandeur": "B.MORABET", "recruteur": "Zakaria"},
            {"statut": "Signature DRH", "titre": "Consultant SAP", "entite": "TGCC", "lieu": "Siège", "demandeur": "O.KETTA", "recruteur": "Zakaria"},
            {"statut": "Clôture", "titre": "Ingénieur étude/qualité", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "A.MOUTANABI", "recruteur": "Zakaria"},
            {"statut": "Clôture", "titre": "Responsable Cybersecurité", "entite": "TGCC", "lieu": "Siège", "demandeur": "Ghazi", "recruteur": "Zakaria"},
            {"statut": "Clôture", "titre": "CHEF DE CHANTIER", "entite": "TGCC", "lieu": "N/A", "demandeur": "M.FENNAN", "recruteur": "Zakaria"},
            {"statut": "Désistement", "titre": "Conducteur de Travaux", "entite": "TGCC", "lieu": "JORF LASFAR", "demandeur": "M.FENNAN", "recruteur": "Zakaria"},
            {"statut": "Désistement", "titre": "Chef de Chantier", "entite": "TGCC", "lieu": "TOARC", "demandeur": "M.FENNAN", "recruteur": "Zakaria"},
            {"statut": "Désistement", "titre": "Magasinier", "entite": "TG WOOD", "lieu": "Oulad Saleh", "demandeur": "K.TAZI", "recruteur": "Ghita"},
        ]
    
    # Définir les colonnes du Kanban
    statuts_kanban = ["Sourcing", "Shortlisté", "Signature DRH", "Clôture", "Désistement"]
    
    # Créer les colonnes Streamlit
    cols = st.columns(len(statuts_kanban))
    
    # CSS pour styliser les cartes (2 par ligne)
    st.markdown("""
    <style>
    .kanban-card {
        border-radius: 8px;
        background-color: #f0f2f6;
        padding: 10px;
        margin-bottom: 8px;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        min-height: 80px;
        width: 100%;
    }
    .kanban-card h4 {
        margin-top: 0;
        margin-bottom: 6px;
        font-size: 0.9em;
        color: #2c3e50;
        line-height: 1.2;
    }
    .kanban-card p {
        margin-bottom: 3px;
        font-size: 0.75em;
        color: #555;
        line-height: 1.1;
    }
    .kanban-header {
        text-align: center;
        font-weight: bold;
        font-size: 1.1em;
        color: #2c3e50;
        padding: 10px;
        background-color: #e8f4fd;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid #bee5eb;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Remplir chaque colonne avec les postes correspondants
    for i, statut in enumerate(statuts_kanban):
        with cols[i]:
            # En-tête de colonne
            st.markdown(f'<div class="kanban-header">{statut}</div>', unsafe_allow_html=True)
            
            # Filtrer les postes pour cette colonne
            postes_in_col = [p for p in postes_data if p["statut"] == statut]
            
            # Afficher les cartes avec 2 par ligne
            for idx in range(0, len(postes_in_col), 2):
                # Créer une ligne avec 2 cartes maximum
                card_cols = st.columns(2)
                
                # Première carte de la ligne
                if idx < len(postes_in_col):
                    poste = postes_in_col[idx]
                    with card_cols[0]:
                        card_html = f"""
                        <div class="kanban-card">
                            <h4><b>{poste['titre']}</b></h4>
                            <p>📍 {poste.get('entite', 'N/A')} - {poste.get('lieu', 'N/A')} | 👤 {poste.get('demandeur', 'N/A')}</p>
                            <p>✍️ {poste.get('recruteur', 'N/A')}</p>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                
                # Deuxième carte de la ligne (si elle existe)
                if idx + 1 < len(postes_in_col):
                    poste = postes_in_col[idx + 1]
                    with card_cols[1]:
                        card_html = f"""
                        <div class="kanban-card">
                            <h4><b>{poste['titre']}</b></h4>
                            <p>📍 {poste.get('entite', 'N/A')} - {poste.get('lieu', 'N/A')} | 👤 {poste.get('demandeur', 'N/A')}</p>
                            <p>✍️ {poste.get('recruteur', 'N/A')}</p>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    # Colonne vide si nombre impair
                    with card_cols[1]:
                        st.empty()


def main():
    st.title("📊 Tableau de Bord RH - Style Power BI")
    st.markdown("---")
    # Date de reporting : permet de fixer la date de référence pour tous les calculs
    if 'reporting_date' not in st.session_state:
        # default to today's date
        st.session_state['reporting_date'] = datetime.now().date()

    with st.sidebar:
        st.subheader("🔧 Filtres - Hebdomadaire")
        # Ensure the session value is a plain date object Streamlit expects.
        # Protect against cases where session_state may contain a str or pd.Timestamp
        rd_val = st.session_state.get('reporting_date', None)
        if rd_val is not None:
            try:
                # pandas Timestamp or datetime -> date
                import pandas as _pd
                if isinstance(rd_val, _pd.Timestamp):
                    st.session_state['reporting_date'] = rd_val.date()
                elif hasattr(rd_val, 'date') and not isinstance(rd_val, str):
                    # datetime -> date (leave date as-is)
                    try:
                        st.session_state['reporting_date'] = rd_val.date()
                    except Exception:
                        pass
                elif isinstance(rd_val, str):
                    # try parsing common formats
                    from dateutil import parser as _parser
                    try:
                        parsed = _parser.parse(rd_val)
                        st.session_state['reporting_date'] = parsed.date()
                    except Exception:
                        # fallback: keep original (Streamlit will raise if invalid)
                        pass
            except Exception:
                # If pandas isn't available or any unexpected issue, ignore and let Streamlit handle
                pass
        # Do not pass both `value` and `key` for the same widget to avoid Streamlit's
        # warning: the widget was created with a default value but also had its
        # value set via the Session State API. Passing `key='reporting_date'`
        # is enough for Streamlit to initialize the widget from
        # `st.session_state['reporting_date']`. Avoid providing `value=` here.
        rd = st.date_input(
            "Date de reporting (hebdomadaire)",
            help="Date utilisée comme référence pour le reporting hebdomadaire",
            key='reporting_date',
            format='DD/MM/YYYY'
        )
    
    # Créer les onglets (Demandes et Recrutement regroupés)
    tabs = st.tabs(["📂 Upload", "🗂️ Demandes & Recrutement", "📅 Hebdomadaire", "🤝 Intégrations"])
    
    # Variables pour stocker les fichiers uploadés
    # Use session_state to persist upload/refresh state
    if 'data_updated' not in st.session_state:
        st.session_state.data_updated = False
    if 'uploaded_excel' not in st.session_state:
        st.session_state.uploaded_excel = None
    uploaded_excel = st.session_state.uploaded_excel
    
    with tabs[0]:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔗 Synchroniser depuis Google Sheets")
            # Respecter la date de reporting si fournie dans st.session_state
            reporting_date = st.session_state.get('reporting_date', None)
            if reporting_date is None:
                today = datetime.now()
            else:
                # reporting_date is a date object from st.date_input; convert to datetime
                if isinstance(reporting_date, datetime):
                    today = reporting_date
                else:
                    today = datetime.combine(reporting_date, datetime.min.time())
            start_of_month = today.replace(day=1)
            # valeur par défaut du Google Sheet (identique à celle utilisée précédemment)
            default_sheet = "https://docs.google.com/spreadsheets/d/1hvghSMjcbdY8yNZOWqALBpgMdLWB5CxVJCDwEm6JULI/edit?gid=785271056#gid=785271056"
            gs_url = st.text_input("URL Google Sheet", value=default_sheet, key="gsheet_url")
            
            if 'synced_recrutement_df' not in st.session_state:
                st.session_state.synced_recrutement_df = None
            
            if st.button("🔁 Synchroniser depuis Google Sheets", 
                        help="Synchroniser les données depuis Google Sheets",
                        use_container_width=True):
                
                try:
                    # Utiliser la fonction de connexion automatique (comme dans Home.py)
                    df_synced = load_data_from_google_sheets(gs_url)
                    
                    if df_synced is not None and len(df_synced) > 0:
                        st.session_state.synced_recrutement_df = df_synced
                        st.session_state.data_updated = True
                        nb_lignes = len(df_synced)
                        nb_colonnes = len(df_synced.columns)
                        st.success(f"✅ Synchronisation Google Sheets réussie ! Les onglets ont été mis à jour. ({nb_lignes} lignes, {nb_colonnes} colonnes)")
                    else:
                        st.warning("⚠️ Aucune donnée trouvée dans la feuille Google Sheets.")
                        
                except Exception as e:
                    err_str = str(e)
                    st.error(f"Erreur lors de la synchronisation: {err_str}")
                    
                    if '401' in err_str or 'Unauthorized' in err_str or 'HTTP Error 401' in err_str:
                        st.error("❌ **Feuille Google privée** - Vérifiez que:")
                        st.markdown("""
                        1. La feuille est partagée avec: `your-service-account@your-project.iam.gserviceaccount.com`
                        2. Les secrets Streamlit sont correctement configurés
                        3. L'URL de la feuille est correcte
                        """)
                    elif 'secrets' in err_str.lower():
                        st.error("❌ **Configuration des secrets manquante**")
                        st.markdown("""
                        Assurez-vous que les secrets suivants sont configurés:
                        - `GCP_TYPE`, `GCP_PROJECT_ID`, `GCP_PRIVATE_KEY_ID`
                        - `GCP_PRIVATE_KEY`, `GCP_CLIENT_EMAIL`, `GCP_CLIENT_ID`
                        - `GCP_AUTH_URI`, `GCP_TOKEN_URI`, etc.
                        """)
                    else:
                        st.error(f"Erreur technique: {err_str}")

        with col2:
            st.subheader("📊 Fichier Excel - Données de Recrutement")
            uploaded_excel = st.file_uploader(
                "Choisir le fichier Excel de recrutement",
                type=['xlsx', 'xls'],
                help="Fichier Excel contenant les données de recrutement",
                key="excel_uploader"
            )
            
            if uploaded_excel is not None:
                # Aperçu des données
                try:
                    preview_excel = pd.read_excel(uploaded_excel, sheet_name=0)
                    st.success(f"✅ Fichier Excel chargé: {uploaded_excel.name} - {len(preview_excel)} lignes, {len(preview_excel.columns)} colonnes")
                    st.dataframe(preview_excel.head(3), use_container_width=True)
                    # Reset file pointer for later use
                    uploaded_excel.seek(0)
                    st.session_state.uploaded_excel = uploaded_excel
                except Exception as e:
                    st.error(f"Erreur lors de la lecture de l'Excel: {e}")
        
        # Bouton pour actualiser les données - s'étale sur les deux colonnes
        st.markdown("---")
        if st.button("🔄 Actualiser les Graphiques", type="primary", use_container_width=True):
            st.session_state.data_updated = True
            st.success("Données mises à jour ! Consultez les autres onglets.")
    
    # Charger les données (avec fichiers uploadés ou fichiers locaux)
    df_integration, df_recrutement = load_data_from_files(None, uploaded_excel)
    
    # Message d'information sur les données chargées
    has_uploaded = (st.session_state.uploaded_excel is not None) or (st.session_state.get('synced_recrutement_df') is not None)
    if df_recrutement is None and df_integration is None:
        st.sidebar.warning("⚠️ Aucune donnée disponible. Veuillez uploader vos fichiers dans l'onglet 'Upload Fichiers'.")
    elif df_recrutement is None:
        st.sidebar.warning("⚠️ Données de recrutement non disponibles. Seules les données d'intégration sont chargées.")
    elif df_integration is None:
        st.sidebar.warning("⚠️ Données d'intégration non disponibles. Seules les données de recrutement sont chargées.")

    with tabs[1]:
        if df_recrutement is not None:
            create_demandes_recrutement_combined_tab(df_recrutement)
        else:
            st.warning("📊 Aucune donnée de recrutement disponible. Veuillez uploader un fichier Excel dans l'onglet 'Upload Fichiers'.")
    
    with tabs[2]:
        create_weekly_report_tab(df_recrutement)

    with tabs[3]:
        # Onglet Intégrations basé sur les données Excel
        if df_recrutement is not None:
            # Créer les filtres spécifiques pour les intégrations (sans période)
            st.sidebar.subheader("🔧 Filtres - Intégrations")
            int_filters = create_integration_filters(df_recrutement, "integrations")
            create_integrations_tab(df_recrutement, int_filters)
        else:
            st.warning("📊 Aucune donnée disponible pour les intégrations. Veuillez uploader un fichier Excel dans l'onglet 'Upload Fichiers'.")

if __name__ == "__main__":
    main()