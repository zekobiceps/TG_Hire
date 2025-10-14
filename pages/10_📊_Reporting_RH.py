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
from io import BytesIO
import json
import gspread
from google.oauth2 import service_account

st.set_page_config(
    page_title="📊 Reporting RH Complet",
    page_icon="📊",
    layout="wide"
)

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
                    df_recrutement[col] = pd.to_datetime(df_recrutement[col], errors='coerce')
            
            # Nettoyer les colonnes avec des espaces
            df_recrutement.columns = df_recrutement.columns.str.strip()
            
            # Nettoyer les colonnes numériques pour éviter les erreurs de type
            numeric_columns = ['Nb de candidats pré-selectionnés']
            for col in numeric_columns:
                if col in df_recrutement.columns:
                    df_recrutement[col] = pd.to_numeric(df_recrutement[col], errors='coerce').fillna(0)

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
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        wrapper = f'<div style="max-height:{max_height}px; overflow:auto;">{html}</div>'
        st.markdown(wrapper, unsafe_allow_html=True)
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

    # KPIs principaux
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nombre de recrutements", len(df_filtered))
    with col2:
        postes_uniques = df_filtered['Poste demandé'].nunique()
        st.metric("Postes concernés", postes_uniques)
    with col3:
        directions_uniques = df_filtered['Direction concernée'].nunique()
        st.metric("Nombre de Directions concernées", directions_uniques)
    
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
        fig_direction = px.bar(
            df_direction,
            x='Count',
            y='Direction',
            title="Comparaison par direction",
            text='Count',
            orientation='h'
        )
        fig_direction.update_traces(
            marker_color='#ff7f0e',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='%{x}<extra></extra>'
        )
        # Largest at top: reverse the category array so descending values appear from top to bottom
        height_dir = max(300, 28 * len(df_direction))
        fig_direction.update_layout(
            height=height_dir,
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(categoryorder='array', categoryarray=list(df_direction['Direction'][::-1]))
        )
        render_plotly_scrollable(fig_direction, max_height=height_dir)

    with col4:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts()
        df_poste = poste_counts.rename_axis('Poste').reset_index(name='Count')
        df_poste = df_poste.sort_values('Count', ascending=False)
        fig_poste = px.bar(
            df_poste,
            x='Count',
            y='Poste',
            title="Comparaison par poste",
            text='Count',
            orientation='h'
        )
        fig_poste.update_traces(
            marker_color='#2ca02c',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='%{x}<extra></extra>'
        )
        height_poste = max(300, 28 * len(df_poste))
        fig_poste.update_layout(
            height=height_poste,
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(categoryorder='array', categoryarray=list(df_poste['Poste'][::-1]))
        )
        render_plotly_scrollable(fig_poste, max_height=height_poste)


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

    with col6:
        # Délai moyen de recrutement - Calcul corrigé selon la formule demandée
        date_reception_col = 'Date de réception de la demande aprés validation de la DRH'
        date_retour_rh_col = 'Date du 1er retour equipe RH  au demandeur'
        
        if date_reception_col in df_filtered.columns and date_retour_rh_col in df_filtered.columns:
            try:
                # Conversion sécurisée des colonnes en datetime
                df_filtered[date_reception_col] = pd.to_datetime(df_filtered[date_reception_col], errors='coerce')
                df_filtered[date_retour_rh_col] = pd.to_datetime(df_filtered[date_retour_rh_col], errors='coerce')
                
                # Vérifier qu'il y a des dates valides
                dates_reception_valides = df_filtered[date_reception_col].notna()
                dates_retour_valides = df_filtered[date_retour_rh_col].notna()
                dates_completes = dates_reception_valides & dates_retour_valides
                
                if dates_completes.sum() > 0:
                    # Calcul : DATEDIFF([Date de réception],[Date du 1er retour equipe RH],day)
                    df_filtered['Duree de recrutement'] = (df_filtered[date_retour_rh_col] - df_filtered[date_reception_col]).dt.days
                    # Filtrer les valeurs positives uniquement (retour après réception)
                    durees_valides = df_filtered['Duree de recrutement'][
                        (df_filtered['Duree de recrutement'] > 0) & df_filtered['Duree de recrutement'].notna()
                    ]
                    
                    if len(durees_valides) > 0:
                        delai_moyen = durees_valides.mean()
                        fig_delai = go.Figure(go.Indicator(
                            mode = "number",
                            value = round(delai_moyen, 1),
                            title = {"text": "Délai moyen de recrutement (jours)"}
                        ))
                        fig_delai.update_layout(height=300)
                        st.plotly_chart(fig_delai, use_container_width=True)
                    else:
                        st.info("Aucune durée de recrutement valide trouvée pour le calcul.")
                else:
                    st.info("Aucune date valide trouvée pour calculer le délai de recrutement.")
            except Exception as e:
                st.error(f"Erreur lors du calcul du délai de recrutement: {e}")
                st.info("Le calcul du délai moyen de recrutement n'est pas disponible.")
        else:
            st.warning(f"Colonnes nécessaires non trouvées: '{date_reception_col}' et/ou '{date_retour_rh_col}'")


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
            title="Répartition par statut de la demande",
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
                xaxis={'categoryorder':'total descending'}
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
        # Horizontal bar for better readability when labels are long
        fig_direction = px.bar(
            df_direction,
            x='Count',
            y='Direction',
            title="Comparaison par direction",
            text='Count',
            orientation='h'
        )
        # Show values inside bars vertically
        fig_direction.update_traces(
            marker_color='#ff7f0e',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='%{x}<extra></extra>'
        )
        # Dynamic height so long lists become scrollable on the page
        height_dir = max(300, 28 * len(df_direction))
        fig_direction.update_layout(
            height=height_dir,
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(categoryorder='array', categoryarray=df_direction['Direction'])
        )
        render_plotly_scrollable(fig_direction, max_height=height_dir)
    
    with col5:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts()
        df_poste = poste_counts.rename_axis('Poste').reset_index(name='Count')
        df_poste = df_poste.sort_values('Count', ascending=False)
        fig_poste = px.bar(
            df_poste,
            x='Count',
            y='Poste',
            title="Comparaison par poste",
            text='Count',
            orientation='h'
        )
        fig_poste.update_traces(
            marker_color='#2ca02c',
            textposition='inside',
            texttemplate='%{x}',
            textfont=dict(size=11),
            textangle=90,
            hovertemplate='%{x}<extra></extra>'
        )
        height_poste = max(300, 28 * len(df_poste))
        fig_poste.update_layout(
            height=height_poste,
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(categoryorder='array', categoryarray=df_poste['Poste'])
        )
        render_plotly_scrollable(fig_poste, max_height=height_poste)

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
            today = datetime.now()
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
                if pd.isna(date_str) or date_str == '' or date_str == 'N/A':
                    return 'N/A'
                try:
                    # Essayer format DD/MM/YYYY d'abord (format souhaité)
                    if isinstance(date_str, str) and '/' in date_str and len(date_str.split('/')) == 3:
                        day, month, year = date_str.split('/')
                        if len(day) <= 2 and len(month) <= 2 and len(year) == 4:
                            parsed_date = pd.to_datetime(f"{day}/{month}/{year}", format='%d/%m/%Y', errors='coerce')
                            if pd.notna(parsed_date):
                                return parsed_date.strftime('%d/%m/%Y')
                    
                    # Fallback: laisser pandas deviner puis reformater
                    parsed_date = pd.to_datetime(date_str, errors='coerce')
                    if pd.notna(parsed_date):
                        return parsed_date.strftime('%d/%m/%Y')
                    else:
                        return 'N/A'
                except:
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
    
    # Obtenir la date actuelle et la semaine dernière
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Lundi de cette semaine
    start_of_last_week = start_of_week - timedelta(days=7)   # Lundi de la semaine dernière
    
    # Définir les colonnes attendues avec des alternatives possibles
    date_reception_col = "Date de réception de la demande après validation de la DRH"
    date_integration_col = "Date d'intégration prévisionnelle"
    candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
    statut_col = "Statut de la demande"
    entite_col = "Entité demandeuse"
    
    # Créer une copie pour les calculs
    df = df_recrutement.copy()
    
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
    real_candidat_col = find_similar_column(candidat_col, available_columns)
    real_statut_col = find_similar_column(statut_col, available_columns)
    real_entite_col = find_similar_column(entite_col, available_columns)
    
    # Si les colonnes essentielles n'existent pas, retourner vide
    if not real_entite_col:
        st.warning(f"⚠️ Colonne 'Entité' non trouvée. Colonnes disponibles: {', '.join(available_columns[:5])}...")
        return {}
    
    if not real_statut_col:
        st.warning(f"⚠️ Colonne 'Statut' non trouvée. Colonnes disponibles: {', '.join(available_columns[:5])}...")
        return {}
    
    # Convertir les dates si les colonnes existent
    if real_date_reception_col:
        df[real_date_reception_col] = pd.to_datetime(df[real_date_reception_col], errors='coerce')
    if real_date_integration_col:
        df[real_date_integration_col] = pd.to_datetime(df[real_date_integration_col], errors='coerce')
    
    # Calculer les métriques par entité
    entites = df[real_entite_col].dropna().unique()
    metrics_by_entity = {}
    
    for entite in entites:
        df_entite = df[df[real_entite_col] == entite]
        
        # 1. Postes ouverts avant début semaine (En cours la semaine dernière)
        postes_avant = 0
        if real_date_reception_col:
            postes_avant = len(df_entite[
                (df_entite[real_statut_col] == 'En cours') &
                (df_entite[real_date_reception_col] < start_of_week)
            ])
        
        # 2. Nouveaux postes ouverts cette semaine (Date réception cette semaine)
        nouveaux_postes = 0
        if real_date_reception_col:
            nouveaux_postes = len(df_entite[
                (df_entite[real_date_reception_col] >= start_of_week) &
                (df_entite[real_date_reception_col] <= today)
            ])
        
        # 3. Postes pourvus cette semaine (Date intégration cette semaine)
        postes_pourvus = 0
        if real_date_integration_col:
            postes_pourvus = len(df_entite[
                (df_entite[real_date_integration_col] >= start_of_week) &
                (df_entite[real_date_integration_col] <= today)
            ])
        
        # 4. Postes en cours cette semaine (Statut "En cours" ET pas de candidat retenu)
        postes_en_cours = len(df_entite[df_entite[real_statut_col] == 'En cours'])
        if real_candidat_col:
            postes_en_cours = len(df_entite[
                (df_entite[real_statut_col] == 'En cours') &
                (df_entite[real_candidat_col].isna() | (df_entite[real_candidat_col].astype(str).str.strip() == ""))
            ])
        
        metrics_by_entity[entite] = {
            'avant': postes_avant,
            'nouveaux': nouveaux_postes, 
            'pourvus': postes_pourvus,
            'en_cours': postes_en_cours
        }
    
    return metrics_by_entity

def create_weekly_report_tab(df_recrutement=None):
    """Onglet Reporting Hebdomadaire"""
    st.header("📅 Reporting Hebdomadaire : Chiffres Clés de la semaine")

    # Calculer les métriques si les données sont disponibles
    if df_recrutement is not None:
        try:
            metrics = calculate_weekly_metrics(df_recrutement)
            total_avant = sum(m['avant'] for m in metrics.values())
            total_nouveaux = sum(m['nouveaux'] for m in metrics.values())
            total_pourvus = sum(m['pourvus'] for m in metrics.values())
            total_en_cours = sum(m['en_cours'] for m in metrics.values())
        except Exception as e:
            st.error(f"⚠️ Erreur lors du calcul des métriques: {str(e)}")
            metrics = {}
            total_avant = total_nouveaux = total_pourvus = total_en_cours = 0
    else:
        metrics = {}
        total_avant = total_nouveaux = total_pourvus = total_en_cours = 0

    # 1. Section "Chiffres Clés"
    st.subheader("Chiffres Clés de la semaine")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Postes en cours cette semaine", total_en_cours)
    col2.metric("Postes pourvus cette semaine", total_pourvus)
    col3.metric("Nouveaux postes ouverts", total_nouveaux)
    col4.metric("Total postes ouverts avant la semaine", total_avant)

    st.markdown("---")

    # 2. Tableau des besoins en cours par entité (AVANT le Kanban)
    st.subheader("📊 Besoins en Cours par Entité")
    
    # Créer le tableau avec des colonnes Streamlit natives
    if metrics and len(metrics) > 0:
        # Préparer les données pour le DataFrame
        table_data = []
        for entite, data in metrics.items():
            table_data.append({
                'Entité': entite,
                'Nb postes ouverts avant début semaine': data['avant'] if data['avant'] > 0 else '-',
                'Nb nouveaux postes ouverts cette semaine': data['nouveaux'] if data['nouveaux'] > 0 else '-',
                'Nb postes pourvus cette semaine': data['pourvus'] if data['pourvus'] > 0 else '-',
                'Nb postes en cours cette semaine': data['en_cours'] if data['en_cours'] > 0 else '-'
            })
        
        # Ajouter la ligne de total
        table_data.append({
            'Entité': '**Total**',
            'Nb postes ouverts avant début semaine': f'**{total_avant}**',
            'Nb nouveaux postes ouverts cette semaine': f'**{total_nouveaux}**',
            'Nb postes pourvus cette semaine': f'**{total_pourvus}**',
            'Nb postes en cours cette semaine': f'**{total_en_cours}**'
        })
        
        # Créer le tableau HTML personnalisé compact et centralisé
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
        
        # Construire le tableau HTML compact et centralisé
        html_table = '<div class="table-container">'
        html_table += '<table class="custom-table">'
        html_table += '<thead><tr>'
        html_table += '<th>Entité</th>'
        html_table += '<th>Nb postes ouverts avant début semaine</th>'
        html_table += '<th>Nb nouveaux postes ouverts cette semaine</th>'
        html_table += '<th>Nb postes pourvus cette semaine</th>'
        html_table += '<th>Nb postes en cours cette semaine</th>'
        html_table += '</tr></thead>'
        html_table += '<tbody>'
        
        # Ajouter les lignes de données (filtrer les entités vides)
        data_rows = [row for row in table_data[:-1] if row["Entité"] and row["Entité"].strip()]
        for row in data_rows:
            html_table += '<tr>'
            html_table += f'<td class="entity-cell">{row["Entité"]}</td>'
            html_table += f'<td>{row["Nb postes ouverts avant début semaine"]}</td>'
            html_table += f'<td>{row["Nb nouveaux postes ouverts cette semaine"]}</td>'
            html_table += f'<td>{row["Nb postes pourvus cette semaine"]}</td>'
            html_table += f'<td>{row["Nb postes en cours cette semaine"]}</td>'
            html_table += '</tr>'
        
        # Ajouter la ligne TOTAL dédiée (dernière ligne pour les totaux de chaque colonne)
        total_row = table_data[-1]
        html_table += '<tr class="total-row">'
        html_table += f'<td class="entity-cell">TOTAL</td>'
        html_table += f'<td>{total_row["Nb postes ouverts avant début semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb nouveaux postes ouverts cette semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb postes pourvus cette semaine"].replace("**", "")}</td>'
        html_table += f'<td>{total_row["Nb postes en cours cette semaine"].replace("**", "")}</td>'
        html_table += '</tr>'
        html_table += '</tbody></table></div>'
        
        # Afficher le tableau HTML centralisé
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        # Tableau par défaut compact centralisé avec le même style
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
        
        # Tableau par défaut HTML compact et centralisé
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

    st.markdown("---")

    # 3. Section "Pipeline de Recrutement (Kanban)"
    st.subheader("Pipeline de Recrutement (Kanban)")

    # Définir les données d'exemple pour le Kanban (ou utiliser les vraies données si disponibles)
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
        
        {"statut": "Clôture", "titre": "Doc Controller", "entite": "TGEM", "lieu": "SIEGE", "demandeur": "A.SANKARI", "recruteur": "Zakaria"},
        {"statut": "Clôture", "titre": "Ingénieur étude/qualité", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "A.MOUTANABI", "recruteur": "Zakaria"},
        {"statut": "Clôture", "titre": "Responsable Cybersecurité", "entite": "TGCC", "lieu": "Siège", "demandeur": "Ghazi", "recruteur": "Zakaria"},
        {"statut": "Clôture", "titre": "CHEF DE CHANTIER", "entite": "TGCC", "lieu": "N/A", "demandeur": "M.FENNAN", "recruteur": "Zakaria"},
        {"statut": "Clôture", "titre": "Ing contrôle de la performance", "entite": "TGCC", "lieu": "Siège", "demandeur": "H.BARIGOU", "recruteur": "Ghita"},
        {"statut": "Clôture", "titre": "Ingénieur Systèmes Réseaux", "entite": "TGCC", "lieu": "Siège", "demandeur": "M.JADDOR", "recruteur": "Ghita"},
        {"statut": "Clôture", "titre": "Responsable étude de prix", "entite": "TGCC", "lieu": "SIEGE", "demandeur": "S.Bennani Zitani", "recruteur": "Ghita"},
        {"statut": "Clôture", "titre": "Responsable Travaux", "entite": "TGEM", "lieu": "Zone Rabat", "demandeur": "S.ACHIR", "recruteur": "Zakaria"},
        
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
            st.markdown("Indiquez le lien vers votre Google Sheet ou laissez le lien par défaut, puis cliquez sur '🔁 Synchroniser'.")
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