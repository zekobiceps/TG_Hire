import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="📊 Reporting RH Complet",
    page_icon="📊",
    layout="wide"
)

def load_data():
    """Charger et préparer les données"""
    try:
        # Charger le CSV (données d'intégration)
        df_integration = pd.read_csv('/workspaces/TG_Hire/2025-10-09T20-31_export.csv')
        df_integration['Date Intégration'] = pd.to_datetime(df_integration['Date Intégration'])
        
        # Charger l'Excel (données de recrutement)
        df_recrutement = pd.read_excel('/workspaces/TG_Hire/Recrutement global PBI All  google sheet (5).xlsx', sheet_name=0)
        
        # Nettoyer et préparer les données de recrutement
        # Convertir les dates
        date_columns = ['Date de réception de la demande aprés validation de la DRH',
                       'Date d\'entrée effective du candidat', 
                       'Date d\'annulation /dépriorisation de la demande']
        
        for col in date_columns:
            if col in df_recrutement.columns:
                df_recrutement[col] = pd.to_datetime(df_recrutement[col], errors='coerce')
        
        # Nettoyer les colonnes avec des espaces
        df_recrutement.columns = df_recrutement.columns.str.strip()
        
        return df_integration, df_recrutement
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return None, None

def create_kpi_cards(df_integration, df_recrutement):
    """Créer les cartes KPI"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_integrations = len(df_integration)
        st.metric(
            label="📥 Total Intégrations", 
            value=total_integrations,
            help="Nombre total de personnes intégrées"
        )
    
    with col2:
        en_cours = len(df_integration[df_integration['Statut'] == 'En cours'])
        st.metric(
            label="⏳ En Cours", 
            value=en_cours,
            delta=f"{en_cours/total_integrations*100:.1f}%",
            help="Intégrations en cours de finalisation"
        )
    
    with col3:
        complet = len(df_integration[df_integration['Statut'] == 'Complet'])
        st.metric(
            label="✅ Complet", 
            value=complet,
            delta=f"{complet/total_integrations*100:.1f}%",
            help="Intégrations terminées"
        )
    
    with col4:
        avg_docs_manquants = df_integration['Docs Manquants'].mean()
        st.metric(
            label="📄 Docs Moy/Personne", 
            value=f"{avg_docs_manquants:.1f}",
            help="Moyenne de documents manquants par personne"
        )
    
    with col5:
        total_recrutements = len(df_recrutement) if df_recrutement is not None else 0
        st.metric(
            label="🎯 Demandes Recrutement", 
            value=total_recrutements,
            help="Total des demandes de recrutement"
        )

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

def create_poste_chart(df):
    """Créer un graphique par poste"""
    poste_stats = df['Poste'].value_counts().head(8)
    
    fig = px.bar(
        x=poste_stats.values,
        y=poste_stats.index,
        orientation='h',
        title="👥 Répartition par Poste (Top 8)",
        color=poste_stats.values,
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(
        xaxis_title="Nombre de personnes",
        yaxis_title="Poste",
        height=400,
        showlegend=False
    )
    
    return fig

def create_docs_analysis(df):
    """Analyser les documents manquants"""
    # Distribution des documents manquants
    fig1 = px.histogram(
        df, 
        x='Docs Manquants',
        nbins=10,
        title="📋 Distribution des Documents Manquants",
        color_discrete_sequence=['#ff9999']
    )
    fig1.update_layout(height=350)
    
    # Box plot par statut
    fig2 = px.box(
        df, 
        x='Statut', 
        y='Docs Manquants',
        title="📊 Documents Manquants par Statut",
        color='Statut',
        color_discrete_map={'En cours': '#ff6b6b', 'Complet': '#51cf66'}
    )
    fig2.update_layout(height=350)
    
    return fig1, fig2

def create_relances_analysis(df):
    """Analyser les relances"""
    # Filtrer les données avec des relances
    df_relances = df[df['Nb Relances'] > 0]
    
    if len(df_relances) > 0:
        fig = px.scatter(
            df_relances,
            x='Docs Manquants',
            y='Nb Relances',
            size='Docs Manquants',
            color='Statut',
            title="🔄 Relation Documents Manquants vs Nombre de Relances",
            hover_data=['Nom', 'Prénom', 'Poste'],
            color_discrete_map={'En cours': '#ff6b6b', 'Complet': '#51cf66'}
        )
        fig.update_layout(height=400)
        return fig
    else:
        return None

def create_recrutement_analysis(df_recrutement):
    """Analyser les données de recrutement"""
    if df_recrutement is None or len(df_recrutement) == 0:
        return None, None
    
    # Statut des demandes
    statut_counts = df_recrutement['Statut de la demande'].value_counts()
    fig1 = px.pie(
        values=statut_counts.values,
        names=statut_counts.index,
        title="🎯 Statut des Demandes de Recrutement"
    )
    
    # Top postes demandés
    poste_counts = df_recrutement['Poste demandé '].value_counts().head(10)
    fig2 = px.bar(
        x=poste_counts.values,
        y=poste_counts.index,
        orientation='h',
        title="📝 Top 10 Postes Demandés",
        color=poste_counts.values,
        color_continuous_scale='blues'
    )
    fig2.update_layout(height=500)
    
    return fig1, fig2

def create_recrutements_clotures_tab(df_recrutement):
    """Onglet Recrutements Clôturés (Image 1)"""
    st.header("🎯 Recrutements (État Clôture)")
    
    # Filtrer seulement les recrutements clôturés
    df_cloture = df_recrutement[df_recrutement['Statut de la demande'] == 'Clôture'].copy()
    
    if len(df_cloture) == 0:
        st.warning("Aucune donnée de recrutement clôturé disponible")
        return
    
    # Sidebar pour les filtres spécifiques
    st.sidebar.subheader("🔧 Filtres - Recrutements")
    
    # Filtre par période
    if 'Date d\'entrée effective du candidat' in df_cloture.columns:
        df_cloture['Année'] = df_cloture['Date d\'entrée effective du candidat'].dt.year
        annees_dispo = sorted([y for y in df_cloture['Année'].dropna().unique() if not pd.isna(y)])
        if annees_dispo:
            annee_select = st.sidebar.selectbox("Période de recrutement", ['Toutes'] + [int(a) for a in annees_dispo], index=1 if annees_dispo else 0)
        else:
            annee_select = 'Toutes'
    else:
        annee_select = 'Toutes'
    
    # Filtre par entité
    entites = ['Toutes'] + sorted(df_cloture['Entité demandeuse'].dropna().unique())
    entite_select = st.sidebar.selectbox("Entité demandeuse", entites)
    
    # Appliquer les filtres
    df_filtered = df_cloture.copy()
    if annee_select != 'Toutes':
        df_filtered = df_filtered[df_filtered['Année'] == annee_select]
    if entite_select != 'Toutes':
        df_filtered = df_filtered[df_filtered['Entité demandeuse'] == entite_select]
    
    # KPIs principaux
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Nombre de recrutements", len(df_filtered))
    with col2:
        postes_uniques = df_filtered['Poste demandé'].nunique()
        st.metric("📝 Postes demandés", postes_uniques)
    with col3:
        directions_uniques = df_filtered['Direction concernée'].nunique()
        st.metric("🏢 Directions concernées", directions_uniques)
    
    # Graphiques en ligne 1
    col1, col2 = st.columns(2)
    
    with col1:
        # Évolution des recrutements par mois (comme dans l'image 1)
        if 'Date d\'entrée effective du candidat' in df_filtered.columns:
            df_filtered['Mois'] = df_filtered['Date d\'entrée effective du candidat'].dt.to_period('M')
            monthly_data = df_filtered.groupby('Mois').size().reset_index(name='Count')
            monthly_data['Mois_str'] = monthly_data['Mois'].astype(str)
            
            fig_evolution = px.bar(
                monthly_data, 
                x='Mois_str', 
                y='Count',
                title="📈 Évolution des recrutements",
                color='Count',
                color_continuous_scale='blues'
            )
            fig_evolution.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_evolution, use_container_width=True)
    
    with col2:
        # Répartition par modalité de recrutement
        if 'Modalité de recrutement' in df_filtered.columns:
            modalite_data = df_filtered['Modalité de recrutement'].value_counts()
            
            # Créer des couleurs personnalisées
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            
            fig_modalite = px.pie(
                values=modalite_data.values,
                names=modalite_data.index,
                title="🎯 Répartition par Modalité de recrutement",
                color_discrete_sequence=colors
            )
            fig_modalite.update_traces(textposition='inside', textinfo='percent+label')
            fig_modalite.update_layout(height=400)
            st.plotly_chart(fig_modalite, use_container_width=True)
    
    # Graphiques en ligne 2
    col3, col4 = st.columns(2)
    
    with col3:
        # Canal de publication (comme graphique en donut dans l'image)
        if 'Canal de publication de l\'offre' in df_filtered.columns:
            canal_data = df_filtered['Canal de publication de l\'offre'].value_counts()
            
            fig_canal = go.Figure(data=[go.Pie(
                labels=canal_data.index, 
                values=canal_data.values,
                hole=.5,
                marker_colors=['#99999a', '#4CAF50']
            )])
            fig_canal.update_traces(textposition='inside', textinfo='percent+label')
            fig_canal.update_layout(
                title="📢 Répartition par Canal de publication de l'offre",
                height=400
            )
            st.plotly_chart(fig_canal, use_container_width=True)
    
    with col4:
        # Analyse promesses d'embauche vs refus
        col_promesses = 'Nb de promesses d\'embauche réalisée'
        col_refus = 'Nb de refus aux promesses d\'embauches'
        
        if col_promesses in df_filtered.columns and col_refus in df_filtered.columns:
            total_promesses = df_filtered[col_promesses].fillna(0).sum()
            total_refus = df_filtered[col_refus].fillna(0).sum()
            
            # Gauge chart pour promesses vs refus
            fig_gauge = go.Figure()
            
            fig_gauge.add_trace(go.Indicator(
                mode = "gauge+number+delta",
                value = total_promesses,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Promesses réalisées vs refusées"},
                delta = {'reference': total_refus, 'relative': True},
                gauge = {
                    'axis': {'range': [None, max(total_promesses, total_refus) * 1.2]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, total_refus], 'color': "lightgray"},
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': total_refus
                    }
                }
            ))
            fig_gauge.update_layout(height=400)
            st.plotly_chart(fig_gauge, use_container_width=True)

def create_demandes_recrutement_tab(df_recrutement):
    """Onglet Demandes de Recrutement (Image 2)"""
    st.header("📋 Demandes de Recrutement")
    
    # Sidebar pour les filtres
    st.sidebar.subheader("🔧 Filtres - Demandes")
    
    # Filtre par période de demande
    if 'Date de réception de la demande aprés validation de la DRH' in df_recrutement.columns:
        df_recrutement['Année_demande'] = df_recrutement['Date de réception de la demande aprés validation de la DRH'].dt.year
        annees_demande = sorted([y for y in df_recrutement['Année_demande'].dropna().unique() if not pd.isna(y)])
        if annees_demande:
            annee_demande_select = st.sidebar.selectbox("Période de la demande", ['Toutes'] + [int(a) for a in annees_demande])
        else:
            annee_demande_select = 'Toutes'
    else:
        annee_demande_select = 'Toutes'
    
    # Appliquer le filtre
    df_filtered = df_recrutement.copy()
    if annee_demande_select != 'Toutes':
        df_filtered = df_filtered[df_filtered['Année_demande'] == annee_demande_select]
    
    # KPI principal - Nombre de demandes (comme dans l'image 2)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.metric("📊 Nombre de demandes", len(df_filtered), 
                 help="Nombre total de demandes de recrutement")
    
    # Graphiques principaux
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Répartition par statut de la demande (pie chart comme dans l'image 2)
        statut_counts = df_filtered['Statut de la demande'].value_counts()
        
        # Couleurs personnalisées pour correspondre à l'image
        color_map = {
            'Clôture': '#1f77b4',      # Bleu
            'Dépriorisé': '#2ca02c',   # Vert
            'Annulé': '#ff7f0e',       # Orange
            'En cours': '#d62728'       # Rouge
        }
        colors = [color_map.get(status, '#8c564b') for status in statut_counts.index]
        
        fig_statut = px.pie(
            values=statut_counts.values,
            names=statut_counts.index,
            title="📊 Répartition par statut de la demande",
            color_discrete_sequence=colors
        )
        fig_statut.update_traces(textposition='inside', textinfo='percent+label')
        fig_statut.update_layout(height=400)
        st.plotly_chart(fig_statut, use_container_width=True)
    
    with col2:
        # Comparaison par raison du recrutement (bar horizontal)
        if 'Raison du recrutement' in df_filtered.columns:
            raison_counts = df_filtered['Raison du recrutement'].value_counts()
            
            fig_raison = px.bar(
                x=raison_counts.values,
                y=raison_counts.index,
                orientation='h',
                title="🔄 Comparaison par raison du recrutement",
                color=raison_counts.values,
                color_continuous_scale='grays'
            )
            fig_raison.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_raison, use_container_width=True)
    
    with col3:
        # Évolution des demandes par mois (bar chart comme dans l'image 2)
        if 'Date de réception de la demande aprés validation de la DRH' in df_filtered.columns:
            df_filtered['Mois'] = df_filtered['Date de réception de la demande aprés validation de la DRH'].dt.to_period('M')
            monthly_demandes = df_filtered.groupby('Mois').size().reset_index(name='Count')
            monthly_demandes['Mois_str'] = monthly_demandes['Mois'].astype(str)
            
            fig_evolution_demandes = px.bar(
                monthly_demandes, 
                x='Mois_str', 
                y='Count',
                title="� Évolution des demandes",
                color='Count',
                color_continuous_scale='blues'
            )
            fig_evolution_demandes.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_evolution_demandes, use_container_width=True)
    
    # Deuxième ligne de graphiques
    col4, col5 = st.columns(2)
    
    with col4:
        # Comparaison par direction (bar horizontal comme dans l'image 2)
        direction_counts = df_filtered['Direction concernée'].value_counts().head(10)
        
        fig_direction = px.bar(
            x=direction_counts.values,
            y=direction_counts.index,
            orientation='h',
            title="🏢 Comparaison par direction",
            color=direction_counts.values,
            color_continuous_scale='oranges'
        )
        fig_direction.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_direction, use_container_width=True)
    
    with col5:
        # Comparaison par poste (bar horizontal comme dans l'image 2)
        poste_counts = df_filtered['Poste demandé'].value_counts().head(15)
        
        fig_poste = px.bar(
            x=poste_counts.values,
            y=poste_counts.index,
            orientation='h',
            title="👥 Comparaison par poste",
            color=poste_counts.values,
            color_continuous_scale='greens'
        )
        fig_poste.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_poste, use_container_width=True)

def main():
    st.title("📊 Tableau de Bord RH - Reporting Power BI Style")
    st.markdown("---")
    
    # Charger les données
    df_integration, df_recrutement = load_data()
    
    if df_recrutement is None:
        st.error("Impossible de charger les données de recrutement")
        return
    
    # Créer les onglets
    tab1, tab2, tab3 = st.tabs(["🎯 Recrutements (Clôture)", "📋 Demandes Recrutement", "📊 Intégrations"])
    
    with tab1:
        create_recrutements_clotures_tab(df_recrutement)
    
    with tab2:
        create_demandes_recrutement_tab(df_recrutement)
    
    with tab3:
        # Onglet pour les données d'intégration (données CSV)
        if df_integration is not None:
            st.header("� Suivi des Intégrations")
            
            # KPIs d'intégration
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Total Intégrations", len(df_integration))
            with col2:
                en_cours = len(df_integration[df_integration['Statut'] == 'En cours'])
                st.metric("⏳ En Cours", en_cours)
            with col3:
                complet = len(df_integration[df_integration['Statut'] == 'Complet'])
                st.metric("✅ Complet", complet)
            with col4:
                avg_docs = df_integration['Docs Manquants'].mean()
                st.metric("📄 Docs Moy/Personne", f"{avg_docs:.1f}")
            
            # Graphiques d'intégration
            col1, col2 = st.columns(2)
            
            with col1:
                timeline_fig = create_integration_timeline(df_integration)
                st.plotly_chart(timeline_fig, use_container_width=True)
            
            with col2:
                affectation_fig = create_affectation_chart(df_integration)
                st.plotly_chart(affectation_fig, use_container_width=True)
            
            # Tableau de données
            st.subheader("📊 Données Détaillées - Intégrations")
            st.dataframe(df_integration, use_container_width=True)
        else:
            st.error("Données d'intégration non disponibles")

if __name__ == "__main__":
    main()