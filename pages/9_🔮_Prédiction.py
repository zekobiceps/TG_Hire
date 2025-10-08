import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
import xgboost as xgb
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
import io
from sklearn.metrics import mean_absolute_percentage_error
warnings.filterwarnings('ignore')

# Configuration de la page
st.set_page_config(
    page_title="Prédiction de Recrutements - TGCC",
    page_icon="🔮",
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
    }
    .sub-header {
        font-size: 1.8rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .insight-card {
        background-color: #e6f3ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1e88e5;
        margin-bottom: 15px;
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
        background-color: #e6f3ff;
        border-bottom: 2px solid #1e88e5;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if 'data' not in st.session_state:
    st.session_state.data = None
if 'cleaned_data_filtered' not in st.session_state:
    st.session_state.cleaned_data_filtered = None
if 'time_series_data' not in st.session_state:
    st.session_state.time_series_data = None
if 'analysis_objective' not in st.session_state:
    st.session_state.analysis_objective = "Les Recrutements Effectifs"
if 'direction_col' not in st.session_state:
    st.session_state.direction_col = None
if 'poste_col' not in st.session_state:
    st.session_state.poste_col = None
if 'date_col' not in st.session_state:
    st.session_state.date_col = None

# Fonctions utilitaires
def convert_df_to_csv(df):
    """Convertir un DataFrame en CSV téléchargeable"""
    return df.to_csv(index=False).encode('utf-8')

def apply_temporal_guard(df, date_col, objective):
    """
    RÈGLE N°1: GARDE-FOU TEMPOREL - Correction la plus critique
    Supprime toutes les lignes avec des dates dans le futur
    """
    current_date = datetime.now().date()
    df = df.copy()
    
    # Convertir la colonne de date
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    # Identifier les lignes futures
    future_mask = df[date_col].dt.date > current_date
    n_future = future_mask.sum()
    
    # Filtrer les données futures
    df_filtered = df[~future_mask]
    
    if n_future > 0:
        st.warning(f"⚠️ **Garde-Fou Temporel**: {n_future} entrées avec des dates futures ont été automatiquement supprimées pour éviter des biais dans les prédictions.")
    
    return df_filtered, n_future

def detect_columns(df):
    """Détecter automatiquement les colonnes importantes"""
    columns = df.columns.tolist()
    
    # Détecter les colonnes de direction
    direction_cols = [c for c in columns if any(word in c.lower() for word in ['direction', 'département', 'dept', 'service'])]
    direction_col = direction_cols[0] if direction_cols else None
    
    # Détecter les colonnes de poste
    poste_cols = [c for c in columns if any(word in c.lower() for word in ['poste', 'fonction', 'job', 'métier', 'emploi'])]
    poste_col = poste_cols[0] if poste_cols else None
    
    # Détecter les colonnes de statut
    statut_cols = [c for c in columns if any(word in c.lower() for word in ['statut', 'status', 'état', 'state'])]
    statut_col = statut_cols[0] if statut_cols else None
    
    return direction_col, poste_col, statut_col

def get_date_column_for_objective(df, objective):
    """
    RÈGLE N°2: Logique de Filtrage Automatisée
    Sélectionner automatiquement la colonne de date selon l'objectif
    """
    columns = df.columns.tolist()
    
    if objective == "Les Demandes de Recrutement":
        # Chercher la colonne "Date de réception de la demande aprés validation de la DRH"
        for col in columns:
            if "réception" in col.lower() and "demande" in col.lower():
                return col
        # Fallback
        for col in columns:
            if "réception" in col.lower() or ("date" in col.lower() and "demande" in col.lower()):
                return col
    else:  # "Les Recrutements Effectifs"
        # Chercher la colonne "Date d'entrée effective du candidat"
        for col in columns:
            if "entrée" in col.lower() and "effective" in col.lower():
                return col
        # Fallback
        for col in columns:
            if "entrée" in col.lower() or "effective" in col.lower():
                return col
    
    # Fallback général - première colonne contenant "date"
    date_cols = [c for c in columns if 'date' in c.lower()]
    return date_cols[0] if date_cols else None

def apply_business_logic_filter(df, objective, statut_col):
    """
    RÈGLE N°2: Appliquer le filtrage métier selon l'objectif
    """
    df = df.copy()
    
    if objective == "Les Demandes de Recrutement":
        # Garder les lignes où le statut contient: "Clôture", "En cours", "Dépriorisé", "Annulé"
        if statut_col and statut_col in df.columns:
            valid_statuses = ["clôture", "cloture", "en cours", "dépriorisé", "depriorise", "annulé", "annule"]
            mask = df[statut_col].astype(str).str.lower().str.strip().isin(valid_statuses)
            df_filtered = df[mask]
            n_filtered = len(df) - len(df_filtered)
            if n_filtered > 0:
                st.info(f"📝 **Filtrage Demandes**: {n_filtered} lignes exclues (statut non pertinent pour l'analyse des demandes)")
        else:
            df_filtered = df
            st.warning("⚠️ Aucune colonne de statut détectée. Toutes les demandes sont conservées.")
    else:  # "Les Recrutements Effectifs"
        # Garder seulement les lignes où la date d'entrée effective n'est pas vide
        date_col = get_date_column_for_objective(df, objective)
        if date_col:
            mask = df[date_col].notna()
            df_filtered = df[mask]
            n_filtered = len(df) - len(df_filtered)
            if n_filtered > 0:
                st.info(f"👨‍💼 **Filtrage Recrutements**: {n_filtered} lignes exclues (pas de date d'entrée effective)")
        else:
            df_filtered = df
            st.warning("⚠️ Aucune colonne de date d'entrée effective détectée.")
    
    return df_filtered

def create_time_series(df, date_col, freq):
    """Créer une série temporelle agrégée"""
    df = df.copy()
    df['date_parsed'] = pd.to_datetime(df[date_col])
    df = df.dropna(subset=['date_parsed'])
    
    # Agréger par fréquence (compter les lignes)
    df_agg = df.set_index('date_parsed').resample(freq).size().reset_index(name='volume')
    df_agg = df_agg.rename(columns={'date_parsed': 'date'})
    
    return df_agg

def calculate_mape(y_true, y_pred):
    """Calculer le MAPE (Mean Absolute Percentage Error)"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    # Éviter la division par zéro
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def predict_with_prophet(df, horizon_months):
    """Prédiction avec Prophet"""
    prophet_df = pd.DataFrame({
        'ds': df['date'],
        'y': df['volume']
    })
    
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05
    )
    model.fit(prophet_df)
    
    future = model.make_future_dataframe(periods=horizon_months, freq='M')
    forecast = model.predict(future)
    
    return model, forecast

def predict_with_holt_winters(df, horizon_months):
    """Prédiction avec Holt-Winters"""
    try:
        model = ExponentialSmoothing(
            df['volume'].values,
            trend='add',
            seasonal='add',
            seasonal_periods=12
        ).fit()
        
        forecast_values = model.forecast(horizon_months)
        
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_months + 1, freq='M')[1:]
        forecast_df = pd.DataFrame({
            'ds': list(df['date']) + list(future_dates),
            'yhat': list(df['volume']) + list(forecast_values)
        })
        
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur Holt-Winters: {e}")
        return None, None

def predict_with_xgboost(df, horizon_months, lookback=12):
    """Prédiction avec XGBoost"""
    try:
        data = df['volume'].values
        X, y = [], []
        
        # Ajuster le lookback s'il est trop grand pour les données mensuelles
        effective_lookback = min(lookback, len(data) - 1)
        if effective_lookback < 1:
            st.error("Pas assez de données pour XGBoost avec cette configuration.")
            return None, None

        for i in range(effective_lookback, len(data)):
            X.append(data[i-effective_lookback:i])
            y.append(data[i])
        
        X, y = np.array(X), np.array(y)
        
        model = xgb.XGBRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        last_sequence = data[-effective_lookback:]
        forecasts = []
        
        for _ in range(horizon_months):
            next_pred = model.predict(np.array([last_sequence]))[0]
            forecasts.append(max(0, next_pred))
            last_sequence = np.append(last_sequence[1:], next_pred)
        
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_months + 1, freq='M')[1:]
        forecast_df = pd.DataFrame({
            'ds': list(df['date']) + list(future_dates),
            'yhat': list(df['volume']) + forecasts
        })
        
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur XGBoost: {e}")
        return None, None

# Titre principal
st.markdown("# 🔮 Prédiction des Recrutements")
st.markdown("---")

# Créer les onglets
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Import des Données",
    "🧹 Nettoyage & Préparation", 
    "📊 Visualisation",
    "🔮 Modélisation & Prédiction"
])

# ============================
# ONGLET 1: IMPORT DES DONNÉES
# ============================
with tab1:
    st.header("📁 Import des Données")
    st.markdown("Importez vos données de recrutement ou utilisez les données d'exemple pour commencer.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Upload du fichier
        uploaded_file = st.file_uploader(
            "Choisissez votre fichier de données",
            type=['csv', 'xlsx', 'xls'],
            help="Formats supportés: CSV, Excel"
        )
        
        # Option données d'exemple
        use_sample = st.checkbox("Utiliser des données d'exemple", value=False)
        
        if use_sample:
            st.info("📊 Génération des données d'exemple en cours...")
            
            # Générer des données d'exemple réalistes
            np.random.seed(42)  # Pour la reproductibilité
            date_range = pd.date_range(start='2020-01-01', end='2024-09-30', freq='D')
            
            directions = [
                "Direction Technique", "Direction RH", "Direction Commerciale", 
                "Direction Financière", "Direction Logistique", "Direction Marketing"
            ]
            
            postes = [
                "Ingénieur", "Technicien", "Chef de projet", "Responsable", 
                "Assistant", "Analyste", "Développeur", "Gestionnaire", 
                "Consultant", "Chargé de mission", "Directeur", "Manager"
            ]
            
            n_samples = 1200
            
            # Générer des demandes
            sample_data = pd.DataFrame({
                'Date de réception de la demande aprés validation de la DRH': 
                    np.random.choice(date_range, n_samples),
                'Direction concernée': 
                    np.random.choice(directions, n_samples, p=[0.25, 0.15, 0.20, 0.15, 0.15, 0.10]),
                'Poste demandé': 
                    np.random.choice(postes, n_samples),
                'Statut de la demande': 
                    np.random.choice(["Clôture", "En cours", "Dépriorisé", "Annulé"], 
                                   n_samples, p=[0.60, 0.15, 0.15, 0.10])
            })
            
            # Ajouter la date d'entrée effective pour les recrutements clôturés
            sample_data['Date d\'entrée effective du candidat'] = pd.NaT
            
            for idx in sample_data.index:
                if sample_data.loc[idx, 'Statut de la demande'] == "Clôture":
                    demand_date = sample_data.loc[idx, 'Date de réception de la demande aprés validation de la DRH']
                    # Délai d'entrée entre 30 et 120 jours
                    entry_delay = np.random.randint(30, 120)
                    entry_date = demand_date + pd.Timedelta(days=entry_delay)
                    
                    # Ne pas dépasser la date actuelle
                    if entry_date <= pd.Timestamp.now():
                        sample_data.loc[idx, 'Date d\'entrée effective du candidat'] = entry_date
            
            st.session_state.data = sample_data
            st.success("✅ Données d'exemple générées avec succès!")
            
        elif uploaded_file is not None:
            try:
                # Lecture robuste du fichier
                if uploaded_file.name.endswith('.csv'):
                    try:
                        data = pd.read_csv(uploaded_file, encoding='utf-8')
                    except UnicodeDecodeError:
                        data = pd.read_csv(uploaded_file, encoding='latin-1')
                else:
                    data = pd.read_excel(uploaded_file)
                
                st.session_state.data = data
                st.success(f"✅ Fichier '{uploaded_file.name}' importé avec succès!")
                
            except Exception as e:
                st.error(f"❌ Erreur lors de l'import: {str(e)}")
        
        # Sélection de l'objectif d'analyse (RÈGLE CRITIQUE)
        if st.session_state.data is not None:
            st.markdown("### 🎯 Choix de l'Objectif")
            
            analysis_objective = st.radio(
                "Que souhaitez-vous analyser et prédire ?",
                options=["Les Demandes de Recrutement", "Les Recrutements Effectifs"],
                index=1,  # Par défaut: Recrutements Effectifs
                help="Ce choix détermine automatiquement la colonne de date et les filtres appliqués."
            )
            
            st.session_state.analysis_objective = analysis_objective
            
            if analysis_objective == "Les Demandes de Recrutement":
                st.info("📝 **Analyse des demandes**: Basée sur la date de réception des demandes. "
                       "Filtrage automatique sur les statuts pertinents.")
            else:
                st.info("👨‍💼 **Analyse des recrutements effectifs**: Basée sur la date d'entrée effective. "
                       "Seuls les recrutements réalisés sont pris en compte.")
    
    # Informations sur les données
    if st.session_state.data is not None:
        with col2:
            st.metric("📄 Lignes", st.session_state.data.shape[0])
            st.metric("📊 Colonnes", st.session_state.data.shape[1])
            
            # Période des données
            date_cols = [col for col in st.session_state.data.columns 
                        if 'date' in col.lower()]
            if date_cols:
                try:
                    dates = pd.to_datetime(st.session_state.data[date_cols[0]], errors='coerce')
                    min_date = dates.min().strftime('%m/%Y')
                    max_date = dates.max().strftime('%m/%Y')
                    st.metric("📅 Période", f"{min_date} - {max_date}")
                except:
                    pass
        
        # Aperçu des données
        st.subheader("📋 Aperçu des données")
        st.dataframe(st.session_state.data.head(), use_container_width=True)
        
        # Informations sur les colonnes
        with st.expander("ℹ️ Informations détaillées sur les colonnes"):
            col_info = pd.DataFrame({
                'Type': st.session_state.data.dtypes,
                'Non-nulles': st.session_state.data.count(),
                'Nulles': st.session_state.data.isnull().sum(),
                'Uniques': [st.session_state.data[col].nunique() for col in st.session_state.data.columns]
            })
            st.dataframe(col_info, use_container_width=True)
    else:
        st.info("👆 Veuillez importer un fichier ou utiliser les données d'exemple pour commencer.")

# ============================
# ONGLET 2: NETTOYAGE & PRÉPARATION (AUTOMATISÉ)
# ============================
with tab2:
    st.header("🧹 Nettoyage & Préparation des Données")
    
    if st.session_state.data is None:
        st.info("👆 Veuillez d'abord importer des données dans l'onglet précédent.")
    else:
        objective = st.session_state.get('analysis_objective', "Les Recrutements Effectifs")
        
        st.info(f"🤖 **Préparation automatisée** basée sur votre objectif: **{objective}**")
        st.markdown("La colonne de date et les filtres métier sont sélectionnés automatiquement.")
        
        # Configuration simplifiée
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⏱️ Fréquence d'agrégation")
            freq_options = {
                "Mensuelle": "M",
                "Trimestrielle": "Q", 
                "Annuelle": "Y"
            }
            selected_freq = st.selectbox(
                "Choisissez la fréquence d'agrégation:",
                options=list(freq_options.keys()),
                index=0,
                help="La fréquence détermine la granularité de l'analyse temporelle"
            )
            freq = freq_options[selected_freq]
        
        with col2:
            st.subheader("📅 Période d'analyse")
            # Détecter la colonne de date selon l'objectif
            date_col = get_date_column_for_objective(st.session_state.data, objective)
            
            if date_col:
                try:
                    # Coerce errors to NaT, then drop them to get a clean date range
                    clean_dates = pd.to_datetime(st.session_state.data[date_col], errors='coerce').dropna()
                    min_date = clean_dates.min().date()
                    max_date = clean_dates.max().date()
                    
                    start_date = st.date_input(
                        "Date de début",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date
                    )
                    end_date = st.date_input(
                        "Date de fin", 
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date
                    )
                except Exception as e:
                    st.warning("⚠️ Impossible de parser les dates automatiquement.")
                    start_date = end_date = None
            else:
                st.warning("⚠️ Aucune colonne de date appropriée détectée")
                start_date = end_date = None

        
        # Filtres contextuels optionnels
        st.subheader("🔍 Filtres contextuels (optionnel)")
        
        # Détecter les colonnes automatiquement
        direction_col, poste_col, statut_col = detect_columns(st.session_state.data)
        
        col3, col4 = st.columns(2)
        
        with col3:
            if direction_col:
                directions = ["Toutes"] + sorted(st.session_state.data[direction_col].dropna().unique().tolist())
                selected_directions = st.multiselect(
                    f"Filtrer par {direction_col}",
                    options=directions,
                    default=["Toutes"]
                )
            else:
                selected_directions = ["Toutes"]
                st.info("Aucune colonne Direction détectée")
        
        with col4:
            if poste_col:
                postes = ["Tous"] + sorted(st.session_state.data[poste_col].dropna().unique().tolist())
                selected_postes = st.multiselect(
                    f"Filtrer par {poste_col}",
                    options=postes,
                    default=["Tous"]
                )
            else:
                selected_postes = ["Tous"]
                st.info("Aucune colonne Poste détectée")
        
        # Bouton de préparation
        if st.button("🚀 Préparer les données automatiquement", type="primary", use_container_width=True):
            with st.spinner("Préparation en cours..."):
                try:
                    df = st.session_state.data.copy()
                    
                    # RÈGLE N°1: GARDE-FOU TEMPOREL - Application immédiate
                    if date_col:
                        df_filtered, n_future = apply_temporal_guard(df, date_col, objective)
                        df = df_filtered
                    else:
                        st.error("❌ Impossible d'appliquer le garde-fou temporel: aucune colonne de date détectée")
                        st.stop()
                    
                    # RÈGLE N°2: LOGIQUE MÉTIER AUTOMATISÉE
                    df = apply_business_logic_filter(df, objective, statut_col)
                    
                    # Filtrage par période
                    if date_col and start_date and end_date:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        df.dropna(subset=[date_col], inplace=True) # Important: drop rows that failed conversion
                        mask = (df[date_col].dt.date >= start_date) & (df[date_col].dt.date <= end_date)
                        df = df[mask]
                        st.info(f"📅 Filtrage temporel appliqué: {start_date} à {end_date}")
                    
                    # Filtres contextuels
                    if direction_col and "Toutes" not in selected_directions:
                        df = df[df[direction_col].isin(selected_directions)]
                        st.info(f"🏢 Filtrage par Direction: {len(selected_directions)} sélectionnées")
                    
                    if poste_col and "Tous" not in selected_postes:
                        df = df[df[poste_col].isin(selected_postes)]
                        st.info(f"👥 Filtrage par Poste: {len(selected_postes)} sélectionnés")
                    
                    # Sauvegarder les données filtrées
                    st.session_state.cleaned_data_filtered = df
                    
                    # Créer la série temporelle agrégée
                    if date_col and not df.empty:
                        time_series = create_time_series(df, date_col, freq)
                        st.session_state.time_series_data = time_series
                        st.session_state.date_col = date_col
                        st.session_state.direction_col = direction_col
                        st.session_state.poste_col = poste_col
                        
                        # Afficher les résultats de la préparation
                        col_res1, col_res2, col_res3 = st.columns(3)
                        
                        with col_res1:
                            st.metric("📊 Lignes conservées", len(df))
                        
                        with col_res2:
                            st.metric("📈 Points temporels", len(time_series))
                        
                        with col_res3:
                            st.metric("⏱️ Fréquence", selected_freq)
                        
                        st.success("✅ **Données préparées avec succès!** Vous pouvez maintenant passer aux onglets suivants.")
                        
                        # Aperçu de la série temporelle
                        st.subheader("📈 Aperçu de la série temporelle")
                        fig = px.line(time_series, x='date', y='volume', 
                                    title=f"Série temporelle - {objective}")
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    elif df.empty:
                        st.warning("⚠️ Aucune donnée ne correspond à vos filtres. La série temporelle est vide.")
                        st.session_state.time_series_data = None
                        st.session_state.cleaned_data_filtered = None

                except Exception as e:
                    st.error(f"❌ Erreur lors de la préparation: {str(e)}")
                    st.exception(e)
        
        # Affichage de l'état actuel
        if st.session_state.cleaned_data_filtered is not None:
            st.success("✅ Données déjà préparées. Vous pouvez modifier les paramètres et relancer la préparation si nécessaire.")

# ============================
# ONGLET 3: VISUALISATION - MIROIR DU PASSÉ
# ============================
with tab3:
    st.header("📊 Visualisation - Miroir du Passé")
    
    if st.session_state.time_series_data is None or st.session_state.time_series_data.empty or st.session_state.cleaned_data_filtered is None:
        st.info("👆 Veuillez d'abord préparer les données dans l'onglet précédent.")
    else:
        time_series = st.session_state.time_series_data
        raw_data = st.session_state.cleaned_data_filtered
        direction_col = st.session_state.direction_col
        poste_col = st.session_state.poste_col
        objective = st.session_state.get('analysis_objective', 'Recrutements')
        
        # Graphique principal - Tendance historique
        st.subheader("📈 Tendance Historique")
        
        fig_trend = px.line(
            time_series, 
            x='date', 
            y='volume',
            title=f"Évolution temporelle - {objective}",
            labels={'date': 'Date', 'volume': 'Volume'}
        )
        
        fig_trend.update_layout(
            height=400,
            showlegend=False,
            xaxis_title="Période",
            yaxis_title="Nombre"
        )
        
        fig_trend.update_traces(
            line=dict(width=3, color='#1f77b4'),
            mode='lines+markers',
            marker=dict(size=6)
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Statistiques de la série
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Historique", f"{time_series['volume'].sum():,}")
        
        with col2:
            st.metric("📈 Maximum", f"{time_series['volume'].max():,}")
        
        with col3:
            st.metric("📉 Minimum", f"{time_series['volume'].min():,}")
        
        with col4:
            st.metric("🎯 Moyenne", f"{time_series['volume'].mean():.1f}")
        
        st.markdown("---")
        
        # Répartition Historique
        st.subheader("🔍 Répartition Historique")
        
        col_left, col_right = st.columns(2)
        
        # Répartition par Direction
        with col_left:
            st.markdown("#### 🏢 Par Direction")
            
            if direction_col and direction_col in raw_data.columns:
                dir_counts = raw_data[direction_col].value_counts().reset_index()
                dir_counts.columns = ['Direction', 'Nombre']
                
                fig_dir = px.bar(
                    dir_counts.sort_values('Nombre', ascending=True).tail(10),  # Top 10
                    x='Nombre',
                    y='Direction',
                    orientation='h',
                    title="Top 10 Directions",
                    color='Nombre',
                    color_continuous_scale='Blues'
                )
                
                fig_dir.update_layout(
                    height=400,
                    showlegend=False,
                    coloraxis_showscale=False
                )
                
                st.plotly_chart(fig_dir, use_container_width=True)
                
                # Tableau détaillé
                with st.expander("📋 Détail par Direction"):
                    dir_counts['Pourcentage'] = (dir_counts['Nombre'] / dir_counts['Nombre'].sum() * 100).round(1)
                    st.dataframe(dir_counts, use_container_width=True)
            else:
                st.info("Aucune colonne Direction détectée dans les données.")
        
        # Répartition par Poste  
        with col_right:
            st.markdown("#### 👥 Par Poste")
            
            if poste_col and poste_col in raw_data.columns:
                poste_counts = raw_data[poste_col].value_counts()
                
                # Top 10 + Autres
                top_10 = poste_counts.head(10)
                others_count = poste_counts.iloc[10:].sum() if len(poste_counts) > 10 else 0
                
                if others_count > 0:
                    top_10_with_others = pd.concat([top_10, pd.Series({'Autres': others_count})])
                else:
                    top_10_with_others = top_10
                
                df_poste = top_10_with_others.reset_index()
                df_poste.columns = ['Poste', 'Nombre']
                
                fig_poste = px.bar(
                    df_poste.sort_values('Nombre', ascending=True),
                    x='Nombre',
                    y='Poste', 
                    orientation='h',
                    title="Top 10 Postes + Autres",
                    color='Nombre',
                    color_continuous_scale='Greens'
                )
                
                fig_poste.update_layout(
                    height=400,
                    showlegend=False,
                    coloraxis_showscale=False
                )
                
                st.plotly_chart(fig_poste, use_container_width=True)
                
                # Tableau détaillé
                with st.expander("📋 Détail par Poste"):
                    poste_df = poste_counts.reset_index()
                    poste_df.columns = ['Poste', 'Nombre']
                    poste_df['Pourcentage'] = (poste_df['Nombre'] / poste_df['Nombre'].sum() * 100).round(1)
                    st.dataframe(poste_df, use_container_width=True)
            else:
                st.info("Aucune colonne Poste détectée dans les données.")
        
        st.markdown("---")
        
        # Analyse temporelle complémentaire
        st.subheader("📅 Analyse Temporelle Détaillée")
        
        # Préparer les données pour l'analyse temporelle
        time_analysis = time_series.copy()
        time_analysis['year'] = time_analysis['date'].dt.year
        time_analysis['month'] = time_analysis['date'].dt.month
        time_analysis['quarter'] = time_analysis['date'].dt.quarter
        
        col_temp1, col_temp2 = st.columns(2)
        
        with col_temp1:
            # Par année
            yearly = time_analysis.groupby('year')['volume'].sum().reset_index()
            if len(yearly) > 1:
                yearly['year'] = yearly['year'].astype(str)
                fig_year = px.bar(
                    yearly,
                    x='year',
                    y='volume',
                    title="Volume Annuel",
                    color='volume',
                    color_continuous_scale='Viridis'
                )
                fig_year.update_layout(height=300, coloraxis_showscale=False)
                st.plotly_chart(fig_year, use_container_width=True)
        
        with col_temp2:
            # Par mois (moyenne)
            monthly = time_analysis.groupby('month')['volume'].mean().reset_index()
            month_names = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
                          'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
            monthly['month_name'] = monthly['month'].map(lambda x: month_names[x])
            
            fig_month = px.bar(
                monthly,
                x='month_name',
                y='volume', 
                title="Volume Moyen par Mois",
                color='volume',
                color_continuous_scale='Plasma'
            )
            fig_month.update_layout(height=300, coloraxis_showscale=False)
            st.plotly_chart(fig_month, use_container_width=True)

# ============================
# ONGLET 4: MODÉLISATION & PRÉDICTION 
# ============================
with tab4:
    st.header("🔮 Modélisation & Prédiction")
    
    if st.session_state.time_series_data is None or st.session_state.time_series_data.empty or st.session_state.cleaned_data_filtered is None:
        st.info("👆 Veuillez d'abord préparer les données dans l'onglet Nettoyage & Préparation.")
    else:
        # Rappel de l'objectif
        objective = st.session_state.get('analysis_objective', 'Recrutements')
        st.info(f"🎯 **Vous prédisez : {objective}**")
        
        time_series = st.session_state.time_series_data
        raw_data = st.session_state.cleaned_data_filtered
        direction_col = st.session_state.direction_col
        poste_col = st.session_state.poste_col
        
        # Configuration de la prédiction
        col1, col2 = st.columns(2)
        
        with col1:
            horizon_months = st.number_input(
                "🔮 Horizon de prévision (mois)",
                min_value=1,
                max_value=24,
                value=6,
                help="Nombre de mois à prédire dans le futur"
            )
        
        with col2:
            model_type = st.selectbox(
                "🤖 Algorithme de prédiction",
                options=["Prophet", "Holt-Winters", "XGBoost"],
                index=0,
                help="Prophet: bon pour tendances et saisonnalité | Holt-Winters: classique et robuste | XGBoost: apprentissage automatique"
            )
        
        # Bouton de lancement
        if st.button("🚀 Lancer la prédiction", type="primary", use_container_width=True):
            with st.spinner(f"🤖 Entraînement du modèle {model_type} en cours..."):
                try:
                    # --- Étape 1: Évaluation du modèle pour le score MAPE ---
                    
                    # Division train/test
                    n_total = len(time_series)
                    n_test = max(1, int(n_total * 0.2))
                    train_data = time_series.iloc[:-n_test].copy()
                    test_data = time_series.iloc[-n_test:].copy()

                    # Entraînement d'un modèle temporaire sur les données d'entraînement
                    if model_type == "Prophet":
                        temp_model, temp_forecast = predict_with_prophet(train_data, n_test)
                    elif model_type == "Holt-Winters":
                        temp_model, temp_forecast = predict_with_holt_winters(train_data, n_test)
                    else:  # XGBoost
                        temp_model, temp_forecast = predict_with_xgboost(train_data, n_test)

                    # Calcul du MAPE en comparant les prédictions aux données de test
                    test_predictions = []
                    if temp_forecast is not None:
                        for test_date in test_data['date']:
                            pred_row = temp_forecast[temp_forecast['ds'].dt.date == test_date.date()]
                            if not pred_row.empty:
                                # support yhat (prévu) ou y (Prophet parfois)
                                if 'yhat' in pred_row.columns:
                                    test_predictions.append(pred_row['yhat'].iloc[0])
                                elif 'y' in pred_row.columns:
                                    test_predictions.append(pred_row['y'].iloc[0])
                                else:
                                    test_predictions.append(np.nan)
                            else:
                                test_predictions.append(np.nan)
                    
                    mape_score = calculate_mape(test_data['volume'].values, test_predictions) if test_predictions else np.nan

                    # Affichage du score de confiance
                    st.subheader("📊 Score de Confiance")
                    col_metric1, col_metric2, col_metric3 = st.columns(3)
                    with col_metric1:
                        if not np.isnan(mape_score):
                            st.metric("Marge d'Erreur Moyenne", f"± {mape_score:.1f}%", help="MAPE calculé sur les données de test")
                        else:
                            st.metric("Marge d'Erreur Moyenne", "N/A")
                    with col_metric2:
                        st.metric("Points d'entraînement", len(train_data))
                    with col_metric3:
                        st.metric("Modèle utilisé", model_type)

                    # --- Étape 2: Génération de la prédiction finale pour l'utilisateur ---

                    # Entraînement du modèle final sur 100% des données historiques
                    st.info("Ré-entraînement du modèle sur toutes les données pour la prédiction finale...")
                    if model_type == "Prophet":
                        final_model, final_forecast = predict_with_prophet(time_series, horizon_months)
                    elif model_type == "Holt-Winters":
                        final_model, final_forecast = predict_with_holt_winters(time_series, horizon_months)
                    else:  # XGBoost
                        final_model, final_forecast = predict_with_xgboost(time_series, horizon_months)

                    if final_model is None or final_forecast is None:
                        st.error("❌ Échec de la prédiction finale.")
                        st.stop()

                    # Préparation des prédictions futures
                    last_date = time_series['date'].max()
                    future_predictions = final_forecast.copy()
                    future_predictions['ds'] = pd.to_datetime(future_predictions['ds'])
                    last_date_ts = pd.to_datetime(last_date)

                    # garder uniquement les dates strictement après la dernière date historique
                    future_predictions = future_predictions[future_predictions['ds'] > last_date_ts].copy()

                    if future_predictions.empty:
                        st.warning("⚠️ Aucune prédiction future générée. Vérifiez la configuration du modèle.")
                    else:
                        # Détecter fréquence d'entraînement (ex. annuelle si médiane des deltas > 300 jours)
                        median_delta = time_series['date'].sort_values().diff().dt.days.median()
                        is_annual = pd.notna(median_delta) and median_delta > 300

                        if is_annual:
                            # répartir les totaux annuels sur les mois selon proportions historiques
                            df_raw = st.session_state.get('cleaned_data_filtered', None)
                            date_col = st.session_state.get('date_col', None)
                            if df_raw is None or date_col is None:
                                month_props = {m: 1/12 for m in range(1,13)}
                            else:
                                df_tmp = df_raw.copy()
                                df_tmp[date_col] = pd.to_datetime(df_tmp[date_col], errors='coerce')
                                df_tmp = df_tmp.dropna(subset=[date_col])
                                df_tmp['month'] = df_tmp[date_col].dt.month
                                month_counts = df_tmp['month'].value_counts().sort_index()
                                if month_counts.sum() == 0:
                                    month_props = {m: 1/12 for m in range(1,13)}
                                else:
                                    month_props = (month_counts / month_counts.sum()).to_dict()

                            monthly_rows = []
                            for _, row in future_predictions.iterrows():
                                year = int(row['ds'].year)
                                total_annual = float(row.get('yhat', row.get('y', 0)))
                                for m in range(1,13):
                                    ds_month = pd.Timestamp(year=year, month=m, day=1)
                                    monthly_val = int(round(total_annual * month_props.get(m, 1/12)))
                                    monthly_rows.append({'date': ds_month, 'predicted_volume': monthly_val})
                            monthly_forecast = pd.DataFrame(monthly_rows).sort_values('date').head(horizon_months).reset_index(drop=True)
                        else:
                            # comportement normal : la prédiction est déjà mensuelle
                            if 'yhat' in future_predictions.columns:
                                monthly_forecast = future_predictions[['ds', 'yhat']].copy().rename(columns={'ds':'date','yhat':'predicted_volume'})
                            else:
                                monthly_forecast = future_predictions[['ds', 'y']].copy().rename(columns={'ds':'date','y':'predicted_volume'})
                            monthly_forecast['date'] = pd.to_datetime(monthly_forecast['date'])
                            monthly_forecast['predicted_volume'] = monthly_forecast['predicted_volume'].round().astype(int).clip(lower=0)
                            monthly_forecast = monthly_forecast.sort_values('date').head(horizon_months).reset_index(drop=True)
                        
                        # --- Affichage des résultats (identique à avant) ---
                        st.subheader("🔮 Prévisions Mensuelles")
                        
                        fig_pred = go.Figure()
                        fig_pred.add_trace(go.Scatter(x=time_series['date'], y=time_series['volume'], mode='lines+markers', name='Historique', line=dict(color='#1f77b4', width=2)))
                        fig_pred.add_trace(go.Scatter(x=monthly_forecast['date'], y=monthly_forecast['predicted_volume'], mode='lines+markers', name='Prédictions', line=dict(color='#ff7f0e', width=3, dash='dash'), marker=dict(size=8)))
                        fig_pred.update_layout(title=f"Prédictions {model_type} - {objective}", xaxis_title="Date", yaxis_title="Volume", height=400, hovermode='x unified')
                        st.plotly_chart(fig_pred, use_container_width=True)
                        
                        display_forecast = monthly_forecast.copy()
                        display_forecast['Mois'] = display_forecast['date'].dt.strftime('%B %Y')
                        display_forecast = display_forecast[['Mois', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})
                        st.dataframe(display_forecast, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # Ventilation par Direction et Poste
                        st.subheader("📊 Ventilation Prévisionnelle")
                        st.markdown("*Basée sur les proportions historiques*")
                        
                        dir_proportions = {}
                        poste_proportions = {}
                        
                        if direction_col and direction_col in raw_data.columns:
                            dir_counts = raw_data[direction_col].value_counts(normalize=True)
                            dir_proportions = dir_counts.to_dict()
                        
                        if poste_col and poste_col in raw_data.columns:
                            poste_counts = raw_data[poste_col].value_counts(normalize=True)
                            poste_proportions = poste_counts.to_dict()
                        
                        col_vent1, col_vent2 = st.columns(2)
                        
                        with col_vent1:
                            if dir_proportions:
                                st.markdown("#### 🏢 Par Direction")
                                dir_forecast_data = []
                                for _, row in monthly_forecast.iterrows():
                                    month = row['date'].strftime('%b %Y')
                                    total = row['predicted_volume']
                                    for direction, proportion in dir_proportions.items():
                                        dir_forecast_data.append({'Mois': month, 'Direction': direction, 'Volume Prédit': int(round(total * proportion)), 'Proportion (%)': f"{proportion*100:.1f}%"})
                                df_dir_forecast = pd.DataFrame(dir_forecast_data)
                                dir_totals = df_dir_forecast.groupby('Direction')['Volume Prédit'].sum().reset_index().sort_values('Volume Prédit', ascending=True)
                                fig_dir = px.bar(dir_totals, x='Volume Prédit', y='Direction', orientation='h', title=f"Total prévu par Direction ({horizon_months} mois)", color='Volume Prédit', color_continuous_scale='Blues')
                                fig_dir.update_layout(height=300, coloraxis_showscale=False)
                                st.plotly_chart(fig_dir, use_container_width=True)
                                with st.expander("📋 Détail mensuel par Direction"):
                                    st.dataframe(df_dir_forecast, use_container_width=True)
                            else:
                                st.info("Aucune colonne Direction disponible pour la ventilation.")
                        
                        with col_vent2:
                            if poste_proportions:
                                st.markdown("#### 👥 Par Poste")
                                poste_forecast_data = []
                                for _, row in monthly_forecast.iterrows():
                                    month = row['date'].strftime('%b %Y')
                                    total = row['predicted_volume']
                                    for poste, proportion in poste_proportions.items():
                                        poste_forecast_data.append({'Mois': month, 'Poste': poste, 'Volume Prédit': int(round(total * proportion)), 'Proportion (%)': f"{proportion*100:.1f}%"})
                                df_poste_forecast = pd.DataFrame(poste_forecast_data)
                                top_n = st.slider("Nombre de postes à afficher", 5, 15, 8, key="top_n_postes")
                                poste_totals = df_poste_forecast.groupby('Poste')['Volume Prédit'].sum().reset_index().sort_values('Volume Prédit', ascending=True).tail(top_n)
                                fig_poste = px.bar(poste_totals, x='Volume Prédit', y='Poste', orientation='h', title=f"Top {top_n} Postes prévus ({horizon_months} mois)", color='Volume Prédit', color_continuous_scale='Greens')
                                fig_poste.update_layout(height=300, coloraxis_showscale=False)
                                st.plotly_chart(fig_poste, use_container_width=True)
                                with st.expander("📋 Détail mensuel par Poste"):
                                    st.dataframe(df_poste_forecast, use_container_width=True)
                            else:
                                st.info("Aucune colonne Poste disponible pour la ventilation.")
                        
                        st.markdown("---")
                        
                        # Export des résultats
                        st.subheader("📥 Export des Résultats")
                        export_data = []
                        for _, row in monthly_forecast.iterrows():
                            month = row['date'].strftime('%Y-%m')
                            month_label = row['date'].strftime('%B %Y')
                            total_volume = row['predicted_volume']
                            export_data.append({'Mois': month, 'Mois_Label': month_label, 'Niveau': 'Total', 'Dimension': 'TOTAL', 'Volume_Predit': total_volume, 'Proportion_Pct': 100.0})
                            if dir_proportions:
                                for direction, proportion in dir_proportions.items():
                                    export_data.append({'Mois': month, 'Mois_Label': month_label, 'Niveau': 'Direction', 'Dimension': direction, 'Volume_Predit': int(round(total_volume * proportion)), 'Proportion_Pct': round(proportion * 100, 2)})
                            if poste_proportions:
                                for poste, proportion in poste_proportions.items():
                                    export_data.append({'Mois': month, 'Mois_Label': month_label, 'Niveau': 'Poste', 'Dimension': poste, 'Volume_Predit': int(round(total_volume * proportion)), 'Proportion_Pct': round(proportion * 100, 2)})
                        
                        export_df = pd.DataFrame(export_data)
                        if not export_df.empty:
                            csv_data = convert_df_to_csv(export_df)
                            st.download_button(label="📥 Télécharger les prévisions détaillées (CSV)", data=csv_data, file_name=f"previsions_{objective.lower().replace(' ', '_')}_{horizon_months}m.csv", mime="text/csv", use_container_width=True)
                            with st.expander("👀 Aperçu des données d'export"):
                                st.dataframe(export_df.head(20), use_container_width=True)
                        
                        st.success(f"✅ **Prédiction terminée avec succès!** Prévisions générées pour {horizon_months} mois avec le modèle {model_type}.")
                    else:
                        st.warning("⚠️ Aucune prédiction future générée. Vérifiez la configuration du modèle.")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction : {str(e)}")
                    with st.expander("🔍 Détails de l'erreur"):
                        st.exception(e)