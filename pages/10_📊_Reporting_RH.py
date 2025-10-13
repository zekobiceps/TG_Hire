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

st.set_page_config(
    page_title="📊 Reporting RH Complet",
    page_icon="📊",
    layout="wide"
)

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


def create_global_filters(df_recrutement, prefix=""):
    """Créer des filtres globaux réutilisables pour tous les onglets"""
    if df_recrutement is None or len(df_recrutement) == 0:
        return {}
    
    filters = {}
    
    # Filtre par entité demandeuse
    entites = ['Toutes'] + sorted(df_recrutement['Entité demandeuse'].dropna().unique())
    filters['entite'] = st.sidebar.selectbox("Entité demandeuse", entites, key=f"{prefix}_entite")
    
    # Filtre par direction concernée
    directions = ['Toutes'] + sorted(df_recrutement['Direction concernée'].dropna().unique())
    filters['direction'] = st.sidebar.selectbox("Direction concernée", directions, key=f"{prefix}_direction")
    
    # Filtre par affectation
    affectations = ['Toutes'] + sorted(df_recrutement['Affectation'].dropna().unique())
    filters['affectation'] = st.sidebar.selectbox("Affectation", affectations, key=f"{prefix}_affectation")
    
    return filters

def apply_global_filters(df, filters):
    """Appliquer les filtres globaux aux données"""
    df_filtered = df.copy()
    
    if filters.get('entite') != 'Toutes':
        df_filtered = df_filtered[df_filtered['Entité demandeuse'] == filters['entite']]
    
    if filters.get('direction') != 'Toutes':
        df_filtered = df_filtered[df_filtered['Direction concernée'] == filters['direction']]
        
    if filters.get('affectation') != 'Toutes':
        df_filtered = df_filtered[df_filtered['Affectation'] == filters['affectation']]
    
    return df_filtered

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
        if excel_file is not None:
            df_recrutement = pd.read_excel(excel_file, sheet_name=0)
        else:
            # Fallback vers fichier local s'il existe
            local_excel = 'Recrutement global PBI All  google sheet (5).xlsx'
            if os.path.exists(local_excel):
                df_recrutement = pd.read_excel(local_excel, sheet_name=0)
        
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

def create_recrutements_clotures_tab(df_recrutement, global_filters):
    """Onglet Recrutements Clôturés avec style carte"""
    
    # Filtrer seulement les recrutements clôturés
    df_cloture = df_recrutement[df_recrutement['Statut de la demande'] == 'Clôture'].copy()
    
    if len(df_cloture) == 0:
        st.warning("Aucune donnée de recrutement clôturé disponible")
        return
    
    # Filtre par période (spécifique à cette section)
    if 'Date d\'entrée effective du candidat' in df_cloture.columns:
        df_cloture['Année'] = df_cloture['Date d\'entrée effective du candidat'].dt.year
        annees_dispo = sorted([y for y in df_cloture['Année'].dropna().unique() if not pd.isna(y)])
        if annees_dispo:
            annee_select = st.sidebar.selectbox("Période de recrutement", ['Toutes'] + [int(a) for a in annees_dispo], index=len(annees_dispo), key="rec_annee")
        else:
            annee_select = 'Toutes'
    else:
        annee_select = 'Toutes'

    # Appliquer les filtres globaux + période
    df_filtered = apply_global_filters(df_cloture, global_filters)
    if annee_select != 'Toutes':
        df_filtered = df_filtered[df_filtered['Année'] == annee_select]

    # KPIs principaux
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nombre de recrutements", len(df_filtered))
    with col2:
        postes_uniques = df_filtered['Poste demandé'].nunique()
        st.metric("Postes concernés", postes_uniques)
    with col3:
        directions_uniques = df_filtered['Direction concernée'].nunique()
        st.metric("Nombre de Direction con...", directions_uniques)
    
    # Graphiques en ligne 1
    col1, col2 = st.columns([2,1])
    
    with col1:
        # Évolution des recrutements par mois (comme dans l'image 1)
        if 'Date d\'entrée effective du candidat' in df_filtered.columns:
            df_filtered['Mois_Année'] = df_filtered['Date d\'entrée effective du candidat'].dt.strftime('%Y-%m')
            monthly_data = df_filtered.groupby('Mois_Année').size().reset_index(name='Count')
            
            fig_evolution = px.bar(
                monthly_data, 
                x='Mois_Année', 
                y='Count',
                title="Évolution des recrutements",
                text='Count'
            )
            fig_evolution.update_traces(marker_color='#1f77b4', textposition='outside')
            fig_evolution.update_layout(height=300, xaxis_title=None, yaxis_title=None)
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
        direction_counts = df_filtered['Direction concernée'].value_counts().nlargest(10)
        fig_direction = px.bar(
            direction_counts,
            y=direction_counts.index,
            x=direction_counts.values,
            orientation='h',
            title="Comparaison par direction",
            text=direction_counts.values
        )
        fig_direction.update_traces(marker_color='#ff7f0e', textposition='auto')
        fig_direction.update_layout(height=300, xaxis_title=None, yaxis_title=None, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_direction, use_container_width=True)

    with col4:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts().nlargest(10)
        fig_poste = px.bar(
            poste_counts,
            y=poste_counts.index,
            x=poste_counts.values,
            orientation='h',
            title="Comparaison par poste",
            text=poste_counts.values
        )
        fig_poste.update_traces(marker_color='#2ca02c', textposition='auto')
        fig_poste.update_layout(height=300, xaxis_title=None, yaxis_title=None, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_poste, use_container_width=True)


    # Ligne 3 - KPIs de délai et candidats
    col5, col6 = st.columns(2)

    with col5:
        # Nombre de candidats présélectionnés
        total_candidats = int(df_filtered['Nb de candidats pré-selectionnés'].sum())
        fig_candidats = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = total_candidats,
            title = {'text': "Nombre de candidats présélectionnés"},
            gauge = {'axis': {'range': [None, total_candidats * 2]},
                     'bar': {'color': "green"},
                    }))
        fig_candidats.update_layout(height=300)
        st.plotly_chart(fig_candidats, use_container_width=True)

    with col6:
        # Délai moyen de recrutement
        date_reception_col = 'Date de réception de la demande aprés validation de la DRH'
        date_reponse_col = 'Date de la 1er réponse du demandeur à l\'équipe RH'
        
        if date_reception_col in df_filtered.columns and date_reponse_col in df_filtered.columns:
            df_filtered['Duree de recrutement'] = (df_filtered[date_reponse_col] - df_filtered[date_reception_col]).dt.days
            delai_moyen = df_filtered['Duree de recrutement'].mean()

            if not pd.isna(delai_moyen):
                fig_delai = go.Figure(go.Indicator(
                    mode = "number",
                    value = delai_moyen,
                    title = {"text": "Délai moyen de recrutement (jours)"}
                ))
                fig_delai.update_layout(height=300)
                st.plotly_chart(fig_delai, use_container_width=True)
            else:
                st.info("Le calcul du délai moyen de recrutement n'est pas disponible.")
        else:
            st.warning("Colonnes de date nécessaires pour le calcul du délai non trouvées.")


def create_demandes_recrutement_tab(df_recrutement, global_filters):
    """Onglet Demandes de Recrutement avec style carte"""
    
    # Filtre par période de demande (spécifique à cette section)
    date_col = 'Date de réception de la demande aprés validation de la DRH'
    if date_col in df_recrutement.columns:
        df_recrutement['Année_demande'] = df_recrutement[date_col].dt.year
        annees_demande = sorted([y for y in df_recrutement['Année_demande'].dropna().unique() if not pd.isna(y)])
        if annees_demande:
            annee_demande_select = st.sidebar.selectbox("Période de la demande", ['Toutes'] + [int(a) for a in annees_demande], index=len(annees_demande), key="dem_annee")
        else:
            annee_demande_select = 'Toutes'
    else:
        annee_demande_select = 'Toutes'
    
    # Appliquer les filtres globaux + période
    df_filtered = apply_global_filters(df_recrutement, global_filters)
    if annee_demande_select != 'Toutes':
        df_filtered = df_filtered[df_filtered['Année_demande'] == annee_demande_select]
    
    # KPI principal - Nombre de demandes
    st.metric("Nombre de demandes", len(df_filtered))

    # Graphiques principaux
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
            fig_raison = px.bar(
                raison_counts,
                x=raison_counts.values,
                y=raison_counts.index,
                orientation='h',
                title="Comparaison par raison du recrutement",
                text=raison_counts.values
            )
            fig_raison.update_traces(marker_color='grey', textposition='auto')
            fig_raison.update_layout(height=300, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_raison, use_container_width=True)
    
    with col3:
        # Évolution des demandes
        if date_col in df_filtered.columns:
            df_filtered['Mois_Année_Demande'] = df_filtered[date_col].dt.strftime('%Y-%m')
            monthly_demandes = df_filtered.groupby('Mois_Année_Demande').size().reset_index(name='Count')
            
            fig_evolution_demandes = px.bar(
                monthly_demandes, 
                x='Mois_Année_Demande', 
                y='Count',
                title="Évolution des demandes",
                text='Count'
            )
            fig_evolution_demandes.update_traces(marker_color='#1f77b4', textposition='outside')
            fig_evolution_demandes.update_layout(height=300, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_evolution_demandes, use_container_width=True)
    
    # Deuxième ligne de graphiques
    col4, col5 = st.columns(2)
    
    with col4:
        # Comparaison par direction
        direction_counts = df_filtered['Direction concernée'].value_counts().nlargest(10)
        fig_direction = px.bar(
            direction_counts,
            y=direction_counts.index,
            x=direction_counts.values,
            orientation='h',
            title="Comparaison par direction",
            text=direction_counts.values
        )
        fig_direction.update_traces(marker_color='#ff7f0e', textposition='auto')
        fig_direction.update_layout(height=400, xaxis_title=None, yaxis_title=None, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_direction, use_container_width=True)
    
    with col5:
        # Comparaison par poste
        poste_counts = df_filtered['Poste demandé'].value_counts().nlargest(15)
        fig_poste = px.bar(
            poste_counts,
            y=poste_counts.index,
            x=poste_counts.values,
            orientation='h',
            title="Comparaison par poste",
            text=poste_counts.values
        )
        fig_poste.update_traces(marker_color='#2ca02c', textposition='auto')
        fig_poste.update_layout(height=400, xaxis_title=None, yaxis_title=None, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_poste, use_container_width=True)

def create_integrations_tab(df_recrutement, global_filters):
    """Onglet Intégrations basé sur les bonnes données"""
    st.header("📊 Intégrations")
    
    # Filtrer les données : Statut "En cours" ET candidat ayant accepté (nom présent)
    candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
    date_integration_col = "Date d'entrée prévisionnelle"
    
    # Critères : Statut "En cours" ET candidat avec nom
    df_integrations = df_recrutement[
        (df_recrutement['Statut de la demande'] == 'En cours') &
        (df_recrutement[candidat_col].notna()) &
        (df_recrutement[candidat_col].str.strip() != "")
    ].copy()
    
    if len(df_integrations) == 0:
        st.warning("Aucune intégration en cours trouvée")
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
    
    with col1:
        # Répartition par affectation
        affectation_counts = df_filtered['Affectation'].value_counts().nlargest(10)
        fig_affectation = px.pie(
            values=affectation_counts.values,
            names=affectation_counts.index,
            title="🏢 Répartition par Affectation"
        )
        fig_affectation.update_traces(textposition='inside', textinfo='percent+label')
        fig_affectation.update_layout(height=400)
        st.plotly_chart(fig_affectation, use_container_width=True)
    
    with col2:
        # Évolution des dates d'intégration prévues
        if date_integration_col in df_filtered.columns:
            df_filtered['Mois_Integration'] = df_filtered[date_integration_col].dt.to_period('M')
            monthly_integration = df_filtered.groupby('Mois_Integration').size().reset_index(name='Count')
            monthly_integration['Mois_str'] = monthly_integration['Mois_Integration'].astype(str)
            
            fig_evolution_int = px.bar(
                monthly_integration, 
                x='Mois_str', 
                y='Count',
                title="📈 Évolution des Intégrations Prévues",
                text='Count'
            )
            fig_evolution_int.update_traces(marker_color='#2ca02c', textposition='outside')
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
        
        # Formater la date pour enlever l'heure
        if date_integration_col in df_display.columns:
            df_display[date_integration_col] = pd.to_datetime(df_display[date_integration_col], errors='coerce').dt.strftime('%d/%m/%Y')
            df_display[date_integration_col] = df_display[date_integration_col].fillna('N/A')
        
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
    
    # Créer les filtres globaux une seule fois
    st.sidebar.subheader("🔧 Filtres Globaux")
    global_filters = create_global_filters(df_recrutement, "combined")
    
    # Créer deux cartes expandables principales (comme dans Home.py)
    with st.expander("📋 **DEMANDES DE RECRUTEMENT**", expanded=False):
        create_demandes_recrutement_tab(df_recrutement, global_filters)
    
    with st.expander("🎯 **RECRUTEMENTS CLÔTURÉS**", expanded=False):
        create_recrutements_clotures_tab(df_recrutement, global_filters)


def calculate_weekly_metrics(df_recrutement):
    """Calcule les métriques hebdomadaires basées sur les vraies données"""
    if df_recrutement is None or len(df_recrutement) == 0:
        return {}
    
    # Obtenir la date actuelle et la semaine dernière
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Lundi de cette semaine
    start_of_last_week = start_of_week - timedelta(days=7)   # Lundi de la semaine dernière
    
    # Convertir les colonnes de dates
    date_reception_col = "Date de réception de la demande après validation de la DRH"
    date_integration_col = "Date d'intégration prévisionnelle"
    candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
    statut_col = "Statut de la demande"
    entite_col = "Entité demandeuse"
    
    # Créer une copie pour les calculs
    df = df_recrutement.copy()
    
    # Convertir les dates
    df[date_reception_col] = pd.to_datetime(df[date_reception_col], errors='coerce')
    df[date_integration_col] = pd.to_datetime(df[date_integration_col], errors='coerce')
    
    # Calculer les métriques par entité
    entites = df[entite_col].dropna().unique()
    metrics_by_entity = {}
    
    for entite in entites:
        df_entite = df[df[entite_col] == entite]
        
        # 1. Postes ouverts avant début semaine (En cours la semaine dernière)
        postes_avant = len(df_entite[
            (df_entite[statut_col] == 'En cours') &
            (df_entite[date_reception_col] < start_of_week)
        ])
        
        # 2. Nouveaux postes ouverts cette semaine (Date réception cette semaine)
        nouveaux_postes = len(df_entite[
            (df_entite[date_reception_col] >= start_of_week) &
            (df_entite[date_reception_col] <= today)
        ])
        
        # 3. Postes pourvus cette semaine (Date intégration cette semaine)
        postes_pourvus = len(df_entite[
            (df_entite[date_integration_col] >= start_of_week) &
            (df_entite[date_integration_col] <= today)
        ])
        
        # 4. Postes en cours cette semaine (Statut "En cours" ET pas de candidat retenu)
        postes_en_cours = len(df_entite[
            (df_entite[statut_col] == 'En cours') &
            (df_entite[candidat_col].isna() | (df_entite[candidat_col].str.strip() == ""))
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
    st.header("📅 Reporting Hebdomadaire")

    # Calculer les métriques si les données sont disponibles
    if df_recrutement is not None:
        metrics = calculate_weekly_metrics(df_recrutement)
        total_avant = sum(m['avant'] for m in metrics.values())
        total_nouveaux = sum(m['nouveaux'] for m in metrics.values())
        total_pourvus = sum(m['pourvus'] for m in metrics.values())
        total_en_cours = sum(m['en_cours'] for m in metrics.values())
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
    
    # CSS pour styliser le tableau comme dans l'image
    st.markdown("""
    <style>
    .besoins-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 0.9em;
    }
    .besoins-table th {
        background-color: #8B0000;
        color: white;
        padding: 8px;
        text-align: center;
        border: 1px solid white;
        font-weight: bold;
        font-size: 0.8em;
    }
    .besoins-table td {
        padding: 8px;
        text-align: center;
        border: 1px solid #ddd;
        background-color: #f9f9f9;
    }
    .besoins-table .total-row {
        background-color: #8B0000 !important;
        color: white !important;
        font-weight: bold;
    }
    .besoins-table .entity-cell {
        text-align: left;
        padding-left: 15px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Construire le HTML du tableau avec les vraies données
    table_html = """
    <table class="besoins-table">
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
    """
    
    # Ajouter les lignes avec les vraies données
    if metrics:
        for entite, data in metrics.items():
            table_html += f"""
            <tr>
                <td class="entity-cell">{entite}</td>
                <td>{data['avant'] if data['avant'] > 0 else '-'}</td>
                <td>{data['nouveaux'] if data['nouveaux'] > 0 else '-'}</td>
                <td>{data['pourvus'] if data['pourvus'] > 0 else '-'}</td>
                <td>{data['en_cours'] if data['en_cours'] > 0 else '-'}</td>
            </tr>
            """
    else:
        # Données par défaut si pas de données Excel
        table_html += """
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
        """
        total_avant = 21
        total_nouveaux = 14
        total_pourvus = 5
        total_en_cours = 30
    
    # Ligne de total
    table_html += f"""
        <tr class="total-row">
            <td class="entity-cell">Total</td>
            <td>{total_avant}</td>
            <td>{total_nouveaux}</td>
            <td>{total_pourvus}</td>
            <td>{total_en_cours}</td>
        </tr>
        </tbody>
    </table>
    """
    
    # Afficher le tableau HTML
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")

    # 3. Section "Pipeline de Recrutement (Kanban)"
    st.subheader("Pipeline de Recrutement (Kanban)")

    # CSS pour styliser les cartes et colonnes Kanban avec lignes verticales complètes
    st.markdown("""
    <style>
    .kanban-container {
        display: flex;
        width: 100%;
    }
    .kanban-column {
        flex: 1;
        border-right: 2px solid #dee2e6;
        padding-right: 15px;
        margin-right: 15px;
        min-height: 500px;
    }
    .kanban-column:last-child {
        border-right: none;
        margin-right: 0;
        padding-right: 0;
    }
    .kanban-header {
        text-align: center;
        font-weight: bold;
        font-size: 1.1em;
        color: #2c3e50;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid #dee2e6;
    }
    .kanban-card {
        border-radius: 5px;
        background-color: #f0f2f6;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #1f77b4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kanban-card h4 {
        margin-top: 0;
        margin-bottom: 5px;
        font-size: 1em;
    }
    .kanban-card p {
        margin-bottom: 2px;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

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

    # Créer le Kanban avec HTML complet pour les lignes verticales
    kanban_html = '<div class="kanban-container">'
    
    for i, statut in enumerate(statuts_kanban):
        # Ouvrir la colonne
        kanban_html += f'<div class="kanban-column">'
        kanban_html += f'<div class="kanban-header">{statut}</div>'
        
        # Filtrer les postes pour la colonne actuelle
        postes_in_col = [p for p in postes_data if p["statut"] == statut]
        
        # Ajouter les cartes à la colonne HTML
        for poste in postes_in_col:
            kanban_html += f"""
            <div class="kanban-card">
                <h4><b>{poste['titre']}</b></h4>
                <p>📍 {poste.get('entite', 'N/A')} - {poste.get('lieu', 'N/A')}</p>
                <p>👤 {poste.get('demandeur', 'N/A')}</p>
                <p>✍️ {poste.get('recruteur', 'N/A')}</p>
            </div>
            """
        
        # Fermer la colonne
        kanban_html += '</div>'
    
    # Fermer le container
    kanban_html += '</div>'
    
    # Afficher le Kanban complet
    st.markdown(kanban_html, unsafe_allow_html=True)


def main():
    st.title("📊 Tableau de Bord RH - Style Power BI")
    st.markdown("---")
    
    # Créer les onglets (Demandes et Recrutement regroupés)
    tabs = st.tabs(["📂 Upload", "� Demandes & Recrutement", "📅 Hebdomadaire", "� Intégrations"])
    
    # Variables pour stocker les fichiers uploadés
    # Use session_state to persist upload/refresh state
    if 'data_updated' not in st.session_state:
        st.session_state.data_updated = False
    if 'uploaded_csv' not in st.session_state:
        st.session_state.uploaded_csv = None
    if 'uploaded_excel' not in st.session_state:
        st.session_state.uploaded_excel = None
    uploaded_csv = st.session_state.uploaded_csv
    uploaded_excel = st.session_state.uploaded_excel
    
    with tabs[0]:
        st.header("📂 Upload des Fichiers de Données")
        st.markdown("Uploadez vos fichiers pour mettre à jour les graphiques en temps réel.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Fichier CSV - Données d'Intégration")
            uploaded_csv = st.file_uploader(
                "Choisir le fichier CSV d'intégration",
                type=['csv'],
                help="Fichier contenant les données d'intégration des candidats",
                key="csv_uploader"
            )
            
            if uploaded_csv is not None:
                st.success(f"✅ Fichier CSV chargé: {uploaded_csv.name}")
                # Aperçu des données
                try:
                    preview_csv = pd.read_csv(uploaded_csv)
                    st.write("**Aperçu des données CSV:**")
                    st.write(f"- Lignes: {len(preview_csv)}")
                    st.write(f"- Colonnes: {len(preview_csv.columns)}")
                    st.dataframe(preview_csv.head(3), use_container_width=True)
                    # Reset file pointer for later use
                    uploaded_csv.seek(0)
                    st.session_state.uploaded_csv = uploaded_csv
                except Exception as e:
                    st.error(f"Erreur lors de la lecture du CSV: {e}")
        
        with col2:
            st.subheader("📊 Fichier Excel - Données de Recrutement")
            uploaded_excel = st.file_uploader(
                "Choisir le fichier Excel de recrutement",
                type=['xlsx', 'xls'],
                help="Fichier Excel contenant les données de recrutement",
                key="excel_uploader"
            )
            
            if uploaded_excel is not None:
                st.success(f"✅ Fichier Excel chargé: {uploaded_excel.name}")
                # Aperçu des données
                try:
                    preview_excel = pd.read_excel(uploaded_excel, sheet_name=0)
                    st.write("**Aperçu des données Excel:**")
                    st.write(f"- Lignes: {len(preview_excel)}")
                    st.write(f"- Colonnes: {len(preview_excel.columns)}")
                    st.dataframe(preview_excel.head(3), use_container_width=True)
                    # Reset file pointer for later use
                    uploaded_excel.seek(0)
                    st.session_state.uploaded_excel = uploaded_excel
                except Exception as e:
                    st.error(f"Erreur lors de la lecture de l'Excel: {e}")
        
        # Bouton pour actualiser les données
        if st.button("🔄 Actualiser les Graphiques", type="primary"):
            st.session_state.data_updated = True
            st.success("Données mises à jour ! Consultez les autres onglets.")
    
    # Charger les données (avec fichiers uploadés ou fichiers locaux)
    df_integration, df_recrutement = load_data_from_files(uploaded_csv, uploaded_excel)
    
    # Message d'information sur les données chargées
    # Only show a success if the user uploaded files or explicitly refreshed
    has_uploaded = (st.session_state.uploaded_csv is not None) or (st.session_state.uploaded_excel is not None)
    if df_recrutement is None and df_integration is None:
        st.sidebar.warning("⚠️ Aucune donnée disponible. Veuillez uploader vos fichiers dans l'onglet 'Upload Fichiers'.")
    elif df_recrutement is None:
        st.sidebar.warning("⚠️ Données de recrutement non disponibles. Seules les données d'intégration sont chargées.")
    elif df_integration is None:
        st.sidebar.warning("⚠️ Données d'intégration non disponibles. Seules les données de recrutement sont chargées.")
    else:
        if has_uploaded or st.session_state.data_updated:
            st.sidebar.success("✅ Toutes les données sont chargées avec succès !")

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
            # Créer les filtres globaux pour les intégrations
            st.sidebar.subheader("🔧 Filtres - Intégrations")
            int_filters = create_global_filters(df_recrutement, "integrations")
            create_integrations_tab(df_recrutement, int_filters)
        else:
            st.warning("📊 Aucune donnée disponible pour les intégrations. Veuillez uploader un fichier Excel dans l'onglet 'Upload Fichiers'.")

if __name__ == "__main__":
    main()