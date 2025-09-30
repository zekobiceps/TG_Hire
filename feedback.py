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
    from googleapiclient.discovery import build
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Chemin vers le fichier de données de feedback
FEEDBACK_DATA_PATH = "feedback_data.json"
FEEDBACK_GSHEET_NAME = "Feedback"  # Nom de l'onglet dans Google Sheets (Feuil4 est l'onglet 4)
FEEDBACK_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit"
FEEDBACK_SHEET_INDEX = 3  # L'index 0 est la première feuille, 3 serait la 4ème feuille (Feuil4)

# -------------------- FONCTIONS D'AUTHENTIFICATION GOOGLE SHEETS --------------------
def get_feedback_google_credentials():
    """Crée les identifiants à partir des secrets Streamlit."""
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
        return service_account.Credentials.from_service_account_info(service_account_info)
    except Exception as e:
        st.error(f"❌ Erreur de format des secrets Google: {e}")
        return None

def get_feedback_gsheet_client():
    """Authentification pour Google Sheets."""
    try:
        creds = get_feedback_google_credentials()
        if creds:
            scoped_creds = creds.with_scopes([
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ])
            gc = gspread.authorize(scoped_creds)
            return gc
    except Exception as e:
        st.error(f"❌ Erreur d'authentification Google Sheets: {str(e)}")
    return None

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
            # Fonction simplifiée inspirée de save_to_google_sheet dans Cartographie.py
            def save_feedback_to_google_sheet():
                """Sauvegarde un feedback dans Google Sheets."""
                try:
                    # Afficher un message de debug pour voir si cette fonction est appelée
                    print("Tentative d'envoi du feedback vers Google Sheets...")
                    
                    # Obtenir le client Google Sheets
                    gc = get_feedback_gsheet_client()
                    if not gc:
                        print("❌ Impossible d'obtenir le client Google Sheets")
                        return False
                        
                    print(f"✅ Client Google Sheets obtenu, tentative d'ouverture de {FEEDBACK_GSHEET_URL}")
                        
                    # Ouvrir la feuille Google Sheets par URL
                    sh = gc.open_by_url(FEEDBACK_GSHEET_URL)
                    print(f"✅ Feuille Google Sheets ouverte avec succès")
                    
                    # Vérifier si la feuille/onglet existe déjà, sinon la créer
                    try:
                        # Essayer d'abord par nom
                        try:
                            worksheet = sh.worksheet(FEEDBACK_GSHEET_NAME)
                            print(f"✅ Onglet '{FEEDBACK_GSHEET_NAME}' trouvé par nom")
                        except gspread.exceptions.WorksheetNotFound:
                            # Essayer par index (Feuil4 serait index 3)
                            try:
                                worksheet = sh.get_worksheet(FEEDBACK_SHEET_INDEX)
                                print(f"✅ Onglet trouvé par index {FEEDBACK_SHEET_INDEX}")
                                if worksheet is None:
                                    raise Exception("Worksheet est None")
                            except Exception as e:
                                print(f"❌ Erreur lors de l'accès par index: {e}")
                                # Créer l'onglet avec des en-têtes
                                print(f"Création d'un nouvel onglet '{FEEDBACK_GSHEET_NAME}'")
                                worksheet = sh.add_worksheet(title=FEEDBACK_GSHEET_NAME, rows=1000, cols=8)
                    except Exception as e:
                        print(f"❌ Erreur lors de l'accès à l'onglet: {e}")
                        # Créer l'onglet avec des en-têtes
                        print(f"Création d'un nouvel onglet '{FEEDBACK_GSHEET_NAME}'")
                        worksheet = sh.add_worksheet(title=FEEDBACK_GSHEET_NAME, rows=1000, cols=8)
                        
                        # Ajouter les en-têtes exacts tels qu'ils sont dans la feuille existante
                        headers = [
                            "timestamp", "analysis_method", "job_title", "job_description_snippet",
                            "cv_count", "feedback_score", "feedback_text", "version_app"
                        ]
                        worksheet.update('A1:H1', [headers])
                        print(f"✅ Nouvel onglet créé avec en-têtes")
                    
                    # Préparer les données à ajouter
                    row_data = [
                        feedback_entry["timestamp"],
                        feedback_entry["analysis_method"],
                        feedback_entry["job_title"],
                        feedback_entry["job_description_snippet"],
                        str(feedback_entry["cv_count"]),
                        str(feedback_entry["feedback_score"]),
                        feedback_entry["feedback_text"],
                        feedback_entry["version_app"]
                    ]
                    
                    # Afficher les données qui seront envoyées
                    print(f"Données à envoyer: {row_data}")
                    
                    # Ajouter la ligne (exactement comme dans Cartographie.py)
                    worksheet.append_row(row_data)
                    print(f"✅ Données envoyées avec succès à Google Sheets")
                    st.success(f"✅ Feedback enregistré dans Google Sheets!")
                    return True
                    
                except Exception as e:
                    print(f"❌ ERREUR : {e}")
                    import traceback
                    print(traceback.format_exc())
                    st.error(f"❌ Erreur lors de la sauvegarde du feedback dans Google Sheets : {e}")
                    return False
            
            # Exécuter la fonction de sauvegarde
            save_feedback_to_google_sheet()
            
    except ImportError:
        # GSpread n'est pas disponible, on continue sans erreur
        pass
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