import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
import xgboost as xgb
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
import io
from sklearn.metrics import mean_absolute_percentage_error
import re
import gspread
from google.oauth2 import service_account
warnings.filterwarnings('ignore')

# Fonctions Google Sheets
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

def predict_with_prophet(df, horizon_periods, freq):
    """Prédiction avec Prophet (adaptée à la fréquence)"""
    prophet_df = df.rename(columns={'date': 'ds', 'volume': 'y'})
    model = Prophet(
        yearly_seasonality=True if freq == 'M' or freq == 'Q' or freq == '2Q' else False,
        weekly_seasonality=False,
        daily_seasonality=False
    )
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=horizon_periods, freq=freq)
    forecast = model.predict(future)
    return model, forecast

def predict_with_holt_winters(df, horizon_periods, freq):
    """Prédiction avec Holt-Winters (adaptée à la fréquence)"""
    try:
        seasonal_map = {'M': 12, 'Q': 4, '2Q': 2, 'Y': 1}
        seasonal_periods = seasonal_map.get(freq)
        
        if seasonal_periods is None or len(df) < 2 * seasonal_periods:
            model = ExponentialSmoothing(df['volume'].values, trend='add').fit()
        else:
            model = ExponentialSmoothing(
                df['volume'].values,
                trend='add',
                seasonal='add',
                seasonal_periods=seasonal_periods
            ).fit()
            
        forecast_values = model.forecast(horizon_periods)
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_periods + 1, freq=freq)[1:]
        forecast_df = pd.DataFrame({'ds': list(df['date']) + list(future_dates), 'yhat': list(df['volume']) + list(forecast_values)})
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur Holt-Winters: {e}")
        return None, None

def predict_with_xgboost(df, horizon_periods, freq, lookback=3):
    """Prédiction avec XGBoost (adaptée à la fréquence)"""
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

def predict_with_random_forest(df, horizon_periods, freq, lookback=12):
    """Prédiction avec Random Forest (adaptée à la fréquence)"""
    try:
        data = df['volume'].values
        effective_lookback = min(lookback, len(data) - 1)
        if effective_lookback < 1:
            st.error("Pas assez de données pour Random Forest.")
            return None, None
        
        # Préparation des données (séquences)
        X, y = [], []
        for i in range(effective_lookback, len(data)):
            X.append(data[i-effective_lookback:i])
            y.append(data[i])
        
        X, y = np.array(X), np.array(y)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Prédictions
        last_sequence = data[-effective_lookback:]
        forecasts = []
        for _ in range(horizon_periods):
            next_pred = model.predict(np.array([last_sequence]))[0]
            forecasts.append(max(0, next_pred))
            last_sequence = np.append(last_sequence[1:], next_pred)
        
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_periods + 1, freq=freq)[1:]
        forecast_df = pd.DataFrame({'ds': list(df['date']) + list(future_dates), 'yhat': list(df['volume']) + list(forecasts)})
        
        return model, forecast_df
    except Exception as e:
        st.error(f"Erreur Random Forest: {e}")
        return None, None

def predict_with_sarima(df, horizon_periods, freq):
    """Prédiction avec SARIMA/SARIMAX (adaptée à la fréquence)"""
    try:
        # Paramètres selon la fréquence
        if freq == 'M':  # Mensuel
            order = (1, 1, 1)
            seasonal_order = (1, 1, 1, 12)
        elif freq == 'Q':  # Trimestriel
            order = (1, 1, 1)
            seasonal_order = (1, 1, 1, 4)
        elif freq == '2Q':  # Semestriel
            order = (1, 1, 1)
            seasonal_order = (1, 1, 1, 2)
        else:  # Annuel ou autre
            order = (1, 1, 1)
            seasonal_order = (0, 0, 0, 0)
        
        # Ajustement du modèle
        model = SARIMAX(
            df['volume'], 
            order=order, 
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        fitted_model = model.fit(disp=False)
        
        # Prédiction
        forecasts = fitted_model.forecast(steps=horizon_periods)
        forecasts = np.clip(forecasts, 0, None)  # Pas de valeurs négatives
        future_dates = pd.date_range(start=df['date'].max(), periods=horizon_periods + 1, freq=freq)[1:]
        
        forecast_df = pd.DataFrame({
            'ds': list(df['date']) + list(future_dates),
            'yhat': list(df['volume']) + list(forecasts)
        })
        
        return fitted_model, forecast_df
    except Exception as e:
        st.error(f"Erreur SARIMA: {e}")
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
    st.markdown("Importez vos données de recrutement depuis Google Sheets ou Excel, ou utilisez les données d'exemple.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔗 Google Sheets")
        # URL par défaut du Google Sheet (identique à celle utilisée dans le reporting)
        default_sheet = "https://docs.google.com/spreadsheets/d/1hvghSMjcbdY8yNZOWqALBpgMdLWB5CxVJCDwEm6JULI/edit?gid=785271056#gid=785271056"
        gs_url = st.text_input("URL Google Sheet", value=default_sheet, key="gsheet_url_prediction")

        if st.button("🔁 Charger depuis Google Sheets",
                    help="Charger les données depuis Google Sheets",
                    width='stretch'):

            try:
                # Utiliser la fonction de chargement Google Sheets
                df_synced = load_data_from_google_sheets(gs_url)

                if df_synced is not None and len(df_synced) > 0:
                    st.session_state.data = df_synced
                    nb_lignes = len(df_synced)
                    nb_colonnes = len(df_synced.columns)
                    
                    # Détecter la période des données
                    periode = "période inconnue"
                    date_cols = [col for col in df_synced.columns if 'date' in col.lower()]
                    if date_cols:
                        try:
                            dates_values = pd.to_datetime(df_synced[date_cols[0]], errors='coerce')
                            if not isinstance(dates_values, pd.Series):
                                dates_values = pd.Series([dates_values])
                            valid_dates = dates_values.dropna()
                            if len(valid_dates) > 0:
                                min_date = str(valid_dates.min())[:7]  # Format YYYY-MM
                                max_date = str(valid_dates.max())[:7]  # Format YYYY-MM
                                periode = f"{min_date} - {max_date}"
                        except:
                            pass
                    
                    st.success(f"✅ Chargement Google Sheets réussi ! ({nb_lignes} lignes, {nb_colonnes} colonnes, période: {periode})")
                    # Tableau supprimé selon les demandes de l'utilisateur
                else:
                    st.warning("⚠️ Aucune donnée trouvée dans la feuille Google Sheets.")

            except Exception as e:
                err_str = str(e)
                st.error(f"Erreur lors du chargement: {err_str}")

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
        st.subheader("📊 Fichier Excel/CSV")
        # Upload du fichier
        uploaded_file = st.file_uploader(
            "Choisissez votre fichier de données",
            type=['csv', 'xlsx', 'xls'],
            help="Formats supportés: CSV, Excel"
        )

        # Option données d'exemple supprimée selon les demandes de l'utilisateur
        
        if uploaded_file is not None:
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
        # Métriques supprimées selon les demandes de l'utilisateur
        
        # Aperçu des données
        st.subheader("📋 Aperçu des données")
        st.dataframe(st.session_state.data.head(), width="stretch")
        
        # Informations supprimées selon les demandes de l'utilisateur
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
                "Semestrielle": "2Q",
                "Annuelle": "Y"
            }
            selected_freq_name = st.selectbox("Choisissez la fréquence:", options=list(freq_options.keys()), index=0)
            freq = freq_options[selected_freq_name]
        
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
        if st.button("🚀 Préparer les données automatiquement", type="primary", width="stretch"):
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
                        df = df[df[date_col].notna()]  # Important: drop rows that failed conversion
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
                            st.metric("⏱️ Fréquence", selected_freq_name)
                        
                        st.success("✅ **Données préparées avec succès!** Vous pouvez maintenant passer aux onglets suivants.")
                        
                        # Aperçu de la série temporelle
                        st.subheader("📈 Aperçu de la série temporelle")
                        fig = px.line(time_series, x='date', y='volume', 
                                    title=f"Série temporelle - {objective}")
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, width="stretch", key='prep_timeseries_fig')
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
        
        # Ajouter dans l'onglet de préparation, après avoir défini la fréquence:
        st.session_state.freq = freq
        st.session_state.selected_freq = selected_freq_name

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
        
        st.plotly_chart(fig_trend, width="stretch", key='vis_trend_fig')
        
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
                
                st.plotly_chart(fig_dir, width="stretch", key='vis_dir_fig')
                
                # Tableau détaillé
                with st.expander("📋 Détail par Direction"):
                    dir_counts['Pourcentage'] = (dir_counts['Nombre'] / dir_counts['Nombre'].sum() * 100).round(1)
                    st.dataframe(dir_counts, width="stretch")
            else:
                st.info("Aucune colonne Direction détectée dans les données.")
        
        # Répartition par Poste  
        with col_right:
            st.markdown("#### 👥 Par Poste")
            
            if poste_col and poste_col in raw_data.columns:
                poste_counts = raw_data[poste_col].value_counts()
                
                # Top 10 + Autres
                top_10 = poste_counts.head(10)
                if len(poste_counts) > 10:
                    others_count = poste_counts[10:].sum()
                else:
                    others_count = 0
                
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
                
                st.plotly_chart(fig_poste, width="stretch", key='vis_poste_fig')
                
                # Tableau détaillé
                with st.expander("📋 Détail par Poste"):
                    poste_df = poste_counts.reset_index()
                    poste_df.columns = ['Poste', 'Nombre']
                    poste_df['Pourcentage'] = (poste_df['Nombre'] / poste_df['Nombre'].sum() * 100).round(1)
                    st.dataframe(poste_df, width="stretch")
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
                st.plotly_chart(fig_year, width="stretch", key='vis_year_fig')
        
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
            st.plotly_chart(fig_month, width="stretch", key='vis_month_fig')

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
            horizon_label_map = {
                "Mensuelle": "mois", "Trimestrielle": "trimestres", 
                "Semestrielle": "semestres", "Annuelle": "années"
            }
            selected_freq_name = st.session_state.get('selected_freq', 'Mensuelle')
            horizon_label = f"🔮 Horizon ({horizon_label_map.get(selected_freq_name, 'périodes')})"
            default_horizon = 12 if freq == 'M' else 8 if freq == 'Q' else 6 if freq == '2Q' else 3
            
            horizon_value = st.number_input(
                horizon_label,
                min_value=1,
                max_value=60,  # Augmenté à 60 au lieu de 24
                value=default_horizon,
                help=f"Nombre de {horizon_label_map.get(selected_freq_name, 'périodes')} à prédire."
            )
        
        with col2:
            model_type = st.selectbox(
                "🤖 Algorithme de prédiction",
                options=["Prophet", "Holt-Winters", "XGBoost", "Random Forest", "SARIMA"],
                index=0,
                help="Prophet: bon pour tendances et saisonnalité | Holt-Winters: classique | XGBoost & Random Forest: ML | SARIMA: séries temporelles statistiques"
            )
        
        # Bouton de lancement
        if st.button("🚀 Lancer la prédiction", type="primary", width="stretch"):
            with st.spinner(f"🤖 Entraînement du modèle {model_type} en cours..."):
                try:
                    # --- Étape 1: Évaluation du modèle pour le score MAPE ---
                    n_total = len(time_series)
                    n_test = max(1, int(n_total * 0.2)) if n_total > 5 else 1
                    train_data = time_series.iloc[:-n_test].copy()
                    test_data = time_series.iloc[-n_test:].copy()
                    
                    mape_score = np.nan
                    if not train_data.empty:
                        # Utiliser la fréquence correcte
                        if model_type == "Prophet": 
                            temp_model, temp_forecast = predict_with_prophet(train_data, n_test, freq)
                        elif model_type == "Holt-Winters": 
                            temp_model, temp_forecast = predict_with_holt_winters(train_data, n_test, freq)
                        elif model_type == "Random Forest":
                            temp_model, temp_forecast = predict_with_random_forest(train_data, n_test, freq)
                        elif model_type == "SARIMA": 
                            temp_model, temp_forecast = predict_with_sarima(train_data, n_test, freq)
                        else: 
                            temp_model, temp_forecast = predict_with_xgboost(train_data, n_test, freq)
                        
                        if temp_forecast is not None:
                            merged = pd.merge(test_data, temp_forecast, left_on='date', right_on='ds', how='left')
                            mape_score = calculate_mape(merged['volume'].values, merged['yhat'].values)

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

                    # --- Étape 2: Prédiction finale sur 100% des données ---
                    st.info("Ré-entraînement du modèle sur 100% des données pour la prédiction finale...")
                    # Utiliser la fréquence correcte pour la prédiction finale
                    if model_type == "Prophet": 
                        final_model, final_forecast = predict_with_prophet(time_series, horizon_value, freq)
                    elif model_type == "Holt-Winters": 
                        final_model, final_forecast = predict_with_holt_winters(time_series, horizon_value, freq)
                    elif model_type == "Random Forest":
                        final_model, final_forecast = predict_with_random_forest(time_series, horizon_value, freq)
                    elif model_type == "SARIMA":
                        final_model, final_forecast = predict_with_sarima(time_series, horizon_value, freq)
                    else:  # XGBoost
                        final_model, final_forecast = predict_with_xgboost(time_series, horizon_value, freq)

                    if final_model is None or final_forecast is None:
                        st.error("❌ Échec de la prédiction finale.")
                        st.stop()

                    last_date = time_series['date'].max()
                    if final_forecast is not None:
                        future_predictions = final_forecast[final_forecast['ds'] > last_date].copy()

                    if future_predictions.empty:
                        st.warning("⚠️ Aucune prédiction future générée. Vérifiez la configuration du modèle.")
                    else:
                        # Normaliser la sortie du modèle dans forecast_df (doit être fait avant toute manipulation)
                        forecast_df = future_predictions.copy()
                        if 'yhat' in forecast_df.columns:
                            forecast_df['yhat'] = forecast_df['yhat'].astype(float)
                        elif 'y' in forecast_df.columns:
                            forecast_df['yhat'] = forecast_df['y'].astype(float)
                        else:
                            forecast_df['yhat'] = 0.0

                        forecast_df = forecast_df[['ds', 'yhat']].rename(columns={'ds': 'date'})
                        forecast_df['predicted_volume'] = forecast_df['yhat'].round().astype(int).clip(lower=0)
                        forecast_df = forecast_df.sort_values('date').reset_index(drop=True)

                        # Prendre uniquement le nombre de périodes demandé
                        forecast_df = forecast_df.head(horizon_value).copy()

                        # Agrégation annuelle si demandée
                        if freq == 'Y' or st.session_state.get('selected_freq', '') == 'Annuelle':
                            forecast_df['year'] = forecast_df['date'].dt.year
                            ann = forecast_df.groupby('year', as_index=False)['predicted_volume'].sum()
                            ann['date'] = pd.to_datetime(ann['year'].astype(str) + '-01-01')
                            forecast_df = ann[['date', 'predicted_volume']].sort_values('date').reset_index(drop=True)

                        # Agrégation semestrielle si demandée (2 semestres par année)
                        if freq == '2Q' or st.session_state.get('selected_freq', '') == 'Semestrielle':
                            tmp = forecast_df.copy()
                            # si on vient d'une agrégation annuelle, s'assurer d'avoir des mois/years cohérents
                            if 'predicted_volume' not in tmp.columns and 'volume' in tmp.columns:
                                tmp['predicted_volume'] = tmp['volume']
                            # si la série est déjà annuelle (year col), reconstruire mois fictifs pour semestre
                            if 'date' in tmp.columns:
                                tmp['month'] = tmp['date'].dt.month
                                tmp['year'] = tmp['date'].dt.year
                            else:
                                tmp['month'] = 1
                                tmp['year'] = tmp.get('year', pd.Series(dtype=int))
                            tmp['semester'] = np.where(tmp['month'] <= 6, 'S1', 'S2')
                            sem = tmp.groupby(['year', 'semester'], as_index=False)['predicted_volume'].sum()
                            
                            # remplace la lambda problématique par une fonction nommée
                            def _sem_date(row):
                                try:
                                    y = int(row['year'])
                                except Exception:
                                    y = int(row.get('year', 0))
                                return pd.to_datetime(f"{y}-04-01") if row['semester'] == 'S1' else pd.to_datetime(f"{y}-10-01")
                            
                            sem['date'] = sem.apply(_sem_date, axis=1)
                            forecast_df = sem[['date', 'predicted_volume', 'year', 'semester']].sort_values(['date']).reset_index(drop=True)

                        # Préparer l'affichage (Période textuelle)
                        if freq == 'Y' or st.session_state.get('selected_freq', '') == 'Annuelle':
                            display_forecast = forecast_df.copy()
                            display_forecast['Période'] = display_forecast['date'].dt.strftime('%Y')
                            display_forecast = display_forecast[['Période', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})
                        elif freq == '2Q' or st.session_state.get('selected_freq', '') == 'Semestrielle':
                            display_forecast = forecast_df.copy()
                            display_forecast['Période'] = display_forecast['year'].astype(str) + display_forecast['semester']
                            display_forecast = display_forecast[['Période', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})
                        elif freq == 'Q':
                            display_forecast = forecast_df.copy()
                            display_forecast['Période'] = display_forecast['date'].dt.to_period('Q').astype(str)
                            display_forecast = display_forecast[['Période', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})
                        else:
                            display_forecast = forecast_df.copy()
                            display_forecast['Période'] = display_forecast['date'].dt.strftime('%B %Y')
                            display_forecast = display_forecast[['Période', 'predicted_volume']].rename(columns={'predicted_volume': 'Volume Prédit'})

                        # Remplacer l'affichage immédiat du tableau par un stockage en session.
                        # Le tableau sera affiché plus bas (après les graphiques) pour préserver l'ordre visuel.

                        # Sauvegarder la forecast pour affichage global et exports
                        st.session_state.forecast_df = forecast_df.copy()
                        st.session_state.display_forecast = display_forecast.copy()
                        # (ne pas stocker de DeltaGenerator dans session_state)
                except Exception as e:
                    st.error(f"❌ Erreur lors de la prédiction : {str(e)}")
                    st.exception(e)

        # Vérifier si une prédiction a été stockée dans session_state
        if 'forecast_df' not in st.session_state:
            # Si la section de visualisation s'exécute avant une prédiction, ne rien afficher
            if st.session_state.time_series_data is not None:
                st.info("ℹ️ Cliquez sur 'Lancer la prédiction' ci-dessus pour visualiser les résultats.")
        else:
            # Récupérer la forecast
            monthly_forecast = st.session_state.forecast_df.copy()
            display_forecast = st.session_state.display_forecast.copy() if 'display_forecast' in st.session_state else None

            # --- Affichage principal: Un seul graphique global combiné ---
            st.subheader("🔮 Prévisions - Vue Globale")
            fig_global = go.Figure()
            fig_global.add_trace(go.Scatter(
                x=time_series['date'],
                y=time_series['volume'],
                mode='lines+markers+text',
                name='Historique',
                line=dict(color='#1f77b4', width=2),
                text=time_series['volume'],
                textposition='top center',
                textfont=dict(size=10)
            ))
            fig_global.add_trace(go.Scatter(
                x=monthly_forecast['date'],
                y=monthly_forecast['predicted_volume'],
                mode='lines+markers+text',
                name='Prédictions',
                line=dict(color='#ff7f0e', width=3),
                marker=dict(size=8),
                text=monthly_forecast['predicted_volume'],
                textposition='top center',
                textfont=dict(size=10)
            ))
            fig_global.update_layout(title=f"Prédictions {model_type} - {objective}", xaxis_title="Date", yaxis_title="Volume", height=450, hovermode='x unified')
            # Afficher le tableau de prévision AVANT le graphique (sans titre redondant)
            if display_forecast is not None:
                # Centrer le tableau en utilisant des colonnes
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.dataframe(display_forecast, width="stretch", key='display_forecast_table')

            st.plotly_chart(fig_global, width="stretch", key='model_global_fig')

            # --- Graphiques de prédiction par Direction et par Poste ---
            st.markdown("---")
            st.subheader("🔍 Détails des Prédictions")

            # Solution simple et fiable : utiliser st.empty() pour éviter les duplications
            # À chaque exécution, le contenu est remplacé au lieu d'être ajouté
            placeholder = st.empty()

            with placeholder.container():
                # Calculer proportions historiques par direction/poste
                raw = st.session_state.cleaned_data_filtered.copy()
                if direction_col and direction_col in raw.columns:
                    dir_counts = raw[direction_col].value_counts(normalize=True).reset_index()
                    dir_counts.columns = ['Direction', 'Prop']
                else:
                    dir_counts = pd.DataFrame(columns=['Direction', 'Prop'])

                if poste_col and poste_col in raw.columns:
                    poste_counts = raw[poste_col].value_counts(normalize=True).reset_index()
                    poste_counts.columns = ['Poste', 'Prop']
                else:
                    poste_counts = pd.DataFrame(columns=['Poste', 'Prop'])

                # Appliquer la répartition proportionnelle aux prévisions globales
                total_pred = monthly_forecast['predicted_volume'].sum()

                # Par Direction
                dir_pred = pd.DataFrame()
                dir_detailed = pd.DataFrame()
                dir_summary = pd.DataFrame()
                if not dir_counts.empty:
                    dir_pred = dir_counts.copy()
                    dir_pred['Predicted'] = (dir_pred['Prop'] * total_pred).round().astype(int)
                    # Créer le détail mensuel par Direction
                    detailed_dir_rows = []
                    for _, row in monthly_forecast.iterrows():
                        for _, d in dir_pred.iterrows():
                            predicted_vol = int(round(d['Prop'] * row['predicted_volume']))
                            if predicted_vol > 0:  # Éviter les lignes avec 0
                                detailed_dir_rows.append({
                                    'date': row['date'].strftime('%Y-%m-%d'), 
                                    'Direction': d['Direction'], 
                                    'predicted_volume': predicted_vol
                                })
                    dir_detailed = pd.DataFrame(detailed_dir_rows)
                    # Créer le résumé (total par Direction)
                    if not dir_detailed.empty:
                        dir_summary = dir_detailed.groupby(['Direction'], as_index=False).agg({
                            'predicted_volume': 'sum'
                        }).sort_values('predicted_volume', ascending=False)
                else:
                    dir_detailed = pd.DataFrame(columns=['date', 'Direction', 'predicted_volume'])
                    dir_summary = pd.DataFrame(columns=['Direction', 'predicted_volume'])

                # Par Poste
                poste_pred = pd.DataFrame()
                poste_detailed = pd.DataFrame()
                poste_summary = pd.DataFrame()
                if not poste_counts.empty:
                    poste_pred = poste_counts.copy()
                    poste_pred['Predicted'] = (poste_pred['Prop'] * total_pred).round().astype(int)
                    # Créer le détail mensuel par Poste
                    detailed_poste_rows = []
                    for _, row in monthly_forecast.iterrows():
                        for _, p in poste_pred.iterrows():
                            predicted_vol = int(round(p['Prop'] * row['predicted_volume']))
                            if predicted_vol > 0:  # Éviter les lignes avec 0
                                detailed_poste_rows.append({
                                    'date': row['date'].strftime('%Y-%m-%d'), 
                                    'Poste': p['Poste'], 
                                    'predicted_volume': predicted_vol
                                })
                    poste_detailed = pd.DataFrame(detailed_poste_rows)
                    # Créer le résumé (total par Poste)
                    if not poste_detailed.empty:
                        poste_summary = poste_detailed.groupby(['Poste'], as_index=False).agg({
                            'predicted_volume': 'sum'
                        }).sort_values('predicted_volume', ascending=False)
                else:
                    poste_detailed = pd.DataFrame(columns=['date', 'Poste', 'predicted_volume'])
                    poste_summary = pd.DataFrame(columns=['Poste', 'predicted_volume'])

                # Afficher deux colonnes: Direction et Poste
                col_dir, col_poste = st.columns(2)

                with col_dir:
                    if not dir_summary.empty:
                        # Graphique en secteurs (pie chart) pour les directions
                        fig_dir_pred = px.pie(
                            dir_summary,
                            values='predicted_volume',
                            names='Direction',
                            title='Répartition cumulée par Direction',
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig_dir_pred.update_traces(textposition='inside', textinfo='percent+label+value')
                        fig_dir_pred.update_layout(height=400, showlegend=True)
                        st.plotly_chart(fig_dir_pred, width="stretch", key='model_dir_fig')

                        with st.expander("📋 Détail mensuel des prédictions par Direction"):
                            if not dir_detailed.empty:
                                # Organiser par Direction puis par date
                                dir_display = dir_detailed.copy()
                                dir_display = dir_display.sort_values(['Direction', 'date']).reset_index(drop=True)
                                st.dataframe(dir_display[['Direction', 'date', 'predicted_volume']], width="stretch")
                                
                                # Ajouter le résumé total
                                st.subheader("📊 Résumé total par Direction")
                                st.dataframe(dir_summary, width="stretch")

                with col_poste:
                    if not poste_summary.empty:
                        # Graphique en barres horizontales sans gradient de couleur
                        fig_poste_pred = px.bar(
                            poste_summary.sort_values('predicted_volume', ascending=True),
                            x='predicted_volume', y='Poste', orientation='h',
                            title='Répartition cumulée par Poste',
                            color_discrete_sequence=['#2E8B57'] * len(poste_summary)  # Couleur verte unie
                        )
                        fig_poste_pred.update_traces(texttemplate='%{x}', textposition='outside')
                        fig_poste_pred.update_layout(height=400, showlegend=False)
                        st.plotly_chart(fig_poste_pred, width="stretch", key='model_poste_fig')

                        with st.expander("📋 Détail mensuel des prédictions par Poste"):
                            if not poste_detailed.empty:
                                # Organiser par Poste puis par date
                                poste_display = poste_detailed.copy()
                                poste_display = poste_display.sort_values(['Poste', 'date']).reset_index(drop=True)
                                st.dataframe(poste_display[['Poste', 'date', 'predicted_volume']], width="stretch")
                                
                                # Ajouter le résumé total
                                st.subheader("📊 Résumé total par Poste")
                                st.dataframe(poste_summary, width="stretch")

            # --- Export unique: créer un fichier Excel multi-onglets (Global / Par_Direction / Par_Poste)
            try:
                bio = io.BytesIO()
                with pd.ExcelWriter(bio, engine='openpyxl') as writer:
                    # Global
                    monthly_forecast.rename(columns={'date': 'Date', 'predicted_volume': 'Predicted_Volume'}).to_excel(writer, sheet_name='Global', index=False)
                    # Par Direction
                    if not dir_detailed.empty:
                        dir_detailed.rename(columns={'date': 'Date'}).to_excel(writer, sheet_name='Par_Direction', index=False)
                    else:
                        pd.DataFrame(columns=['Date','Direction','predicted_volume']).to_excel(writer, sheet_name='Par_Direction', index=False)
                    # Par Poste
                    if not poste_detailed.empty:
                        poste_detailed.rename(columns={'date': 'Date'}).to_excel(writer, sheet_name='Par_Poste', index=False)
                    else:
                        pd.DataFrame(columns=['Date','Poste','predicted_volume']).to_excel(writer, sheet_name='Par_Poste', index=False)
                bio.seek(0)
                export_filename = f"previsions_completes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                st.download_button("⬇️ Télécharger l'export complet (Excel)", data=bio.getvalue(), file_name=export_filename, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='download_full_export')
            except Exception as e:
                st.error(f"Erreur lors de la création du fichier d'export: {e}")