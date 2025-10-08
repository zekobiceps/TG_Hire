import streamlit as st
from datetime import datetime
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

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Prédiction de Recrutements - TGCC",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 600; margin-bottom: 1rem; }
    .sub-header { font-size: 1.8rem; font-weight: 500; margin-bottom: 0.5rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 4px; padding: 10px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #e6f3ff; border-bottom: 2px solid #1e88e5; }
</style>
""", unsafe_allow_html=True)

# --- INITIALISATION DES VARIABLES DE SESSION ---
if 'data' not in st.session_state: st.session_state.data = None
if 'cleaned_data_filtered' not in st.session_state: st.session_state.cleaned_data_filtered = None
if 'time_series_data' not in st.session_state: st.session_state.time_series_data = None
if 'analysis_objective' not in st.session_state: st.session_state.analysis_objective = "Les Recrutements Effectifs"
if 'direction_col' not in st.session_state: st.session_state.direction_col = None
if 'poste_col' not in st.session_state: st.session_state.poste_col = None
if 'date_col' not in st.session_state: st.session_state.date_col = None
if 'freq' not in st.session_state: st.session_state.freq = 'M'
if 'selected_freq' not in st.session_state: st.session_state.selected_freq = 'Mensuelle'

# --- FONCTIONS UTILITAIRES ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def apply_temporal_guard(df, date_col):
    current_date = datetime.now().date()
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    future_mask = df[date_col].dt.date > current_date
    n_future = future_mask.sum()
    df_filtered = df[~future_mask]
    if n_future > 0:
        st.warning(f"⚠️ **Garde-Fou Temporel**: {n_future} entrées avec des dates futures ont été supprimées.")
    return df_filtered, n_future

def detect_columns(df):
    columns = df.columns.tolist()
    direction_cols = [c for c in columns if any(word in c.lower() for word in ['direction', 'département', 'dept', 'service'])]
    direction_col = direction_cols[0] if direction_cols else None
    poste_cols = [c for c in columns if any(word in c.lower() for word in ['poste', 'fonction', 'job', 'métier', 'emploi'])]
    poste_col = poste_cols[0] if poste_cols else None
    statut_cols = [c for c in columns if any(word in c.lower() for word in ['statut', 'status', 'état', 'state'])]
    statut_col = statut_cols[0] if statut_cols else None
    return direction_col, poste_col, statut_col

def get_date_column_for_objective(df, objective):
    columns = df.columns.tolist()
    if objective == "Les Demandes de Recrutement":
        for col in columns:
            if "réception" in col.lower() and "demande" in col.lower(): return col
        for col in columns:
            if "réception" in col.lower() or ("date" in col.lower() and "demande" in col.lower()): return col
    else:
        for col in columns:
            if "entrée" in col.lower() and "effective" in col.lower(): return col
        for col in columns:
            if "entrée" in col.lower() or "effective" in col.lower(): return col
    date_cols = [c for c in columns if 'date' in c.lower()]
    return date_cols[0] if date_cols else None

def apply_business_logic_filter(df, objective, statut_col):
    df = df.copy()
    if objective == "Les Demandes de Recrutement":
        if statut_col and statut_col in df.columns:
            valid_statuses = ["clôture", "cloture", "en cours", "dépriorisé", "depriorise", "annulé", "annule"]
            mask = df[statut_col].astype(str).str.lower().str.strip().isin(valid_statuses)
            df_filtered = df[mask]
            if (len(df) - len(df_filtered)) > 0:
                st.info(f"📝 **Filtrage Demandes**: {len(df) - len(df_filtered)} lignes exclues (statut non pertinent).")
        else:
            df_filtered = df
    else: 
        date_col = get_date_column_for_objective(df, objective)
        if date_col:
            mask = df[date_col].notna()
            df_filtered = df[mask]
            if (len(df) - len(df_filtered)) > 0:
                st.info(f"👨‍💼 **Filtrage Recrutements**: {len(df) - len(df_filtered)} lignes exclues (pas de date d'entrée effective).")
        else:
            df_filtered = df
    return df_filtered

def create_time_series(df, date_col, freq):
    df = df.copy()
    df['date_parsed'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['date_parsed'])
    df_agg = df.set_index('date_parsed').resample(freq).size().reset_index(name='volume')
    df_agg = df_agg.rename(columns={'date_parsed': 'date'})
    return df_agg

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if mask.sum() == 0: return np.nan
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

# --- FONCTIONS DE PRÉDICTION ADAPTATIVES ---
def predict_with_prophet(df, horizon_periods, freq):
    prophet_df = df.rename(columns={'date': 'ds', 'volume': 'y'})
    model = Prophet(yearly_seasonality='auto', weekly_seasonality=False, daily_seasonality=False)
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=horizon_periods, freq=freq)
    forecast = model.predict(future)
    return model, forecast

def predict_with_holt_winters(df, horizon_periods, freq):
    try:
        seasonal_map = {'M': 12, 'Q': 4, '2Q': 2, 'Y': 1}
        seasonal_periods = seasonal_map.get(freq)
        
        if seasonal_periods is None or len(df) < 2 * seasonal_periods:
            model = ExponentialSmoothing(df['volume'].values, trend='add').fit()
        else:
            model = ExponentialSmoothing(df['volume'].values, trend='add', seasonal='add', seasonal_periods=seasonal_periods).fit()
            
        forecast_values = model.forecast(horizon_periods)
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_periods + 1, freq=freq)[1:]
        forecast_df = pd.DataFrame({'ds': list(df['date']) + list(future_dates), 'yhat': list(df['volume']) + list(forecast_values)})
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur Holt-Winters: {e}")
        return None, None

def predict_with_xgboost(df, horizon_periods, freq, lookback=3):
    try:
        data = df['volume'].values
        effective_lookback = min(lookback, len(data) - 1)
        if effective_lookback < 1:
            st.error("Pas assez de données pour XGBoost.")
            return None, None
        X, y = [], []
        for i in range(effective_lookback, len(data)):
            X.append(data[i-effective_lookback:i])
            y.append(data[i])
        X, y = np.array(X), np.array(y)
        model = xgb.XGBRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        last_sequence = data[-effective_lookback:]
        forecasts = []
        for _ in range(horizon_periods):
            next_pred = model.predict(np.array([last_sequence]))[0]
            forecasts.append(max(0, next_pred))
            last_sequence = np.append(last_sequence[1:], next_pred)
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_periods + 1, freq=freq)[1:]
        forecast_df = pd.DataFrame({'ds': list(df['date']) + list(future_dates), 'yhat': list(df['volume']) + forecasts})
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur XGBoost: {e}")
        return None, None

# --- INTERFACE UTILISATEUR ---
st.markdown("# 🔮 Prédiction des Recrutements")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📁 Import", "🧹 Préparation", "📊 Visualisation", "🔮 Prédiction"])

with tab1:
    st.header("📁 Import des Données")
    # ... (Code de l'onglet 1 inchangé)
    # Pour la concision, le code de l'onglet 1 est omis ici mais doit être conservé dans votre fichier final.

with tab2:
    st.header("🧹 Préparation des Données")
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("👆 Veuillez d'abord importer des données.")
    else:
        objective = st.session_state.get('analysis_objective', "Les Recrutements Effectifs")
        st.info(f"🤖 **Préparation automatisée** basée sur l'objectif: **{objective}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⏱️ Fréquence d'agrégation")
            freq_options = {
                "Mensuelle": "M",
                "Trimestrielle": "Q",
                "Semestrielle": "2Q",
                "Annuelle": "Y"
            }
            selected_freq_name = st.selectbox("Choisissez la fréquence:", options=list(freq_options.keys()), index=0)
            freq = freq_options[selected_freq_name]
        
        # ... (Le reste du code de l'onglet 2 est inchangé, mais assurez-vous de sauvegarder la fréquence)
        
        if st.button("🚀 Préparer les données", type="primary", use_container_width=True):
            with st.spinner("Préparation en cours..."):
                # ... (Votre logique de préparation de données)
                # À la fin du bloc try, après avoir créé la time_series, ajoutez ces lignes :
                st.session_state.freq = freq
                st.session_state.selected_freq = selected_freq_name
                # ...
                pass # Placeholder

with tab3:
    st.header("📊 Visualisation")
    # ... (Code de l'onglet 3 inchangé)
    # Pour la concision, le code de l'onglet 3 est omis ici mais doit être conservé dans votre fichier final.

with tab4:
    st.header("🔮 Modélisation & Prédiction")
    
    if 'time_series_data' not in st.session_state or st.session_state.time_series_data is None or st.session_state.time_series_data.empty:
        st.info("👆 Veuillez d'abord préparer les données dans l'onglet Préparation.")
    else:
        objective = st.session_state.get('analysis_objective', 'Recrutements')
        st.info(f"🎯 **Vous prédisez : {objective}**")
        
        time_series = st.session_state.time_series_data
        raw_data = st.session_state.cleaned_data_filtered
        freq = st.session_state.get('freq', 'M')
        selected_freq_name = st.session_state.get('selected_freq', 'Mensuelle')

        col1, col2 = st.columns(2)
        
        with col1:
            horizon_label_map = {
                "Mensuelle": "mois", "Trimestrielle": "trimestres",
                "Semestrielle": "semestres", "Annuelle": "années"
            }
            horizon_label = f"🔮 Horizon ({horizon_label_map.get(selected_freq_name, 'périodes')})"
            default_horizon = 12 if freq == 'M' else 8 if freq == 'Q' else 6 if freq == '2Q' else 3
            
            horizon_periods = st.number_input(
                horizon_label, min_value=1, max_value=48, value=default_horizon,
                help=f"Nombre de {horizon_label_map.get(selected_freq_name, 'périodes')} à prédire."
            )
        
        with col2:
            model_type = st.selectbox("🤖 Algorithme", options=["Prophet", "Holt-Winters", "XGBoost"], index=0)
        
        if st.button("🚀 Lancer la prédiction", type="primary", use_container_width=True):
            with st.spinner(f"🤖 Entraînement du modèle {model_type} en cours..."):
                try:
                    # --- Étape 1: Évaluation du modèle pour le score MAPE ---
                    n_total = len(time_series)
                    n_test = max(1, int(n_total * 0.2)) if n_total > 5 else 1
                    train_data = time_series.iloc[:-n_test].copy()
                    test_data = time_series.iloc[-n_test:].copy()
                    
                    mape_score = np.nan
                    if not train_data.empty:
                        if model_type == "Prophet": temp_model, temp_forecast = predict_with_prophet(train_data, n_test, freq)
                        elif model_type == "Holt-Winters": temp_model, temp_forecast = predict_with_holt_winters(train_data, n_test, freq)
                        else: temp_model, temp_forecast = predict_with_xgboost(train_data, n_test, freq)
                        
                        if temp_forecast is not None:
                            merged = pd.merge(test_data, temp_forecast, left_on='date', right_on='ds', how='left')
                            mape_score = calculate_mape(merged['volume'].values, merged['yhat'].values)

                    st.subheader("📊 Score de Confiance")
                    # ... (affichage des métriques)

                    # --- Étape 2: Prédiction finale sur 100% des données ---
                    st.info("Ré-entraînement du modèle sur 100% des données pour la prédiction finale...")
                    if model_type == "Prophet": final_model, final_forecast = predict_with_prophet(time_series, horizon_periods, freq)
                    elif model_type == "Holt-Winters": final_model, final_forecast = predict_with_holt_winters(time_series, horizon_periods, freq)
                    else: final_model, final_forecast = predict_with_xgboost(time_series, horizon_periods, freq)

                    if final_model is None or final_forecast is None:
                        st.error("❌ Échec de la prédiction finale."); st.stop()

                    last_date = time_series['date'].max()
                    future_predictions = final_forecast[final_forecast['ds'] > last_date].copy()

                    if not future_predictions.empty:
                        forecast_df = future_predictions[['ds', 'yhat']].rename(columns={'ds': 'date'})
                        forecast_df['predicted_volume'] = forecast_df['yhat'].round().astype(int).apply(lambda x: max(0, x))
                        forecast_df = forecast_df.head(horizon_periods)

                        st.subheader("🔮 Prévisions")
                        display_forecast = forecast_df.copy()
                        if freq == 'Y': display_forecast['Période'] = display_forecast['date'].dt.strftime('%Y')
                        elif freq == 'Q': display_forecast['Période'] = display_forecast['date'].dt.to_period('Q').astype(str)
                        elif freq == '2Q': display_forecast['Période'] = display_forecast['date'].dt.to_period('2Q').astype(str).str.replace('Q2', 'S1').str.replace('Q4', 'S2')
                        else: display_forecast['Période'] = display_forecast['date'].dt.strftime('%B %Y')
                        
                        display_forecast = display_forecast[['Période', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})
                        st.dataframe(display_forecast, use_container_width=True)

                        fig_pred = go.Figure()
                        fig_pred.add_trace(go.Scatter(x=time_series['date'], y=time_series['volume'], mode='lines+markers', name='Historique'))
                        fig_pred.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['predicted_volume'], mode='lines+markers', name='Prédictions', line=dict(dash='dash')))
                        fig_pred.update_layout(title=f"Prédictions {model_type} - {objective}", height=400)
                        st.plotly_chart(fig_pred, use_container_width=True)
                        
                        # ... (Le reste du code pour la ventilation et l'export reste identique) ...
                        st.success(f"✅ **Prédiction terminée avec succès!**")
                    else:
                        st.warning("⚠️ Aucune prédiction future générée.")

                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction : {str(e)}"); st.exception(e)
