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
                           'Date d\'annulation /dépriorisation de la demande']
            
            for col in date_columns:
                if col in df_recrutement.columns:
                    df_recrutement[col] = pd.to_datetime(df_recrutement[col], errors='coerce')
            
            # Nettoyer les colonnes avec des espaces
            df_recrutement.columns = df_recrutement.columns.str.strip()

            # Vérification basique des colonnes critiques et message dans les logs
            required_cols = [
                'Statut de la demande', 'Poste demandé', 'Direction concernée',
                'Entité demandeuse', 'Modalité de recrutement', "Canal de publication de l'offre"
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
                color_continuous_scale='Blues'
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
        # Analyse candidats présélectionnés
        col_candidats = 'Nb de candidats pré-selectionnés'
        
        if col_candidats in df_filtered.columns:
            # Créer un graphique en jauge pour les candidats présélectionnés
            total_candidats = df_filtered[col_candidats].fillna(0).sum()
            nb_demandes = len(df_filtered)
            
            fig_candidats = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = total_candidats,
                title = {'text': f"Candidats présélectionnés<br>({nb_demandes} demandes)"},
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, total_candidats * 1.2]},
                    'bar': {'color': "green"},
                    'steps': [
                        {'range': [0, total_candidats * 0.5], 'color': "lightgray"},
                        {'range': [total_candidats * 0.5, total_candidats], 'color': "gray"}
                    ],
                }
            ))
            fig_candidats.update_layout(height=400)
            st.plotly_chart(fig_candidats, use_container_width=True)

    # Délai moyen de recrutement (comme dans l'image)
    st.subheader("⏱️ Délai moyen de recrutement")
    
    if 'Date de réception de la demande aprés validation de la DRH' in df_filtered.columns and 'Date d\'entrée effective du candidat' in df_filtered.columns:
        # Calculer les délais
        df_filtered['Délai_jours'] = (df_filtered['Date d\'entrée effective du candidat'] - 
                                     df_filtered['Date de réception de la demande aprés validation de la DRH']).dt.days
        
        delai_moyen = df_filtered['Délai_jours'].mean()
        
        if not pd.isna(delai_moyen):
            # Créer un graphique de barre horizontale pour le délai
            fig_delai = go.Figure(go.Bar(
                x=[delai_moyen],
                y=['Délai moyen'],
                orientation='h',
                marker_color='#1f77b4',
                text=[f'{delai_moyen:.0f} jours'],
                textposition='auto'
            ))
            fig_delai.update_layout(
                title="⏱️ Délai moyen de recrutement",
                xaxis_title="Jours",
                height=200,
                showlegend=False
            )
            st.plotly_chart(fig_delai, use_container_width=True)

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
        st.markdown(f"<h1 style='text-align: center; color: #1f77b4; font-size: 4em;'>{len(df_filtered)}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 1.2em;'>Nombre de demandes</p>", unsafe_allow_html=True)
    
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
            
            try:
                fig_raison = px.bar(
                    x=raison_counts.values,
                    y=raison_counts.index,
                    orientation='h',
                    title="🔄 Comparaison par raison du recrutement",
                    color=raison_counts.values,
                    color_continuous_scale='Greys'
                )
                fig_raison.update_layout(height=400, showlegend=False)
            except Exception as e:
                st.error(f"Erreur lors de la création du graphique des raisons: {e}")
                fig_raison = None
            if fig_raison is not None:
                st.plotly_chart(fig_raison, use_container_width=True)
            else:
                st.info("Graphique 'Raison du recrutement' indisponible pour ces données.")
    
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
                title="📈 Évolution des demandes",
                color='Count',
                color_continuous_scale='Blues'
            )
            fig_evolution_demandes.update_layout(height=400, showlegend=False)
            try:
                st.plotly_chart(fig_evolution_demandes, use_container_width=True)
            except Exception as e:
                st.error(f"Erreur lors de l'affichage du graphique d'évolution des demandes: {e}")
    
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
            color_continuous_scale='Oranges'
        )
        fig_direction.update_layout(height=500, showlegend=False)
        try:
            st.plotly_chart(fig_direction, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur lors de l'affichage du graphique par direction: {e}")
    
    with col5:
        # Comparaison par poste (bar horizontal comme dans l'image 2)
        poste_counts = df_filtered['Poste demandé'].value_counts().head(15)
        
        fig_poste = px.bar(
            x=poste_counts.values,
            y=poste_counts.index,
            orientation='h',
            title="👥 Comparaison par poste",
            color=poste_counts.values,
            color_continuous_scale='Greens'
        )
        fig_poste.update_layout(height=500, showlegend=False)
        try:
            st.plotly_chart(fig_poste, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur lors de l'affichage du graphique par poste: {e}")

def main():
    st.title("📊 Tableau de Bord RH - Style Power BI")
    st.markdown("---")
    
    # Créer les onglets
    tab1, tab2, tab3, tab4 = st.tabs(["📂 Upload Fichiers", "🎯 Recrutements (Clôture)", "📋 Demandes Recrutement", "📊 Intégrations"])
    
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
    
    with tab1:
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
        else:
            st.sidebar.info("ℹ️ Données chargées depuis les fichiers locaux de l'application. Uploadez vos fichiers pour remplacer ces données.")
    
    with tab2:
        if df_recrutement is not None:
            create_recrutements_clotures_tab(df_recrutement)
        else:
            st.warning("📊 Aucune donnée de recrutement disponible. Veuillez uploader un fichier Excel dans l'onglet 'Upload Fichiers'.")
    
    with tab3:
        if df_recrutement is not None:
            create_demandes_recrutement_tab(df_recrutement)
        else:
            st.warning("📋 Aucune donnée de recrutement disponible. Veuillez uploader un fichier Excel dans l'onglet 'Upload Fichiers'.")
    
    with tab4:
        # Onglet pour les données d'intégration (données CSV)
        if df_integration is not None:
            st.header("📊 Suivi des Intégrations")
            
            # KPIs d'intégration
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Total Intégrations", len(df_integration))
            with col2:
                en_cours = len(df_integration[df_integration['Statut'] == 'En cours']) if 'Statut' in df_integration.columns else 0
                st.metric("⏳ En Cours", en_cours)
            with col3:
                complet = len(df_integration[df_integration['Statut'] == 'Complet']) if 'Statut' in df_integration.columns else 0
                st.metric("✅ Complet", complet)
            with col4:
                avg_docs = df_integration['Docs Manquants'].mean() if 'Docs Manquants' in df_integration.columns else 0
                st.metric("📄 Docs Moy/Personne", f"{avg_docs:.1f}")
            
            # Graphiques d'intégration
            if 'Date Intégration' in df_integration.columns and 'Statut' in df_integration.columns:
                col1, col2 = st.columns(2)
                
                with col1:
                    timeline_fig = create_integration_timeline(df_integration)
                    st.plotly_chart(timeline_fig, use_container_width=True)
                
                with col2:
                    if 'Affectation' in df_integration.columns:
                        affectation_fig = create_affectation_chart(df_integration)
                        st.plotly_chart(affectation_fig, use_container_width=True)
                    else:
                        st.info("Colonne 'Affectation' non trouvée dans les données")
            else:
                st.info("Colonnes requises non trouvées pour les graphiques (Date Intégration, Statut)")
            
            # Tableau de données
            st.subheader("📊 Données Détaillées - Intégrations")
            st.dataframe(df_integration, use_container_width=True)
        else:
            st.warning("📊 Aucune donnée d'intégration disponible. Veuillez uploader un fichier CSV dans l'onglet 'Upload Fichiers'.")

if __name__ == "__main__":
    main()