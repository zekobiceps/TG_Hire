import streamlit as st
import pandas as pd
import io
import requests
import json
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time
import re
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Imports pour la méthode sémantique
from sentence_transformers import SentenceTransformer, util
import torch

# Import des fonctions avancées d'analyse
from utils import (rank_resumes_with_ensemble, batch_process_resumes, 
                 save_feedback, get_average_feedback_score, 
                 get_feedback_summary)

# -------------------- Configuration de la clé API DeepSeek --------------------
# --- CORRECTION : Déplacé à l'intérieur des fonctions pour éviter l'erreur au démarrage ---

# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Analyse CV AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
</style>
""", unsafe_allow_html=True)

# -------------------- Chargement des modèles ML (mis en cache) --------------------
@st.cache_resource
def load_embedding_model():
    """Charge le modèle SentenceTransformer une seule fois."""
    return SentenceTransformer('all-MiniLM-L6-v2')

embedding_model = load_embedding_model()

# -------------------- Fonctions de traitement --------------------
def get_api_key():
    """Récupère la clé API depuis les secrets et gère l'erreur."""
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        if not api_key:
            st.error("❌ La clé API DeepSeek est vide dans les secrets. Veuillez la vérifier.")
            return None
        return api_key
    except KeyError:
        st.error("❌ Le secret 'DEEPSEEK_API_KEY' est introuvable. Veuillez le configurer dans les paramètres de votre application Streamlit.")
        return None

def extract_text_from_pdf(file):
    try:
        pdf = PdfReader(file)
        text = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text.strip() if text else "Aucun texte lisible trouvé."
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
        logic['Niveau d\'études'] = f"Candidat: Bac+{resume_entities['Niveau d\'études']} vs Requis: Bac+{jd_entities['Niveau d\'études']} (+{score_from_edu} pts)"
        
        score_from_exp = 0
        if resume_entities["Années d'expérience"] >= jd_entities["Années d'expérience"]:
            score_from_exp = EXPERIENCE_WEIGHT
            current_score += score_from_exp
        logic['Expérience'] = f"Candidat: {resume_entities['Années d\'expérience']} ans vs Requis: {jd_entities['Années d\'expérience']} ans (+{score_from_exp} pts)"
        
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

def get_deepseek_analysis(text):
    API_KEY = get_api_key()
    if not API_KEY: return "Analyse impossible."
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"En tant qu'expert en recrutement, analyse le CV suivant et identifie les points forts et faibles. Texte du CV : {text}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur IA : {e}"

# -------------------- Interface Utilisateur --------------------
st.title("📄 Analyseur de CVs Intelligent")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil", "📖 Guide des Méthodes", "📈 Statistiques de Feedback"])

with tab1:
    st.markdown("### 📄 Informations du Poste")
    col1, col2 = st.columns([2, 1])
    with col1:
        job_title = st.text_input("Intitulé du poste", placeholder="Ex: Archiviste Junior")
        job_description = st.text_area("Description du poste", height=200, key="jd_ranking", placeholder="Collez la description...")
    with col2:
        st.markdown("#### 📤 Importer des CVs")
        uploaded_files_ranking = st.file_uploader("Importer des CVs", type=["pdf"], accept_multiple_files=True, key="ranking_uploader")
    
    st.markdown("---")
    
    analysis_method = st.radio(
        "✨ Choisissez votre méthode de classement",
        ["Méthode Cosinus (Mots-clés)", "Méthode Sémantique (Embeddings)", "Scoring par Règles (Regex)", 
         "Analyse par IA (DeepSeek)", "Analyse combinée (Ensemble)"],
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
            with st.spinner("Lecture des fichiers PDF..."):
                for file in uploaded_files_ranking:
                    text = extract_text_from_pdf(file)
                    if not "Erreur" in text:
                        resumes.append(text)
                        file_names.append(file.name)
            
            # Analyse selon la méthode choisie
            with st.spinner(f"Analyse des CVs en cours avec {analysis_method}..."):
                results, explanations, logic = {}, None, None
                
                if analysis_method == "Analyse par IA (DeepSeek)":
                    results = rank_resumes_with_ai(job_description, resumes, file_names)
                    explanations = results.get("explanations")
                
                elif analysis_method == "Scoring par Règles (Regex)":
                    rule_results = rank_resumes_with_rules(job_description, resumes, file_names)
                    results = {"scores": [r["score"] for r in rule_results]}
                    logic = {r["file_name"]: r["logic"] for r in rule_results}
                
                elif analysis_method == "Méthode Sémantique (Embeddings)":
                    results = rank_resumes_with_embeddings(job_description, resumes, file_names)
                    logic = results.get("logic")
                
                elif analysis_method == "Analyse combinée (Ensemble)":
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
                
                else:  # Méthode Cosinus par défaut
                    results = rank_resumes_with_cosine(job_description, resumes, file_names)
                    logic = results.get("logic")

            scores = results.get("scores", [])
            if scores is not None and len(scores) > 0:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                results_df = pd.DataFrame(ranked_resumes, columns=["Nom du CV", "Score brut"])
                results_df["Rang"] = range(1, len(results_df) + 1)
                results_df["Score"] = results_df["Score brut"].apply(lambda x: f"{x*100:.1f}%")
                
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
                            st.markdown(explanations.get(file_name, "N/A"))
                
                # Sauvegarder les résultats pour le feedback
                st.session_state.last_analysis_result = results_df
                st.session_state.cv_analysis_feedback = False
                
                # Demander un feedback à l'utilisateur
                st.markdown("---")
                st.markdown("### 🌟 Donnez-nous votre feedback")
                st.markdown("Comment évaluez-vous la qualité des résultats fournis par cette analyse ?")
                
                feedback_col1, feedback_col2 = st.columns([3, 1])
                with feedback_col1:
                    feedback_score = st.slider("Note", 1, 5, 3, key="feedback_slider")
                    feedback_text = st.text_area("Commentaires (optionnel)", key="feedback_text", 
                                               placeholder="Qu'avez-vous apprécié ? Que pourrait-on améliorer ?")
                
                with feedback_col2:
                    if st.button("Envoyer feedback", key="send_feedback"):
                        save_feedback(
                            analysis_method=analysis_method,
                            job_title=job_title,
                            job_description_snippet=job_description[:200],
                            cv_count=len(file_names),
                            feedback_score=feedback_score,
                            feedback_text=feedback_text
                        )
                        st.session_state.cv_analysis_feedback = True
                        st.success("Merci pour votre feedback ! 🙏")
            else:
                st.error("L'analyse n'a retourné aucun score.")

with tab2:
    st.markdown("### 📂 Importer un ou plusieurs CVs")
    uploaded_files_analysis = st.file_uploader("Importer des CVs", type=["pdf"], key="analysis_uploader_single", accept_multiple_files=True)
    
    analysis_type_single = st.selectbox(
        "Type d'analyse souhaité",
        ("Analyse par IA (DeepSeek)", "Analyse par Regex (Extraction d'entités)", "Analyse par la Méthode Sémantique", "Analyse par la Méthode Cosinus")
    )
    captions = {
        "Analyse par IA (DeepSeek)": "Analyse qualitative (points forts/faibles). Consomme vos tokens !",
        "Analyse par Regex (Extraction d'entités)": "Extrait des informations structurées (compétences, diplômes, etc.).",
        "Analyse par la Méthode Sémantique": "Calcule un score de pertinence basé sur le sens (nécessite une description de poste).",
        "Analyse par la Méthode Cosinus": "Calcule un score de pertinence basé sur les mots-clés (nécessite une description de poste)."
    }
    st.caption(captions.get(analysis_type_single))

    job_desc_single = ""
    if "Analyse par la Méthode" in analysis_type_single:
        job_desc_single = st.text_area("Description de poste pour le calcul du score", height=150, key="jd_single")

    if uploaded_files_analysis and st.button("🚀 Lancer l'analyse", type="primary", width="stretch", key="btn_single_analysis"):
        for uploaded_file in uploaded_files_analysis:
            with st.expander(f"Résultat pour : **{uploaded_file.name}**", expanded=True):
                with st.spinner("Analyse en cours..."):
                    text = extract_text_from_pdf(uploaded_file)
                    if "Erreur" in text:
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
                        else: # Analyse IA
                            analysis_result = get_deepseek_analysis(text)
                            st.markdown(analysis_result)

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
    st.header("📈 Statistiques de Feedback Utilisateur")
    
    # Récupération des statistiques
    feedback_stats = get_feedback_summary()
    
    if len(feedback_stats) > 0:
        # Affichage des scores moyens par méthode
        st.subheader("🌟 Satisfaction moyenne par méthode d'analyse")
        
        # Convertir les colonnes numériques en type numérique
        feedback_stats["Score moyen"] = pd.to_numeric(feedback_stats["Score moyen"])
        feedback_stats["Nombre d'évaluations"] = pd.to_numeric(feedback_stats["Nombre d'évaluations"])
        
        # Filtrer uniquement les méthodes avec des évaluations
        feedback_with_evals = feedback_stats[feedback_stats["Nombre d'évaluations"] > 0]
        
        if not feedback_with_evals.empty:
            # Graphique des scores moyens
            fig_scores = go.Figure()
            fig_scores.add_trace(go.Bar(
                x=feedback_with_evals["Score moyen"],
                y=feedback_with_evals["Méthode"],
                orientation='h',
                marker_color=["#0068c9", "#83c9ff", "#29b09d", "#7defa1", "#ff2b2b"][:len(feedback_with_evals)]
            ))
            fig_scores.update_layout(
                title="Score moyen par méthode (sur 5)",
                height=300,
                margin={"l": 150, "r": 10, "t": 30, "b": 30},
                xaxis={"range": [0, 5]},
            )
            
            st.plotly_chart(fig_scores, use_container_width=True)
            
            # Graphique du nombre d'évaluations
            fig_evals = go.Figure(data=[go.Pie(
                labels=feedback_with_evals["Méthode"],
                values=feedback_with_evals["Nombre d'évaluations"],
                marker_colors=["#0068c9", "#83c9ff", "#29b09d", "#7defa1", "#ff2b2b"][:len(feedback_with_evals)]
            )])
            fig_evals.update_layout(
                title="Distribution des évaluations",
                height=300,
            )
            
            st.plotly_chart(fig_evals, use_container_width=True)
            
            # Affichage du tableau de statistiques
            st.subheader("📊 Détails des statistiques")
            st.dataframe(feedback_stats, width="stretch", height=200)
            
            # Méthode la mieux notée
            if len(feedback_with_evals) > 1:
                best_method = feedback_with_evals.loc[feedback_with_evals["Score moyen"].idxmax()]
                st.success(f"🏆 La méthode la mieux notée est : **{best_method['Méthode']}** avec un score de **{best_method['Score moyen']:.2f}/5** sur {best_method['Nombre d\'évaluations']} évaluations.")
        else:
            st.info("Aucune méthode n'a encore reçu d'évaluations.")
    else:
        st.info("Aucun feedback n'a encore été enregistré. Les statistiques apparaîtront ici une fois que des utilisateurs auront évalué les analyses de CV.")
        
        # Exemple de feedback
        with st.expander("Comment les feedbacks sont-ils collectés ?"):
            st.markdown("""
            Après chaque analyse de CV, un formulaire de feedback apparaît en bas de la page pour demander à l'utilisateur d'évaluer la qualité des résultats.
            
            Les utilisateurs peuvent :
            1. Attribuer une note de 1 à 5 étoiles
            2. Laisser un commentaire optionnel
            3. Envoyer leur feedback pour améliorer la précision de l'analyse
            
            Ces données sont ensuite agrégées pour identifier les méthodes les plus pertinentes selon les utilisateurs.
            """)

with st.sidebar:
    st.markdown("### 🔧 Configuration")
    if st.button("Test Connexion API DeepSeek"):
        API_KEY = get_api_key()
        if API_KEY:
            try:
                response = requests.get("https://api.deepseek.com/v1/models", headers={"Authorization": f"Bearer {API_KEY}"})
                if response.status_code == 200:
                    st.success("✅ Connexion API réussie")
                else:
                    st.error(f"❌ Erreur de connexion ({response.status_code})")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")