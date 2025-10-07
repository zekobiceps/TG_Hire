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
                        # Filtrage par date
                        if filter_start_date and filter_end_date:
                            data_to_clean = data_to_clean[
                                (data_to_clean[date_col].dt.date >= filter_start_date) &
                                (data_to_clean[date_col].dt.date <= filter_end_date)
                            ]
                        
                        # Agrégation temporelle
                        agg_data = aggregate_time_series(
                            data_to_clean,
                            date_col,
                            value_col,
                            freq,
                            agg_func
                        )
                        
                        # Renommer les colonnes pour plus de clarté
                        agg_data.columns = ['date', 'value']
                        
                        # Générer des caractéristiques temporelles
                        final_data = generate_time_features(agg_data, 'date')
                        
                        # Stocker les données nettoyées
                        st.session_state.cleaned_data = final_data
                        st.session_state.date_col = 'date'
                        st.session_state.value_col = 'value'
                        st.session_state.freq = freq
                        
                        st.success("✅ Données préparées avec succès!")
                        
                        # Afficher un aperçu
                        st.subheader("📋 Aperçu des données préparées")
                        st.dataframe(final_data.head(10))
                        
                        # Téléchargement des données nettoyées
                        csv_clean = convert_df_to_csv(final_data)
                        st.download_button(
                            "📥 Télécharger les données préparées",
                            data=csv_clean,
                            file_name="donnees_recrutement_preparees.csv",
                            mime="text/csv"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la préparation des données: {str(e)}")
            else:
                st.error("❌ Veuillez sélectionner les colonnes de date et valeur")
    else:
        st.warning("⚠️ Veuillez d'abord importer des données dans l'onglet 'Import des Données'")

# ============================
# TAB 3: VISUALISATION
# ============================
with tab3:
    st.markdown('<div class="sub-header">Visualisation et Analyse Exploratoire</div>', unsafe_allow_html=True)
    
    if st.session_state.cleaned_data is not None:
        df = st.session_state.cleaned_data
        date_col = st.session_state.date_col
        value_col = st.session_state.value_col
        
        # Métriques principales
        st.subheader("📈 Métriques clés")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total des recrutements",
                f"{df[value_col].sum():,.0f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Moyenne par période",
                f"{df[value_col].mean():.1f}",
                delta=f"{df[value_col].mean() - df[value_col].median():.1f}"
            )
        
        with col3:
            # Tendance récente (dernier trimestre vs avant-dernier)
            recent_mask = df[date_col] >= (df[date_col].max() - pd.Timedelta(days=90))
            older_mask = (df[date_col] >= (df[date_col].max() - pd.Timedelta(days=180))) & (df[date_col] < (df[date_col].max() - pd.Timedelta(days=90)))
            
            if sum(recent_mask) > 0 and sum(older_mask) > 0:
                recent_avg = df.loc[recent_mask, value_col].mean()
                older_avg = df.loc[older_mask, value_col].mean()
                delta_pct = ((recent_avg / older_avg) - 1) * 100 if older_avg > 0 else 0
                
                st.metric(
                    "Tendance récente",
                    f"{recent_avg:.1f}",
                    delta=f"{delta_pct:.1f}%"
                )
            else:
                st.metric(
                    "Tendance récente",
                    f"{df[value_col].iloc[-1]:.1f}",
                    delta=None
                )
        
        with col4:
            # Saisonnalité (écart-type / moyenne)
            cv = df[value_col].std() / df[value_col].mean() if df[value_col].mean() > 0 else 0
            st.metric(
                "Variabilité",
                f"{cv:.2f}",
                delta=None,
                help="Coefficient de variation (écart-type / moyenne). Plus il est élevé, plus la série est variable."
            )
        
        # Séries temporelles principales
        st.subheader("📊 Évolution temporelle")
        
        # Créer la figure
        fig = px.line(
            df,
            x=date_col,
            y=value_col,
            title=f"Évolution des recrutements au cours du temps",
            labels={date_col: "Date", value_col: "Nombre de recrutements"}
        )
        
        # Ajouter des points de données
        fig.add_trace(
            go.Scatter(
                x=df[date_col],
                y=df[value_col],
                mode='markers',
                marker=dict(size=8, opacity=0.6),
                name='Points de données'
            )
        )
        
        # Ajouter une ligne de tendance
        # Calculer les coefficients de régression linéaire
        x = np.arange(len(df))
        y = df[value_col].values
        coeffs = np.polyfit(x, y, 1)
        trend = np.polyval(coeffs, x)
        
        fig.add_trace(
            go.Scatter(
                x=df[date_col],
                y=trend,
                mode='lines',
                line=dict(color='red', dash='dash', width=2),
                name='Tendance'
            )
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Analyses supplémentaires
        col5, col6 = st.columns(2)
        
        with col5:
            st.subheader("📅 Analyse par mois")
            
            # Agrégation par mois
            monthly_data = df.groupby('month')[value_col].agg(['mean', 'sum']).reset_index()
            monthly_data['month_name'] = monthly_data['month'].apply(lambda x: datetime(2020, x, 1).strftime('%B'))
            
            # Graphique par mois
            fig_monthly = px.bar(
                monthly_data,
                x='month_name',
                y='mean',
                title="Moyenne des recrutements par mois",
                labels={'month_name': 'Mois', 'mean': 'Moyenne des recrutements'},
                category_orders={"month_name": [datetime(2020, i, 1).strftime('%B') for i in range(1, 13)]}
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col6:
            st.subheader("🔄 Analyse par trimestre")
            
            # Agrégation par trimestre
            quarterly_data = df.groupby('quarter')[value_col].agg(['mean', 'sum']).reset_index()
            
            # Graphique par trimestre
            fig_quarterly = px.bar(
                quarterly_data,
                x='quarter',
                y='mean',
                title="Moyenne des recrutements par trimestre",
                labels={'quarter': 'Trimestre', 'mean': 'Moyenne des recrutements'},
                text_auto='.1f'
            )
            st.plotly_chart(fig_quarterly, use_container_width=True)
        
        # Décomposition (tendance, saisonnalité, résidus)
        st.subheader("🔍 Décomposition de la série temporelle")
        
        # Créer une version au format Prophet pour faciliter les visualisations
        prophet_df = create_prophet_dataset(df, date_col, value_col)
        
        # Essayer de décomposer avec Prophet
        try:
            decomp_model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
            decomp_model.fit(prophet_df)
            
            # Extraire les composantes
            forecast = decomp_model.predict(prophet_df)
            
            # Afficher les composantes
            fig_comp = decomp_model.plot_components(forecast)
            st.pyplot(fig_comp)
            
        except Exception as e:
            st.warning(f"⚠️ Impossible de décomposer la série temporelle: {str(e)}")
            st.info("💡 Essayez avec un jeu de données plus grand ou une autre fréquence d'agrégation.")
        
    else:
        st.warning("⚠️ Veuillez d'abord préparer les données dans l'onglet 'Nettoyage & Préparation'")

# ============================
# TAB 4: MODÉLISATION & PRÉDICTION
# ============================
with tab4:
    st.markdown('<div class="sub-header">Modélisation et Prédiction</div>', unsafe_allow_html=True)
    
    if st.session_state.cleaned_data is not None:
        df = st.session_state.cleaned_data
        date_col = st.session_state.date_col
        value_col = st.session_state.value_col
        
        # Paramètres de prédiction
        st.subheader("⚙️ Paramètres de prédiction")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            horizon_days = st.slider(
                "Horizon de prévision (jours)",
                min_value=30,
                max_value=730,
                value=180,
                step=30,
                help="Nombre de jours à prédire dans le futur"
            )
            
            # Mettre à jour la session state
            st.session_state.forecast_horizon = horizon_days
        
        with col2:
            model_choice = st.selectbox(
                "Modèle de prévision",
                options=["Prophet", "Holt-Winters", "XGBoost"],
                index=0,
                help="Algorithme utilisé pour la prédiction"
            )
        
        with col3:
            if model_choice == "Prophet":
                seasonality_mode = st.selectbox(
                    "Mode de saisonnalité",
                    options=["additive", "multiplicative"],
                    index=0,
                    help="Mode de saisonnalité pour Prophet"
                )
            elif model_choice == "Holt-Winters":
                seasonal_periods = st.number_input(
                    "Périodes saisonnières",
                    min_value=1,
                    max_value=52,
                    value=12,
                    help="Nombre de périodes dans un cycle saisonnier"
                )
            elif model_choice == "XGBoost":
                lookback = st.slider(
                    "Fenêtre d'observation",
                    min_value=7,
                    max_value=90,
                    value=30,
                    help="Nombre de points passés à considérer pour la prédiction"
                )
        
        # Paramètres avancés
        with st.expander("Paramètres avancés"):
            if model_choice == "Prophet":
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    changepoint_prior_scale = st.slider(
                        "Changepoint Prior Scale",
                        min_value=0.001,
                        max_value=0.5,
                        value=0.05,
                        step=0.001,
                        format="%.3f",
                        help="Flexibilité de la tendance (plus élevé = plus flexible)"
                    )
                
                with col5:
                    seasonality_prior_scale = st.slider(
                        "Seasonality Prior Scale",
                        min_value=0.1,
                        max_value=20.0,
                        value=10.0,
                        step=0.1,
                        help="Flexibilité de la saisonnalité (plus élevé = plus flexible)"
                    )
                
                with col6:
                    col6_1, col6_2, col6_3 = st.columns(3)
                    
                    with col6_1:
                        weekly = st.checkbox("Hebdomadaire", value=False)
                    
                    with col6_2:
                        monthly = st.checkbox("Mensuelle", value=True)
                    
                    with col6_3:
                        yearly = st.checkbox("Annuelle", value=True)
        
        # Bouton pour lancer la prédiction
        if st.button("🚀 Lancer la prédiction", type="primary"):
            with st.spinner("Entraînement du modèle et génération des prévisions..."):
                # Créer un dataset au format Prophet
                prophet_df = create_prophet_dataset(df, date_col, value_col)
                
                try:
                    if model_choice == "Prophet":
                        model, forecast = predict_with_prophet(
                            prophet_df,
                            horizon_days,
                            seasonality=seasonality_mode,
                            changepoint_prior_scale=changepoint_prior_scale,
                            seasonality_prior_scale=seasonality_prior_scale,
                            weekly=weekly,
                            monthly=monthly,
                            yearly=yearly
                        )
                    elif model_choice == "Holt-Winters":
                        model, forecast = predict_with_holt_winters(
                            prophet_df,
                            horizon_days,
                            seasonal_periods=seasonal_periods
                        )
                    elif model_choice == "XGBoost":
                        model, forecast = predict_with_xgboost(
                            prophet_df,
                            horizon_days,
                            lookback=lookback
                        )
                    
                    # Stocker les résultats
                    st.session_state.model = model
                    st.session_state.forecast_results = forecast
                    
                    st.success("✅ Prédiction générée avec succès!")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction: {str(e)}")
        
        # Afficher les résultats de prédiction s'ils existent
        if st.session_state.forecast_results is not None:
            forecast = st.session_state.forecast_results
            
            st.subheader("📊 Résultats de la prédiction")
            
            # Métriques de prédiction
            future_data = forecast[forecast['ds'] > df[date_col].max()]
            
            col7, col8, col9 = st.columns(3)
            
            with col7:
                st.metric(
                    "Total prédit",
                    f"{future_data['yhat'].sum():.0f}",
                    help="Somme des recrutements prédits sur l'horizon"
                )
            
            with col8:
                st.metric(
                    "Moyenne prédite",
                    f"{future_data['yhat'].mean():.1f}",
                    delta=f"{future_data['yhat'].mean() - df[value_col].mean():.1f}",
                    help="Moyenne des recrutements prédits sur l'horizon"
                )
            
            with col9:
                # Tendance (comparaison entre la moyenne future et la moyenne passée)
                delta_pct = ((future_data['yhat'].mean() / df[value_col].mean()) - 1) * 100 if df[value_col].mean() > 0 else 0
                
                st.metric(
                    "Évolution tendancielle",
                    f"{delta_pct:.1f}%",
                    help="Variation entre la moyenne prédite et la moyenne historique"
                )
            
            # Graphique de prédiction
            st.subheader("📈 Graphique de la prédiction")
            
            # Préparer les données pour le graphique
            historical_dates = df[date_col]
            historical_values = df[value_col]
            
            fig_forecast = go.Figure()
            
            # Ajouter les données historiques
            fig_forecast.add_trace(
                go.Scatter(
                    x=historical_dates,
                    y=historical_values,
                    mode='lines+markers',
                    name='Données historiques',
                    line=dict(color='blue')
                )
            )
            
            # Ajouter les prédictions
            fig_forecast.add_trace(
                go.Scatter(
                    x=forecast['ds'],
                    y=forecast['yhat'],
                    mode='lines',
                    name='Prédiction',
                    line=dict(color='red')
                )
            )
            
            # Ajouter l'intervalle de confiance
            fig_forecast.add_trace(
                go.Scatter(
                    x=forecast['ds'].tolist() + forecast['ds'].tolist()[::-1],
                    y=forecast['yhat_upper'].tolist() + forecast['yhat_lower'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(255,0,0,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Intervalle de confiance'
                )
            )
            
            # Mettre à jour la mise en page
            fig_forecast.update_layout(
                title=f"Prédiction des recrutements - Horizon: {horizon_days} jours",
                xaxis_title="Date",
                yaxis_title="Nombre de recrutements",
                height=500,
                hovermode="x unified"
            )
            
            # Ajouter une ligne verticale pour séparer historique et prédiction
            fig_forecast.add_vline(
                x=df[date_col].max(),
                line_width=2,
                line_dash="dash",
                line_color="green",
                annotation_text="Début prédiction",
                annotation_position="top right"
            )
            
            st.plotly_chart(fig_forecast, use_container_width=True)
            
            # Tableau détaillé des prédictions
            st.subheader("📋 Détails des prédictions")
            
            # Filtrer pour n'afficher que les prédictions futures
            future_forecast = forecast[forecast['ds'] > df[date_col].max()].copy()
            
            # Préparer les colonnes à afficher
            future_forecast['Date'] = future_forecast['ds'].dt.strftime('%d/%m/%Y')
            future_forecast['Prédiction'] = future_forecast['yhat'].round(1)
            future_forecast['Borne inférieure'] = future_forecast['yhat_lower'].round(1)
            future_forecast['Borne supérieure'] = future_forecast['yhat_upper'].round(1)
            
            # Afficher le tableau
            st.dataframe(
                future_forecast[['Date', 'Prédiction', 'Borne inférieure', 'Borne supérieure']],
                use_container_width=True
            )
            
            # Téléchargement des prédictions
            csv_forecast = convert_df_to_csv(future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])
            st.download_button(
                "📥 Télécharger les prédictions",
                data=csv_forecast,
                file_name=f"predictions_recrutements_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Insights de la prédiction
            st.subheader("🧠 Insights")
            
            # Diviser en périodes pour analyse
            if len(future_forecast) > 0:
                # Période 1: 1-3 mois
                period1 = future_forecast[future_forecast['ds'] <= (df[date_col].max() + pd.Timedelta(days=90))]
                # Période 2: 4-6 mois
                period2 = future_forecast[(future_forecast['ds'] > (df[date_col].max() + pd.Timedelta(days=90))) &
                                        (future_forecast['ds'] <= (df[date_col].max() + pd.Timedelta(days=180)))]
                # Période 3: au-delà de 6 mois
                period3 = future_forecast[future_forecast['ds'] > (df[date_col].max() + pd.Timedelta(days=180))]
                
                col10, col11, col12 = st.columns(3)
                
                with col10:
                    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                    st.markdown("**Court terme (1-3 mois)**")
                    if len(period1) > 0:
                        st.metric("Total", f"{period1['yhat'].sum():.0f} recrutements")
                        st.metric("Moyenne", f"{period1['yhat'].mean():.1f} par période")
                        
                        # Tendance par rapport à l'historique récent
                        recent_hist = df[df[date_col] >= (df[date_col].max() - pd.Timedelta(days=90))]
                        if len(recent_hist) > 0:
                            delta_pct = ((period1['yhat'].mean() / recent_hist[value_col].mean()) - 1) * 100 if recent_hist[value_col].mean() > 0 else 0
                            st.metric("Évolution", f"{delta_pct:.1f}% vs. 3 derniers mois")
                    else:
                        st.write("Pas de données pour cette période")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col11:
                    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                    st.markdown("**Moyen terme (4-6 mois)**")
                    if len(period2) > 0:
                        st.metric("Total", f"{period2['yhat'].sum():.0f} recrutements")
                        st.metric("Moyenne", f"{period2['yhat'].mean():.1f} par période")
                        
                        # Comparaison avec le court terme
                        if len(period1) > 0:
                            delta_pct = ((period2['yhat'].mean() / period1['yhat'].mean()) - 1) * 100 if period1['yhat'].mean() > 0 else 0
                            st.metric("Évolution", f"{delta_pct:.1f}% vs. court terme")
                    else:
                        st.write("Pas de données pour cette période")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col12:
                    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                    st.markdown("**Long terme (>6 mois)**")
                    if len(period3) > 0:
                        st.metric("Total", f"{period3['yhat'].sum():.0f} recrutements")
                        st.metric("Moyenne", f"{period3['yhat'].mean():.1f} par période")
                        
                        # Comparaison avec le moyen terme
                        if len(period2) > 0:
                            delta_pct = ((period3['yhat'].mean() / period2['yhat'].mean()) - 1) * 100 if period2['yhat'].mean() > 0 else 0
                            st.metric("Évolution", f"{delta_pct:.1f}% vs. moyen terme")
                    else:
                        st.write("Pas de données pour cette période")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Analyses complémentaires
                with st.expander("Analyses complémentaires"):
                    # Trouver les pics de recrutement
                    peaks = future_forecast[future_forecast['yhat'] > future_forecast['yhat'].mean() + future_forecast['yhat'].std()]
                    
                    if len(peaks) > 0:
                        st.subheader("🔍 Pics de recrutement prévus")
                        
                        peaks_sorted = peaks.sort_values(by='yhat', ascending=False).head(5)
                        for _, row in peaks_sorted.iterrows():
                            st.markdown(f"📌 **{row['Date']}**: {row['Prédiction']:.0f} recrutements prévus")
                    
                    # Analyser les tendances par mois
                    future_forecast['month'] = future_forecast['ds'].dt.month
                    future_forecast['month_name'] = future_forecast['ds'].dt.strftime('%B')
                    
                    monthly_avg = future_forecast.groupby('month_name')['yhat'].mean().reset_index()
                    monthly_avg['month'] = pd.to_datetime(monthly_avg['month_name'], format='%B').dt.month
                    monthly_avg = monthly_avg.sort_values(by='month')
                    
                    st.subheader("📅 Tendance mensuelle")
                    
                    fig_monthly = px.bar(
                        monthly_avg,
                        x='month_name',
                        y='yhat',
                        title="Prédictions moyennes par mois",
                        labels={'month_name': 'Mois', 'yhat': 'Recrutements prévus (moyenne)'},
                        category_orders={"month_name": [datetime(2020, i, 1).strftime('%B') for i in range(1, 13)]}
                    )
                    st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.warning("⚠️ Veuillez d'abord préparer les données dans l'onglet 'Nettoyage & Préparation'")

# Footer
st.markdown("---")
st.markdown("### 📊 TGCC Prédiction des Recrutements | v1.0")
st.markdown("*Une application d'analyse et de prédiction pour optimiser la stratégie RH*")
