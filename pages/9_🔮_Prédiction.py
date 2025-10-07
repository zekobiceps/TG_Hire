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
if 'forecast_results' not in st.session_state:
    st.session_state.forecast_results = None
if 'model' not in st.session_state:
    st.session_state.model = None
if 'forecast_horizon' not in st.session_state:
    st.session_state.forecast_horizon = 90
if 'selected_uid' not in st.session_state:
    st.session_state.selected_uid = None

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
st.markdown('<div class="main-header">🔮 Prédiction des Recrutements</div>', unsafe_allow_html=True)
st.markdown('---')

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
            # Créer des données d'exemple
            date_range = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
            values = [
                # Tendance de base avec saisonnalité
                10 + i*0.05 + 5*np.sin(i/30) + 
                # Effet mensuel (plus de recrutements en début de mois)
                (10 if i % 30 < 5 else 0) +
                # Effet trimestriel
                (15 if i % 90 < 10 else 0) +
                # Bruit aléatoire
                np.random.normal(0, 3)
                for i in range(len(date_range))
            ]
            
            # Regroupement par jour
            sample_data = pd.DataFrame({
                'date': date_range,
                'recrutements': [max(0, int(round(v))) for v in values]
            })
            
            # Agrégation par mois pour simplifier
            sample_data = sample_data.groupby(pd.Grouper(key='date', freq='M')).sum().reset_index()
            
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
        
        st.subheader("🔄 Sélection des colonnes principales")
        
        # Sélection des colonnes de date et valeur (montrer toutes les colonnes pour que l'utilisateur choisisse)
        col1, col2 = st.columns(2)
        
        with col1:
            all_cols = data_to_clean.columns.tolist()
            # Marquer les colonnes candidates date pour l'info utilisateur
            date_candidate_cols = [c for c in all_cols if 'date' in c.lower() or 'time' in c.lower() or 'jour' in c.lower()]
            default_date_index = all_cols.index(date_candidate_cols[0]) if date_candidate_cols else 0
            
            date_col = st.selectbox(
                "Sélectionnez la colonne de date (toutes les colonnes sont listées ci-dessous)",
                options=all_cols,
                index=default_date_index,
                key="date_col"
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
                        
                        # Agrégation temporelle
                        aggregated_data = aggregate_time_series(data_to_clean, agg_date_col, value_col, freq, agg_func)
                        
                        # Mettre à jour les données nettoyées dans l'état de session
                        st.session_state.cleaned_data = aggregated_data
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
    st.markdown('<div class="sub-header">Modélisation et Prédiction</div>', unsafe_allow_html=True)
    
    if st.session_state.cleaned_data is not None:
        data_to_model = st.session_state.cleaned_data
        
        st.subheader("⚙️ Configuration du Modèle")
        
        # Sélection de la colonne de date et de la colonne de valeur
        date_col = st.selectbox("Colonne de date", options=data_to_model.columns, index=0, key="model_date_col")
        value_col = st.selectbox("Colonne de valeur", options=data_to_model.columns, index=1, key="model_value_col")
        
        # Options pour définir la cible de prévision
        target_mode = st.selectbox(
            "Mode de définition de la période de prévision",
            options=["Horizon en jours", "Jusqu'à une date", "Pour un mois/année", "Pour une année"],
            index=0
        )

        if target_mode == "Horizon en jours":
            horizon_days = st.slider("Horizon de prévision (jours)", min_value=30, max_value=1825, value=180, step=30)
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
            horizon_days = (pd.to_datetime(target_date.date()) - pd.to_datetime(pd.to_datetime(data_to_model[date_col]).max().date())).days
        else:  # "Pour une année"
            years = list(range(datetime.now().year, datetime.now().year + 11))
            sel_year = st.selectbox("Année", options=years, index=1)
            target_date = datetime(sel_year, 12, 31).date()
            horizon_days = (pd.to_datetime(target_date) - pd.to_datetime(pd.to_datetime(data_to_model[date_col]).max().date())).days

        if horizon_days < 1:
            st.error("La date cible doit être postérieure à la dernière date historique. Ajustez la sélection.")
        st.session_state.forecast_horizon = int(horizon_days)
        
        # Choix du modèle
        model_type = st.selectbox(
            "Type de Modèle",
            options=["Prophet", "Holt-Winters", "XGBoost"],
            index=0
        )
        
        st.subheader("📊 Résultats de la Prédiction")
        
        if st.button("🔮 Effectuer la Prédiction", type="primary"):
            with st.spinner("Prédiction en cours..."):
                try:
                    if model_type == "Prophet":
                        # Préparer les données pour Prophet
                        prophet_data = create_prophet_dataset(data_to_model, date_col, value_col)
                        
                        # Effectuer la prédiction avec Prophet
                        model, forecast = predict_with_prophet(prophet_data, horizon=horizon_days)
                        
                        # Afficher les résultats
                        st.write(f"Prévisions avec Prophet pour les {horizon_days} prochains jours:")
                        st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(10))
                        
                        # Graphique des prévisions
                        fig_prophet = go.Figure()
                        fig_prophet.add_trace(go.Scatter(x=prophet_data['ds'], y=prophet_data['y'], mode='lines', name='Historique'))
                        fig_prophet.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Prévision', line=dict(color='red')))
                        fig_prophet.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Intervalle de Confiance Inférieur', line=dict(color='red', dash='dash')))
                        fig_prophet.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Intervalle de Confiance Supérieur', line=dict(color='red', dash='dash')))
                        
                        fig_prophet.update_layout(
                            title="Prévisions avec Prophet",
                            xaxis_title="Date",
                            yaxis_title="Nombre de Recrutements",
                            legend_title="Légende",
                            template="plotly_white"
                        )
                        
                        st.plotly_chart(fig_prophet, use_container_width=True)
                        
                        # Enregistrer le modèle dans l'état de session
                        st.session_state.model = model
                        st.success("Modèle Prophet entraîné et prévisions effectuées.")
                    
                    elif model_type == "Holt-Winters":
                        # Préparer les données (format attendu par Holt-Winters)
                        hw_data = data_to_model[[date_col, value_col]].rename(columns={date_col: 'ds', value_col: 'y'})
                        
                        # Effectuer la prévision avec Holt-Winters
                        model, forecast = predict_with_holt_winters(hw_data, horizon=horizon_days)
                        
                        # Afficher les résultats
                        st.write(f"Prévisions avec Holt-Winters pour les {horizon_days} prochains jours:")
                        st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(10))
                        
                        # Graphique des prévisions
                        fig_hw = go.Figure()
                        fig_hw.add_trace(go.Scatter(x=hw_data['ds'], y=hw_data['y'], mode='lines', name='Historique'))
                        fig_hw.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Prévision', line=dict(color='red')))
                        fig_hw.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Intervalle de Confiance Inférieur', line=dict(color='red', dash='dash')))
                        fig_hw.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Intervalle de Confiance Supérieur', line=dict(color='red', dash='dash')))
                        
                        fig_hw.update_layout(
                            title="Prévisions avec Holt-Winters",
                            xaxis_title="Date",
                            yaxis_title="Nombre de Recrutements",
                            legend_title="Légende",
                            template="plotly_white"
                        )
                        
                        st.plotly_chart(fig_hw, use_container_width=True)
                        
                        # Enregistrer le modèle dans l'état de session
                        st.session_state.model = model
                        st.success("Modèle Holt-Winters entraîné et prévisions effectuées.")
                    
                    else:  # XGBoost
                        # Préparer les données pour XGBoost (format supervisé)
                        xgb_data = data_to_model[[date_col, value_col]].rename(columns={date_col: 'ds', value_col: 'y'})
                        
                        # Effectuer la prévision avec XGBoost
                        model, forecast = predict_with_xgboost(xgb_data, horizon=horizon_days)
                        
                        # Afficher les résultats
                        st.write(f"Prévisions avec XGBoost pour les {horizon_days} prochains jours:")
                        st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(10))
                        
                        # Graphique des prévisions
                        fig_xgb = go.Figure()
                        fig_xgb.add_trace(go.Scatter(x=xgb_data['ds'], y=xgb_data['y'], mode='lines', name='Historique'))
                        fig_xgb.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Prévision', line=dict(color='red')))
                        fig_xgb.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Intervalle de Confiance Inférieur', line=dict(color='red', dash='dash')))
                        fig_xgb.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Intervalle de Confiance Supérieur', line=dict(color='red', dash='dash')))
                        
                        fig_xgb.update_layout(
                            title="Prévisions avec XGBoost",
                            xaxis_title="Date",
                            yaxis_title="Nombre de Recrutements",
                            legend_title="Légende",
                            template="plotly_white"
                        )
                        
                        st.plotly_chart(fig_xgb, use_container_width=True)
                        
                        # Enregistrer le modèle dans l'état de session
                        st.session_state.model = model
                        st.success("Modèle XGBoost entraîné et prévisions effectuées.")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction: {str(e)}")
    else:
        st.info("👆 Veuillez nettoyer et préparer les données dans l'onglet précédent avant de modéliser et prédire")