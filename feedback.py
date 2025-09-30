# -------------------- FONCTIONS DE GESTION DU FEEDBACK --------------------
import json
import os
import pandas as pd
from datetime import datetime
import streamlit as st

# Imports pour Google Sheets
try:
    import gspread
    from google.oauth2 import service_account
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Chemin vers le fichier de données de feedback
FEEDBACK_DATA_PATH = "feedback_data.json"
FEEDBACK_GSHEET_NAME = "TG_Hire_Feedback_Analytics"
FEEDBACK_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1FBeN0s7ESjZ6BPoG4iB4VQ6w-MfRL1GWBGEkbqPR0gI/edit"

def save_feedback(analysis_method, job_title, job_description_snippet, cv_count, feedback_score, feedback_text=""):
    """
    Sauvegarde un feedback utilisateur localement et dans Google Sheets si disponible.
    
    Args:
        analysis_method: Méthode d'analyse utilisée (Cosinus, Sémantique, Règles, IA, Ensemble)
        job_title: Intitulé du poste analysé
        job_description_snippet: Extrait de la description du poste (200 premiers caractères)
        cv_count: Nombre de CV analysés dans cette session
        feedback_score: Note de satisfaction (1-5)
        feedback_text: Commentaires textuels de l'utilisateur (optionnel)
        
    Returns:
        Boolean indiquant si le feedback a été sauvegardé avec succès
    """
    # Préparation des données de feedback
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_version = "1.0.0"  # À mettre à jour manuellement ou via un système de versioning
    
    feedback_entry = {
        "timestamp": timestamp,
        "analysis_method": analysis_method,
        "job_title": job_title,
        "job_description_snippet": job_description_snippet[:200] if job_description_snippet else "",
        "cv_count": cv_count,
        "feedback_score": feedback_score,
        "feedback_text": feedback_text,
        "version_app": app_version
    }
    
    # Chargement des données existantes ou création d'un nouveau fichier
    feedback_data = []
    if os.path.exists(FEEDBACK_DATA_PATH):
        try:
            with open(FEEDBACK_DATA_PATH, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        except:
            feedback_data = []
    
    # Ajout du nouveau feedback
    feedback_data.append(feedback_entry)
    
    # Sauvegarde locale
    try:
        with open(FEEDBACK_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde locale du feedback: {e}")
        return False
    
    # Sauvegarde dans Google Sheets si disponible
    try:
        if GSPREAD_AVAILABLE:
            # Créer les identifiants pour Google Sheets directement ici, comme dans 8_🗺️_Cartographie.py
            try:
                service_account_info = {
                    "type": st.secrets["GCP_TYPE"],
                    "project_id": st.secrets["GCP_PROJECT_ID"],
                    "private_key_id": st.secrets.get("GCP_PRIVATE_KEY_ID", ""),
                    "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'),
                    "client_email": st.secrets["GCP_CLIENT_EMAIL"],
                    "client_id": st.secrets.get("GCP_CLIENT_ID", ""),
                    "auth_uri": st.secrets.get("GCP_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": st.secrets["GCP_TOKEN_URI"],
                    "auth_provider_x509_cert_url": st.secrets.get("GCP_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": st.secrets.get("GCP_CLIENT_CERT_URL", "")
                }
                
                # Créer les identifiants avec les scopes nécessaires
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                
                # Connecter à Google Sheets
                gc = gspread.authorize(creds)
                
                # Ouvrir la feuille de feedback spécifique
                try:
                    spreadsheet = gc.open_by_url(FEEDBACK_GSHEET_URL)
                except Exception as e:
                    st.warning(f"⚠️ URL de la feuille de feedback introuvable, impossible de sauvegarder en ligne: {e}")
                    return True
                    
                # Si on arrive ici, c'est que spreadsheet existe
                try:
                    # Vérifier si la feuille Feedback existe déjà, sinon la créer
                    try:
                        worksheet = spreadsheet.worksheet(FEEDBACK_GSHEET_NAME)
                    except gspread.exceptions.WorksheetNotFound:
                        worksheet = spreadsheet.add_worksheet(title=FEEDBACK_GSHEET_NAME, rows=1000, cols=8)
                        
                        # Ajouter les en-têtes
                        headers = [
                            "timestamp", "analysis_method", "job_title", "job_description_snippet",
                            "cv_count", "feedback_score", "feedback_text", "version_app"
                        ]
                        worksheet.update('A1:H1', [headers])
                    
                    # Convertir l'entrée de feedback en ligne
                    row = [
                        feedback_entry["timestamp"],
                        feedback_entry["analysis_method"],
                        feedback_entry["job_title"],
                        feedback_entry["job_description_snippet"],
                        str(feedback_entry["cv_count"]),
                        str(feedback_entry["feedback_score"]),
                        feedback_entry["feedback_text"],
                        feedback_entry["version_app"]
                    ]
                    
                    # Ajouter la ligne (comme dans 8_🗺️_Cartographie.py)
                    worksheet.append_row(row)
                    st.success(f"✅ Feedback enregistré dans Google Sheets avec succès!")
                except Exception as e:
                    st.error(f"❌ Erreur lors de la sauvegarde du feedback dans Google Sheets: {e}")
                    st.info("Le feedback a été sauvegardé localement, mais pas dans Google Sheets.")
    except ImportError:
        # GSpread n'est pas disponible, on continue sans erreur
        pass
    
    return True

def get_average_feedback_score(analysis_method=None):
    """
    Récupère le score moyen de feedback pour une méthode donnée ou pour toutes les méthodes.
    
    Args:
        analysis_method: Méthode d'analyse spécifique (ou None pour toutes les méthodes)
        
    Returns:
        Score moyen et nombre d'évaluations
    """
    if not os.path.exists(FEEDBACK_DATA_PATH):
        return 0, 0
    
    try:
        with open(FEEDBACK_DATA_PATH, 'r', encoding='utf-8') as f:
            feedback_data = json.load(f)
        
        if analysis_method:
            relevant_feedback = [f for f in feedback_data if f["analysis_method"] == analysis_method]
        else:
            relevant_feedback = feedback_data
        
        if not relevant_feedback:
            return 0, 0
        
        total_score = sum(f["feedback_score"] for f in relevant_feedback)
        return total_score / len(relevant_feedback), len(relevant_feedback)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des scores de feedback: {e}")
        return 0, 0

def get_feedback_summary():
    """
    Génère un résumé des feedbacks reçus pour chaque méthode d'analyse.
    
    Returns:
        DataFrame contenant les statistiques de feedback
    """
    methods = [
        "Méthode Cosinus (Mots-clés)",
        "Méthode Sémantique (Embeddings)",
        "Scoring par Règles (Regex)",
        "Analyse combinée (Ensemble)",
        "Analyse par IA (DeepSeek)"
    ]
    
    summary_data = []
    
    for method in methods:
        avg_score, count = get_average_feedback_score(method)
        summary_data.append({
            "Méthode": method,
            "Score moyen": round(avg_score, 2),
            "Nombre d'évaluations": count
        })
    
    # Ajouter le score global
    overall_avg, overall_count = get_average_feedback_score()
    summary_data.append({
        "Méthode": "Toutes méthodes confondues",
        "Score moyen": round(overall_avg, 2),
        "Nombre d'évaluations": overall_count
    })
    
    return pd.DataFrame(summary_data)