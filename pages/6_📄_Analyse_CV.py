import streamlit as st
import pandas as pd
import io
import requests
import google.generativeai as genai
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time
import re
import os
from datetime import datetime
from typing import cast
import plotly.graph_objects as go
import plotly.express as px
from utils import display_commit_info

# Imports optionnels pour la manipulation des PDF (s'il manque, le code utilisera des fallbacks)
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from pypdf import PdfReader as PypdfReader
except Exception:
    PypdfReader = None

# Imports pour OCR (Cas des CV scannés)
try:
    import pytesseract
    from pdf2image import convert_from_path, convert_from_bytes
except Exception:
    pytesseract = None
    convert_from_path = None

# Imports pour la méthode sémantique
from sentence_transformers import SentenceTransformer, util
import torch

# Import des fonctions avancées d'analyse
from utils import (rank_resumes_with_ensemble, batch_process_resumes, 
                 save_feedback, get_average_feedback_score, get_feedback_summary)

# -------------------- Configuration de la clé API DeepSeek --------------------
# --- CORRECTION : Déplacé à l'intérieur des fonctions pour éviter l'erreur au démarrage ---

# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Analyse CV AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

# --- Vérification unique de la clé API DeepSeek au démarrage ---
# Évite les messages d'erreur multiples lors du redémarrage après un push
_deepseek_api_available = False
try:
    _api_key_check = st.secrets.get("DEEPSEEK_API_KEY", None)
    if _api_key_check:
        _deepseek_api_available = True
except Exception:
    pass

if not _deepseek_api_available:
    st.warning("⚠️ Le secret 'DEEPSEEK_API_KEY' n'est pas configuré. Certaines fonctionnalités IA seront désactivées.")

# Initialisation des variables de session
if "cv_analysis_feedback" not in st.session_state:
    st.session_state.cv_analysis_feedback = False
if "last_analysis_method" not in st.session_state:
    st.session_state.last_analysis_method = None
if "last_analysis_result" not in st.session_state:
    st.session_state.last_analysis_result = None
if "last_job_title" not in st.session_state:
    st.session_state.last_job_title = ""
if "last_job_description" not in st.session_state:
    st.session_state.last_job_description = ""
if "last_cv_count" not in st.session_state:
    st.session_state.last_cv_count = 0
    
# Variables pour le système de feedback persistent
if "show_feedback_form" not in st.session_state:
    st.session_state.show_feedback_form = False
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False
if "global_feedback_score" not in st.session_state:
    st.session_state.global_feedback_score = 3
    
# Variables pour conserver les résultats de l'analyse même après feedback
if "ranked_resumes" not in st.session_state:
    st.session_state.ranked_resumes = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "scores" not in st.session_state:
    st.session_state.scores = []

# -------------------- CSS --------------------
st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px; 
}
.stTextArea textarea {
    white-space: pre-wrap !important;
}
.feedback-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f0f8ff;
    margin-bottom: 1rem;
}
.feedback-title {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}
.method-stats {
    padding: 0.5rem;
    border-radius: 0.3rem;
    background-color: #f5f5f5;
    margin: 0.2rem 0;
}
.progress-bar-container {
    width: 100%;
    height: 10px;
    background-color: #f0f0f0;
    border-radius: 5px;
    margin: 10px 0;
    overflow: hidden;
}
.progress-bar {
    height: 100%;
    background-color: #4CAF50;
    border-radius: 5px;
}
/* Réduire la taille du texte des métriques */
[data-testid="metric-container"] {
    font-size: 0.8em !important;
}
[data-testid="metric-container"] > div:first-child {
    font-size: 0.75em !important;
}
[data-testid="metric-container"] > div:last-child {
    font-size: 0.7em !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Chargement des modèles ML (mis en cache) --------------------
@st.cache_resource
def load_embedding_model():
    """Charge le modèle SentenceTransformer une seule fois de manière sécurisée."""
    try:
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        st.warning(f"⚠️ Impossible de charger le modèle sémantique (embedding). La méthode 'Sémantique' sera indisponible. Erreur: {e}")
        return None

embedding_model = load_embedding_model()

# -------------------- Fonctions de traitement --------------------
def get_api_key():
    """Récupère la clé API depuis les secrets et gère l'erreur silencieusement."""
    try:
        api_key = st.secrets.get("DEEPSEEK_API_KEY", None)
        if not api_key:
            # Message déjà affiché au démarrage, ne pas répéter
            return None
        return api_key
    except Exception:
        return None

def extract_text_from_pdf(file):
    try:
        # Utiliser un buffer mémoire pour plus de compatibilité
        import io
        try:
            file.seek(0)
            data = file.read()
            bio = io.BytesIO(data)
        except Exception:
            bio = file

        # 0) PyMuPDF (fitz) - PRIORITÉ ABSOLUE pour l'ordre de lecture
        # sort=True remet le texte dans l'ordre de lecture visuel (haut-gauche -> bas-droite)
        # C'est CRUCIAL pour les CVs où le nom est dans un en-tête graphique.
        if fitz:
            try:
                bio.seek(0)
                doc = fitz.open(stream=bio, filetype="pdf")
                text_parts = []
                for page in doc:
                    # sort=True est la clé ici pour éviter que le nom ne finisse à la fin du fichier
                    text_parts.append(page.get_text("text", sort=True))
                text = "\n".join(text_parts).strip()
                if len(text) > 50:  # Validation minimale
                    return text
            except Exception as e:
                print(f"fitz sorting error: {e}")

        # 1) pdfplumber (meilleur pour extraction de texte mise en page)
        try:
            import pdfplumber
            bio.seek(0)
            with pdfplumber.open(bio) as pdf:
                parts = []
                for page in pdf.pages:
                    pt = page.extract_text()
                    if pt:
                        parts.append(pt)
                text = "\n".join(parts).strip()
                if text:
                    return text
        except Exception as e:
            # Ignorer et essayer d'autres méthodes
            print(f"pdfplumber error: {e}")

        # 2) PyPDF2
        try:
            import PyPDF2
            bio.seek(0)
            reader = PyPDF2.PdfReader(bio)
            parts = []
            for page in reader.pages:
                try:
                    pt = page.extract_text()
                except Exception:
                    pt = None
                if pt:
                    parts.append(pt)
            text = "\n".join(parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"PyPDF2 error: {e}")

        # 3) pypdf
        try:
            from pypdf import PdfReader as PypdfReader
            bio.seek(0)
            reader = PypdfReader(bio)
            parts = []
            for page in reader.pages:
                try:
                    pt = page.extract_text()
                except Exception:
                    pt = None
                if pt:
                    parts.append(pt)
            text = "\n".join(parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"pypdf error: {e}")

        # Aucun texte extrait -> PDF probablement scanné (images) ou protégé
        # Tentative OCR si disponible
        if pytesseract and convert_from_bytes:
            try:
                bio.seek(0)
                # On convertit le contenu du BytesIO en bytes
                pdf_bytes = bio.read()
                # On convertit la première page en image
                images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
                if images:
                    ocr_text = pytesseract.image_to_string(images[0], lang='fra+eng')
                    if len(ocr_text.strip()) > 10:
                        return ocr_text
            except Exception as e:
                print(f"OCR failed: {e}")

        return "Aucun texte lisible trouvé. Le PDF est peut-être un scan (images) ou protégé par mot de passe."
    except Exception as e:
        return f"Erreur d'extraction du texte: {str(e)}"

# --- MÉTHODE 1 : SIMILARITÉ COSINUS (AVEC LOGIQUE) ---
def rank_resumes_with_cosine(job_description, resumes, file_names):
    try:
        documents = [job_description] + resumes
        vectorizer = TfidfVectorizer(stop_words='english').fit(documents)
        vectors = vectorizer.transform(documents).toarray()
        
        cosine_similarities = cosine_similarity([vectors[0]], vectors[1:]).flatten()
        
        logic = {}
        feature_names = vectorizer.get_feature_names_out()
        for i, resume_text in enumerate(resumes):
            jd_vector = vectors[0]
            resume_vector = vectors[i+1]
            common_keywords_indices = (jd_vector > 0) & (resume_vector > 0)
            common_keywords = feature_names[common_keywords_indices]
            logic[file_names[i]] = {"Mots-clés communs importants": list(common_keywords[:10])}

        return {"scores": cosine_similarities, "logic": logic}
    except Exception as e:
        st.error(f"❌ Erreur Cosinus: {e}")
        return {"scores": [], "logic": {}}

# --- MÉTHODE 2 : WORD EMBEDDINGS (AVEC LOGIQUE) ---
def rank_resumes_with_embeddings(job_description, resumes, file_names):
    if embedding_model is None:
        st.error("❌ Le modèle sémantique n'est pas chargé. Impossible d'utiliser cette méthode.")
        return {"scores": [0] * len(resumes), "logic": {}}
        
    try:
        jd_embedding = embedding_model.encode(job_description, convert_to_tensor=True)
        resume_embeddings = embedding_model.encode(resumes, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(jd_embedding, resume_embeddings)
        scores = cosine_scores.flatten().cpu().numpy()

        logic = {}
        jd_sentences = [s.strip() for s in job_description.split('.') if len(s.strip()) > 10]
        if not jd_sentences: jd_sentences = [job_description]
        jd_sent_embeddings = embedding_model.encode(jd_sentences, convert_to_tensor=True)

        for i, resume_text in enumerate(resumes):
            resume_sentences = [s.strip() for s in resume_text.split('\n') if len(s.strip()) > 10]
            if not resume_sentences: continue
            resume_sent_embeddings = embedding_model.encode(resume_sentences, convert_to_tensor=True)
            
            similarity_matrix = util.pytorch_cos_sim(resume_sent_embeddings, jd_sent_embeddings)
            best_matches = {}
            for jd_idx, jd_sent in enumerate(jd_sentences):
                best_match_score, best_match_idx = torch.max(similarity_matrix[:, jd_idx], dim=0)
                if best_match_score > 0.5: # Seuil de pertinence
                     best_matches[jd_sent] = resume_sentences[best_match_idx.item()]
            logic[file_names[i]] = {"Phrases les plus pertinentes (Annonce -> CV)": best_matches}

        return {"scores": scores, "logic": logic}
    except Exception as e:
        st.error(f"❌ Erreur Sémantique : {e}")
        return {"scores": [], "logic": {}}

# --- ANALYSE PAR REGEX AMÉLIORÉE (AVEC CALCUL D'EXPÉRIENCE) ---
def regex_analysis(text):
    text_lower = text.lower()
    
    # --- CALCUL D'EXPÉRIENCE BASÉ SUR LES DATES ---
    total_experience_months = 0
    
    # Patterns pour différents formats de dates
    # 1. Format MM/YYYY - MM/YYYY
    # 2. Format Mois YYYY - Mois YYYY
    # 3. Format YYYY - YYYY
    # 4. Format période (X ans et Y mois)
    date_patterns = [
        # Format MM/YYYY - MM/YYYY ou Mois YYYY - Mois YYYY
        re.findall(r'(\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{4}|aujourd\'hui|présent|jour|current)|([a-zéèêëàâäôöùûüïîç]+\.?\s+\d{4})\s*-\s*([a-zéèêëàâäôöùûüïîç]+\.?\s+\d{4}|aujourd\'hui|présent|jour|current)', text, re.IGNORECASE),
        # Format YYYY - YYYY
        re.findall(r'(?<!\d)(\d{4})\s*-\s*(\d{4}|aujourd\'hui|présent|jour|current)(?!\d)', text, re.IGNORECASE),
        # Format "X ans et Y mois" ou "X années d'expérience"
        re.findall(r'(\d+)\s+ans?\s+(?:et\s+(\d+)\s+mois)?|(\d+)\s+années?\s+d[e\']expérience', text, re.IGNORECASE)
    ]
    
    month_map = {
        # Français
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, 
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
        "jan": 1, "fév": 2, "mar": 3, "avr": 4, "mai": 5, "juin": 6, 
        "juil": 7, "août": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12,
        # Anglais
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    def parse_date(date_str):
        if not date_str:
            return None
            
        date_str = date_str.lower().strip().replace('.','').replace('û','u')
        
        # Traitement des mentions "aujourd'hui", "présent", etc.
        if any(current_term in date_str for current_term in ["aujourd'hui", "présent", "current", "jour"]):
            return datetime.now()
            
        # Pour le format année seule (YYYY)
        if re.match(r'^\d{4}$', date_str):
            return datetime(int(date_str), 1, 1)
            
        # Pour les formats avec mois en lettres
        for month_name, month_num in month_map.items():
            if month_name in date_str:
                year_match = re.search(r'\d{4}', date_str)
                if year_match:
                    year = int(year_match.group())
                    return datetime(year, month_num, 1)
                    
        # Format MM/YYYY par défaut
        try:
            return datetime.strptime(date_str, '%m/%Y')
        except ValueError:
            # En cas d'échec, on essaie de nettoyer davantage
            cleaned = re.sub(r'[^\d/]', '', date_str).strip()
            if re.match(r'^\d{1,2}/\d{4}$', cleaned):
                return datetime.strptime(cleaned, '%m/%Y')
                
        return None

    # Traitement du format MM/YYYY - MM/YYYY ou Mois YYYY - Mois YYYY
    for match in date_patterns[0]:
        try:
            start_str, end_str = match[0] or match[2], match[1] or match[3]
            
            start_date = parse_date(start_str)
            end_date = datetime.now() if any(current_term in end_str.lower() for current_term in ["aujourd'hui", "présent", "current", "jour"]) else parse_date(end_str)
            
            if start_date and end_date:
                duration = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                total_experience_months += max(0, duration)
        except Exception:
            continue
    
    # Traitement du format YYYY - YYYY
    for match in date_patterns[1]:
        try:
            start_year, end_year = match
            
            if any(current_term in end_year.lower() for current_term in ["aujourd'hui", "présent", "current", "jour"]):
                end_date = datetime.now()
                start_date = datetime(int(start_year), 1, 1)
            else:
                start_date = datetime(int(start_year), 1, 1)
                end_date = datetime(int(end_year), 12, 31)
                
            duration = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            total_experience_months += max(0, duration)
        except Exception:
            continue
    
    # Traitement des mentions explicites d'années d'expérience
    for match in date_patterns[2]:
        try:
            years = int(match[0] or match[2] or 0)  # Années
            months = int(match[1] or 0)             # Mois (optionnel)
            
            total_experience_months += years * 12 + months
        except Exception:
            continue
    
    # Si aucune expérience détectée mais "X ans d'expérience" est mentionné directement
    if total_experience_months == 0:
        # Recherche de mentions d'expérience directes en français et en anglais
        direct_exp_patterns = [
            r'(\d+)\s*(?:an(?:s|né(?:e|es))?)\s+d[\'e]\s*(?:expérience|exp\.)',  # X ans d'expérience
            r'expérience\s+(?:de|d[\'e])\s+(\d+)\s*(?:an(?:s|né(?:e|es))?)',      # expérience de X ans
            r'(\d+)\s*(?:year(?:s)?)\s+(?:of)?\s*experience',                    # X years experience (EN)
            r'experience\s+(?:of)?\s+(\d+)\s*(?:year(?:s)?)',                    # experience of X years (EN)
        ]
        
        for pattern in direct_exp_patterns:
            direct_exp_match = re.search(pattern, text_lower)
            if direct_exp_match:
                try:
                    years = int(direct_exp_match.group(1))
                    total_experience_months = years * 12
                    break
                except:
                    continue
    
    # Arrondi à l'année la plus proche
    total_experience_years = round(total_experience_months / 12)

    education_level = 0
    # Patterns d'éducation améliorés avec équivalents internationaux
    edu_patterns = {
        8: r'doctorat|phd|ph\.d|docteur|doctorate',
        5: r'bac\s*\+\s*5|master|m\.?sc\.?|ingénieur|mba|diplôme\s+d[\'e]ingénieur',
        3: r'bac\s*\+\s*3|licence|bachelor|b\.?sc\.?|diplôme\s+universitaire\s+de\s+technologie|d\.?u\.?t',
        2: r'bac\s*\+\s*2|bts|dut|deug',
        0: r'baccalauréat|bac|high\s+school|secondary\s+education'
    }
    
    # On commence par rechercher le diplôme le plus élevé
    levels = sorted(edu_patterns.keys(), reverse=True)
    for level in levels:
        pattern = edu_patterns[level]
        if re.search(pattern, text_lower):
            education_level = level
            break
            
    skills = []
    
    # Recherche de sections spécifiques où les compétences peuvent se trouver
    skill_sections = [
        r"(?:compétences|skills|competences)\s*(?:techniques|technical)?\s*[:;](.*?)(?:\n\n|\Z)",
        r"(?:profil|profile)\s+(?:recherché|sought|technique|technical)\s*[:;](.*?)(?:\n\n|\Z)",
        r"(?:technologies|outils|tools|langages|languages)\s*[:;](.*?)(?:\n\n|\Z)",
        r"(?:expertise|savoir-faire)\s*[:;](.*?)(?:\n\n|\Z)"
    ]
    
    # Stop words plus complets (FR/EN)
    stop_words = [
        # Français
        "profil", "recherché", "maîtrise", "bonne", "expérience", "esprit", "basé", "casablanca", 
        "missions", "principales", "confirmée", "idéalement", "selon", "avoir", "être", "connaissance",
        "capable", "capacité", "aptitude", "compétence", "technique", "solide", "avancée",
        # Anglais
        "profile", "required", "mastery", "good", "experience", "spirit", "based", "mission", "main",
        "confirmed", "ideally", "according", "have", "being", "knowledge", "able", "ability", "skill",
        "technical", "solid", "advanced"
    ]
    
    # Recherche dans les différentes sections
    for pattern in skill_sections:
        section_match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            # Extraction des mots pertinents (mots de 4 lettres minimum, incluant caractères spéciaux techniques)
            words = re.findall(r'\b[a-zA-ZÀ-ÿ\+\#\.]{4,}\b', section_text)
            skills.extend([word for word in words if word.lower() not in stop_words])
    
    # Si aucune section trouvée, chercher dans tout le texte
    if not skills:
        # Recherche de termes techniques communs
        tech_patterns = [
            r'\b(?:python|java(?:script)?|typescript|c\+\+|ruby|php|html5?|css3?|sql|nosql|mongodb|mysql|postgresql|oracle|azure|aws|gcp|react(?:js)?|angular(?:js)?|vue(?:js)?|node(?:js)?|express(?:js)?|django|flask|spring|hibernate|docker|kubernetes|jenkins|git|jira|confluence|agile|scrum|kanban)\b',
            r'\b(?:excel|word|powerpoint|outlook|office|sharepoint|teams|visio|project|access|onedrive|dynamics|power\s*bi|tableau|qlik(?:view)?|looker|microstrategy)\b',
            r'\b(?:sap|oracle|salesforce|workday|netsuite|peoplesoft|microsoft\s*dynamics|jd\s*edwards|sage|quickbooks)\b'
        ]
        
        for pattern in tech_patterns:
            tech_matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.extend(tech_matches)

    return {
        "Niveau d'études": education_level,
        "Années d'expérience": total_experience_years,
        "Compétences clés extraites": list(set(skills))
    }

# --- SCORING PAR RÈGLES AVEC REGEX AMÉLIORÉ ---
def rank_resumes_with_rules(job_description, resumes, file_names):
    jd_entities = regex_analysis(job_description)
    results = []
    
    SKILL_WEIGHT = 5
    EDUCATION_WEIGHT = 30
    EXPERIENCE_WEIGHT = 20
    
    for i, resume_text in enumerate(resumes):
        resume_entities = regex_analysis(resume_text)
        current_score = 0
        logic = {}
        
        jd_skills = jd_entities["Compétences clés extraites"]
        common_skills = [skill for skill in jd_skills if re.search(r'\b' + re.escape(skill) + r'\b', resume_text.lower())]
        
        score_from_skills = len(common_skills) * SKILL_WEIGHT
        current_score += score_from_skills
        logic['Compétences correspondantes'] = f"{common_skills} (+{score_from_skills} pts)"

        score_from_edu = 0
        if resume_entities["Niveau d'études"] >= jd_entities["Niveau d'études"]:
            score_from_edu = EDUCATION_WEIGHT
            current_score += score_from_edu
        logic['Niveau d\'études'] = "Candidat: Bac+{} vs Requis: Bac+{} (+{} pts)".format(resume_entities["Niveau d'études"], jd_entities["Niveau d'études"], score_from_edu)
        
        score_from_exp = 0
        if resume_entities["Années d'expérience"] >= jd_entities["Années d'expérience"]:
            score_from_exp = EXPERIENCE_WEIGHT
            current_score += score_from_exp
        logic['Expérience'] = "Candidat: {} ans vs Requis: {} ans (+{} pts)".format(resume_entities["Années d'expérience"], jd_entities["Années d'expérience"], score_from_exp)
        
        results.append({"file_name": file_names[i], "score": current_score, "logic": logic})

    max_score = (len(jd_entities["Compétences clés extraites"]) * SKILL_WEIGHT) + EDUCATION_WEIGHT + EXPERIENCE_WEIGHT
    
    if max_score > 0:
        for res in results:
            res["score"] = min(res["score"] / max_score, 1.0)
            
    return results

# --- MÉTHODE 4 : ANALYSE PAR IA (PARSING CORRIGÉ) ---
def get_detailed_score_with_ai(job_description, resume_text):
    API_KEY = get_api_key()
    if not API_KEY: return {"score": 0.0, "explanation": "❌ Analyse IA impossible."}
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
    En tant qu'expert en recrutement, évalue la pertinence du CV suivant pour la description de poste donnée.
    Fournis ta réponse en deux parties :
    1. Un score de correspondance en pourcentage (ex: "Score: 85%").
    2. Une analyse détaillée expliquant les points forts et les points à améliorer.
    ---
    Description du poste: {job_description}
    ---
    Texte du CV: {resume_text}
    """
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        full_response_text = response.json()["choices"][0]["message"]["content"]
        score_match = re.search(r"score(?: de correspondance)?\s*:\s*(\d+)\s*%", full_response_text, re.IGNORECASE)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        return {"score": score, "explanation": full_response_text}
    except Exception as e:
        st.warning(f"⚠️ Erreur IA : {e}")
        return {"score": 0.0, "explanation": "Erreur"}

def rank_resumes_with_ai(job_description, resumes, file_names):
    scores_data = []
    for resume_text in resumes:
        scores_data.append(get_detailed_score_with_ai(job_description, resume_text))
    return {"scores": [d["score"] for d in scores_data], "explanations": {file_names[i]: d["explanation"] for i, d in enumerate(scores_data)}}



# --- FONCTIONS GEMINI ---

def get_gemini_api_key():
    try:
        return st.secrets.get("Gemini_API_KEY", None)
    except Exception:
        return None

def get_detailed_score_with_gemini(job_description, resume_text):
    API_KEY = get_gemini_api_key()
    if not API_KEY: return {"score": 0.0, "explanation": "❌ Clé Gemini manquante."}
    
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    En tant qu'expert en recrutement, évalue la pertinence du CV suivant pour la description de poste donnée.
    Fournis ta réponse en deux parties :
    1. Un score de correspondance en pourcentage (ex: "Score: 85%").
    2. Une analyse détaillée expliquant les points forts et les points à améliorer.
    ---
    Description du poste: {job_description}
    ---
    Texte du CV: {resume_text}
    """
    
    try:
        response = model.generate_content(prompt)
        text_resp = response.text
        
        # Extraction du score
        score_match = re.search(r"score(?: de correspondance)?\s*:\s*(\d+)\s*%", text_resp, re.IGNORECASE)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        
        return {"score": score, "explanation": text_resp}
    except Exception as e:
        return {"score": 0.0, "explanation": f"Erreur Gemini: {e}"}

def rank_resumes_with_gemini(job_description, resumes, file_names):
    scores_data = []
    # Placeholder pour barre de progression si intégrée, sinon boucle simple
    progress_bar = st.progress(0)
    for i, resume_text in enumerate(resumes):
        scores_data.append(get_detailed_score_with_gemini(job_description, resume_text))
        progress_bar.progress((i + 1) / len(resumes))
        time.sleep(1) # Petit délai pour éviter rate limits tier gratuit
    progress_bar.empty()
    return {"scores": [d["score"] for d in scores_data], "explanations": {file_names[i]: d["explanation"] for i, d in enumerate(scores_data)}}

def get_gemini_profile_analysis(text: str, candidate_name: str | None = None) -> str:
    API_KEY = get_gemini_api_key()
    if not API_KEY: return "❌ Analyse impossible (clé API Gemini manquante)."
    
    # Logique Nom
    if candidate_name and is_valid_name_candidate(candidate_name):
        safe_name = candidate_name
    else:
        extracted = extract_name_from_cv_text(text)
        if extracted and extracted.get('name'):
            safe_name = extracted['name']
        else:
            safe_name = "Candidat"
    
    safe_name = safe_name.replace("##", "").replace("**", "").strip()

    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Tu es un expert en recrutement. Analyse le CV suivant et génère un résumé structuré et concis EN FRANÇAIS.

Règles NOM :
- Nom identifié : "{safe_name}".
- Si "{safe_name}" est inapproprié (Candidat, Permis B...), Trouve le vrai nom dans le texte.
- Sinon garde "{safe_name}".

**Format de sortie OBLIGATOIRE** :

**👤 [Nom du Candidat]**

**📊 Synthèse**
[2-3 phrases]

**🎓 Formation**
[Diplôme le plus élevé]

**💼 Expérience**
[Dernier poste]

**🛠️ Compétences clés**
[4-5 compétences]

**💡 Points forts**
[2-3 points]

**⚠️ Points d'attention**
[1-2 points]

Texte du CV :
{text[:4000]}
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Erreur Gemini : {e}"

def get_gemini_auto_classification(text: str, full_name: str | None) -> dict:
    API_KEY = get_gemini_api_key()
    safe_name = (full_name or "Candidat").strip()
    if not API_KEY:
        return {
            "macro_category": "Non classé",
            "sub_category": "Autre",
            "years_experience": 0,
            "profile_summary": f"Erreur config Gemini",
            "candidate_name": safe_name
        }
        
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
    
    prompt = f"""
    Expert recrutement. Analyse CV.
    
    1. Check Nom: "{safe_name}". Corrige si faux (Permis B, etc).
    2. Macro-catégorie (UNE SEULE) : "Fonctions supports", "Logistique", "Production/Technique".
    3. Sous-catégorie.
    4. Années expérience (int).
    5. Récapitulatif (2-3 phrases).

    JSON output only:
    {{ "candidate_name": "...", "macro_category": "...", "sub_category": "...", "years_experience": 0, "profile_summary": "..." }}
    
    CV:
    {text[:4000]}
    """
    
    try:
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        
        # Fallback values handle
        macro = data.get("macro_category") or "Non classé"
        if macro not in ["Fonctions supports", "Logistique", "Production/Technique"]: macro = "Non classé"
        
        return {
            "macro_category": macro,
            "sub_category": data.get("sub_category", "Autre"),
            "years_experience": int(data.get("years_experience", 0)),
            "profile_summary": data.get("profile_summary", ""),
            "candidate_name": data.get("candidate_name", safe_name)
        }
    except Exception as e:
        return {
            "macro_category": "Non classé",
            "sub_category": "Autre",
            "years_experience": 0,
            "profile_summary": f"Erreur Gemini: {e}",
            "candidate_name": safe_name
        }

def get_deepseek_profile_analysis(text: str, candidate_name: str | None = None) -> str:
    """
    Génère une analyse de profil générique et concise en français.
    Retourne un texte structuré avec les points clés du candidat.
    Format en 2 colonnes pour affichage, commence par synthèse + nom.
    """
    API_KEY = get_api_key()
    if not API_KEY:
        return "❌ Analyse impossible (clé API manquante)."
    
    # --- LOGIQUE AMÉLIORÉE POUR LE NOM ---
    safe_name = ""
    
    # 1. Priorité au nom passé en argument s'il est valide
    if candidate_name and is_valid_name_candidate(candidate_name):
        safe_name = candidate_name
    else:
        # 2. Sinon, tentative d'extraction locale robuste
        extracted = extract_name_from_cv_text(text)
        if extracted and extracted.get('name'):
            safe_name = extracted['name']
        else:
            safe_name = "Candidat"
    
    # Nettoyage final du nom (au cas où des ## resteraient)
    safe_name = safe_name.replace("##", "").replace("**", "").strip()
    # -------------------------------------
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    prompt = f"""Tu es un expert en recrutement. Analyse le CV suivant et génère un résumé structuré et concis EN FRANÇAIS.

Règles NOM STRICTES (alignées avec l'extraction locale) :
- Utilise STRICTEMENT le nom fourni ci-dessous s'il est présent.
- Ne modifie PAS le nom (pas d'ajout de points, parenthèses, intitulés).
- N'invente JAMAIS de nom. Si le nom ci-dessus est "Candidat (Nom non détecté)", REPRENDS-LE tel quel.
- Ignore toute ligne contenant des mots interdits fréquents (ex: AutoCAD, ORSYS, Secteur, BIM, Owner, PSPO, Client, Missions, Permis, Angleterre, Irlande, Luxembourg, Urbanisme, Agro-alimentaire, Lecture, Multi-disciplinary, Engineering, Studies, Parcours, Professionnel, Ivalua, PRM, AMF, Alerting, Blockchain, Projects, Purposes, Program).

**Format de sortie OBLIGATOIRE** - Respecte EXACTEMENT cet ordre et ces titres :

**👤 {safe_name}**

**📊 Synthèse**
[2-3 phrases max : années d'expérience, type de profil (junior/confirmé/senior), domaine d'expertise principal]

**🎓 Formation**
[Diplôme le plus élevé - établissement - année si disponible]

**💼 Expérience**
[Dernier poste occupé - entreprise - durée]
[Secteur(s) d'activité]

**🛠️ Compétences clés**
[4-5 compétences techniques, séparées par des virgules]

**💡 Points forts**
[2-3 points forts, une ligne chacun]

**⚠️ Points d'attention**
[1-2 éléments à vérifier en entretien]

Contraintes STRICTES :
- Commence TOUJOURS par le nom puis la synthèse
- Sois factuel et concis (pas de formules de politesse)
- Si info absente du CV, écris "Non précisé"
- Maximum 12 lignes au total

Texte du CV :
{text[:4000]}
"""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"❌ Erreur lors de l'analyse : {e}"


def get_deepseek_analysis(text):
    API_KEY = get_api_key()
    if not API_KEY: return "Analyse impossible."
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
     Tu es un expert en recrutement. À partir du texte du CV ci-dessous, classe le poste cible dans UNE seule des trois macro-catégories suivantes :

     1. Fonctions supports
         • Direction RH : Recrutement, paie, formation, relations sociales.
         • Direction Finance : Comptabilité, trésorerie, fiscalité, audit.
         • Contrôle de Gestion : Analyse de la performance, budgets.
         • Direction des Achats : Sourcing, négociation, approvisionnements.
         • Direction Logistique : Gestion des flux, transport, entreposage.
         • Direction Informatique (DSI) : Infrastructure, support, cybersécurité.
         • QHSE : Normes ISO, sécurité au travail, environnement.
         • Direction Juridique : Conformité, contrats.
         • Communication / Marketing : Image de marque, digital.

     2. Logistique
         • Activités centrées sur la gestion des flux physiques, transport, entrepôts, distribution.

     3. Production/Technique
         • BTP / Génie Civil : Études de prix, conduite de travaux.
         • Industrie : Production, ligne d'assemblage, usinage, électromécanique, automatisme.
         • R&D / Bureau d'études : Conception, ingénierie.
         • Commercial / Vente : Développement du chiffre d'affaires lié à une offre technique ou industrielle.

     Consigne IMPORTANTE :
     - Réponds UNIQUEMENT par le nom exact d'UNE SEULE des trois macro-catégories ci-dessous :
        "Fonctions supports" OU "Logistique" OU "Production/Technique".
     - Ne donne aucune explication supplémentaire.

     Texte du CV :
     {text}
     """
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        # Récupérer uniquement la catégorie (nettoyer la réponse)
        result = response.json()["choices"][0]["message"]["content"].strip()
        res_low = result.lower()
        # Normaliser la réponse pour s'assurer qu'elle correspond à l'une des trois catégories
        if "support" in res_low:
            return "Fonctions supports"
        if "logist" in res_low:
            return "Logistique"
        if "production" in res_low or "technique" in res_low:
            return "Production/Technique"
        # Garder la réponse originale si elle ne correspond pas aux patterns prévus
        return result
    except Exception as e:
        return f"Erreur IA : {e}"



def clean_json_string(json_str):
    """Nettoie la réponse de l'IA pour extraire uniquement le bloc JSON valide."""
    import re
    # Enlever les balises Markdown ```json ... ```
    if "```" in json_str:
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
    
    # Trouver le premier '{' et le dernier '}'
    start = json_str.find('{')
    end = json_str.rfind('}')
    
    if start != -1 and end != -1:
        return json_str[start : end + 1]
    return json_str

def get_deepseek_auto_classification(text: str, local_extracted_name: str | None) -> dict:
    API_KEY = get_api_key()
    hint_name = (local_extracted_name or "").strip()
    
    # Fallback immédiat si pas de clé
    default_response = {
        "macro_category": "Non classé",
        "sub_category": "Autre",
        "years_experience": 0,
        "candidate_name": hint_name or "Candidat",
        "profile_summary": "Analyse impossible (clé manquante)."
    }
    
    if not API_KEY: return default_response

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    # Prompt renforcé avec liste noire
    prompt = f"""
    Agis comme un système ATS (Applicant Tracking System) expert. Analyse ce CV brut.

    --- TÂCHE 1 : EXTRACTION NOM ---
    Trouve le "Prénom NOM" du candidat.
    Indice algorithmique : "{hint_name}".
    
    RÈGLES CRITIQUES NOM :
    1. Si l'indice semble correct (un vrai nom), utilise-le.
    2. Si l'indice est vide, cherche dans l'en-tête.
    3. INTERDIT : Ne renvoie JAMAIS un titre de poste comme nom (ex: "Ingénieur", "Développeur", "Manager", "Curriculum Vitae", "Profil").
    4. INTERDIT : Ne renvoie JAMAIS une adresse email ou un numéro de téléphone.
    5. Format : "Prénom NOM" (Nom en majuscule si possible).

    --- TÂCHE 2 : CLASSIFICATION ---
    Macro-catégorie (CHOISIR UNE SEULE) : 
    - "Fonctions supports" (RH, Finance, Juridique, IT Support, Achats)
    - "Logistique" (Supply Chain, Transport, Stock)
    - "Production/Technique" (Ingénierie, BTP, Industrie, R&D)

    --- TÂCHE 3 : INFO ---
    - Années d'expérience (nombre entier).
    - Résumé : Une phrase "Punchy" commençant par le nom.

    Réponds UNIQUEMENT ce JSON :
    {{
        "candidate_name": "...",
        "macro_category": "...",
        "sub_category": "...",
        "years_experience": 0,
        "profile_summary": "..."
    }}

    CV TEXTE (Début) :
    {text[:3000]}
    """

    try:
        response = requests.post(url, headers=headers, data=json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }))
        response.raise_for_status()
        
        # Nettoyage et Parsing
        raw_content = response.json()["choices"][0]["message"]["content"]
        clean_content = clean_json_string(raw_content)
        data = json.loads(clean_content)

        # Validation post-traitement (Safety check)
        final_name = data.get("candidate_name", "Candidat")
        
        # Liste noire de sécurité (si l'IA hallucine encore)
        blacklist = ["curriculum", "vitae", "resume", "profil", "ingénieur", "manager", "développeur", "page", "cv"]
        if any(bad in final_name.lower() for bad in blacklist):
            final_name = hint_name if hint_name else "Candidat (Nom non détecté)"

        # Normalisation catégorie
        macro = data.get("macro_category")
        if macro not in ["Fonctions supports", "Logistique", "Production/Technique"]:
            macro = "Non classé"

        return {
            "macro_category": macro,
            "sub_category": data.get("sub_category", "Autre"),
            "years_experience": data.get("years_experience", 0),
            "candidate_name": final_name,
            "profile_summary": data.get("profile_summary", "")
        }

    except Exception as e:
        print(f"DeepSeek Error: {e}")
        # En cas d'erreur IA, on renvoie au moins le nom trouvé localement
        default_response["candidate_name"] = hint_name or "Erreur Extraction"
        return default_response


def extract_name_smart_email(text):
    """
    Extrait le nom via l'email ET vérifie sa présence dans le texte pour confirmer.
    Gère les formats : prenom.nom, prenom_nom, nom.prenom
    """
    import re
    if not text: return None
    
    # 1. Trouver les emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Liste d'emails génériques à ignorer
    ignore_emails = ['contact', 'info', 'recrutement', 'job', 'stages', 'rh', 'email', 'gmail', 'yahoo']
    
    for email in emails:
        user_part = email.split('@')[0]
        
        # Si l'email est générique, on saute
        if any(bad in user_part.lower() for bad in ignore_emails):
            continue
            
        # Séparateurs possibles dans l'email (point, underscore, tiret)
        parts = re.split(r'[._-]', user_part)
        
        # On ne garde que les parties alphabétiques de plus de 2 lettres (évite les chiffres ou initiales)
        valid_parts = [p for p in parts if p.isalpha() and len(p) >= 3]
        
        if len(valid_parts) >= 2:
            # On a potentiellement Prénom et Nom. On cherche ces mots dans les 1000 premiers caractères du CV
            header_text = text[:1000]
            found_parts = []
            
            for part in valid_parts:
                # On cherche le mot exact dans le texte (insensible à la casse)
                match = re.search(r'\b' + re.escape(part) + r'\b', header_text, re.IGNORECASE)
                if match:
                    # On récupère la version écrite dans le CV (ex: "DUPONT" au lieu de "dupont")
                    found_parts.append(match.group(0))
            
            # Si on a retrouvé au moins 2 parties du nom dans le texte, c'est un match solide !
            if len(found_parts) >= 2:
                # On retourne les parties trouvées, jointes par un espace
                return {"name": " ".join(found_parts), "confidence": 0.99, "method_used": "smart_email_cross_check"}
                
    return None

# -------------------- Extraction de noms des CV (AMÉLIORÉE) --------------------

def is_valid_name_candidate(text: str) -> bool:
    """
    Vérifie si un texte ressemble à un vrai nom.
    Plus permissif pour accepter les noms composés et formats internationaux.
    """
    if not text or len(text) < 2:
        return False
    
    # Nettoyage de base
    text = text.strip()
    
    # Rejets évidents
    if len(text) > 50 and ' ' not in text: return False  # Trop long sans espace
    if re.search(r'\d', text): return False  # Contient des chiffres
    if re.search(r'[@€$£%&:]', text): return False  # Caractères spéciaux invalides (inclut : et &)
    if text.count('-') > 3: return False  # Trop de tirets
    
    # Doit contenir au moins une voyelle (sauf exceptions très rares)
    if not re.search(r'[aeiouyàâäéèêëïîôöùûü]', text.lower()):
        return False
    
    # Ratio de lettres (doit être principalement des lettres)
    # On enlève espaces et tirets pour le calcul
    clean_chars = re.sub(r'[\s\-\.]', '', text)
    if not clean_chars: return False
    
    return True


def is_likely_name_line(line: str) -> bool:
    """
    Détermine si une ligne a de fortes chances d'être un nom (et pas un titre).
    """
    line_lower = line.lower().strip()
    words = line_lower.split()
    
    # 1. Mots INTERDITS : S'ils sont présents, ce n'est PAS un nom
    forbidden_words = [
        # Mots génériques et titres de sections
        'cv', 'curriculum', 'vitae', 'resume', 'profil', 'profile',
        'expérience', 'experience', 'formation', 'education', 
        'compétences', 'skills', 'langues', 'languages',
        'projet', 'project', 'contact', 'téléphone', 'email', 'adresse',
        'page', 'date', 'diplômes', 'formations', 'certifications', 'hobbies', 'loisirs',
        'permis', 'vehicule', 'véhicule', 'conduite', 'driver', 'driving', 'b', 'voiture',
        'centres', 'intérêt', 'projets', 'réalisés', 'professionnelles',
        'coordonnées', 'spécialisations', 'management', 'onboarding', 'performance',
        'sommaire', 'summary', 'objectif', 'objective', 'propos', 'about', 'me', 'moi',
        'bac', 'baccalauréat', 'baccalaureate', 'degree', 'niveau', 'level',
        'logiciels', 'maîtrisés', 'activités', 'associatives',
        
        # Écoles et Universités (Faux positifs fréquents)
        'école', 'ecole', 'school', 'business', 'university', 'université',
        'hec', 'essec', 'esc', 'em', 'dauphine', 'polytechnique', 'centrale', 'mines',
        'master', 'bachelor', 'licence', 'mba', 'diplôme', 'diplome', 'msc',
        'lycée', 'lycee', 'college', 'collège', 'institut', 'academy',
        
        # Compétences techniques & Outils
        'excel', 'vba', 'power', 'bi', 'crm', 'python', 'java', 'sql', 'office',
        'pack', 'adobe', 'suite', 'google', 'cloud', 'aws', 'azure', 'sap', 'erp',
        'photoshop', 'illustrator', 'indesign', 'canva', 'jira', 'trello',
        
        # Entreprises connues (pour éviter "BNP Paribas" comme nom)
        'bnp', 'paribas', 'société', 'générale', 'crédit', 'agricole', 'sncf',
        'groupe', 'group', 'bank', 'banque', 'service', 'civique', 'unilever',
        'orange', 'capgemini', 'atos', 'sopra', 'steria', 'accenture', 'deloitte',
        'kpmg', 'ey', 'pwc', 'mazars', 'nge', 'mire',
        
        # Pays et Villes (souvent en en-tête)
        'france', 'paris', 'maroc', 'casablanca', 'rabat', 'lyon', 'marseille',
        'toulouse', 'bordeaux', 'lille', 'nantes', 'strasbourg', 'rennes',
        
        # Blancs ou très courts
        'non', 'trouvé',
        'analyste', 'financière', 'contrôleuse', 'gestion', 'ingénieur',
        'directeur', 'directrice', 'manager', 'consultant', 'développeur', 'responsable',
        'développement', 'rh', 'sirh', 'assistant', 'assistante', 'stagiaire',
        'technicien', 'commercial', 'vente', 'marketing', 'comptable', 'auditeur',
        'senior', 'junior', 'expert', 'chef', 'actuaire', 'data', 'scientist',
        'chargé', 'chargée', 'officer', 'executive', 'associate', 'partner',
        
        # Postes et métiers supplémentaires
        'job', 'étudiant', 'etudiant', 'student', 'intern', 'internship', 'stage',
        'engineer', 'developer', 'designer', 'analyst', 'specialist', 'coordinator',
        'ia', 'ai', 'ml', 'machine', 'learning', 'deep',
        'mécanique', 'mecanique', 'électrique', 'electrique', 'civil', 'industriel',
        
        # Termes de documents/réunions
        'weekly', 'meeting', 'decks', 'deck', 'presentation', 'rapport', 'report',
        'document', 'documents', 'fichier', 'fichiers', 'dossier', 'dossiers',
        
        # Verbes d'action (souvent en bullet points)
        'gérer', 'piloter', 'management', 'coordonner', 'développer', 'créer',
        'réaliser', 'participer', 'contribuer', 'superviser', 'analyser',
        
        # Entreprises supplémentaires (faux positifs fréquents)
        'procter', 'gamble', 'l\'oréal', 'loreal', 'carrefour', 'hsbc', 'edf',
        
        # Langues et nationalités
        'français', 'francais', 'anglais', 'arabe', 'espagnol', 'courant', 'bilingue',
        'nationality', 'nationalité', 'franco-moroccan', 'franco-marocain',
        
        # Termes RH et certifications
        'gpec', 'gepp', 'hdi', 'certification', 'certifications', 'itil',
        
        # Logiciels et outils supplémentaires
        'diapason', 'ktp', 'summit', 'anaplan', 'swiftnet', 'servicenow', 'remedy',
        'dynamics', 'confluence', 'slack', 'figma', 'tableau',
        
        # Loisirs et intérêts
        'intérêts', 'interets', 'football', 'natation', 'voyages', 'lecture',
        'sport', 'voyage', 'bénévolat', 'benevolat', 'danse', 'musique',
        
        # Termes scientifiques/académiques
        'physiologie', 'physiopathologie', 'physiopathologies', 'humaine', 'modélisation',
        
        # Mots génériques supplémentaires
        'soft', 'hard', 'about', 'linkedin', 'trésorier', 'tresorier', 'ingénieure', 'ingenieure',
        
        # ====== NOUVEAUX MOTS INTERDITS (Faux positifs observés) ======
        # Termes techniques/métiers
        'simulation', 'numérique', 'numerique', 'pensée', 'pensee', 'critique', 'lecture',
        'concept', 'partenaire', 'entreprise', 'entreprises',
        'charge', 'chargee', 'delivery', 'delivery', 'secteur', 'agro-alimentaire',
        'multi-disciplinary', 'multidisciplinary', 'engineering', 'studies', 'etudes', 'études',
        'parcours', 'professionnel', 'profile',
        
        # Sections CV supplémentaires  
        'experiences', 'expériences', 'professionelles', 'professionnelle',
        'competences', 'realisations', 'réalisations',
        
        # Entreprises/Lieux supplémentaires
        'saem', 'corum', 'montpellier', 'groupement', 'mousquetaires', 'intermarché',
        'leclerc', 'auchan', 'lidl', 'casino', 'monoprix',
        'puteaux', 'orsys', 'angleterre', 'irlande', 'luxembourg',
        'ivalua', 'prm',
        
        # Termes anglais courants
        'delivery', 'manager', 'coordinator', 'specialist', 'officer', 'owner', 'pspo',
        'technical', 'professional', 'summary', 'overview',
        'and', 'alerting', 'blockchain', 'projects', 'purposes', 'program',
        
        # Logiciels techniques / CAO / Outils scientifiques
        'logiciels', 'abaqus', 'catia', 'solidworks', 'autocad', 'ansys', 'matlab', 'bim', 'software',
        'xlstat', 'minitab', 'spss', 'stata', 'r', 'rstudio', 'hive', 'psql',
        'rtgs', 'target', 'swift', 'bpce',
        
        # Soft skills et termes RH
        'stress', 'équipe', 'equipe', 'organisation', 'esprit', 'sens',
        'gestion', 'autonomie', 'rigueur', 'adaptabilité', 'adaptabilite',
        'dynamisme', 'motivation', 'travail', 'team', 'leadership',
        
        # Titres de postes
        'cash', 'flux', 'foncier', 'trésorerie', 'tresorerie',
        # Termes génériques récurrents à exclure
        'client', 'missions',
        # Certifications/Accréditations spécifiques
        'amf',
        # Mots à bannir (Faux positifs signalés)
        'formateur', 'cuisine', 'agile', 'scrum', 'méthodologie', 'methodologie',
        'ocp', 'sa', 'sarl', 'sas', 'inc', 'ltd', 'group', 'groupe', 'holding',
        'résidence', 'residence', 'immeuble', 'apt', 'app', 'étage',
        'compétence', 'competence', 'professionnelle', 'limitée',
        
        # Mots à bannir (Faux positifs signalés)
        'formateur', 'cuisine', 'agile', 'scrum', 'méthodologie', 'methodologie',
        'ocp', 'sa', 'sarl', 'sas', 'inc', 'ltd', 'group', 'groupe', 'holding',
        'résidence', 'residence', 'immeuble', 'apt', 'app', 'étage',
        'compétence', 'competence', 'professionnelle', 'limitée',
    ]

    # --- 1.1 FILTRAGE AGRESSIF (Substrings) ---
    # Certains mots invalident TOUTE la ligne même s'ils sont collés
    # Ex: "GestionDeProjet", "CompétenceProfessionnelle"
    fatal_substrings = [
        'compétence', 'competence', 'formation', 'education', 
        'projets', 'réalisés', 'experience', 'expérience', 
        'sommaire', 'summary', 'profil', 'profile',
        'soft', 'hard', 'skills', 'outils', 'logiciels',
        'management', 'agile', 'scrum', 'methodologie', 'méthodologie'
    ]
    if any(fs in line_lower for fs in fatal_substrings):
        return False

    
    # Si un mot de la ligne est interdit -> Rejet
    if any(w in forbidden_words for w in words):
        return False
    
    # Rejet si la ligne contient des caractères spéciaux typiques de labels
    if ':' in line or '&' in line:
        return False
    # Rejet si la ligne contient ponctuation indicative de titres/sections
    if any(p in line for p in ['.', '(', ')', '/', ',']) or any(c.isdigit() for c in line):
        return False

    # 2. Vérifications de structure
    # Doit contenir entre 2 et 5 mots (ex: "Jean Dupont" ou "Jean-Pierre de la Tour")
    if len(words) < 2 or len(words) > 5:
        return False
    
    # Mots d'arrêt (Articles) : acceptés dans un nom compos, mais ne doivent pas constituer tout le nom
    stop_words = ['de', 'du', 'des', 'le', 'la', 'les', 'van', 'von', 'da', 'di']
    
    # Si tous les mots sont des stop words -> Rejet
    if all(w in stop_words for w in words):
        return False
    
    # Au moins un mot doit commencer par une majuscule (sauf si tout est en majuscule)
    # Note: line.isupper() gère les noms tout en majuscule
    if not line.isupper() and not any(w[0].isupper() for w in line.split() if w):
        return False
        
    return True


def score_name_candidate(text: str) -> float:
    """
    Attribue un score de probabilité (0-1) qu'un texte soit un nom.
    """
    score = 0.0
    words = text.split()
    
    # Longueur idéale (2-3 mots)
    if 2 <= len(words) <= 3: score += 0.3
    elif len(words) == 4: score += 0.2
    
    # Casse (Casing)
    if text.isupper():  # TOUT EN MAJUSCULES (fréquent pour les noms de famille)
        score += 0.2
    elif all(w[0].isupper() for w in words if w):  # Title Case
        score += 0.2
    elif len(words) >= 2 and words[-1].isupper() and words[0][0].isupper():  # Prénom NOM
        score += 0.3
        
    # Validation basique
    if is_valid_name_candidate(text):
        score += 0.2
    else:
        return 0  # Si invalide, score 0 direct
        
    return min(score, 1.0)


def clean_merged_text_pdf(text: str) -> str:
    """
    Corrige les problèmes de parsing PDF où les mots sont collés.
    Ex: 'Verneuil enABDALLAH' -> 'Verneuil en ABDALLAH'
    Ex: '0787860895HADDOUCHI' -> '0787860895 HADDOUCHI'
    Ex: 'CompétenceProfessionnelle' -> 'Compétence Professionnelle'
    """
    if not text: return ""
    
    # 1. Séparer minuscule/Majuscule (CamelCase strict)
    # Ex: 'CompétenceProfessionnelle' -> 'Compétence Professionnelle'
    # Attention: 'McDonald' -> 'Mc Donald' (Acceptable pour l'analyse)
    text = re.sub(r'([a-zà-ÿ])([A-ZÀ-Ÿ])', r'\1 \2', text)
    
    # 2. Séparer Chiffre/Lettre (ex: 95HADDOUCHI)
    text = re.sub(r'([0-9])([a-zA-Z]{2,})', r'\1 \2', text)
    
    return text

def extract_name_from_cv_text(text):
    """
    Extrait le nom complet d'un CV avec une approche heuristique avancée.
    Gère les cas comme "## Hiba BELFARJI" ou les mises en page OCR.
    """
    if not text or len(text.strip()) < 10:
        return {"name": None, "confidence": 0, "method_used": "text_too_short"}
    
    # NETTOYAGE CRITIQUE : Séparation des mots collés (OCR/PDF mal formés)
    text = clean_merged_text_pdf(text)
    
    lines = text.split('\n')
    
    # --- ÉTAPE 1 : Nettoyage préliminaire des lignes ---
    # MODIF : Augmentation de la portée d'analyse à 200 lignes pour capturer les noms dans les sidebars (multi-colonnes)
    SCAN_LIMIT = 200
    cleaned_lines = []
    
    # On itère avec l'index pour pénaliser la position si nécessaire
    for idx, line in enumerate(lines[:SCAN_LIMIT]):
        # Enlever les caractères de formatage Markdown ou OCR
        clean = line.strip()
        clean = re.sub(r'^##\s*', '', clean)  # Enlever "## " au début
        clean = re.sub(r'^\*\*\s*', '', clean)  # Enlever "** " au début
        clean = re.sub(r'\s*\*\*$', '', clean)  # Enlever " **" à la fin
        clean = re.sub(r'^[-•➢–]\s*', '', clean)  # Enlever les puces
        clean = re.sub(r'^[o]\s*', '', clean) # Enlever autres puces OCR
        
        if not clean:
            continue
            
        # On garde l'info de ligne originelle si besoin
        cleaned_lines.append(clean)
        
        # Gestion des noms espacés (ex: "I c h r a k B A K I A" ou "M a r w a n  L A A N I G R I")
        # Si la ligne contient beaucoup d'espaces et des lettres isolées
        if len(clean) > 5 and ' ' in clean:
            # Compte le nombre de tokens de 1 lettre
            single_letter_tokens = [w for w in clean.split() if len(w) == 1 and w.isalpha()]
            if len(single_letter_tokens) > len(clean.split()) / 2:
                # C'est probablement un texte espacé
                # AMÉLIORATION: Reconstituer en se basant sur les transitions de casse
                # "I c h r a k B A K I A" -> "Ichrak BAKIA"
                result_parts = []
                current_word = ""
                prev_was_lower = False
                
                for char in clean:
                    if char == ' ':
                        continue  # Ignorer les espaces
                    
                    is_upper = char.isupper()
                    
                    # Transition minuscule -> majuscule = nouveau mot (prénom terminé, nom commence)
                    if prev_was_lower and is_upper and current_word:
                        result_parts.append(current_word)
                        current_word = char
                    else:
                        current_word += char
                    
                    prev_was_lower = char.islower()
                
                if current_word:
                    result_parts.append(current_word)
                
                # Si on a au moins 2 parties, c'est probablement Prénom NOM
                if len(result_parts) >= 2:
                    normalized = ' '.join(result_parts)
                    cleaned_lines.append(normalized)
                elif result_parts:
                    # Sinon fallback sur l'ancienne méthode
                    temp = re.sub(r'\s{2,}', '|', clean)
                    temp = temp.replace(' ', '')
                    normalized = temp.replace('|', ' ')
                    if normalized != clean:
                        cleaned_lines.append(normalized)

    # --- ÉTAPE 1-BIS : Fusion de lignes (Pour les cas : L1=Prénom, L2=Nom) ---
    # Ex: "Oussama" \n "GARMOUMI"
    merged_candidates = []
    if len(cleaned_lines) > 1:
        for i in range(len(cleaned_lines) - 1):
            l1 = cleaned_lines[i]
            l2 = cleaned_lines[i+1]
            # Si l1 ressemble à un prénom (Title) et l2 à un nom (Upper) ou vice versa
            # Et qu'ils ne sont pas trop longs
            if len(l1.split()) == 1 and len(l2.split()) == 1:
                # Oussama \n GARMOUMI
                if l1.istitle() and l2.isupper():
                    merged_candidates.append(f"{l1} {l2}")
                # GARMOUMI \n Oussama
                elif l1.isupper() and l2.istitle():
                    merged_candidates.append(f"{l1} {l2}")

    # --- ÉTAPE 2 : Recherche de patterns explicites (Regex forte) ---
    # Pattern : Prénom (Title) NOM (Upper) ou NOM (Upper) Prénom (Title)
    # Ex: "Hiba BELFARJI" ou "BELFARJI Hiba"
    regex_strong = r'^([A-ZÀ-Ÿ][a-zà-ÿ]+(?:-[A-ZÀ-Ÿ][a-zà-ÿ]+)?)\s+([A-ZÀ-Ÿ]{2,}(?:\s+[A-ZÀ-Ÿ]{2,})?)$'
    regex_reverse = r'^([A-ZÀ-Ÿ]{2,}(?:\s+[A-ZÀ-Ÿ]{2,})?)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:-[A-ZÀ-Ÿ][a-zà-ÿ]+)?)$'
    
    # Test d'abord sur les candidats mergés
    for cand in merged_candidates:
         if re.match(regex_strong, cand) or re.match(regex_reverse, cand):
             # Vérif extra : pas de mot interdit
             if is_likely_name_line(cand):
                 return {"name": cand, "confidence": 0.90, "method_used": "merged_lines_regex"}

    for line in cleaned_lines:
        line_clean = line.strip()
        # Test Prénom NOM
        match = re.match(regex_strong, line_clean)
        if match and is_likely_name_line(line_clean):
            return {"name": line_clean, "confidence": 0.95, "method_used": "regex_strong_firstname_lastname"}
        
        # Test NOM Prénom
        match = re.match(regex_reverse, line_clean)
        if match and is_likely_name_line(line_clean):
            return {"name": line_clean, "confidence": 0.95, "method_used": "regex_strong_lastname_firstname"}

    # --- ÉTAPE 3 : Système de Scoring (Heuristique) ---
    best_candidate = None
    best_score = 0.0
    
    for line in cleaned_lines:
        # Check rapide anti-spam (si ligne > 6 mots, peu probable que ce soit un nom sauf espacé)
        if len(line.split()) > 6:
            continue

        if not is_likely_name_line(line):
            continue
            
        current_score = score_name_candidate(line)
        
        # Bonus si la ligne est isolée (pas de phrase avant/après dans le bloc original ?? Difficile à dire ici)
        # Mais on peut pénaliser les lignes très bas si elles n'ont pas un score excellent
        
        if current_score > best_score:
            best_score = current_score
            best_candidate = line
            
    # --- ÉTAPE 4 : Fallback Proximité Email/Tel (Deep Scan) ---
    # Recherche étendue jusqu'à SCAN_LIMIT au lieu de 50
    if best_score < 0.6:
        for i, line in enumerate(lines[:SCAN_LIMIT]):
            # Si on trouve un email ou un tel
            if re.search(r'@[\w\.-]+', line) or re.search(r'(?:(?:\+|00)33|0)\s*[1-9]', line):
                # Regarder 10 lignes AVANT (contexte immédiat)
                start_range = max(0, i - 10)
                # Mais aussi 3 lignes APRÈS (parfois le nom est sous l'email dans les sidebars)
                end_range = min(len(lines), i + 3)
                
                context_lines = lines[start_range:i] + lines[i+1:end_range]
                
                for ctx_line in context_lines:
                    ctx_line = ctx_line.strip()
                    # Nettoyage léger
                    clean_ctx = re.sub(r'^##\s*', '', ctx_line)
                    clean_ctx = re.sub(r'^\*\*\s*', '', clean_ctx)
                    clean_ctx = re.sub(r'\s*\*\*$', '', clean_ctx)
                    clean_ctx = re.sub(r'^[-•➢–]\s*', '', clean_ctx)
                    
                    if not clean_ctx: continue

                    if is_likely_name_line(clean_ctx):
                        cand_score = score_name_candidate(clean_ctx)
                        # On booste le score car proche des contacts
                        boosted_score = cand_score + 0.3
                        if boosted_score > best_score:
                            best_score = boosted_score
                            best_candidate = clean_ctx

    # --- ÉTAPE 5 : Fallback Ultime (Recherche de patterns faibles) ---
    # Si toujours rien, on cherche n'importe quoi qui ressemble à "Prénom NOM" même sans contexte
    if not best_candidate or best_score < 0.4:
        # Regex plus permissive (admet Title Title) pour les cas comme "Elkani Sadia"
        regex_permissive = r'^([A-ZÀ-Ÿ][a-zà-ÿ]+)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+)$'
        
        for line in cleaned_lines:
             if re.match(regex_permissive, line) and is_likely_name_line(line):
                 # On vérifie quand même que ce n'est pas un nom de ville ou d'école connu (déjà filtré par is_likely)
                 score = 0.5 # Score moyen
                 if score > best_score:
                     best_score = score
                     best_candidate = line
    
    if best_candidate and best_score > 0.4:
        return {"name": best_candidate, "confidence": best_score, "method_used": "scoring_best_match"}

    if best_candidate and best_score > 0.4:
        return {"name": best_candidate, "confidence": best_score, "method_used": "scoring_best_match"}

    return {"name": None, "confidence": 0, "method_used": "not_found"}


def extract_name_from_line(line):
    """Extrait un nom candidat d'une ligne en utilisant des heuristiques (fonction legacy)"""
    if not line or len(line.strip()) < 5:
        return None
    
    # Nettoyer la ligne
    line = line.strip()
    line = re.sub(r'^##\s*', '', line)  # Enlever "## " au début
    line = re.sub(r'^\*\*\s*', '', line)  # Enlever "** " au début
    line = re.sub(r'\s*\*\*$', '', line)  # Enlever " **" à la fin
    
    # Utiliser les nouvelles fonctions
    if is_likely_name_line(line):
        score = score_name_candidate(line)
        if score > 0.4:
            return line
    
    return None

# -------------------- Génération du ZIP organisé --------------------
def merge_results_with_ai_analysis(original_results):
    """
    Intègre les résultats des analyses IA dans les résultats originaux.
    Met à jour les catégories des CV qui ont été analysés par l'IA.
    """
    # Créer une copie pour ne pas modifier l'original
    updated_results = original_results.copy()
    
    # Si des analyses IA existent, intégrer les résultats
    if hasattr(st.session_state, 'deepseek_analyses') and st.session_state.deepseek_analyses:
        ai_results = {result['Fichier']: result['Catégorie'] for result in st.session_state.deepseek_analyses}
        
        for i, result in enumerate(updated_results):
            filename = result['file']
            if filename in ai_results:
                ai_category = ai_results[filename]
                # Normaliser la catégorie IA selon nos catégories standard
                if "support" in ai_category.lower():
                    updated_results[i]['category'] = 'Fonctions supports'
                elif "logistique" in ai_category.lower():
                    updated_results[i]['category'] = 'Logistique'
                elif "production" in ai_category.lower() or "technique" in ai_category.lower():
                    updated_results[i]['category'] = 'Production/Technique'
                # Si la catégorie IA n'est pas reconnue, on garde "Non classé"
    
    return updated_results

def create_organized_zip(results, file_list):
    """
    Crée un fichier ZIP avec les CV organisés par catégorie et renommés.
    Intègre automatiquement les résultats des analyses IA.
    Retourne les bytes du ZIP et un DataFrame manifest.
    """
    import zipfile
    import io
    from io import BytesIO
    
    # Intégrer les analyses IA dans les résultats
    merged_results = merge_results_with_ai_analysis(results)
    
    zip_buffer = BytesIO()
    manifest_data = []
    
    # Créer les dossiers par catégorie
    folders = {
        'Production': 'Production/',
        'Production/Technique': 'Production/',
        'Fonctions supports': 'Fonctions_supports/',
        'Logistique': 'Logistique/',
        'Non classé': 'Non_classe/'
    }
    
    # Déterminer quelles catégories sont réellement présentes
    categories_present = set(result['category'] for result in merged_results)
    folders_to_create = set()
    for category in categories_present:
        if category in folders:
            folders_to_create.add(folders[category])
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Créer seulement les dossiers nécessaires
        for folder in folders_to_create:
            zip_file.writestr(folder, '')
        
        # Traiter chaque CV avec les résultats intégrant l'IA
        for result in merged_results:
            original_name = result['file']
            category = result['category']
            
            # Déterminer le nom final du fichier
            if 'extracted_name' in result and result['extracted_name'] and result['extracted_name']['name']:
                # Utiliser le nom extrait
                extracted_name = result['extracted_name']['name']
                # Normaliser les espaces multiples et nettoyer
                try:
                    import re as _re
                    cleaned_extracted = _re.sub(r"\s+", " ", extracted_name).strip()
                except Exception:
                    cleaned_extracted = extracted_name.strip()
                final_name = f"{cleaned_extracted}.pdf"
                confidence = result['extracted_name']['confidence']
                method = result['extracted_name']['method_used']
            else:
                # Garder le nom original
                final_name = original_name
                confidence = 0
                method = 'original_name'
            
            # Déterminer le dossier de destination
            folder = folders.get(category, 'Non_classe/')
            file_path_in_zip = folder + final_name
            
            # Trouver le fichier original dans file_list
            original_file = None
            for item in file_list:
                if item['name'] == original_name:
                    original_file = item['file']
                    break
            
            if original_file:
                try:
                    # Lire le contenu du fichier original
                    original_file.seek(0)
                    file_content = original_file.read()
                    # Ajouter au ZIP
                    zip_file.writestr(file_path_in_zip, file_content)
                    
                    # Ajouter au manifest (une colonne par champ + récap profil + années exp)
                    manifest_data.append({
                        'fichier_original': original_name,
                        'nouveau_nom': final_name,
                        'categorie': category,
                        'sous_categorie': result.get('sub_category', ''),
                        'annees_experience': result.get('years_experience', 0),
                        'confiance_extraction': confidence,
                        'methode_extraction': method,
                        'recap_profil': result.get('profile_summary', ''),
                        'dossier': folder.rstrip('/')
                    })
                except Exception as e:
                    st.warning(f"Erreur lors du traitement de {original_name}: {e}")
        
        # Créer et ajouter le manifest CSV (avec point-virgule pour Excel FR) + Excel natif
        if manifest_data:
            manifest_df = pd.DataFrame(manifest_data)
            # CSV avec point-virgule pour Excel FR et encodage utf-8-sig (BOM)
            manifest_csv = manifest_df.to_csv(index=False, sep=';', encoding='utf-8-sig')
            zip_file.writestr('manifest.csv', manifest_csv.encode('utf-8-sig'))
            
            # Ajouter aussi un fichier Excel natif (.xlsx) pour compatibilité Excel 2010
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                manifest_df.to_excel(writer, index=False, sheet_name='Manifest')
            excel_buffer.seek(0)
            zip_file.writestr('manifest.xlsx', excel_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue(), pd.DataFrame(manifest_data)

# -------------------- Interface Utilisateur --------------------
st.title("📄 Analyseur de CVs Intelligent")
display_commit_info()
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil", "📖 Guide des Méthodes", "📈 Statistiques de Feedback", "🗂️ Auto-classification"])

with tab1:
    st.markdown("### 📄 Informations du Poste")
    col1, col2 = st.columns([2, 1])
    with col1:
        # Menu déroulant pour choisir entre annonce et fiche de poste
        job_source = st.selectbox(
            "Source des informations du poste",
            ["Annonce (saisie manuelle)", "Fiche de poste (PDF)"],
            index=0
        )
        
        job_title = ""
        job_description = ""
        fiche_poste_text = ""
        
        if job_source == "Annonce (saisie manuelle)":
            job_title = st.text_input("Intitulé du poste", placeholder="Ex: Archiviste Junior")
            job_description = st.text_area("Description du poste", height=200, key="jd_ranking", placeholder="Collez la description...")
        else:  # Fiche de poste (PDF)
            fiche_poste_file = st.file_uploader("Importer une fiche de poste (PDF)", type=["pdf"], key="fiche_poste_uploader")
            if fiche_poste_file:
                fiche_poste_text = extract_text_from_pdf(fiche_poste_file)
                if fiche_poste_text and not fiche_poste_text.startswith("Erreur"):
                    # Use the fiche content silently (no success toast)
                    job_description = fiche_poste_text  # Utiliser le contenu de la fiche comme description
                else:
                    st.error("Erreur lors de la lecture de la fiche de poste.")
                    
    with col2:
        st.markdown("#### 📤 Importer des CVs")
        uploaded_files_ranking = st.file_uploader("Importer des CVs", type=["pdf"], accept_multiple_files=True, key="ranking_uploader")
    
    st.markdown("---")
    
    analysis_method = st.radio(
        "✨ Choisissez votre méthode de classement",
        ["Méthode Cosinus (Mots-clés)", "Méthode Sémantique (Embeddings)", "Scoring par Règles (Regex)", 
         "Analyse combinée (Ensemble)", "Analyse par IA (DeepSeek)", "Analyse par IA (Gemini)"],
        index=0, help="Consultez l'onglet 'Guide des Méthodes'."
    )
    
    # Options supplémentaires pour l'analyse combinée
    if analysis_method == "Analyse combinée (Ensemble)":
        st.markdown("### 🔢 Paramètres de combinaison")
        col1, col2, col3 = st.columns(3)
        with col1:
            cosinus_weight = st.slider("Poids Cosinus", 0.0, 1.0, 0.2, 0.1, key="slider_cosinus")
        with col2:
            semantic_weight = st.slider("Poids Sémantique", 0.0, 1.0, 0.4, 0.1, key="slider_semantic")
        with col3:
            rules_weight = st.slider("Poids Règles", 0.0, 1.0, 0.4, 0.1, key="slider_rules")
            
        # Normalisation des poids
        total_weight = cosinus_weight + semantic_weight + rules_weight
        if total_weight > 0:
            norm_cosinus = cosinus_weight / total_weight
            norm_semantic = semantic_weight / total_weight
            norm_rules = rules_weight / total_weight
            st.info(f"Poids normalisés : Cosinus {norm_cosinus:.2f}, Sémantique {norm_semantic:.2f}, Règles {norm_rules:.2f}")
        else:
            st.warning("Veuillez attribuer un poids non nul à au moins une méthode.")
    
    # Options pour le traitement par lots
    use_batch_processing = False
    if len(uploaded_files_ranking or []) > 20:
        use_batch_processing = st.checkbox("Activer le traitement par lots (recommandé pour plus de 20 CVs)", 
                                         value=True, 
                                         help="Traite les CVs par petits groupes pour éviter les problèmes de mémoire")
        if use_batch_processing:
            batch_size = st.slider("Taille du lot", min_value=5, max_value=50, value=10, 
                                  help="Nombre de CVs traités simultanément")

    if st.button("🔍 Analyser et Classer", type="primary", width="stretch", disabled=not (uploaded_files_ranking and job_description)):
        # Sauvegarder les informations pour le feedback
        st.session_state.last_analysis_method = analysis_method
        st.session_state.last_job_title = job_title
        st.session_state.last_job_description = job_description
        st.session_state.last_cv_count = len(uploaded_files_ranking)
        
        # Traitement standard ou par lots selon le nombre de CVs
        if use_batch_processing:
            # Créer une barre de progression
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            def update_progress(progress):
                progress_placeholder.text(f"Traitement en cours... {int(progress * 100)}%")
                progress_bar.progress(progress)
            
            # Traitement par lots
            results, file_names = batch_process_resumes(
                job_description=job_description,
                file_list=uploaded_files_ranking,
                analysis_method=analysis_method,
                batch_size=batch_size,
                progress_callback=update_progress,
                extract_text_from_pdf_func=extract_text_from_pdf,
                rank_resumes_funcs={
                    'cosine': rank_resumes_with_cosine,
                    'embeddings': rank_resumes_with_embeddings,
                    'rules': rank_resumes_with_rules,
                    'ai': rank_resumes_with_ai,
                    'ensemble': lambda jd, res, fnames, **kwargs: rank_resumes_with_ensemble(
                        jd, res, fnames,
                        cosine_func=rank_resumes_with_cosine,
                        semantic_func=rank_resumes_with_embeddings,
                        rules_func=rank_resumes_with_rules,
                        **kwargs
                    )
                }
            )
            
            explanations = results.get("explanations")
            logic = results.get("logic")
            
            # Nettoyer la barre de progression
            progress_placeholder.empty()
            progress_bar.empty()
            
        else:
            # Lecture des fichiers PDF
            resumes, file_names = [], []
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            total_files = len(uploaded_files_ranking)
            
            for idx, file in enumerate(uploaded_files_ranking):
                progress_placeholder.info(f"📄 Lecture du fichier ({idx+1}/{total_files}) : {file.name}")
                progress_bar.progress((idx + 1) / total_files * 0.3)  # 30% pour lecture
                text = extract_text_from_pdf(file)
                if not "Erreur" in text:
                    resumes.append(text)
                    file_names.append(file.name)
            
            # Analyse selon la méthode choisie
            results, explanations, logic = {}, None, None
            
            
            if analysis_method == "Analyse par IA (Gemini)":
                progress_placeholder.info(f"🤖 Analyse Gemini en cours...")
                result = rank_resumes_with_gemini(job_description, resumes, file_names)
                results = {"scores": result["scores"], "explanations": result["explanations"]}
                explanations = result["explanations"]
                progress_bar.progress(1.0)

            elif analysis_method == "Analyse par IA (DeepSeek)":
                # Analyse IA avec progression individuelle
                progress_placeholder.info(f"🤖 Analyse par IA en cours (0/{len(resumes)})...")
                progress_bar.progress(0.3)
                
                scores_data = []
                for i, resume_text in enumerate(resumes):
                    progress_placeholder.info(f"🤖 Analyse par IA ({i+1}/{len(resumes)}) : {file_names[i]}")
                    progress_bar.progress(0.3 + (i + 1) / len(resumes) * 0.7)
                    scores_data.append(get_detailed_score_with_ai(job_description, resume_text))
                
                results = {"scores": [d["score"] for d in scores_data], "explanations": {file_names[i]: d["explanation"] for i, d in enumerate(scores_data)}}
                explanations = results.get("explanations")

            
            elif analysis_method == "Scoring par Règles (Regex)":
                progress_placeholder.info(f"📏 Analyse par règles en cours...")
                rule_results = rank_resumes_with_rules(job_description, resumes, file_names)
                results = {"scores": [r["score"] for r in rule_results]}
                logic = {r["file_name"]: r["logic"] for r in rule_results}
                progress_bar.progress(1.0)
            
            elif analysis_method == "Méthode Sémantique (Embeddings)":
                progress_placeholder.info(f"🧠 Analyse sémantique en cours...")
                results = rank_resumes_with_embeddings(job_description, resumes, file_names)
                logic = results.get("logic")
                progress_bar.progress(1.0)
            
            elif analysis_method == "Analyse combinée (Ensemble)":
                progress_placeholder.info(f"🔗 Analyse combinée en cours...")
                results = rank_resumes_with_ensemble(
                    job_description, resumes, file_names,
                    cosinus_weight=cosinus_weight,
                    semantic_weight=semantic_weight,
                    rules_weight=rules_weight,
                    cosine_func=rank_resumes_with_cosine,
                    semantic_func=rank_resumes_with_embeddings,
                    rules_func=rank_resumes_with_rules
                )
                logic = results.get("logic")
                progress_bar.progress(1.0)
            
            else:  # Méthode Cosinus par défaut
                progress_placeholder.info(f"📐 Analyse cosinus en cours...")
                results = rank_resumes_with_cosine(job_description, resumes, file_names)
                logic = results.get("logic")
                progress_bar.progress(1.0)

            # Nettoyer les indicateurs de progression
            progress_placeholder.empty()
            progress_bar.empty()

            scores = results.get("scores", [])
            if scores is not None and len(scores) > 0:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                results_df = pd.DataFrame(ranked_resumes, columns=["Nom du CV", "Score brut"])
                results_df["Rang"] = range(1, len(results_df) + 1)
                results_df["Score"] = results_df["Score brut"].apply(lambda x: f"{x*100:.1f}%")
                
                # Sauvegarder les résultats dans la session pour maintenir l'affichage
                st.session_state.last_analysis_result = results_df
                st.session_state.last_analysis_method = analysis_method
                st.session_state.ranked_resumes = ranked_resumes
                st.session_state.file_names = file_names
                st.session_state.scores = scores
                st.session_state.logic = logic
                st.session_state.job_title = job_title
                st.session_state.job_description = job_description
                st.session_state.last_job_title = job_title
                st.session_state.last_job_description = job_description
                st.session_state.last_file_names = file_names
                st.session_state.explanations = explanations
                
            else:
                st.error("L'analyse n'a retourné aucun score.")

    # Affichage des résultats (toujours visible, même après feedback)
    if hasattr(st.session_state, 'last_analysis_result') and st.session_state.last_analysis_result is not None:
        results_df = st.session_state.last_analysis_result
        ranked_resumes = st.session_state.ranked_resumes
        logic = getattr(st.session_state, 'logic', None)
        explanations = getattr(st.session_state, 'explanations', None)
        
        st.markdown("### 🏆 Résultats du Classement")
        st.dataframe(results_df[["Rang", "Nom du CV", "Score"]], width="stretch", hide_index=True)
        
        if logic:
            st.markdown("### 🧠 Logique de Scoring")
            for _, row in results_df.iterrows():
                file_name = row["Nom du CV"]
                with st.expander(f"Détail du score pour : **{file_name}**"):
                    st.json(logic.get(file_name, {}))

        if explanations:
            st.markdown("### 📝 Analyse détaillée par l'IA")
            for _, row in results_df.iterrows():
                file_name = row["Nom du CV"]
                with st.expander(f"Analyse pour : **{file_name}**"):
                    explanation = explanations.get(file_name, "N/A")
                    import re
                    
                    # Extraction et affichage du score
                    score_match = re.search(r"score(?: de correspondance)?\s*:\s*(\d+)\s*%", explanation, re.IGNORECASE)
                    if score_match:
                        st.markdown(f"**Score : {score_match.group(1)}%**")
                    
                    # Nouvelle approche : affichage complet avec troncature intelligente
                    def smart_truncate(text, max_length=1000):
                        """Tronque intelligemment le texte en gardant le sens"""
                        if len(text) <= max_length:
                            return text
                        
                        # Cherche le dernier point, point d'exclamation ou d'interrogation avant la limite
                        truncate_pos = max_length
                        for i in range(max_length, max(0, max_length-200), -1):
                            if text[i] in '.!?':
                                truncate_pos = i + 1
                                break
                        
                        return text[:truncate_pos].strip() + "..."
                    
                    # Afficher l'explication complète avec troncature intelligente
                    cleaned_explanation = explanation.replace("Score:", "").replace(f"{score_match.group(1)}%" if score_match else "", "").strip()
                    st.markdown(smart_truncate(cleaned_explanation))
        
        # Système de feedback par CV avec formulaires pour éviter les rechargements
        st.markdown("---")
        st.markdown("### 💬 Feedback sur les résultats")
        
        for i, (file_name, score) in enumerate(ranked_resumes):
            with st.expander(f"💬 Évaluer le classement de : {file_name}"):
                feedback_key = f"feedback_form_{i}"
                submitted_key = f"submitted_{i}"
                
                # Vérifier si le feedback pour ce CV a déjà été soumis
                if submitted_key not in st.session_state:
                    st.session_state[submitted_key] = False
                
                # Si déjà soumis, afficher un message de confirmation
                if st.session_state[submitted_key]:
                    st.success(f"✅ Merci pour votre feedback sur {file_name} !")
                else:
                    # Créer un formulaire pour chaque CV pour éviter les rechargements
                    with st.form(key=feedback_key):
                        st.markdown(f"#### 📊 Évaluation du CV : {file_name}")
                        st.caption(f"Score actuel : {score*100:.1f}%")

                        # Slider pour la notation (1-5)
                        cv_feedback_score = st.slider(
                            f"Note pour {file_name} (1 = Très insatisfaisant, 5 = Excellent)",
                            min_value=1,
                            max_value=5,
                            value=3,
                            step=1,
                            key=f"cv_rating_{i}",
                            help="Glissez pour donner votre note"
                        )

                        # Affichage visuel de la note
                        score_labels = {
                            1: "⭐ Très insatisfaisant",
                            2: "⭐⭐ Insatisfaisant",
                            3: "⭐⭐⭐ Acceptable",
                            4: "⭐⭐⭐⭐ Satisfaisant",
                            5: "⭐⭐⭐⭐⭐ Excellent"
                        }
                        cv_feedback_text = st.text_area(
                            "Commentaires spécifiques (optionnel)",
                            placeholder=f"Points forts/faibles du classement de {file_name}...",
                            height=80,
                            key=f"cv_comment_{i}"
                        )

                        # Bouton de soumission avec style amélioré
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            cv_submit_button = st.form_submit_button(
                                label=f"📤 Évaluer",
                                type="secondary"
                            )
                        
                        if cv_submit_button:
                            job_title = getattr(st.session_state, 'job_title', '')
                            job_description = getattr(st.session_state, 'job_description', '')
                            analysis_method = getattr(st.session_state, 'last_analysis_method', '')
                            
                            result = save_feedback(
                                analysis_method=f"{analysis_method} (CV individuel)",
                                job_title=job_title,
                                job_description_snippet=job_description[:200],
                                cv_count=1,
                                feedback_score=cv_feedback_score,
                                feedback_text=f"Feedback pour {file_name}: {cv_feedback_text}"
                            )
                            st.session_state[submitted_key] = True
                            if result:
                                st.success(f"✅ Merci pour votre feedback sur {file_name} !")
                                st.rerun()
                            else:
                                st.error("❌ Échec de l'enregistrement du feedback.")
        
        # Feedback global sur l'analyse
        st.markdown("---")
        st.markdown("### 🌟 Feedback global sur l'analyse")

        # Formulaire de feedback global directement visible
        if not getattr(st.session_state, 'feedback_submitted', False):
            with st.form(key='feedback_form'):
                st.markdown("**Comment évaluez-vous la qualité globale des résultats de cette analyse ?**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Slider pour la notation (1-5)
                    global_feedback_score = st.slider(
                        "Note globale (1 = Très insatisfaisant, 5 = Excellent)",
                        min_value=1,
                        max_value=5,
                        value=3,
                        step=1,
                        help="Glissez pour donner votre note"
                    )

                    # Critères d'évaluation spécifiques
                    st.markdown("**Critères évalués :**")
                    user_criteria = st.multiselect(
                        "Sélectionnez les critères :",
                        options=[
                            "Pertinence du classement",
                            "Clarté de la logique d'analyse",
                            "Rapidité d'exécution",
                            "Facilité d'utilisation",
                            "Précision des scores",
                            "Qualité des explications",
                            "Autre"
                        ],
                        default=[],
                        help="Tous les critères qui s'appliquent"
                    )
                    
                with col2:
                    # Champ pour les commentaires
                    global_feedback_text = st.text_area(
                        "Commentaires et suggestions d'amélioration (optionnel)",
                        placeholder="Qu'avez-vous apprécié ? Que pourrait-on améliorer ? Quelles fonctionnalités ajouter ?",
                        height=200
                    )

                # Bouton de soumission avec style amélioré
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    submit_button = st.form_submit_button(
                        label="📤 Envoyer mon feedback",
                        type="primary",
                        width="stretch"
                    )

                if submit_button:
                    job_title = getattr(st.session_state, 'job_title', '')
                    job_description = getattr(st.session_state, 'job_description', '')
                    analysis_method = getattr(st.session_state, 'last_analysis_method', '')
                    file_names = getattr(st.session_state, 'file_names', [])

                    criteria_text = ", ".join(user_criteria) if user_criteria else ""

                    result = save_feedback(
                        analysis_method=analysis_method,
                        job_title=job_title,
                        job_description_snippet=job_description,
                        cv_count=len(file_names),
                        feedback_score=global_feedback_score,
                        feedback_text=global_feedback_text,
                        user_criteria=criteria_text,
                        improvement_suggestions=global_feedback_text
                    )
                    st.session_state.feedback_submitted = True
                    if result:
                        st.success("✅ Merci pour votre feedback ! Il nous aidera à améliorer notre système.")
                        st.balloons()  # Animation festive
                        st.rerun()
                    else:
                        st.error("❌ Échec de l'enregistrement du feedback.")

        # Message si le feedback a déjà été soumis
        elif getattr(st.session_state, 'feedback_submitted', False):
            st.success("✅ Merci pour votre feedback ! Il nous aidera à améliorer notre système.")

with tab2:
    st.markdown("### 📂 Importer un ou plusieurs CVs")
    uploaded_files_analysis = st.file_uploader("Importer des CVs", type=["pdf"], key="analysis_uploader_single", accept_multiple_files=True)
    
    analysis_type_single = st.selectbox(
        "Type d'analyse souhaité",
        ("Analyse par IA (DeepSeek)", "Analyse par IA (Gemini)", "Analyse par Regex (Extraction d'entités)", "Analyse par la Méthode Sémantique", 
         "Analyse par la Méthode Cosinus", "Analyse Combinée (Ensemble)")
    )
    captions = {
        "Analyse par IA (DeepSeek)": "Analyse qualitative (points forts/faibles).",
        "Analyse par IA (Gemini)": "Analyse par Google Gemini (Rapide & Performant).",
        "Analyse par Regex (Extraction d'entités)": "Extrait des informations structurées (compétences, diplômes, etc.).",
        "Analyse par la Méthode Sémantique": "Calcule un score de pertinence basé sur le sens (nécessite une description de poste).",
        "Analyse par la Méthode Cosinus": "Calcule un score de pertinence basé sur les mots-clés (nécessite une description de poste).",
        "Analyse Combinée (Ensemble)": "Combine plusieurs méthodes d'analyse pour un score plus robuste (nécessite une description de poste)."
    }
    st.caption(captions.get(analysis_type_single))

    job_desc_single = ""
    if "Analyse par la Méthode" in analysis_type_single or "Analyse Combinée" in analysis_type_single:
        job_desc_single = st.text_area("Description de poste pour le calcul du score", height=150, key="jd_single")

    if uploaded_files_analysis and st.button("🚀 Lancer l'analyse", type="primary", width="stretch", key="btn_single_analysis"):
        total_files = len(uploaded_files_analysis)
        progress_bar_tab2 = st.progress(0)
        progress_text_tab2 = st.empty()
        
        for file_idx, uploaded_file in enumerate(uploaded_files_analysis):
            progress_text_tab2.info(f"🤖 Analyse en cours ({file_idx+1}/{total_files}) : {uploaded_file.name}")
            progress_bar_tab2.progress((file_idx + 1) / total_files)
            
            with st.expander(f"Résultat pour : **{uploaded_file.name}**", expanded=True):
                text = extract_text_from_pdf(uploaded_file)
                if "Erreur" in text or (text and text.strip().startswith("Aucun texte lisible trouvé")):
                    # Message clair pour les PDFs scannés ou protégés
                    if text and text.strip().startswith("Aucun texte lisible trouvé"):
                        st.error("❌ Aucun texte lisible trouvé dans le PDF. Il s'agit probablement d'un PDF scanné (images) ou protégé.\n💡 Collez manuellement le contenu ou utilisez un OCR externe (ex: tesseract) pour convertir le PDF en texte.")
                    else:
                        st.error(f"❌ {text}")
                else:
                    if analysis_type_single == "Analyse par Regex (Extraction d'entités)":
                        entities = regex_analysis(text)
                        st.info("**Entités extraites par la méthode Regex**")
                        st.json(entities)
                    elif "Méthode Sémantique" in analysis_type_single:
                        if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                        else:
                            result = rank_resumes_with_embeddings(job_desc_single, [text], [uploaded_file.name])
                            score = result["scores"][0]
                            st.metric("Score de Pertinence Sémantique", f"{score*100:.1f}%")
                    elif "Méthode Cosinus" in analysis_type_single:
                        if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                        else:
                            result = rank_resumes_with_cosine(job_desc_single, [text], [uploaded_file.name])
                            score = result["scores"][0]
                            st.metric("Score de Pertinence Cosinus", f"{score*100:.1f}%")
                    elif "Analyse Combinée" in analysis_type_single:
                        if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                        else:
                            result = rank_resumes_with_ensemble(
                                job_desc_single, [text], [uploaded_file.name],
                                cosinus_weight=0.2, semantic_weight=0.4, rules_weight=0.4,
                                cosine_func=rank_resumes_with_cosine,
                                semantic_func=rank_resumes_with_embeddings,
                                rules_func=rank_resumes_with_rules
                            )
                            score = result["scores"][0]
                            st.metric("Score de Pertinence Combinée", f"{score*100:.1f}%")
                            
                            # Affichage de la logique si disponible
                            if "logic" in result:
                                logic = result["logic"].get(uploaded_file.name, {})
                                if logic:
                                    st.markdown("**Détail de l'analyse combinée :**")
                                    st.json(logic)
                    elif analysis_type_single == "Analyse par IA (Gemini)":
                        # Extraire le nom du candidat pour Gemini
                        extracted = extract_name_from_cv_text(text)
                        candidate_name = extracted.get('name') if extracted else None
                        
                        analysis_result = get_gemini_profile_analysis(text, candidate_name)
                        
                        st.markdown("### 🤖 Résultat de l'analyse Gemini")
                        st.markdown(analysis_result)

                    else: # Analyse IA
                        # Extraire le nom du candidat
                        extracted = extract_name_from_cv_text(text)
                        candidate_name = extracted.get('name') if extracted else None
                        analysis_result = get_deepseek_profile_analysis(text, candidate_name)
                        
                        # Affichage en 2 colonnes
                        col1, col2 = st.columns(2)
                        # Découper le résultat en sections
                        sections = analysis_result.split('**')
                        left_sections = []
                        right_sections = []
                        current_section = ""
                        section_count = 0
                        
                        for i, section in enumerate(sections):
                            if section.strip():
                                if i % 2 == 1:  # C'est un titre
                                    current_section = f"**{section}**"
                                else:  # C'est le contenu
                                    full_section = current_section + section
                                    if section_count < 3:
                                        left_sections.append(full_section)
                                    else:
                                        right_sections.append(full_section)
                                    section_count += 1
                        
                        with col1:
                            st.markdown("".join(left_sections))
                        with col2:
                            st.markdown("".join(right_sections))
        
        # Nettoyer la progression
        progress_text_tab2.empty()
        progress_bar_tab2.empty()
        st.success(f"✅ Analyse terminée pour {total_files} CV(s).")

with tab3:
    st.header("📖 Comprendre les Méthodes d'Analyse")
    st.markdown("Chaque méthode a ses propres forces et faiblesses. Voici un guide pour vous aider à choisir la plus adaptée à votre besoin.")
    
    st.subheader("1. Méthode Cosinus (Basée sur les Mots-clés)")
    st.markdown("""
    - **Principe** : Compare la fréquence des mots exacts entre le CV et l'annonce.
    - **Comment ça marche ?** Elle utilise un modèle mathématique (TF-IDF) pour donner plus de poids aux mots rares et importants. Le score représente la similarité de ces "sacs de mots-clés".
    - **Idéal pour** : Un premier tri très rapide et grossier.
    - **Avantages** : ✅ Extrêmement rapide, ne nécessite aucune IA externe.
    - **Limites** : ❌ Ne comprend absolument pas le contexte ou les synonymes.
    """)
    
    st.subheader("2. Méthode Sémantique (Basée sur les Embeddings)")
    st.markdown("""
    - **Principe** : Utilise une IA pour convertir les phrases en vecteurs de sens, puis compare ces vecteurs.
    - **Comment ça marche ?** Au lieu de comparer des mots, on compare la "direction" de ces vecteurs. Deux vecteurs qui pointent dans la même direction représentent des idées sémantiquement similaires.
    - **Idéal pour** : Obtenir un score plus intelligent qui comprend les nuances du langage.
    - **Avantages** : ✅ Comprend le contexte et les synonymes. Excellent équilibre entre vitesse et intelligence.
    - **Limites** : ❌ Un peu plus lente que la méthode cosinus.
    """)

    st.subheader("3. Scoring par Règles (Basé sur Regex)")
    st.markdown("""
    - **Principe** : Imite la façon dont un recruteur humain lit un CV. On définit des règles claires (compétences, expérience, diplôme) et on attribue des points.
    - **Comment ça marche ?** Le code extrait dynamiquement les exigences de l'annonce, puis recherche ces éléments dans chaque CV pour calculer un score.
    - **Idéal pour** : Des postes où les critères sont très clairs et objectifs.
    - **Avantages** : ✅ Totalement transparent (le détail du score est affiché), 100% personnalisable et sans dépendances complexes.
    - **Limites** : ❌ Très rigide. Si une compétence est formulée différemment, elle ne sera pas détectée.
    """)
    
    st.subheader("4. Analyse par IA (Basée sur un LLM)")
    st.markdown("""
    - **Principe** : On envoie le CV et l'annonce à un grand modèle de langage (DeepSeek) en lui demandant d'agir comme un expert en recrutement.
    - **Comment ça marche ?** L'IA lit et comprend les deux textes, puis utilise sa vaste connaissance pour évaluer la pertinence et formuler une explication.
    - **Idéal pour** : Obtenir une analyse fine et contextuelle, similaire à celle d'un premier entretien.
    - **Avantages** : ✅ La plus précise et la plus "humaine". Comprend les nuances et fournit des explications de haute qualité.
    - **Limites** : ❌ La plus lente, et chaque analyse **consomme vos tokens !**
    """)
    
    st.subheader("5. Analyse combinée (Ensemble)")
    st.markdown("""
    - **Principe** : Combine plusieurs méthodes d'analyse (Cosinus, Sémantique, Règles) en un seul score pondéré.
    - **Comment ça marche ?** Chaque CV est analysé selon les trois méthodes, puis les scores sont multipliés par les poids attribués à chaque méthode et additionnés.
    - **Idéal pour** : Obtenir un classement plus équilibré qui tire parti des forces de chaque méthode. Réduire les faux positifs et les faux négatifs.
    - **Avantages** : ✅ Plus robuste face aux biais de chaque méthode individuelle. Hautement personnalisable via les poids attribués. Fournit des explications détaillées.
    - **Limites** : ❌ Plus lent que les méthodes individuelles (mais plus rapide que l'analyse par IA). Complexité accrue.
    
    ##### Comment ajuster les poids ?
    - **Augmentez le poids Cosinus** lorsque les mots-clés exacts sont très importants (termes techniques spécifiques).
    - **Augmentez le poids Sémantique** pour les postes créatifs ou les compétences transversales, où la compréhension du contexte est cruciale.
    - **Augmentez le poids Règles** pour les postes avec des exigences formelles strictes en termes d'expérience ou de diplômes.
    """)

with tab4:


    # Récupération des statistiques (pré-chargement à l'ouverture de l'onglet)
    feedback_stats = get_feedback_summary()

    if len(feedback_stats) > 0:
        # Métriques principales
        st.subheader("📈 Métriques Clés")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_feedbacks = feedback_stats["Nombre d'évaluations"].sum()
            st.metric("Total Feedbacks", total_feedbacks, help="Nombre total d'évaluations reçues")

        with col2:
            avg_score = (feedback_stats["Score moyen"] * feedback_stats["Nombre d'évaluations"]).sum() / total_feedbacks
            st.metric("Score Moyen Global", f"{avg_score:.2f}/5", help="Satisfaction moyenne globale")

        with col3:
            best_method = feedback_stats.loc[feedback_stats["Score moyen"].idxmax()]
            st.metric("Meilleure Méthode", best_method["Méthode"].split(" (")[0], help=f"Score: {best_method['Score moyen']:.2f}/5")

        with col4:
            most_used = feedback_stats.loc[feedback_stats["Nombre d'évaluations"].idxmax()]
            evaluations_count = most_used["Nombre d'évaluations"]
            st.metric("Top", most_used["Méthode"].split(" (")[0], help=f"{evaluations_count} évaluations")

        st.markdown("---")

        # Graphiques améliorés
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🌟 Satisfaction par Méthode")
            # Filtrer uniquement les méthodes avec des évaluations
            feedback_with_evals = feedback_stats[feedback_stats["Nombre d'évaluations"] > 0]

            if not feedback_with_evals.empty:
                # Graphique en barres horizontales avec couleurs
                fig_scores = go.Figure()
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

                for i, (_, row) in enumerate(feedback_with_evals.iterrows()):
                    fig_scores.add_trace(go.Bar(
                        x=[row["Score moyen"]],
                        y=[row["Méthode"]],
                        orientation='h',
                        name=row["Méthode"],
                        marker_color=colors[i % len(colors)],
                        showlegend=False
                    ))

                fig_scores.update_layout(
                    title="Score moyen par méthode (sur 5)",
                    height=max(300, len(feedback_with_evals) * 40),
                    margin={"l": 200, "r": 20, "t": 40, "b": 20},
                    xaxis={"range": [0, 5], "title": "Score moyen"},
                    yaxis={"title": ""},
                )

                st.plotly_chart(fig_scores, width="stretch")

        with col2:
            st.subheader("📊 Distribution des Évaluations")
            if not feedback_with_evals.empty:
                # Camembert avec pourcentages
                fig_evals = go.Figure(data=[go.Pie(
                    labels=feedback_with_evals["Méthode"],
                    values=feedback_with_evals["Nombre d'évaluations"],
                    marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'],
                    textinfo='label+percent',
                    hovertemplate="<b>%{label}</b><br>%{value} évaluations (%{percent})<extra></extra>"
                )])

                fig_evals.update_layout(
                    title="Répartition des feedbacks par méthode",
                    height=400,
                    margin={"l": 20, "r": 20, "t": 40, "b": 20},
                    font=dict(size=14),
                    legend=dict(font=dict(size=16))
                )

                st.plotly_chart(fig_evals, width="stretch")

        st.markdown("---")

        # Tableau détaillé avec style amélioré
        st.subheader("📋 Détails des Statistiques")

        # Préparer les données pour l'affichage
        display_stats = feedback_stats.copy()
        display_stats["Score Formaté"] = display_stats.apply(lambda row: 
            f"{row['Score moyen']:.2f}/5 {'🟢' if row['Score moyen'] >= 4.0 else '🟡' if row['Score moyen'] >= 3.0 else '🔴'}", axis=1)
        display_stats["Fiabilité"] = display_stats["Nombre d'évaluations"].apply(
            lambda x: "Très fiable 🎯" if x >= 10 else "À confirmer ⚠️" if x >= 5 else "Données limitées 📊")
        
        # Afficher le tableau avec colonnes formatées
        st.dataframe(
            display_stats[["Méthode", "Score Formaté", "Nombre d'évaluations", "Fiabilité"]],
            column_config={
                "Méthode": st.column_config.TextColumn("Méthode d'Analyse", width="medium"),
                "Score Formaté": st.column_config.TextColumn("Score Moyen", width="small"),
                "Nombre d'évaluations": st.column_config.NumberColumn("Évaluations", width="small"),
                "Fiabilité": st.column_config.TextColumn("Fiabilité", width="medium")
            },
            hide_index=True,
            width="stretch"
        )

        # Insights et recommandations
        st.markdown("---")
        st.subheader("💡 Insights & Recommandations")

        if len(feedback_with_evals) > 1:
            best_method = feedback_with_evals.loc[feedback_with_evals["Score moyen"].idxmax()]
            worst_method = feedback_with_evals.loc[feedback_with_evals["Score moyen"].idxmin()]

            # Assurer un scalaire numérique pour l'écart de score (aide Pylance)
            best_score = cast(float, best_method["Score moyen"])
            worst_score = cast(float, worst_method["Score moyen"])

            col1, col2 = st.columns(2)

            with col1:
                st.success(f"🏆 **Meilleure méthode** : {best_method['Méthode']} avec un score de {best_score:.2f}/5")
                st.info("💭 **Recommandation** : Priorisez cette méthode pour vos analyses futures.")

            with col2:
                if best_score - worst_score > 0.5:
                    st.warning(f"⚠️ **Méthode à améliorer** : {worst_method['Méthode']} (score: {worst_score:.2f}/5)")
                    st.info("💭 **Suggestion** : Collectez plus de feedbacks pour affiner cette méthode.")

        # Évolution temporelle (si assez de données)
        if total_feedbacks >= 10:
            st.subheader("📈 Évolution de la Satisfaction")
            st.info("📊 Avec plus de données, nous pourrons afficher des graphiques d'évolution temporelle de la satisfaction utilisateur.")

    else:
        # Interface vide avec call-to-action
        st.info("Aucun feedback n'a encore été enregistré.")
        st.markdown("""
        <div style='margin-top:1em;'>
        <b>Comment ça marche :</b><br>
        1. Effectuez des analyses de CV<br>
        2. Évaluez les résultats obtenus<br>
        3. Les statistiques s'affichent automatiquement ici
        </div>
        """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔧 Configuration")
    if st.button("Test Connexion IA (DeepSeek & Gemini)"):
        # Test DeepSeek
        ds_key = get_api_key()
        if ds_key:
            try:
                response = requests.get("https://api.deepseek.com/v1/models", headers={"Authorization": f"Bearer {ds_key}"})
                if response.status_code == 200:
                    st.success("✅ DeepSeek : Connecté")
                else:
                    st.error(f"❌ DeepSeek : Erreur {response.status_code}")
            except Exception as e:
                st.error(f"❌ DeepSeek : {e}")
        else:
            st.warning("⚠️ DeepSeek : Clé manquante")
            
        # Test Gemini
        gem_key = get_gemini_api_key()
        if gem_key:
            try:
                genai.configure(api_key=gem_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Ping")
                if response:
                     st.success("✅ Gemini : Connecté")
            except Exception as e:
                st.error(f"❌ Gemini : {e}")
        else:
             st.warning("⚠️ Gemini : Clé manquante")

with tab5:
    st.header("🗂️ Auto-classification de CVs (3 catégories)")
    st.markdown("Chargez jusqu'à 100 CVs (PDF). L'outil extrait le texte et classe automatiquement chaque CV dans l'une des 3 catégories : Fonctions supports, Logistique, Production/Technique.")

    # Importer des CVs uniquement via upload
    uploaded_files_auto = st.file_uploader("Importer des CVs (PDF)", type=["pdf"], accept_multiple_files=True, key="auto_uploader")

    # Construire la liste de fichiers uniquement à partir des uploads
    file_list = []
    if uploaded_files_auto:
        for uf in uploaded_files_auto:
            file_list.append({'name': uf.name, 'file': uf})

    # Afficher immédiatement combien de CVs ont été uploadés
    if len(file_list) > 0:
        st.success(f"✅ {len(file_list)} CV(s) uploadé(s) et prêts pour traitement.")
        # Message d'instruction supprimé

        # Limiter à 200 pour sécurité
        if len(file_list) > 200:
            st.warning('Plus de 200 CVs trouvés. Seuls les 200 premiers seront traités.')
            file_list = file_list[:200]

        # Initialiser les variables de session pour la classification et l'analyse DeepSeek
        if 'classification_results' not in st.session_state:
            st.session_state.classification_results = None
        if 'deepseek_analyses' not in st.session_state:
            st.session_state.deepseek_analyses = []
        if 'last_action' not in st.session_state:
            st.session_state.last_action = None
        
        # Afficher un indicateur de statut si une action a été effectuée précédemment
        if st.session_state.last_action:
            action_message = {
                "classified": "✅ CVs classifiés avec succès ! Vous pouvez maintenant analyser les CVs non classés avec l'IA.",
                "analyzed": "✅ CVs non classés analysés avec DeepSeek IA !",
                "reset": "🔄 Analyses IA réinitialisées."
            }
            st.success(action_message.get(st.session_state.last_action, ""))
            # Réinitialiser pour ne pas afficher le message à chaque rechargement
            st.session_state.last_action = None
        
        # Option pour renommer et organiser les CV
        rename_and_organize = st.checkbox(
            "📁 Renommer les CV et organiser par dossiers",
            help="Extrait automatiquement les noms des candidats et organise les CV par catégorie dans un fichier ZIP"
        )

        # Choix du modèle IA pour la classification
        classif_model = st.radio("Modèle IA pour la classification", ["DeepSeek", "Gemini"], horizontal=True)
        
        # Bouton de classification primaire
        if st.button("📂 Lancer l'auto-classification", type='primary'):
            # Réinitialiser les analyses DeepSeek lors d'une nouvelle classification
            st.session_state.deepseek_analyses = []
            
            results = []
            progress = st.progress(0)
            total = len(file_list)
            # placeholder pour afficher le fichier en cours de traitement
            processing_placeholder = st.empty()
            spinner_text = 'Extraction, classification et extraction des noms en cours...' if rename_and_organize else 'Extraction et classification en cours...'
            
            with st.spinner(spinner_text):
                for i, item in enumerate(file_list):
                    f = item['file']
                    name = item['name']
                    # Mettre à jour le fichier en cours
                    processing_placeholder.info(f"Traitement ({i+1}/{total}) : {name}")
                    try:
                        text = extract_text_from_pdf(f)
                    except Exception:
                        text = ''

                    # --- NOUVELLE LOGIQUE D'EXTRACTION DE NOM ---
                    # 1. Extraction locale intelligente (Email Cross-Check)
                    local_extraction = extract_name_smart_email(text)
                    extracted_name_info = local_extraction
                    
                    if not extracted_name_info:
                         # Fallback sur l'ancienne méthode regex
                         extracted_name_info = extract_name_from_cv_text(text) if text else None

                    # Détermination du nom à envoyer à l'IA comme indice
                    if extracted_name_info and extracted_name_info.get('name'):
                        display_name = extracted_name_info['name']
                    else:
                        display_name = os.path.splitext(name)[0]

                    # Classification principale 100% via IA (macro + sous-cat + récap)
                    text_for_ai = (text or '')[:3000]
                    
                    if classif_model == "Gemini":
                        classification = get_gemini_auto_classification(text_for_ai, display_name)
                    else:
                        classification = get_deepseek_auto_classification(text_for_ai, display_name)

                    cat = classification.get('macro_category', 'Non classé')
                    sub_cat = classification.get('sub_category', 'Autre')
                    profile_summary = classification.get('profile_summary', '')
                    years_exp = classification.get('years_experience', 0)
                    
                    # Mise à jour du nom extrait si l'IA en a trouvé un meilleur
                    ai_name = classification.get('candidate_name')
                    # On fait confiance à l'IA si elle a trouvé un nom différent de "Candidat" et qu'on n'avait pas de certitude absolue (0.99)
                    if ai_name and "Candidat" not in ai_name and "Erreur" not in ai_name:
                         # Si notre méthode locale n'était pas sûre à 99% (smart email), on prend celle de l'IA
                         if not (extracted_name_info and extracted_name_info.get('confidence', 0) >= 0.99):
                            extracted_name_info = {
                                "name": ai_name,
                                "confidence": 1.0,
                                "method_used": f"{classif_model}_Refined"
                            }

                    result_item = {
                        'file': name,
                        'category': cat,
                        'sub_category': sub_cat,
                        'years_experience': years_exp,
                        'profile_summary': profile_summary,
                        'text_snippet': (text or '')[:800],
                        'full_text': text  # Garder le texte complet pour le ZIP
                    }

                    # Conserver l'info de nom extrait pour le ZIP si demandé
                    if extracted_name_info:
                        result_item['extracted_name'] = extracted_name_info

                    results.append(result_item)
                    progress.progress((i+1)/total)

            # Nettoyer le placeholder
            processing_placeholder.empty()

            # Stocker les résultats de classification dans la session state
            st.session_state.classification_results = results
            st.session_state.rename_and_organize_option = rename_and_organize
            st.session_state.uploaded_files_list = file_list  # Stocker pour le ZIP
            st.session_state.last_action = "classified"
        
        # Si des résultats de classification existent (soit de l'action actuelle ou précédente), les afficher
        if st.session_state.classification_results:
            # Convertir les résultats en DataFrame
            df = pd.DataFrame(st.session_state.classification_results)
            
            # Calcul des statistiques pour le message de résumé
            num_total = len(df)
            num_supports = len(df[df['category'] == 'Fonctions supports'])
            num_logistics = len(df[df['category'] == 'Logistique'])
            num_production = len(df[df['category'] == 'Production/Technique'])
            num_unclassified = len(df[df['category'] == 'Non classé'])
            num_classified = num_total - num_unclassified
            
            # Message de succès avec statistiques et pourcentages
            percent_classified = int(round(num_classified / num_total * 100)) if num_total > 0 else 0
            percent_unclassified = int(round(num_unclassified / num_total * 100)) if num_total > 0 else 0
            st.success(f"✅ Traitement terminé : {num_total} CV(s) traité(s), dont {num_classified} ({percent_classified}%) classé(s) et {num_unclassified} ({percent_unclassified}%) non classé(s).")
            
            # Utiliser le DataFrame pour l'affichage
            display_df = df.copy()

            # Préparer un nom d'affichage par ligne (nom extrait si dispo, sinon nom de fichier sans extension)
            def _get_display_name_for_row(row):
                extracted = row.get('extracted_name')
                if isinstance(extracted, dict) and extracted.get('name'):
                    return extracted['name']
                return os.path.splitext(row['file'])[0]

            display_df['display_name'] = display_df.apply(_get_display_name_for_row, axis=1)

            # Affichage en 3 colonnes avec panneaux repliables par sous-catégorie
            cols = st.columns(3)
            cats = ['Fonctions supports', 'Logistique', 'Production/Technique']
            for idx, cat_label in enumerate(cats):
                with cols[idx]:
                    sub_df = display_df[display_df['category'] == cat_label]
                    count_cat = len(sub_df)
                    st.subheader(f"{cat_label} ({count_cat})")
                    if sub_df.empty:
                        st.write('Aucun CV classé ici.')
                    else:
                        # Regrouper par sous-catégorie (sous-direction / sous-filière)
                        sub_df = sub_df.copy()
                        if 'sub_category' in sub_df.columns:
                            sub_df['sub_category'] = sub_df['sub_category'].fillna('Autre')
                        else:
                            sub_df['sub_category'] = 'Autre'
                        subcats = sorted(sub_df['sub_category'].unique())
                        for subcat in subcats:
                            filtered = sub_df[sub_df['sub_category'] == subcat]
                            count_subcat = len(filtered)
                            with st.expander(f"📂 {subcat} ({count_subcat})"):
                                for _, r in filtered.iterrows():
                                    card_title = r['display_name']
                                    recap = r.get('profile_summary') or r.get('text_snippet') or ''
                                    years_exp = r.get('years_experience', 0)
                                    with st.expander(f"👤 {card_title}"):
                                        if years_exp and years_exp > 0:
                                            st.markdown(f"**📅 {years_exp} ans d'expérience**")
                                        st.markdown(recap)

            # Catégorie "Autres" pour les non classés
            nc = df[df['category'] == 'Non classé']
            if not nc.empty:
                st.markdown('---')
                count_nc = len(nc)
                st.subheader(f'🔍 Autres / Non classés ({count_nc})')
                st.dataframe(nc[['file', 'text_snippet']], width="stretch")
                
                # Bouton pour analyser les CV non classés avec DeepSeek
                analyze_button = st.button('🔍 Analyser les CV non classés avec Intelligence Artificielle', type='secondary')
                
                # Si on clique sur le bouton
                if analyze_button:
                    # Exécuter l'analyse
                    unclassified_results = []
                    unclassified_progress = st.progress(0)
                    unclassified_total = len(nc)
                    processing_ai_placeholder = st.empty()
                    
                    with st.spinner('Analyse des CVs non classés avec Intelligence Artificielle...'):
                        for i, (_, row) in enumerate(nc.iterrows()):
                            name = row['file']
                            text_snippet = row['text_snippet']
                            # Mettre à jour le fichier en cours
                            processing_ai_placeholder.info(f"Analyse par IA ({i+1}/{unclassified_total}) : {name}")
                            
                            try:
                                # Utiliser l'API DeepSeek pour analyser le CV
                                category = get_deepseek_analysis(text_snippet)
                                unclassified_results.append({'Fichier': name, 'Catégorie': category})
                            except Exception as e:
                                unclassified_results.append({'Fichier': name, 'Catégorie': f"Erreur: {str(e)}"})
                            
                            unclassified_progress.progress((i+1)/unclassified_total)
                    
                    # Nettoyer le placeholder
                    processing_ai_placeholder.empty()
                    
                    # Stocker les résultats dans la session state
                    st.session_state.deepseek_analyses = unclassified_results
                    st.session_state.last_action = "analyzed"
            
            # Afficher les analyses IA s'il y en a
            if st.session_state.deepseek_analyses:
                st.markdown('---')
                st.subheader("📝 Analyses par Intelligence Artificielle des CV non classés")
                
                # Ajouter un bouton pour réinitialiser les analyses si nécessaire
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.success(f"✅ Analyse par Intelligence Artificielle pour {len(st.session_state.deepseek_analyses)} CV(s) non classés.")
                with col2:
                    if st.button("🔄 Réinitialiser analyses", key="reset_deepseek"):
                        st.session_state.deepseek_analyses = []
                        st.session_state.last_action = "reset"
                        st.experimental_rerun()
                
                # Créer un tableau pour afficher les résultats de manière plus organisée
                ai_results_df = pd.DataFrame(st.session_state.deepseek_analyses)
                
                # Afficher le tableau avec les catégories attribuées
                st.dataframe(ai_results_df, width="stretch", hide_index=True)

            # Préparer un CSV à 4 colonnes en prenant en compte les analyses IA
            # Déterminer les noms à utiliser (extraits ou originaux)
            def get_display_name(row):
                original_name = row['file']
                if (hasattr(st.session_state, 'rename_and_organize_option') and 
                    st.session_state.rename_and_organize_option and 
                    'extracted_name' in row and row['extracted_name'] and 
                    row['extracted_name']['name']):
                    return row['extracted_name']['name']
                return original_name
            
            # Créer un DataFrame avec les résultats intégrés (incluant les analyses IA)
            merged_results_for_csv = merge_results_with_ai_analysis(st.session_state.classification_results)
            df_merged = pd.DataFrame(merged_results_for_csv)
            
            # Récupérer les classifications finales (après IA) avec les bons noms
            supports = [get_display_name(row) for _, row in df_merged[df_merged['category'] == 'Fonctions supports'].iterrows()]
            logistics = [get_display_name(row) for _, row in df_merged[df_merged['category'] == 'Logistique'].iterrows()]
            production = [get_display_name(row) for _, row in df_merged[df_merged['category'] == 'Production/Technique'].iterrows()]
            unclassified = [get_display_name(row) for _, row in df_merged[df_merged['category'] == 'Non classé'].iterrows()]

            max_len = max(len(supports), len(logistics), len(production), len(unclassified)) if max(len(supports), len(logistics), len(production), len(unclassified)) > 0 else 0
            # Pad lists
            supports += [''] * (max_len - len(supports))
            logistics += [''] * (max_len - len(logistics))
            production += [''] * (max_len - len(production))
            unclassified += [''] * (max_len - len(unclassified))

            export_df = pd.DataFrame({
                'Fonctions supports': supports,
                'Logistique': logistics,
                'Production/Technique': production,
                'Non classés': unclassified
            })

            # Séparateur visuel
            st.markdown("---")
            
            # Comptage des CVs par catégorie pour l'affichage
            count_support = len([x for x in supports if x])
            count_logistics = len([x for x in logistics if x]) 
            count_production = len([x for x in production if x])
            count_unclassified = len([x for x in unclassified if x])
            
            # Ajouter un indicateur pour montrer que les analyses IA sont incluses
            ai_indicator = " (incluant les analyses IA)" if hasattr(st.session_state, 'deepseek_analyses') and st.session_state.deepseek_analyses else ""
            st.markdown(f"**Résumé{ai_indicator}**: {count_support} en Fonctions supports, {count_logistics} en Logistique, {count_production} en Production/Technique, {count_unclassified} Non classés.")
            
            # Générer Excel avec séparateur correct (utiliser sep=';' pour Excel FR)
            csv = export_df.to_csv(index=False, sep=';').encode('utf-8-sig')  # utf-8-sig pour BOM Excel
            
            # Générer aussi un fichier Excel natif (.xlsx)
            from io import BytesIO
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Classification')
            excel_data = excel_buffer.getvalue()
            
            # Boutons de téléchargement
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(label='⬇️ Télécharger Excel (.xlsx)', data=excel_data, file_name='classification_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            with col2:
                st.download_button(label='⬇️ Télécharger CSV (;)', data=csv, file_name='classification_results.csv', mime='text/csv')
            
            with col3:
                # Bouton ZIP disponible si l'option de renommage était cochée
                if hasattr(st.session_state, 'rename_and_organize_option') and st.session_state.rename_and_organize_option:
                    if st.button('📦 Préparer et télécharger le ZIP organisé'):
                        with st.spinner('Création du fichier ZIP organisé...'):
                            try:
                                zip_data, manifest_df = create_organized_zip(st.session_state.classification_results, st.session_state.uploaded_files_list)
                                st.success('✅ ZIP créé avec succès !')
                                
                                # Afficher un aperçu du manifest
                                with st.expander("📋 Aperçu du contenu du ZIP"):
                                    st.dataframe(manifest_df, width="stretch")
                                
                                # Bouton de téléchargement du ZIP
                                st.download_button(
                                    label='⬇️ Télécharger le ZIP organisé',
                                    data=zip_data,
                                    file_name='CVs_Classes_Organises.zip',
                                    mime='application/zip'
                                )
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la création du ZIP : {e}")
                else:
                    st.info("💡 Cochez l'option 'Renommer les CV' lors du prochain traitement pour activer le téléchargement ZIP organisé.")


# --- FONCTIONS GEMINI (NOUVEAU) ---


# --- FIN FONCTIONS GEMINI ---

