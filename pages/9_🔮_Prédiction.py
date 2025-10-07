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

# Création des onglets
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
# TAB 2: NETTOYAGE DES DONNÉES
# ============================
with tab2:
    st.markdown('<div class="sub-header">Nettoyage et Préparation des Données</div>', unsafe_allow_html=True)
    
    if st.session_state.data is not None:
        data_to_clean = st.session_state.data.copy()
        
        # Déterminer les colonnes de date selon l'objectif
        if 'analysis_objective' in st.session_state:
            if st.session_state.analysis_objective == "Les Demandes de Recrutement":
                primary_date_col_options = [col for col in data_to_clean.columns 
                                           if 'demande' in col.lower() or 'réception' in col.lower()]
                date_col_label = "Date de réception de la demande"
            else:  # Recrutements Effectifs
                primary_date_col_options = [col for col in data_to_clean.columns 
                                          if 'entrée' in col.lower() or 'effective' in col.lower()]
                date_col_label = "Date d'entrée effective"
                
            # Si aucune colonne correspondante n'est trouvée, utiliser toutes les colonnes date
            if not primary_date_col_options:
                primary_date_col_options = [col for col in data_to_clean.columns 
                                          if 'date' in col.lower() or 'time' in col.lower() or 'jour' in col.lower()]
        else:
            # Comportement par défaut si l'objectif n'est pas défini
            primary_date_col_options = [col for col in data_to_clean.columns 
                                      if 'date' in col.lower() or 'time' in col.lower() or 'jour' in col.lower()]
            date_col_label = "Colonne de date"
        
        st.subheader("🔄 Configuration de l'analyse")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sélection de la colonne de date principale
            if primary_date_col_options:
                date_col = st.selectbox(
                    f"Sélectionnez la {date_col_label}",
                    options=data_to_clean.columns,
                    index=data_to_clean.columns.get_loc(primary_date_col_options[0]) if primary_date_col_options[0] in data_to_clean.columns else 0,
                    key="clean_date_col"
                )
            else:
                date_col = st.selectbox(
                    f"Sélectionnez la {date_col_label}",
                    options=data_to_clean.columns,
                    key="clean_date_col"
                )
                
            # Convertir la colonne en datetime
            try:
                data_to_clean[date_col] = pd.to_datetime(data_to_clean[date_col])
                min_date = data_to_clean[date_col].min()
                max_date = data_to_clean[date_col].max()
                st.success(f"✓ Colonne de date valide: {min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}")
            except Exception as exc:
                st.warning(f"⚠️ La colonne sélectionnée ne semble pas être une date valide: {str(exc)}")
        
        with col2:
            all_cols = data_to_clean.columns.tolist()
            # Suggestion automatique : colonnes numériques en tête de liste dans le menu (mais laisser tout)
            numeric_cols = data_to_clean.select_dtypes(include=['number']).columns.tolist()
            # Build ordered options: numeric first (unique), then the rest
            ordered_cols = list(dict.fromkeys(numeric_cols + [c for c in all_cols if c not in numeric_cols]))
            default_value_index = 0 if ordered_cols else 0
            
            value_col = st.selectbox(
                "Sélectionnez la colonne de valeurs (recrutements) — vous pouvez choisir n'importe quelle colonne",
                options=ordered_cols,
                index=default_value_index,
                key="value_col"
            )
            
            # Essayer de convertir la colonne choisie en numérique pour la suite
            try:
                coerced = pd.to_numeric(data_to_clean[value_col], errors='coerce')
                non_null_count = coerced.notna().sum()
                total_count = len(coerced)
                if non_null_count == 0:
                    st.error("❌ La colonne sélectionnée ne contient aucune valeur numérique convertible. Choisissez une autre colonne.")
                elif non_null_count < total_count:
                    st.warning(f"⚠️ {total_count - non_null_count} valeurs sur {total_count} sont non-convertibles et seront traitées comme NaN.")
                else:
                    st.success("✓ Colonne de valeurs valide (numérique)")
            except Exception as exc:
                st.error(f"❌ Erreur lors de la vérification de la colonne de valeurs: {str(exc)}")
        
        # -----------------------
        # Colonne date de recrutement & filtre status
        # -----------------------
        st.markdown("**Paramètres liés aux recrutements confirmés**")
        recruit_date_candidates = [c for c in all_cols if ('entrée' in c.lower() or 'entrée' in c.lower() or 'effective' in c.lower() or 'effecti' in c.lower() or 'date' in c.lower())]
        # prefer common name
        preferred = None
        for name in ["date d'entrée effective du candidat", "date d'entrée", "date_entree", "date_entree_effective"]:
            for c in all_cols:
                if name.lower() in c.lower().replace('_',' '):
                    preferred = c
                    break
            if preferred:
                break

        recruit_date_default = all_cols.index(preferred) if preferred and preferred in all_cols else (all_cols.index(recruit_date_candidates[0]) if recruit_date_candidates else 0)
        recruit_date_col = st.selectbox(
            "Colonne de date à utiliser pour les recrutements (date d'entrée effective)",
            options=all_cols,
            index=recruit_date_default,
            help="Choisissez la colonne qui indique la date d'entrée effective du candidat (utilisée pour compter les recrutements confirmés)",
            key="recruit_date_col"
        )

        # Détecter colonne status/statu
        status_candidates = [c for c in all_cols if 'status' in c.lower() or 'statut' in c.lower() or 'state' in c.lower()]
        status_col = None
        if status_candidates:
            status_col = st.selectbox("Colonne de statut (filtrer sur les recrutements confirmés)", options=status_candidates, index=0, key="status_col")
            # proposer la valeur confirmée par défaut
            confirmed_default = "Clôture"
            confirmed_value = st.text_input("Valeur indiquant recrutement confirmé (insensible à la casse)", value=confirmed_default, key="confirmed_value")
        else:
            st.info("Aucune colonne 'status' détectée automatiquement. Vous pouvez filtrer manuellement après préparation si nécessaire.")
            confirmed_value = None
        # -----------------------
        
        # Paramètres d'agrégation
        st.subheader("⏱️ Paramètres d'agrégation temporelle")
        
        col3, col4 = st.columns(2)
        
        with col3:
            aggregation_freq = st.selectbox(
                "Fréquence d'agrégation",
                options=["Journalière (D)", "Hebdomadaire (W)", "Mensuelle (M)", "Trimestrielle (Q)", "Annuelle (Y)"],
                index=2,
                key="agg_freq"
            )
            
            # Mapper l'option à la fréquence pandas
            freq_map = {
                "Journalière (D)": "D",
                "Hebdomadaire (W)": "W",
                "Mensuelle (M)": "M",
                "Trimestrielle (Q)": "Q",
                "Annuelle (Y)": "Y"
            }
            freq = freq_map[aggregation_freq]
        
        with col4:
            aggregation_func = st.selectbox(
                "Fonction d'agrégation",
                options=["Somme", "Moyenne", "Compte", "Médiane"],
                index=0,
                key="agg_func"
            )
            
            # Mapper l'option à la fonction
            func_map = {
                "Somme": "sum",
                "Moyenne": "mean",
                "Compte": "count",
                "Médiane": "median"
            }
            agg_func = func_map[aggregation_func]
        
        # Filtrage des données
        st.subheader("🔍 Filtrage des données (optionnel)")
        
        col5, col6 = st.columns(2)
        
        with col5:
            if date_col and pd.api.types.is_datetime64_any_dtype(data_to_clean[date_col]):
                min_date_possible = data_to_clean[date_col].min().date()
                max_date_possible = data_to_clean[date_col].max().date()
                
                filter_start_date = st.date_input(
                    "Date de début",
                    value=min_date_possible,
                    min_value=min_date_possible,
                    max_value=max_date_possible
                )
        
        with col6:
            if date_col and pd.api.types.is_datetime64_any_dtype(data_to_clean[date_col]):
                filter_end_date = st.date_input(
                    "Date de fin",
                    value=max_date_possible,
                    min_value=min_date_possible,
                    max_value=max_date_possible
                )
        
        # Appliquer la préparation des données
        if st.button("✅ Préparer les données", type="primary"):
            if date_col and value_col:
                with st.spinner("Préparation des données en cours..."):
                    try:
                        # Filtrage par date (filtre global si demandé)
                        if filter_start_date and filter_end_date:
                            data_to_clean = data_to_clean[
                                (pd.to_datetime(data_to_clean[date_col]).dt.date >= filter_start_date) &
                                (pd.to_datetime(data_to_clean[date_col]).dt.date <= filter_end_date)
                            ]

                        # Filtrer les recrutements confirmés si une colonne status est choisie
                        if status_col and confirmed_value:
                            # comparaison insensible à la casse et strip
                            mask_status = data_to_clean[status_col].astype(str).str.strip().str.lower() == str(confirmed_value).strip().lower()
                            data_to_clean = data_to_clean[mask_status]
                        
                        # Choisir la colonne de date pour l'agrégation : préférer la date d'entrée effective
                        agg_date_col = recruit_date_col if recruit_date_col else date_col
                        data_to_clean[agg_date_col] = pd.to_datetime(data_to_clean[agg_date_col])

                        # --- Gestion robuste de la colonne de valeur avant agrégation ---
                        final_value_col = value_col
                        tmp_created = False

                        # Si la colonne choisie est numérique -> ok
                        if pd.api.types.is_numeric_dtype(data_to_clean[final_value_col]):
                            pass
                        else:
                            # Tenter de convertir en numérique
                            coerced = pd.to_numeric(data_to_clean[final_value_col], errors='coerce')
                            if coerced.notna().sum() > 0:
                                # créer une colonne temporaire numérique
                                tmp_col = "_tmp_value_numeric"
                                data_to_clean[tmp_col] = coerced
                                final_value_col = tmp_col
                                tmp_created = True
                            else:
                                # si utilisateur a fourni une colonne status, créer un indicateur recruté
                                if status_col and confirmed_value:
                                    tmp_col = "_tmp_recruited_flag"
                                    data_to_clean[tmp_col] = (data_to_clean[status_col].astype(str).str.strip().str.lower() == str(confirmed_value).strip().lower()).astype(int)
                                    final_value_col = tmp_col
                                    tmp_created = True
                                else:
                                    # si la fonction d'agrégation est 'count', on peut continuer (count fonctionne sur toute colonne)
                                    if agg_func != 'count':
                                        raise RuntimeError(
                                            "La colonne choisie n'est pas numérique et ne peut pas être agrégée avec la fonction sélectionnée. "
                                            "Choisissez une colonne numérique, sélectionnez 'Compte' comme fonction d'agrégation, ou indiquez une colonne 'status' pour créer un indicateur de recrutement."
                                        )

                        # Agrégation temporelle (utiliser final_value_col)
                        aggregated_data = aggregate_time_series(data_to_clean, agg_date_col, final_value_col, freq, agg_func)

                        # Si on a utilisé une colonne temporaire, renommer la colonne agrégée pour garder le nom original value_col
                        if tmp_created:
                            # aggregated_data aura deux colonnes : 'date' et tmp_col (ou le nom final_value_col)
                            cols = aggregated_data.columns.tolist()
                            if len(cols) >= 2:
                                aggregated_data = aggregated_data.rename(columns={cols[1]: value_col})
                        
                        # Mettre à jour les données nettoyées dans l'état de session
                        # Stocker les données filtrées (brutes) et la série agrégée explicitement
                        st.session_state.cleaned_data_filtered = data_to_clean.copy()
                        # Normaliser noms de colonnes agrégées
                        try:
                            aggregated_data.columns = ['date', 'value']
                        except Exception:
                            pass
                        st.session_state.cleaned_data = aggregated_data.copy()
                        st.session_state.cleaned_data_aggregated = aggregated_data.copy()
                        # Conserver métadonnées utiles pour les onglets suivants
                        st.session_state.date_col = 'date'
                        st.session_state.value_col = 'value'
                        st.session_state.freq = freq

                        st.success("✅ Données préparées avec succès!")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la préparation des données: {str(e)}")
        
        # Affichage des données nettoyées
        if st.session_state.cleaned_data is not None:
            st.markdown("### Données nettoyées et agrégées")
            st.dataframe(st.session_state.cleaned_data.head(10))
            
            # Option de téléchargement des données nettoyées
            csv_cleaned = convert_df_to_csv(st.session_state.cleaned_data)
            st.download_button(
                "📥 Télécharger les données nettoyées",
                data=csv_cleaned,
                file_name="donnees_recrutement_nettoyees.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Veuillez importer des données dans l'onglet précédent pour les nettoyer et les préparer")

# ============================
# TAB 3: VISUALISATION
# ============================
with tab3:
    st.markdown('<div class="sub-header">Visualisation des Données</div>', unsafe_allow_html=True)
    
    if st.session_state.cleaned_data is not None:
        data_to_viz = st.session_state.cleaned_data
        
        st.subheader("📈 Visualisation des tendances")
        
        # Sélection de la colonne de date et de la colonne de valeur
        date_col = st.selectbox("Colonne de date", options=data_to_viz.columns, index=0, key="viz_date_col")
        value_col = st.selectbox("Colonne de valeur", options=data_to_viz.columns, index=1, key="viz_value_col")
        
        # Type de graphique
        chart_type = st.selectbox(
            "Type de graphique",
            options=["Ligne", "Barres", "Aires", "Scatter"],
            index=0
        )
        
        # Couleurs personnalisées pour les graphiques
        color = st.color_picker("Choisissez une couleur pour les graphiques", "#1f77b4")
        
        # Graphique de tendance
        fig = go.Figure()
        
        if chart_type == "Ligne":
            fig.add_trace(go.Scatter(x=data_to_viz[date_col], y=data_to_viz[value_col], mode='lines', name='Tendance', line=dict(color=color, width=2)))
        elif chart_type == "Barres":
            fig.add_trace(go.Bar(x=data_to_viz[date_col], y=data_to_viz[value_col], name='Tendance', marker_color=color))
        elif chart_type == "Aires":
            fig.add_trace(go.Scatter(x=data_to_viz[date_col], y=data_to_viz[value_col], mode='lines', name='Tendance', fill='tozeroy', line=dict(color=color, width=2)))
        else:  # Scatter
            fig.add_trace(go.Scatter(x=data_to_viz[date_col], y=data_to_viz[value_col], mode='markers', name='Tendance', marker=dict(color=color, size=8)))
        
        # Mise en forme du graphique
        fig.update_layout(
            title="Tendance des Recrutements dans le Temps",
            xaxis_title="Date",
            yaxis_title="Nombre de Recrutements",
            legend_title="Légende",
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Visualisation des valeurs manquantes
        st.subheader("📉 Visualisation des Valeurs Manquantes")
        
        if data_to_viz.isnull().sum().sum() > 0:
            # Graphique des valeurs manquantes
            fig_missing = px.imshow(data_to_viz.isnull(), 
                                    labels=dict(x="Colonnes", y="Lignes", color="Valeurs Manquantes"),
                                    x=data_to_viz.columns,
                                    y=data_to_viz.index,
                                    color_continuous_scale="Blues",
                                    title="Carte de Chaleur des Valeurs Manquantes")
            st.plotly_chart(fig_missing, use_container_width=True)
        else:
            st.info("Aucune valeur manquante détectée dans les données.")
        
        # Analyse de corrélation
        st.subheader("🔍 Analyse de Corrélation")
        
        if data_to_viz.select_dtypes(include=['number']).shape[1] > 1:
            # Matrice de corrélation
            corr_matrix = data_to_viz.select_dtypes(include=['number']).corr()
            
            # Graphique de la matrice de corrélation
            fig_corr = px.imshow(corr_matrix, 
                                labels=dict(x="Variables", y="Variables", color="Corrélation"),
                                x=corr_matrix.columns,
                                y=corr_matrix.index,
                                color_continuous_scale="RdBu",
                                title="Matrice de Corrélation")
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Pas assez de variables numériques pour effectuer une analyse de corrélation.")
    else:
        st.info("👆 Veuillez nettoyer et préparer les données dans l'onglet précédent pour les visualiser")

# ============================
# TAB 4: MODÉLISATION & PRÉDICTION
# ============================
with tab4:
    st.markdown('<div class="sub-header">Modélisation et Prédiction Stratégique</div>', unsafe_allow_html=True)
    
    if 'cleaned_data_aggregated' in st.session_state and st.session_state.cleaned_data_aggregated is not None:
        data_to_model = st.session_state.cleaned_data_aggregated
        data_filtered = st.session_state.cleaned_data_filtered if 'cleaned_data_filtered' in st.session_state else None
        
        # Variables contextuelles
        direction_col = st.session_state.direction_col if 'direction_col' in st.session_state else None
        poste_col = st.session_state.poste_col if 'poste_col' in st.session_state else None
        date_col = st.session_state.date_col if 'date_col' in st.session_state else 'date'
        value_col = st.session_state.value_col if 'value_col' in st.session_state else 'value'
        
        # Titre dynamique selon l'objectif
        if 'analysis_objective' in st.session_state:
            analysis_type = st.session_state.analysis_objective
        else:
            analysis_type = "Recrutements"
        
        st.subheader("⚙️ Configuration de la prévision")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Options pour définir la cible de prévision
            target_mode = st.selectbox(
                "Mode de définition de la période de prévision",
                options=["Horizon en jours", "Jusqu'à une date", "Pour un mois/année", "Pour une année"],
                index=2  # Par défaut: "Pour un mois/année"
            )

            if target_mode == "Horizon en jours":
                horizon_days = st.slider("Horizon de prévision (jours)", min_value=30, max_value=1825, value=365, step=30)
            elif target_mode == "Jusqu'à une date":
                last_hist_date = pd.to_datetime(data_to_model[date_col]).max().date()
                target_date = st.date_input("Date cible (prévoir jusqu'à)", value=last_hist_date + timedelta(days=180), min_value=last_hist_date + timedelta(days=1))
                horizon_days = (pd.to_datetime(target_date) - pd.to_datetime(last_hist_date)).days
            elif target_mode == "Pour un mois/année":
                years = list(range(datetime.now().year, datetime.now().year + 11))
                sel_year = st.selectbox("Année", options=years, index=1)
                months = list(range(1,13))
                sel_month = st.selectbox("Mois", options=months, index=0, format_func=lambda m: datetime(2000, m, 1).strftime('%B'))
                # prévoir jusqu'au dernier jour du mois sélectionné
                target_date = datetime(sel_year, sel_month, 1) + pd.offsets.MonthEnd(0)
                last_hist_date = pd.to_datetime(data_to_model[date_col]).max().date()
                horizon_days = (pd.to_datetime(target_date.date()) - pd.to_datetime(last_hist_date)).days
            else:  # "Pour une année"
                years = list(range(datetime.now().year, datetime.now().year + 11))
                sel_year = st.selectbox("Année", options=years, index=1)
                target_date = datetime(sel_year, 12, 31).date()
                last_hist_date = pd.to_datetime(data_to_model[date_col]).max().date()
                horizon_days = (pd.to_datetime(target_date) - pd.to_datetime(last_hist_date)).days

            if horizon_days < 1:
                st.error("La date cible doit être postérieure à la dernière date historique.")
            else:
                st.session_state.forecast_horizon = int(horizon_days)
        
        with col2:
            # Choix du modèle
            model_type = st.selectbox(
                "Type de Modèle",
                options=["Prophet", "Holt-Winters", "XGBoost"],
                index=0
            )
            
            # Options spécifiques selon le modèle
            if model_type == "Prophet":
                seasonality = st.selectbox(
                    "Mode de saisonnalité",
                    options=["additive", "multiplicative"],
                    index=0,
                    help="Additive: variations constantes, Multiplicative: variations proportionnelles"
                )
                
                # Options avancées dans un expander
                with st.expander("Options avancées"):
                    changepoint_prior_scale = st.slider(
                        "Flexibilité de tendance (changepoint_prior_scale)",
                        min_value=0.001, max_value=0.5, value=0.05, step=0.001,
                        format="%.3f",
                        help="Plus la valeur est élevée, plus la tendance est flexible"
                    )
                    
                    seasonality_prior_scale = st.slider(
                        "Amplitude de saisonnalité (seasonality_prior_scale)",
                        min_value=0.1, max_value=20.0, value=10.0, step=0.1,
                        format="%.1f",
                        help="Plus la valeur est élevée, plus la saisonnalité est forte"
                    )
                    
                    include_seasons = st.multiselect(
                        "Inclure les saisonnalités",
                        options=["Hebdomadaire", "Mensuelle", "Annuelle"],
                        default=["Mensuelle", "Annuelle"],
                        help="Sélectionnez les saisonnalités à inclure dans le modèle"
                    )
                    
                    weekly = "Hebdomadaire" in include_seasons
                    monthly = "Mensuelle" in include_seasons
                    yearly = "Annuelle" in include_seasons
        
        # Section prévision
        st.subheader("🔮 Prévision du volume global")
        
        if st.button("🚀 Lancer la prévision", type="primary"):
            with st.spinner("Calcul des prévisions en cours..."):
                try:
                    # PARTIE 1: PRÉDICTION DU VOLUME GLOBAL
                    if model_type == "Prophet":
                        # Préparer les données pour Prophet
                        prophet_data = create_prophet_dataset(data_to_model, date_col, value_col)
                        
                        # Effectuer la prédiction avec Prophet et les paramètres choisis
                        model, forecast = predict_with_prophet(
                            prophet_data, 
                            horizon=horizon_days,
                            seasonality=seasonality,
                            changepoint_prior_scale=changepoint_prior_scale,
                            seasonality_prior_scale=seasonality_prior_scale,
                            weekly=weekly,
                            monthly=monthly,
                            yearly=yearly
                        )
                        
                        # Enregistrer les résultats
                        st.session_state.forecast_results = forecast
                        st.session_state.model = model
                        st.session_state.model_type = "Prophet"
                        
                    elif model_type == "Holt-Winters":
                        # Préparer les données pour Holt-Winters
                        hw_data = data_to_model[[date_col, value_col]].rename(columns={date_col: 'ds', value_col: 'y'})
                        
                        # Déterminer seasonal_periods selon la fréquence
                        if st.session_state.freq == "D":
                            seasonal_periods = 7  # hebdomadaire
                        elif st.session_state.freq == "W":
                            seasonal_periods = 52  # annuelle
                        elif st.session_state.freq == "M":
                            seasonal_periods = 12  # annuelle
                        elif st.session_state.freq == "Q":
                            seasonal_periods = 4  # annuelle
                        else:
                            seasonal_periods = 1  # pas de saisonnalité
                            
                        # Effectuer la prédiction avec Holt-Winters
                        model, forecast = predict_with_holt_winters(
                            hw_data, 
                            horizon=horizon_days,
                            seasonal_periods=seasonal_periods
                        )
                        
                        # Enregistrer les résultats
                        st.session_state.forecast_results = forecast
                        st.session_state.model = model
                        st.session_state.model_type = "Holt-Winters"
                        
                    else:  # XGBoost
                        # Préparer les données pour XGBoost
                        xgb_data = data_to_model[[date_col, value_col]].rename(columns={date_col: 'ds', value_col: 'y'})
                        
                        # Calculer lookback approprié (environ 20% des données, min 7, max 60)
                        lookback = min(max(7, int(len(xgb_data) * 0.2)), 60)
                        
                        # Effectuer la prédiction avec XGBoost
                        model, forecast = predict_with_xgboost(
                            xgb_data, 
                            horizon=horizon_days,
                            lookback=lookback
                        )
                        
                        # Enregistrer les résultats
                        st.session_state.forecast_results = forecast
                        st.session_state.model = model
                        st.session_state.model_type = "XGBoost"
                    
                    # Afficher le graphique de prévision du volume
                    st.success(f"✅ Prévision du volume global réalisée pour les {horizon_days} prochains jours")
                    
                    # Graphique des prévisions
                    fig_forecast = go.Figure()
                    
                    # Période historique
                    historical_dates = forecast[forecast['ds'] <= pd.to_datetime(last_hist_date)]['ds']
                    historical_values = forecast[forecast['ds'] <= pd.to_datetime(last_hist_date)]['yhat']
                    
                    fig_forecast.add_trace(go.Scatter(
                        x=historical_dates,
                        y=historical_values,
                        mode='lines',
                        name='Historique',
                        line=dict(color='blue')
                    ))
                    
                    # Période de prévision
                    future_dates = forecast[forecast['ds'] > pd.to_datetime(last_hist_date)]['ds']
                    future_values = forecast[forecast['ds'] > pd.to_datetime(last_hist_date)]['yhat']
                    future_lower = forecast[forecast['ds'] > pd.to_datetime(last_hist_date)]['yhat_lower']
                    future_upper = forecast[forecast['ds'] > pd.to_datetime(last_hist_date)]['yhat_upper']
                    
                    fig_forecast.add_trace(go.Scatter(
                        x=future_dates,
                        y=future_values,
                        mode='lines',
                        name='Prévision',
                        line=dict(color='red')
                    ))
                    
                    # Intervalle de confiance
                    fig_forecast.add_trace(go.Scatter(
                        x=future_dates,
                        y=future_upper,
                        mode='lines',
                        name='Borne supérieure',
                        line=dict(color='rgba(255, 0, 0, 0.2)', dash='dash')
                    ))
                    
                    fig_forecast.add_trace(go.Scatter(
                        x=future_dates,
                        y=future_lower,
                        mode='lines',
                        name='Borne inférieure',
                        line=dict(color='rgba(255, 0, 0, 0.2)', dash='dash'),
                        fill='tonexty'  # Remplir l'aire entre les bornes
                    ))
                    
                    fig_forecast.update_layout(
                        title=f"Prévision du nombre de {analysis_type} avec {model_type}",
                        xaxis_title="Date",
                        yaxis_title=f"Nombre de {analysis_type}",
                        legend_title="Légende",
                        template="plotly_white"
                    )
                    
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    
                    # PARTIE 2: CALCUL DES PROPORTIONS ET RÉPARTITION STRATÉGIQUE
                    if data_filtered is not None and (direction_col or poste_col):
                        st.markdown("---")
                        st.subheader("📊 Ventilation de la prédiction")
                        st.markdown(f"Répartition prévisionnelle des {analysis_type} basée sur les proportions historiques")
                        
                        # Obtenir uniquement les prévisions futures (après la date max historique)
                        future_forecast = forecast[forecast['ds'] > pd.to_datetime(last_hist_date)].copy()
                        
                        # Agréger par mois pour une meilleure lisibilité
                        future_forecast['year_month'] = future_forecast['ds'].dt.strftime('%Y-%m')
                        monthly_forecast = future_forecast.groupby('year_month')['yhat'].sum().reset_index()
                        monthly_forecast = monthly_forecast.rename(columns={'yhat': 'predicted_volume'})
                        
                        # Ajouter la date formatée pour l'affichage
                        monthly_forecast['month_display'] = pd.to_datetime(monthly_forecast['year_month'] + '-01').dt.strftime('%b %Y')
                        
                        # Afficher la prévision mensuelle
                        st.markdown("#### Prévision mensuelle du volume")
                        
                        # Formater en tableau
                        monthly_table = monthly_forecast.copy()
                        monthly_table['predicted_volume'] = monthly_table['predicted_volume'].round().astype(int)
                        monthly_table = monthly_table.rename(columns={
                            'month_display': 'Mois',
                            'predicted_volume': f'Nombre de {analysis_type}'
                        })
                        
                        st.dataframe(
                            monthly_table[['Mois', f'Nombre de {analysis_type}']],
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Onglets pour les différentes ventilations
                        ventilation_tabs = st.tabs(["Par Direction", "Par Poste"])
                        
                        # VENTILATION PAR DIRECTION
                        with ventilation_tabs[0]:
                            if direction_col and direction_col in data_filtered.columns:
                                # Calculer les proportions historiques par direction
                                dir_counts = data_filtered[direction_col].value_counts()
                                dir_proportions = dir_counts / dir_counts.sum()
                                
                                # Créer un DataFrame pour les résultats
                                dir_results = []
                                
                                for _, row in monthly_forecast.iterrows():
                                    month = row['month_display']
                                    total_volume = row['predicted_volume']
                                    
                                    for direction, proportion in dir_proportions.items():
                                        # Calculer le nombre prévu pour cette direction ce mois-ci
                                        predicted_count = total_volume * proportion
                                        
                                        dir_results.append({
                                            'month': month,
                                            'direction': direction,
                                            'predicted_count': predicted_count,
                                            'proportion': proportion * 100
                                        })
                                
                                dir_results_df = pd.DataFrame(dir_results)
                                
                                # Créer le graphique de répartition par direction
                                months_to_show = min(len(monthly_forecast), 6)  # Limiter à 6 mois pour la lisibilité
                                
                                # Agréger par direction pour tous les mois sélectionnés
                                dir_summary = dir_results_df.groupby('direction')['predicted_count'].sum().reset_index()
                                dir_summary = dir_summary.sort_values('predicted_count', ascending=False)
                                
                                fig_dir_forecast = px.bar(
                                    dir_summary,
                                    x='predicted_count',
                                    y='direction',
                                    orientation='h',
                                    labels={
                                        'predicted_count': f'Nombre de {analysis_type} prévus',
                                        'direction': 'Direction'
                                    },
                                    title=f"Prévision des {analysis_type} par Direction",
                                    color='predicted_count',
                                    color_continuous_scale=px.colors.sequential.Blues
                                )
                                
                                fig_dir_forecast.update_layout(
                                    yaxis={'categoryorder':'total ascending'},
                                    showlegend=False
                                )
                                
                                st.plotly_chart(fig_dir_forecast, use_container_width=True)
                                
                                # Tableau détaillé par mois
                                with st.expander("Voir le détail mois par mois"):
                                    for month in monthly_forecast['month_display'].unique():
                                        st.markdown(f"##### {month}")
                                        
                                        month_data = dir_results_df[dir_results_df['month'] == month].copy()
                                        month_data['predicted_count'] = month_data['predicted_count'].round().astype(int)
                                        month_data = month_data.sort_values('predicted_count', ascending=False)
                                        
                                        display_df = month_data[['direction', 'predicted_count', 'proportion']]
                                        display_df.columns = ['Direction', f'Nombre de {analysis_type}', 'Pourcentage (%)']
                                        display_df['Pourcentage (%)'] = display_df['Pourcentage (%)'].round(1)
                                        
                                        st.dataframe(display_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("Les données ne contiennent pas d'information de Direction pour la ventilation")
                        
                        # VENTILATION PAR POSTE
                        with ventilation_tabs[1]:
                            if poste_col and poste_col in data_filtered.columns:
                                # Paramètres de filtrage des postes
                                top_n_postes = st.slider(
                                    "Nombre de postes à afficher:",
                                    min_value=5,
                                    max_value=20,
                                    value=10,
                                    step=1
                                )
                                
                                search_poste = st.text_input(
                                    "Rechercher un poste spécifique:",
                                    placeholder="Ex: Ingénieur, Technicien..."
                                )
                                
                                # Calculer les proportions historiques par poste
                                poste_counts = data_filtered[poste_col].value_counts()
                                poste_proportions = poste_counts / poste_counts.sum()
                                
                                # Créer un DataFrame pour les résultats
                                poste_results = []
                                
                                for _, row in monthly_forecast.iterrows():
                                    month = row['month_display']
                                    total_volume = row['predicted_volume']
                                    
                                    for poste, proportion in poste_proportions.items():
                                        # Calculer le nombre prévu pour ce poste ce mois-ci
                                        predicted_count = total_volume * proportion
                                        
                                        poste_results.append({
                                            'month': month,
                                            'poste': poste,
                                            'predicted_count': predicted_count,
                                            'proportion': proportion * 100
                                        })
                                
                                poste_results_df = pd.DataFrame(poste_results)
                                
                                # Filtrer les résultats selon le critère de recherche
                                if search_poste:
                                    search_results = poste_results_df[
                                        poste_results_df['poste'].str.lower().str.contains(search_poste.lower())
                                    ]
                                    
                                    if len(search_results) > 0:
                                        st.markdown(f"##### Résultats pour '{search_poste}'")
                                        
                                        # Agréger les résultats de recherche par poste
                                        search_summary = search_results.groupby('poste')['predicted_count'].sum().reset_index()
                                        search_summary['predicted_count'] = search_summary['predicted_count'].round().astype(int)
                                        search_summary = search_summary.sort_values('predicted_count', ascending=False)
                                        
                                        st.dataframe(
                                            search_summary.rename(
                                                columns={'poste': 'Poste', 'predicted_count': f'Nombre de {analysis_type} prévus'}
                                            ),
                                            hide_index=True,
                                            use_container_width=True
                                        )
                                    else:
                                        st.warning(f"Aucun poste correspondant à '{search_poste}' n'a été trouvé")
                                
                                # Agréger par poste pour tous les mois
                                poste_summary = poste_results_df.groupby('poste')['predicted_count'].sum().reset_index()
                                poste_summary = poste_summary.sort_values('predicted_count', ascending=False)
                                
                                # Graphique des top N postes
                                top_postes = poste_summary.head(top_n_postes)
                                
                                fig_poste_forecast = px.bar(
                                    top_postes,
                                    x='predicted_count',
                                    y='poste',
                                    orientation='h',
                                    labels={
                                        'predicted_count': f'Nombre de {analysis_type} prévus',
                                        'poste': 'Poste'
                                    },
                                    title=f"Top {top_n_postes} des postes prévus",
                                    color='predicted_count',
                                    color_continuous_scale=px.colors.sequential.Greens
                                )
                                
                                fig_poste_forecast.update_layout(
                                    yaxis={'categoryorder':'total ascending'},
                                    showlegend=False
                                )
                                
                                st.plotly_chart(fig_poste_forecast, use_container_width=True)
                                
                                # Tableau détaillé
                                with st.expander(f"Voir le détail des {top_n_postes} postes les plus demandés"):
                                    display_df = top_postes.copy()
                                    display_df['predicted_count'] = display_df['predicted_count'].round().astype(int)
                                    
                                    # Calculer la proportion
                                    total = display_df['predicted_count'].sum()
                                    display_df['proportion'] = (display_df['predicted_count'] / total * 100).round(1)
                                    
                                    display_df.columns = ['Poste', f'Nombre de {analysis_type}', 'Pourcentage (%)']
                                    
                                    st.dataframe(display_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("Les données ne contiennent pas d'information de Poste pour la ventilation")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction: {str(e)}")
                    st.exception(e)
    else:
        st.info("👆 Veuillez préparer les données dans l'onglet précédent avant de modéliser et prédire")