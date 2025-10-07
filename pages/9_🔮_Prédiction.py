import streamlit as st
import requests
from datetime import datetime, timedelta
import json
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from utils import deepseek_generate
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
import xgboost as xgb
from prophet.plot import add_changepoints_to_plot
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
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
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None
if 'cleaned_data_aggregated' not in st.session_state:
    st.session_state.cleaned_data_aggregated = None
if 'cleaned_data_filtered' not in st.session_state:
    st.session_state.cleaned_data_filtered = None
if 'forecast_results' not in st.session_state:
    st.session_state.forecast_results = None
if 'model' not in st.session_state:
    st.session_state.model = None
if 'forecast_horizon' not in st.session_state:
    st.session_state.forecast_horizon = 90
if 'selected_uid' not in st.session_state:
    st.session_state.selected_uid = None
if 'analysis_objective' not in st.session_state:
    st.session_state.analysis_objective = "Les Recrutements Effectifs"

# Fonctions utilitaires
def convert_df_to_csv(df):
    """Convertir un DataFrame en CSV téléchargeable"""
    return df.to_csv(index=False).encode('utf-8')

def generate_time_features(df, date_col):
    """Générer des caractéristiques temporelles à partir d'une colonne de date"""
    df = df.copy()
    df['date'] = pd.to_datetime(df[date_col])
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    df['quarter'] = df['date'].dt.quarter
    df['day_of_week'] = df['date'].dt.dayofweek
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['is_month_start'] = df['date'].dt.is_month_start
    df['is_month_end'] = df['date'].dt.is_month_end
    df['is_quarter_start'] = df['date'].dt.is_quarter_start
    df['is_quarter_end'] = df['date'].dt.is_quarter_end
    df['is_year_start'] = df['date'].dt.is_year_start
    df['is_year_end'] = df['date'].dt.is_year_end
    return df

def aggregate_time_series(df, date_col, value_col, freq, agg_func='sum'):
    """Agréger une série temporelle selon une fréquence donnée"""
    df = df.copy()
    df['date'] = pd.to_datetime(df[date_col])
    df = df.set_index('date')
    
    if agg_func == 'sum':
        return df.resample(freq)[value_col].sum().reset_index()
    elif agg_func == 'mean':
        return df.resample(freq)[value_col].mean().reset_index()
    elif agg_func == 'count':
        return df.resample(freq)[value_col].count().reset_index()
    elif agg_func == 'median':
        return df.resample(freq)[value_col].median().reset_index()
    else:
        return df.resample(freq)[value_col].sum().reset_index()

def create_prophet_dataset(df, date_col, value_col):
    """Créer un dataset au format Prophet (ds, y)"""
    prophet_df = pd.DataFrame()
    prophet_df['ds'] = pd.to_datetime(df[date_col])
    prophet_df['y'] = df[value_col]
    return prophet_df

def predict_with_prophet(df, horizon, seasonality='additive', changepoint_prior_scale=0.05, 
                        seasonality_prior_scale=10.0, weekly=False, monthly=True, yearly=True):
    """Effectuer une prévision avec Prophet"""
    model = Prophet(
        seasonality_mode=seasonality,
        weekly_seasonality=weekly,
        yearly_seasonality=yearly,
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_prior_scale=seasonality_prior_scale
    )
    
    if monthly:
        model.add_seasonality(name='monthly', period=30.4375, fourier_order=5)
    
    model.fit(df)
    
    future = model.make_future_dataframe(periods=horizon, freq='D')
    forecast = model.predict(future)
    
    return model, forecast

def predict_with_holt_winters(df, horizon, seasonal_periods=12):
    """Effectuer une prévision avec Holt-Winters"""
    model = ExponentialSmoothing(
        df['y'].values,
        seasonal_periods=seasonal_periods,
        trend='add',
        seasonal='add'
    )
    fitted_model = model.fit()
    forecast = fitted_model.forecast(horizon)
    
    # Créer un dataframe similaire à celui de Prophet pour la cohérence
    future_dates = pd.date_range(start=df['ds'].iloc[-1] + timedelta(days=1), periods=horizon)
    forecast_df = pd.DataFrame({
        'ds': future_dates,
        'yhat': forecast,
        'yhat_lower': forecast * 0.9,  # Approximation simplifiée des intervalles
        'yhat_upper': forecast * 1.1
    })
    
    # Concaténer avec les données historiques pour avoir un format cohérent
    historical = pd.DataFrame({
        'ds': df['ds'],
        'yhat': df['y'],
        'yhat_lower': df['y'] * 0.9,
        'yhat_upper': df['y'] * 1.1
    })
    
    full_forecast = pd.concat([historical, forecast_df])
    
    return fitted_model, full_forecast

def predict_with_xgboost(df, horizon, lookback=30):
    """Effectuer une prévision avec XGBoost"""
    # Préparation des données
    X, y = [], []
    data = df['y'].values
    
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i])
        y.append(data[i])
    
    X = np.array(X)
    y = np.array(y)
    
    # Division train/test
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    # Entraînement du modèle
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100)
    model.fit(X_train, y_train)
    
    # Préparation des futures entrées pour la prédiction
    last_x = data[-lookback:]
    forecasts = []
    
    # Prédiction itérative
    for i in range(horizon):
        next_pred = model.predict(np.array([last_x]))[0]
        forecasts.append(next_pred)
        last_x = np.append(last_x[1:], next_pred)
    
    # Créer un dataframe similaire à celui de Prophet pour la cohérence
    future_dates = pd.date_range(start=df['ds'].iloc[-1] + timedelta(days=1), periods=horizon)
    forecast_df = pd.DataFrame({
        'ds': future_dates,
        'yhat': forecasts,
        'yhat_lower': [f * 0.9 for f in forecasts],
        'yhat_upper': [f * 1.1 for f in forecasts]
    })
    
    # Concaténer avec les données historiques pour avoir un format cohérent
    historical = pd.DataFrame({
        'ds': df['ds'],
        'yhat': df['y'],
        'yhat_lower': df['y'] * 0.9,
        'yhat_upper': df['y'] * 1.1
    })
    
    full_forecast = pd.concat([historical, forecast_df])
    
    return model, full_forecast

# Titre principal
st.markdown('<div class="main-header">🔮 Prédiction des Recrutements</div>', unsafe_allow_html=True)

# --- Assurer la définition des onglets (évite l'erreur "tab3 is not defined" dans certains contextes) ---
if not all(n in globals() for n in ('tab1','tab2','tab3','tab4')):
    tab1, tab2, tab3, tab4 = st.tabs([
        "📁 Import des Données",
        "🧹 Nettoyage & Préparation",
        "📊 Visualisation",
        "🔮 Modélisation & Prédiction"
    ])

# ============================
# TAB 1: IMPORT DES DONNÉES
# ============================
with tab1:
    st.markdown('<div class="sub-header">Import des Données</div>', unsafe_allow_html=True)
    st.markdown(
        """Importez vos données de recrutement pour commencer l'analyse. Le fichier doit contenir au minimum:
        - Une colonne de date (demandes ou recrutements effectifs)
        - Une colonne de valeurs numériques (nombre de recrutements)"""
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choisissez votre fichier de données",
            type=['csv', 'xlsx', 'xls'],
            help="Formats supportés: CSV, Excel"
        )
        
        use_sample = st.checkbox("Ou utiliser des données d'exemple", value=False)
        
        if use_sample:
            st.info("Utilisation des données d'exemple pour la démonstration")
            # Créer des données d'exemple plus riches avec Direction et Poste
            date_range = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
            
            # Générer des directions et postes fictifs
            directions = ["Direction Technique", "Direction RH", "Direction Commerciale", 
                         "Direction Financière", "Direction Logistique"]
            
            postes = ["Ingénieur", "Technicien", "Chef de projet", "Responsable", 
                     "Assistant", "Analyste", "Développeur", "Gestionnaire", 
                     "Consultant", "Chargé de mission"]
            
            # Générer des données aléatoires mais cohérentes
            n_samples = 1000
            
            sample_data = pd.DataFrame({
                'Date de réception de la demande aprés validation de la DRH': 
                    pd.to_datetime(np.random.choice(date_range, n_samples)),
                'Direction concernée': 
                    np.random.choice(directions, n_samples, p=[0.4, 0.2, 0.2, 0.1, 0.1]),
                'Poste demandé': 
                    np.random.choice(postes, n_samples),
                'Statut de la demande': 
                    np.random.choice(["Clôture", "En cours", "Dépriorisé", "Annulé"], n_samples, p=[0.7, 0.1, 0.1, 0.1])
            })
            
            # Ajouter la date d'entrée effective uniquement pour les recrutements clôturés
            sample_data['Date d\'entrée effective du candidat'] = None
            mask_closed = sample_data['Statut de la demande'] == "Clôture"
            
            # Pour les demandes clôturées, ajouter une date d'entrée entre 30 et 120 jours après la réception
            for idx in sample_data[mask_closed].index:
                demand_date = sample_data.loc[idx, 'Date de réception de la demande aprés validation de la DRH']
                entry_delay = np.random.randint(30, 120)
                entry_date = demand_date + pd.Timedelta(days=entry_delay)
                # Ne pas dépasser aujourd'hui
                if entry_date <= pd.Timestamp.now():
                    sample_data.loc[idx, 'Date d\'entrée effective du candidat'] = entry_date
            
            st.session_state.data = sample_data
            st.success("✅ Données d'exemple chargées avec succès!")
            
        elif uploaded_file is not None:
            try:
                # Lecture du fichier (robuste : CSV utf-8/latin-1, puis Excel via BytesIO)
                fname = uploaded_file.name.lower()
                file_bytes = uploaded_file.read()

                if fname.endswith('.csv'):
                    # Essayer utf-8 puis latin-1
                    try:
                        data = pd.read_csv(io.StringIO(file_bytes.decode('utf-8')))
                    except UnicodeDecodeError:
                        data = pd.read_csv(io.StringIO(file_bytes.decode('latin-1')))
                elif fname.endswith(('.xls', '.xlsx')):
                    # Utiliser BytesIO pour pandas.read_excel (openpyxl recommandé)
                    try:
                        data = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
                    except Exception:
                        # fallback sans engine (pandas choisira)
                        data = pd.read_excel(io.BytesIO(file_bytes))
                else:
                    # Extension inconnue : tenter CSV puis Excel
                    try:
                        data = pd.read_csv(io.StringIO(file_bytes.decode('utf-8')))
                    except Exception:
                        try:
                            data = pd.read_csv(io.StringIO(file_bytes.decode('latin-1')))
                        except Exception:
                            data = pd.read_excel(io.BytesIO(file_bytes))

                st.session_state.data = data
                st.success(f"✅ Fichier '{uploaded_file.name}' importé avec succès!")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'import: {str(e)}")
                
        # NOUVEAU: Sélection de l'objectif de l'analyse
        if st.session_state.data is not None:
            st.markdown("### 🎯 Objectif de l'analyse")
            st.markdown("Choisissez ce que vous souhaitez analyser et prédire:")
            
            analysis_objective = st.radio(
                "Que souhaitez-vous analyser et prédire ?",
                options=["Les Demandes de Recrutement", "Les Recrutements Effectifs"],
                horizontal=True,
                index=1,  # Par défaut: Recrutements Effectifs
                key="analysis_objective"
            )
            
            # Stocker l'objectif dans st.session_state (REMOVED: already handled by the radio button key)
            
            # Afficher une explication selon le choix
            if analysis_objective == "Les Demandes de Recrutement":
                st.info("📝 Vous allez analyser et prédire les **demandes** de recrutement reçues. "
                        "L'analyse sera basée sur la date de réception des demandes.")
            else:
                st.info("👨‍💼 Vous allez analyser et prédire les **recrutements effectivement réalisés**. "
                        "L'analyse sera basée sur la date d'entrée effective des candidats.")
    
    # Afficher les informations si les données sont chargées
    if st.session_state.data is not None:
        with col2:
            st.metric("📄 Nombre de lignes", st.session_state.data.shape[0])
            st.metric("📊 Nombre de colonnes", st.session_state.data.shape[1])
            
            # Date minimale et maximale si une colonne de date est identifiée
            date_cols = [col for col in st.session_state.data.columns if 'date' in col.lower() or 'time' in col.lower() or 'jour' in col.lower()]
            if date_cols:
                try:
                    first_date = pd.to_datetime(st.session_state.data[date_cols[0]]).min()
                    last_date = pd.to_datetime(st.session_state.data[date_cols[0]]).max()
                    st.metric("📅 Période", f"{first_date.strftime('%d/%m/%Y')} - {last_date.strftime('%d/%m/%Y')}")
                except:
                    pass
        
        # Aperçu des données
        st.subheader("📋 Aperçu des données")
        st.dataframe(st.session_state.data.head(10))
        
        # Informations sur les colonnes
        st.subheader("ℹ️ Informations sur les colonnes")
        col_info = pd.DataFrame({
            'Type': st.session_state.data.dtypes,
            'Valeurs non-nulles': st.session_state.data.count(),
            'Valeurs nulles': st.session_state.data.isnull().sum(),
            '% Valeurs nulles': (st.session_state.data.isnull().sum() / len(st.session_state.data) * 100).round(2),
            'Valeurs uniques': [st.session_state.data[col].nunique() for col in st.session_state.data.columns]
        })
        st.dataframe(col_info)
        
        # Option de téléchargement des données
        csv = convert_df_to_csv(st.session_state.data)
        st.download_button(
            "📥 Télécharger les données",
            data=csv,
            file_name="donnees_recrutement.csv",
            mime="text/csv"
        )
    else:
        st.info("👆 Veuillez importer un fichier ou utiliser les données d'exemple pour commencer")

# ============================
# TAB 2: NETTOYAGE DES DONNÉES (AUTOMATISÉ)
# ============================
with tab2:
    st.markdown('<div class="sub-header">Nettoyage et Préparation des Données (Automatique)</div>', unsafe_allow_html=True)

    if st.session_state.data is not None:
        df_raw = st.session_state.data.copy()

        st.info("La préparation est automatisée : la colonne de date et le filtrage de statut sont choisis selon l'objectif sélectionné dans l'onglet Import.")

        # Identifier colonnes utiles
        all_cols = df_raw.columns.tolist()
        direction_cols = [c for c in all_cols if 'direction' in c.lower() or 'département' in c.lower()]
        poste_cols = [c for c in all_cols if 'poste' in c.lower() or 'fonction' in c.lower()]
        statut_cols = [c for c in all_cols if 'statut' in c.lower() or 'status' in c.lower() or 'state' in c.lower()]

        direction_col = direction_cols[0] if direction_cols else None
        poste_col = poste_cols[0] if poste_cols else None
        statut_col = statut_cols[0] if statut_cols else None

        # Choix d'agrégation (simplifié: M, Q, Y)
        st.subheader("⏱️ Fréquence d'agrégation")
        aggregation_freq = st.selectbox(
            "Fréquence d'agrégation",
            options=["Mensuelle (M)", "Trimestrielle (Q)", "Annuelle (Y)"],
            index=0,
            key="agg_freq_auto"
        )
        freq_map = {"Mensuelle (M)": "M", "Trimestrielle (Q)": "Q", "Annuelle (Y)": "Y"}
        freq = freq_map[aggregation_freq]
        st.session_state.freq = freq

        # Filtres contextuels sur direction/poste
        st.subheader("🔍 Filtres contextuels (optionnel)")
        if direction_col:
            dirs = sorted(df_raw[direction_col].dropna().unique().tolist())
            sel_dirs = st.multiselect("Filtrer par Direction", options=["Toutes"] + dirs, default=["Toutes"], key="auto_sel_dirs")
        else:
            sel_dirs = ["Toutes"]

        if poste_col:
            postes = sorted(df_raw[poste_col].dropna().unique().tolist())
            sel_postes = st.multiselect("Filtrer par Poste", options=["Tous"] + postes, default=["Tous"], key="auto_sel_postes")
        else:
            sel_postes = ["Tous"]

        # Période d'analyse
        st.subheader("📅 Période d'analyse (optionnelle)")
        # detect best date columns for the two objectives
        def detect_date_col_for_objective(df, objective):
            # prefer explicit names
            name_map = {
                "Les Demandes de Recrutement": ["date de réception", "date de reception", "date de reception de la demande", "date de réception de la demande aprés validation de la drh"],
                "Les Recrutements Effectifs": ["date d'entrée effective", "date d'entree effective", "date d'entrée effective du candidat", "date d'entrée du candidat", "date d'entrée"]
            }
            candidates = name_map.get(objective, [])
            for n in candidates:
                for c in df.columns:
                    if n in c.lower().replace('_',' '):
                        return c
            # fallback to any column with 'entrée' or 'réception' or 'effective' or 'reception'
            for c in df.columns:
                low = c.lower()
                if objective == "Les Demandes de Recrutement" and ("réception" in low or "reception" in low or "demande" in low):
                    return c
                if objective == "Les Recrutements Effectifs" and ("entrée" in low or "entree" in low or "effective" in low):
                    return c
            # fallback generic date
            for c in df.columns:
                if 'date' in c.lower():
                    return c
            return None

        objective = st.session_state.get('analysis_objective', "Les Recrutements Effectifs")
        date_col_auto = detect_date_col_for_objective(df_raw, objective)
        if date_col_auto is None:
            st.warning("Aucune colonne de date détectée automatiquement — la préparation risque d'échouer. Vérifiez vos colonnes.")
        else:
            try:
                df_raw[date_col_auto] = pd.to_datetime(df_raw[date_col_auto], errors='coerce')
                min_date_possible = df_raw[date_col_auto].min().date()
                max_date_possible = df_raw[date_col_auto].max().date()
                start = st.date_input("Date de début", value=min_date_possible, min_value=min_date_possible, max_value=max_date_possible, key="auto_start")
                end = st.date_input("Date de fin", value=max_date_possible, min_value=min_date_possible, max_value=max_date_possible, key="auto_end")
            except Exception as e:
                st.error(f"Erreur conversion date automatique: {e}")
                start = None
                end = None

        # Bouton : préparer
        if st.button("✅ Préparer les données automatiquement", type="primary"):
            with st.spinner("Préparation automatique en cours..."):
                try:
                    df = df_raw.copy()

                    # Determine objective-specific filters and date column
                    if objective == "Les Demandes de Recrutement":
                        used_date_col = detect_date_col_for_objective(df, objective) or date_col_auto
                        # Keep rows where statut contains any of the listed values (if statut_col detected)
                        valid_status_values = ["clôture", "cloture", "en cours", "dépriorisé", "depriorisé", "annulé", "annule"]
                        if statut_col:
                            mask_stat = df[statut_col].astype(str).str.strip().str.lower().fillna("")
                            df = df[mask_stat.isin(valid_status_values) | mask_stat.str.contains('|'.join([v for v in valid_status_values if ' ' in v]) , na=False) | mask_stat.str.len().gt(0) & mask_stat.isin(valid_status_values)]
                        # else: don't filter by status if none found (keep all)
                    else:  # Recrutements Effectifs
                        used_date_col = detect_date_col_for_objective(df, objective) or date_col_auto
                        # Keep rows where used_date_col is not null OR statut == 'Clôture' when status exists
                        if used_date_col:
                            df[used_date_col] = pd.to_datetime(df[used_date_col], errors='coerce')
                            mask_date = df[used_date_col].notna()
                            if statut_col:
                                mask_status_closed = df[statut_col].astype(str).str.strip().str.lower() == "clôture"
                                df = df[mask_date | mask_status_closed]
                            else:
                                df = df[mask_date]
                        else:
                            # if no date col, fallback to keeping only rows with statut == 'clôture' if statut_col exists
                            if statut_col:
                                df = df[df[statut_col].astype(str).str.strip().str.lower() == "clôture"]

                    # Apply temporal filter if available
                    if date_col_auto and start and end:
                        df = df[(pd.to_datetime(df[date_col_auto]).dt.date >= start) & (pd.to_datetime(df[date_col_auto]).dt.date <= end)]

                    # Apply context filters
                    if direction_col and sel_dirs and "Toutes" not in sel_dirs:
                        df = df[df[direction_col].isin(sel_dirs)]
                    if poste_col and sel_postes and "Tous" not in sel_postes:
                        df = df[df[poste_col].isin(sel_postes)]

                    # Final cleaned filtered dataframe (raw rows retained for proportions)
                    st.session_state.cleaned_data_filtered = df.copy()

                    # Aggregation: count rows per period using chosen date
                    if not date_col_auto:
                        raise RuntimeError("Aucune colonne de date détectée automatiquement pour l'agrégation.")
                    df_agg = df.copy()
                    df_agg['__agg_date'] = pd.to_datetime(df_agg[date_col_auto])
                    df_agg = df_agg.dropna(subset=['__agg_date'])
                    df_agg = df_agg.set_index('__agg_date').resample(freq).size().reset_index(name='value')
                    df_agg = df_agg.rename(columns={'__agg_date': 'date'})

                    # Generate time features for modelling convenience
                    st.session_state.cleaned_data_aggregated = generate_time_features(df_agg, 'date')
                    st.session_state.cleaned_data = st.session_state.cleaned_data_aggregated.copy()
                    st.session_state.direction_col = direction_col
                    st.session_state.poste_col = poste_col
                    st.session_state.date_col = 'date'
                    st.session_state.value_col = 'value'

                    st.success("✅ Données préparées automatiquement et agrégées avec succès!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Erreur lors de la préparation automatique: {e}")
    else:
        st.info("👆 Veuillez importer des données dans l'onglet Import pour lancer la préparation")

# ============================
# TAB 3: VISUALISATION (Miroir du Passé)
# ============================
with tab3:
    st.markdown('<div class="sub-header">Visualisation - Miroir du Passé</div>', unsafe_allow_html=True)

    if st.session_state.cleaned_data_aggregated is not None and st.session_state.cleaned_data_filtered is not None:
        agg = st.session_state.cleaned_data_aggregated.copy()
        raw = st.session_state.cleaned_data_filtered.copy()
        direction_col = st.session_state.direction_col
        poste_col = st.session_state.poste_col
        analysis_type = st.session_state.get('analysis_objective', "Recrutements")

        st.subheader(f"📈 Historique agrégé - {analysis_type}")
        fig = px.line(agg, x='date', y='value', title=f"Série historique ({analysis_type})", labels={'date': 'Date', 'value': 'Nombre'})
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Répartition Historique")

        cols = st.columns(2)
        with cols[0]:
            if direction_col and direction_col in raw.columns:
                dir_counts = raw[direction_col].value_counts().reset_index()
                dir_counts.columns = ['Direction', 'Nombre']
                fig_dir = px.bar(dir_counts.sort_values('Nombre', ascending=False), x='Direction', y='Nombre', title="Répartition historique par Direction", labels={'Nombre': 'Nombre'})
                st.plotly_chart(fig_dir, use_container_width=True)
            else:
                st.info("Aucune colonne 'Direction' détectée pour la répartition.")

        with cols[1]:
            if poste_col and poste_col in raw.columns:
                poste_counts = raw[poste_col].value_counts()
                top10 = poste_counts.head(10)
                others = poste_counts.iloc[10:].sum() if len(poste_counts) > 10 else 0
                top_series = pd.concat([top10, pd.Series({"Autres": others})])
                df_poste = top_series.reset_index()
                df_poste.columns = ['Poste', 'Nombre']
                fig_poste = px.bar(df_poste.sort_values('Nombre', ascending=False), x='Poste', y='Nombre', title="Top 10 des Postes (Historique)", labels={'Nombre': 'Nombre'})
                st.plotly_chart(fig_poste, use_container_width=True)
            else:
                st.info("Aucune colonne 'Poste' détectée pour la répartition.")
    else:
        st.info("👆 Veuillez préparer les données automatiquement dans l'onglet précédent pour visualiser l'historique.")

# ============================
# TAB 4: MODÉLISATION & PRÉDICTION (Confiance & Export)
# ============================
with tab4:
    st.markdown('<div class="sub-header">Modélisation et Prédiction Stratégique</div>', unsafe_allow_html=True)

    if st.session_state.cleaned_data_aggregated is None or st.session_state.cleaned_data_filtered is None:
        st.info("👆 Veuillez préparer les données automatiquement dans l'onglet Nettoyage & Préparation avant de modéliser et prédire")
    else:
        # Reminder of objective
        st.info(f"Vous êtes en train de prédire : **{st.session_state.get('analysis_objective','Recrutements')}**")

        data_to_model = st.session_state.cleaned_data_aggregated.copy()
        data_filtered = st.session_state.cleaned_data_filtered.copy()
        direction_col = st.session_state.direction_col
        poste_col = st.session_state.poste_col
        freq = st.session_state.freq

        # Forecast horizon selection (keep existing options)
        col1, col2 = st.columns(2)
        with col1:
            horizon_months = st.number_input("Horizon de prévision (mois)", min_value=1, max_value=60, value=12, step=1)
        with col2:
            model_type = st.selectbox("Type de Modèle", options=["Prophet","Holt-Winters","XGBoost"], index=0)

        if st.button("🚀 Lancer la prévision", type="primary"):
            with st.spinner("Entraînement et prévision en cours..."):
                try:
                    # Prepare prophet-like dataframe
                    prophet_df = create_prophet_dataset(data_to_model, 'date', 'value')

                    # Compute a simple holdout for MAPE: last 20% of time series
                    prophet_df_sorted = prophet_df.sort_values('ds').reset_index(drop=True)
                    n_total = len(prophet_df_sorted)
                    n_test = max(1, int(n_total * 0.2))
                    train_df = prophet_df_sorted.iloc[:-n_test]
                    test_df = prophet_df_sorted.iloc[-n_test:]

                    # Train and forecast according to selected model
                    if model_type == "Prophet":
                        model = Prophet()
                        model.fit(train_df)
                        future = model.make_future_dataframe(periods=len(test_df) + horizon_months*30, freq='D')
                        forecast_full = model.predict(future)
                    elif model_type == "Holt-Winters":
                        hw_df = train_df.rename(columns={'ds':'ds','y':'y'})
                        seasonal_periods = 12
                        hw_model, forecast_full = predict_with_holt_winters(hw_df, horizon=horizon_months*30, seasonal_periods=seasonal_periods)
                        model = hw_model
                    else:  # XGBoost
                        xgb_df = train_df.rename(columns={'ds':'ds','y':'y'})
                        lookback = min(max(7, int(len(xgb_df)*0.2)), 60)
                        xgb_model, forecast_full = predict_with_xgboost(xgb_df, horizon=horizon_months*30, lookback=lookback)
                        model = xgb_model

                    # Derive predictions for the test period for MAPE
                    # Align forecasts with test_df by matching dates
                    # forecast_full may contain historical + future; ensure columns ds & yhat exist
                    if 'yhat' not in forecast_full.columns and 'yhat' in forecast_full.columns:
                        pass
                    # Merge to compute MAPE on test period where actuals exist
                    pred_hist = forecast_full[['ds','yhat']].merge(test_df[['ds','y']], on='ds', how='inner')
                    if pred_hist.empty:
                        # fallback: use train fitted values vs train actuals
                        pred_hist = forecast_full[['ds','yhat']].merge(train_df[['ds','y']], on='ds', how='inner')

                    # Compute MAPE safely
                    def safe_mape(y_true, y_pred):
                        y_true = np.array(y_true, dtype=float)
                        y_pred = np.array(y_pred, dtype=float)
                        mask = y_true != 0
                        if mask.sum() == 0:
                            return np.nan
                        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

                    if not pred_hist.empty:
                        mape_val = safe_mape(pred_hist['y'], pred_hist['yhat'])
                    else:
                        mape_val = np.nan

                    st.metric("Marge d'Erreur Moyenne", f"± {round(mape_val,2)}%" if not np.isnan(mape_val) else "N/A")

                    # Build final forecast for the horizon (aggregate monthly)
                    # Ensure forecast_full has ds and yhat; take future portion beyond last historical date
                    last_hist = prophet_df_sorted['ds'].max()
                    if 'yhat' not in forecast_full.columns and 'yhat' not in forecast_full.columns:
                        st.warning("Prédictions indisponibles dans le format attendu.")
                        return

                    future_mask = pd.to_datetime(forecast_full['ds']) > pd.to_datetime(last_hist)
                    future_df = forecast_full.loc[future_mask, ['ds','yhat']].copy()
                    # Resample to monthly buckets
                    future_df['ds'] = pd.to_datetime(future_df['ds'])
                    future_df['year_month'] = future_df['ds'].dt.to_period('M').dt.to_timestamp()
                    monthly_pred = future_df.groupby('year_month')['yhat'].sum().reset_index().rename(columns={'year_month':'date','yhat':'predicted_total'})
                    monthly_pred['date'] = pd.to_datetime(monthly_pred['date'])
                    monthly_pred['predicted_total'] = monthly_pred['predicted_total'].round().astype(int)

                    st.subheader("🔮 Prévision mensuelle (volume total)")
                    st.dataframe(monthly_pred.rename(columns={'date':'Mois','predicted_total':f'Nombre prédit'}), use_container_width=True)

                    # PARTIE: Ventilation par Direction et Poste (proportions historiques)
                    # Compute historical proportions
                    results_dir = []
                    results_poste = []

                    # Use filtered raw rows to compute proportions
                    if direction_col and direction_col in data_filtered.columns:
                        dir_props = data_filtered[direction_col].value_counts(normalize=True)
                    else:
                        dir_props = pd.Series()

                    if poste_col and poste_col in data_filtered.columns:
                        poste_props = data_filtered[poste_col].value_counts(normalize=True)
                    else:
                        poste_props = pd.Series()

                    # For each month, allocate totals
                    for _, row in monthly_pred.iterrows():
                        month_label = row['date'].strftime('%b %Y')
                        total = row['predicted_total']
                        # directions
                        for d, p in dir_props.items():
                            results_dir.append({'Mois': month_label, 'Direction': d, 'Predicted': int(round(total * p)), 'Proportion': float(p*100)})
                        # postes
                        for p_name, p in poste_props.items():
                            results_poste.append({'Mois': month_label, 'Poste': p_name, 'Predicted': int(round(total * p)), 'Proportion': float(p*100)})

                    df_dir_forecast = pd.DataFrame(results_dir) if results_dir else pd.DataFrame(columns=['Mois','Direction','Predicted','Proportion'])
                    df_poste_forecast = pd.DataFrame(results_poste) if results_poste else pd.DataFrame(columns=['Mois','Poste','Predicted','Proportion'])

                    # Display summary charts
                    st.markdown("---")
                    st.subheader("📊 Ventilation prévisionnelle - Résumé")
                    colA, colB = st.columns(2)
                    with colA:
                        if not df_dir_forecast.empty:
                            dir_totals = df_dir_forecast.groupby('Direction')['Predicted'].sum().reset_index().sort_values('Predicted', ascending=False)
                            fig_dir = px.bar(dir_totals, x='Direction', y='Predicted', title='Total prévisionnel par Direction')
                            st.plotly_chart(fig_dir, use_container_width=True)
                        else:
                            st.info("Aucune donnée Direction pour la ventilation.")

                    with colB:
                        if not df_poste_forecast.empty:
                            poste_totals = df_poste_forecast.groupby('Poste')['Predicted'].sum().reset_index().sort_values('Predicted', ascending=False)
                            top_n = st.slider("Top N postes à afficher", 5, 20, 10)
                            fig_poste = px.bar(poste_totals.head(top_n), x='Poste', y='Predicted', title=f'Top {top_n} postes prévus')
                            st.plotly_chart(fig_poste, use_container_width=True)
                        else:
                            st.info("Aucune donnée Poste pour la ventilation.")

                    # Consolidated downloadable CSV: monthly_pred + aggregated direction/poste per month
                    # Build consolidated table: month, total, direction, direction_pred, poste, poste_pred
                    consolidated_rows = []
                    for _, mrow in monthly_pred.iterrows():
                        month_label = mrow['date'].strftime('%b %Y')
                        total = mrow['predicted_total']
                        # directions - create per direction rows
                        if not df_dir_forecast.empty:
                            dr = df_dir_forecast[df_dir_forecast['Mois'] == month_label]
                            for _, rr in dr.iterrows():
                                consolidated_rows.append({
                                    'Mois': month_label,
                                    'Niveau': 'Direction',
                                    'Dimension': rr['Direction'],
                                    'Predicted': rr['Predicted'],
                                    'Proportion (%)': rr['Proportion'],
                                    'Total_Month': total
                                })
                        # postes
                        if not df_poste_forecast.empty:
                            pr = df_poste_forecast[df_poste_forecast['Mois'] == month_label]
                            for _, rr in pr.iterrows():
                                consolidated_rows.append({
                                    'Mois': month_label,
                                    'Niveau': 'Poste',
                                    'Dimension': rr['Poste'],
                                    'Predicted': rr['Predicted'],
                                    'Proportion (%)': rr['Proportion'],
                                    'Total_Month': total
                                })

                    consolidated_df = pd.DataFrame(consolidated_rows)

                    if not consolidated_df.empty:
                        csv_bytes = convert_df_to_csv(consolidated_df)
                        st.download_button("📥 Télécharger la ventilation complète (CSV)", data=csv_bytes, file_name="ventilation_previsionnelle.csv", mime="text/csv")
                    else:
                        st.info("Aucune ventilation à télécharger (données manquantes).")

                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction: {e}")
                    st.exception(e)