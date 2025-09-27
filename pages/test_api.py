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

# Imports pour la méthode sémantique (spaCy a été retiré)
from sentence_transformers import SentenceTransformer, util
import torch

# -------------------- Configuration de la clé API DeepSeek --------------------
try:
    API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except KeyError:
    API_KEY = None
    st.error("❌ Le secret 'DEEPSEEK_API_KEY' est introuvable. Veuillez le configurer.")

# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Analyse CV AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- CSS --------------------
st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px; 
}
.stTextArea textarea {
    white-space: pre-wrap !important;
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
def extract_text_from_pdf(file):
    """Extrait le texte d'un fichier PDF."""
    try:
        pdf = PdfReader(file)
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip() if text else "Aucun texte lisible trouvé."
    except Exception as e:
        return f"Erreur d'extraction du texte: {str(e)}"

# --- MÉTHODE 1 : SIMILARITÉ COSINUS ---
def rank_resumes_with_cosine(job_description, resumes):
    try:
        documents = [job_description] + resumes
        vectorizer = TfidfVectorizer().fit_transform(documents)
        vectors = vectorizer.toarray()
        cosine_similarities = cosine_similarity([vectors[0]], vectors[1:]).flatten()
        return cosine_similarities
    except Exception as e:
        st.error(f"❌ Erreur Cosinus: {e}")
        return []

# --- MÉTHODE 2 : WORD EMBEDDINGS ---
def rank_resumes_with_embeddings(job_description, resumes):
    try:
        jd_embedding = embedding_model.encode(job_description, convert_to_tensor=True)
        resume_embeddings = embedding_model.encode(resumes, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(jd_embedding, resume_embeddings)
        return cosine_scores.flatten().cpu().numpy()
    except Exception as e:
        st.error(f"❌ Erreur Sémantique : {e}")
        return []

# --- ANALYSE PAR REGEX (REMPLACE NER) ---
def regex_analysis(text):
    """Analyse un texte avec des expressions régulières pour extraire des entités."""
    text_lower = text.lower()
    
    SKILLS_TECH = ["ged", "edms", "archivage", "dématérialisation", "numérisation", "sap", "aconex", "oracle", "jira"]
    SKILLS_SOFT = ["gestion de projet", "communication", "leadership", "rigueur", "analyse", "collaboration", "animation d'équipe"]
    
    found_tech = {skill for skill in SKILLS_TECH if re.search(r'\b' + re.escape(skill) + r'\b', text_lower)}
    found_soft = {skill for skill in SKILLS_SOFT if re.search(r'\b' + re.escape(skill) + r'\b', text_lower)}
    
    experience_match = re.search(r"(\d+)\s*(ans|années)\s*d'expérience", text_lower)
    experience = int(experience_match.group(1)) if experience_match else 0
    
    return {
        "Compétences Techniques": list(found_tech),
        "Compétences Comportementales": list(found_soft),
        "Années d'expérience détectées": experience
    }

# --- SCORING PAR RÈGLES AVEC REGEX (REMPLACE NER) ---
def rank_resumes_with_rules(job_description, resumes):
    """Classe les CVs en utilisant un scoring basé sur des règles et des Regex."""
    jd_entities = regex_analysis(job_description)
    scores = []

    TECH_SKILL_WEIGHT = 10
    EXPERIENCE_WEIGHT = 20
    
    for resume_text in resumes:
        resume_entities = regex_analysis(resume_text)
        current_score = 0
        
        common_tech_skills = set(jd_entities["Compétences Techniques"]) & set(resume_entities["Compétences Techniques"])
        current_score += len(common_tech_skills) * TECH_SKILL_WEIGHT
        
        required_exp = jd_entities.get("Années d'expérience détectées", 0)
        candidate_exp = resume_entities.get("Années d'expérience détectées", 0)
        if required_exp > 0 and candidate_exp >= required_exp:
            current_score += EXPERIENCE_WEIGHT
            
        scores.append(current_score)

    max_possible_score = len(jd_entities["Compétences Techniques"]) * TECH_SKILL_WEIGHT
    if jd_entities.get("Années d'expérience détectées", 0) > 0:
        max_possible_score += EXPERIENCE_WEIGHT

    if max_possible_score > 0:
        normalized_scores = [s / max_possible_score for s in scores]
    else:
        normalized_scores = [0.0] * len(scores)
        
    return normalized_scores

# --- MÉTHODE 4 : ANALYSE PAR IA ---
def get_detailed_score_with_ai(job_description, resume_text):
    if not API_KEY: return {"score": 0.0, "explanation": "❌ Analyse IA impossible. Clé API non configurée."}
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
    En tant qu'expert en recrutement, évalue la pertinence du CV suivant pour la description de poste donnée.
    Fournis ta réponse en deux parties distinctes et clairement identifiées.
    1. Un score de correspondance en pourcentage (par exemple, "Score: 85%").
    2. Une analyse détaillée en points, expliquant pourquoi ce score a été attribué.
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
        score_match = re.search(r"Score:\s*(\d+)%", full_response_text)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        return {"score": score, "explanation": full_response_text}
    except Exception as e:
        st.warning(f"⚠️ Erreur IA : {e}")
        return {"score": 0.0, "explanation": "Erreur"}

def rank_resumes_with_ai(job_description, resumes, file_names):
    scores_data = []
    for i, resume_text in enumerate(resumes):
        detailed_response = get_detailed_score_with_ai(job_description, resume_text)
        scores_data.append({
            "file_name": file_names[i],
            "score": detailed_response["score"],
            "explanation": detailed_response["explanation"]
        })
    return scores_data

def get_deepseek_analysis(text):
    if not API_KEY: return "Analyse impossible."
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
    En tant qu'expert en recrutement, analyse le CV suivant.
    Identifie les points forts et les points faibles de ce candidat sous des titres dédiés.
    Voici le texte du CV : {text}
    """
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur IA : {e}"

# -------------------- Interface Utilisateur --------------------
st.title("📄 Analyseur de CVs Intelligent")

tab1, tab2, tab3 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil", "📖 Guide des Méthodes"])

# --- ONGLET CLASSEMENT ---
with tab1:
    st.markdown("### 📄 Informations du Poste")
    job_description = st.text_area("Description du poste", height=200, key="jd_ranking")
    st.markdown("#### 📤 Importer des CVs")
    uploaded_files_ranking = st.file_uploader("Importer des CVs", type=["pdf"], accept_multiple_files=True, key="ranking_uploader")
    
    st.markdown("---")
    
    analysis_method = st.radio(
        "✨ Choisissez votre méthode de classement",
        ["Similarité Cosinus (Mots-clés)", "Similarité Sémantique (Embeddings)", "Scoring par Règles (Regex)", "Analyse par IA (DeepSeek)"],
        index=0, help="Consultez l'onglet 'Guide des Méthodes'."
    )

    if st.button("🔍 Analyser et Classer", type="primary", use_container_width=True, disabled=not (uploaded_files_ranking and job_description)):
        # --- CORRECTION ICI : Extraction du texte AVANT utilisation ---
        resumes, file_names = [], []
        with st.spinner("Lecture des fichiers PDF..."):
            for file in uploaded_files_ranking:
                text = extract_text_from_pdf(file)
                if not "Erreur" in text:
                    resumes.append(text)
                    file_names.append(file.name)
        
        with st.spinner("Analyse des CVs en cours..."):
            scores, explanations = [], None
            if analysis_method == "Analyse par IA (DeepSeek)":
                scores_data = rank_resumes_with_ai(job_description, resumes, file_names)
                scores = [data["score"] for data in scores_data]
                explanations = {data["file_name"]: data["explanation"] for data in scores_data}
            elif analysis_method == "Scoring par Règles (Regex)":
                scores = rank_resumes_with_rules(job_description, resumes)
            elif analysis_method == "Similarité Sémantique (Embeddings)":
                scores = rank_resumes_with_embeddings(job_description, resumes)
            else: # Cosinus par défaut
                scores = rank_resumes_with_cosine(job_description, resumes)

            if scores:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                results_df = pd.DataFrame(ranked_resumes, columns=["Nom du CV", "Score brut"])
                results_df["Rang"] = range(1, len(results_df) + 1)
                results_df["Score"] = results_df["Score brut"].apply(lambda x: f"{x*100:.1f}%")
                
                st.markdown("### 🏆 Résultats du Classement")
                st.dataframe(results_df[["Rang", "Nom du CV", "Score"]], use_container_width=True, hide_index=True)
                
                if explanations:
                    st.markdown("### 📝 Analyse détaillée par l'IA")
                    for _, row in results_df.iterrows():
                        file_name = row["Nom du CV"]
                        score = row["Score brut"]
                        with st.expander(f"Analyse pour : **{file_name}** (Score: {score*100:.1f}%)"):
                            st.markdown(explanations.get(file_name, "Aucune explication disponible."))

# --- ONGLET ANALYSE DE PROFIL ---
with tab2:
    uploaded_file_analysis = st.file_uploader("Importer un CV", type=["pdf"], key="analysis_uploader")
    analysis_type_single = st.selectbox(
        "Type d'analyse souhaité",
        ("Analyse par IA (Points forts/faibles)", "Analyse par Regex (Extraction d'entités)")
    )
    if uploaded_file_analysis and st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True):
        # --- CORRECTION ICI : Extraction du texte AVANT utilisation ---
        with st.spinner("Analyse en cours..."):
            text = extract_text_from_pdf(uploaded_file_analysis)
            if "Erreur" in text:
                st.error(f"❌ {text}")
            else:
                st.markdown("### 📋 Résultat de l'Analyse")
                if analysis_type_single == "Analyse par Regex (Extraction d'entités)":
                    entities = regex_analysis(text)
                    st.info("**Entités extraites par la méthode Regex**")
                    st.json(entities)
                else: # Analyse IA par défaut
                    analysis_result = get_deepseek_analysis(text)
                    st.markdown(analysis_result)

# --- ONGLET GUIDE DES MÉTHODES ---
with tab3:
    st.header("📖 Comprendre les Méthodes d'Analyse")
    st.subheader("1. Similarité Cosinus (Mots-clés)")
    st.markdown("- **Principe** : Compare la fréquence des mots exacts.")
    st.markdown("- **Avantages** : ✅ Très rapide.")
    st.markdown("- **Limites** : ❌ Ne comprend pas le contexte.")
    
    st.subheader("2. Similarité Sémantique (Embeddings)")
    st.markdown("- **Principe** : Compare le sens des phrases.")
    st.markdown("- **Avantages** : ✅ Comprend le contexte et les synonymes.")
    st.markdown("- **Limites** : ❌ Un peu plus lente.")

    st.subheader("3. Scoring par Règles (Regex)")
    st.markdown("- **Principe** : Recherche des mots-clés et applique un score.")
    st.markdown("- **Avantages** : ✅ Transparent, personnalisable, sans dépendances lourdes.")
    st.markdown("- **Limites** : ❌ Rigide, peut manquer des informations.")
    
    st.subheader("4. Analyse par IA (LLM)")
    st.markdown("- **Principe** : Un expert IA évalue le CV.")
    st.markdown("- **Avantages** : ✅ La plus précise, fournit des explications.")
    st.markdown("- **Limites** : ❌ La plus lente et consomme vos tokens.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🔧 Configuration")
    if st.button("Test Connexion API DeepSeek"):
        if API_KEY:
            # ... (votre code de test)
            st.success("Test effectué.")
        else:
            st.error("❌ Clé API non configurée")