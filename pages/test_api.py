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

# --- NOUVEAUTÉ : Imports pour les nouvelles méthodes ---
from sentence_transformers import SentenceTransformer, util
import spacy

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

# --- NOUVEAUTÉ : Mise en cache des modèles pour la performance ---
@st.cache_resource
def load_spacy_model():
    """Charge le modèle spaCy une seule fois."""
    return spacy.load("fr_core_news_sm")

@st.cache_resource
def load_embedding_model():
    """Charge le modèle SentenceTransformer une seule fois."""
    return SentenceTransformer('all-MiniLM-L6-v2')

# Charger les modèles au démarrage
nlp = load_spacy_model()
embedding_model = load_embedding_model()


# -------------------- Fonctions de traitement des CV --------------------
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

# --- MÉTHODE 1 : SIMILARITÉ COSINUS (EXISTANTE) ---
def rank_resumes_with_cosine(job_description, resumes):
    """Classe les CVs en utilisant la similarité cosinus (TF-IDF)."""
    try:
        documents = [job_description] + resumes
        vectorizer = TfidfVectorizer().fit_transform(documents)
        vectors = vectorizer.toarray()
        cosine_similarities = cosine_similarity([vectors[0]], vectors[1:]).flatten()
        return cosine_similarities
    except Exception as e:
        st.error(f"❌ Erreur Cosinus: {e}")
        return []

# --- NOUVEAUTÉ : MÉTHODE 2 : WORD EMBEDDINGS ---
def rank_resumes_with_embeddings(job_description, resumes):
    """Classe les CVs en utilisant la similarité sémantique (Sentence-BERT)."""
    try:
        # Encodage des textes en vecteurs sémantiques
        jd_embedding = embedding_model.encode(job_description, convert_to_tensor=True)
        resume_embeddings = embedding_model.encode(resumes, convert_to_tensor=True)
        
        # Calcul de la similarité cosinus sur les vecteurs sémantiques
        cosine_scores = util.pytorch_cos_sim(jd_embedding, resume_embeddings)
        return cosine_scores.flatten().cpu().numpy()
    except Exception as e:
        st.error(f"❌ Erreur Embeddings: {e}")
        return []

# --- NOUVEAUTÉ : MÉTHODE 3 : SCORING PAR RÈGLES (NER) ---
def rank_resumes_with_ner(job_description, resumes):
    """Classe les CVs en utilisant un scoring basé sur des règles et la NER."""
    
    # --- PERSONNALISEZ VOS RÈGLES ICI ---
    # Définissez les compétences clés que vous recherchez
    SKILLS_TECH = ["python", "sql", "pandas", "streamlit", "docker", "git"]
    SKILLS_SOFT = ["gestion de projet", "communication", "leadership", "agile"]
    
    scores = []
    for resume_text in resumes:
        doc = nlp(resume_text.lower())
        
        current_score = 0
        
        # Règle 1 : Points pour les compétences techniques
        found_tech_skills = [skill for skill in SKILLS_TECH if skill in doc.text]
        current_score += len(found_tech_skills) * 10 # 10 points par compétence technique
        
        # Règle 2 : Points pour les soft skills
        found_soft_skills = [skill for skill in SKILLS_SOFT if skill in doc.text]
        current_score += len(found_soft_skills) * 5 # 5 points par soft skill
        
        # Règle 3 : Points pour l'expérience (exemple simple)
        if re.search(r"(\d+)\s*(ans|années)\s*d'expérience", doc.text):
            current_score += 15 # Bonus si le nombre d'années est mentionné
            
        scores.append(current_score)

    # Normaliser les scores entre 0 et 1 pour la cohérence
    max_score = sum([10 for _ in SKILLS_TECH]) + sum([5 for _ in SKILLS_SOFT]) + 15
    if max_score > 0:
        normalized_scores = [s / max_score for s in scores]
    else:
        normalized_scores = [0.0 for _ in scores]
        
    return normalized_scores

# --- MÉTHODE 4 : ANALYSE PAR IA (EXISTANTE) ---
def get_detailed_score_with_ai(job_description, resume_text):
    """Évalue la pertinence d'un CV en utilisant l'IA."""
    # ... (Le reste de votre fonction get_detailed_score_with_ai reste identique) ...
    if not API_KEY:
        return {"score": 0.0, "explanation": "❌ Analyse IA impossible. Clé API non configurée."}
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
    En tant qu'expert en recrutement, évalue la pertinence du CV suivant pour la description de poste donnée.
    Fournis ta réponse en deux parties :
    1. Un score de correspondance en pourcentage (ex: "Score: 85%").
    2. Une analyse détaillée expliquant les points forts et les points à améliorer.

    ---
    Description du poste:
    {job_description}
    ---
    Texte du CV:
    {resume_text}
    ---
    """
    payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": "You are a professional recruiter assistant."}, {"role": "user", "content": prompt}], "stream": False, "temperature": 0.0}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        full_response_text = response.json()["choices"][0]["message"]["content"].strip()
        score_match = re.search(r"Score:\s*(\d+)%", full_response_text)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        return {"score": score, "explanation": full_response_text}
    except Exception as e:
        st.warning(f"⚠️ Erreur IA: {e}")
        return {"score": 0.0, "explanation": "❌ Analyse IA échouée."}

def rank_resumes_with_ai(job_description, resumes, file_names):
    """Classe les CVs en utilisant l'IA."""
    # ... (Votre fonction rank_resumes_with_ai reste identique) ...
    scores_data = []
    for i, resume_text in enumerate(resumes):
        detailed_response = get_detailed_score_with_ai(job_description, resume_text)
        scores_data.append({"file_name": file_names[i], "score": detailed_response["score"], "explanation": detailed_response["explanation"]})
    return scores_data

# ... (Votre fonction get_deepseek_analysis pour l'onglet 2 reste identique) ...
def get_deepseek_analysis(text):
    #...
    return "Analyse..."


# -------------------- INTERFACE UTILISATEUR --------------------
st.title("📄 Analyseur de CVs Intelligent")

tab1, tab2 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil"])

# -------------------- ONGLET 1 : CLASSEMENT --------------------
with tab1:
    st.markdown("### 📄 Informations du Poste")
    job_description = st.text_area("Description du poste", placeholder="Coller la description complète du poste ici...", height=250)
    
    st.markdown("### 📤 Importer des CVs")
    uploaded_files_ranking = st.file_uploader(
        "Sélectionnez les CVs (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="ranking_uploader"
    )
    
    st.markdown("---")
    
    # --- NOUVEAUTÉ : Sélecteur avec les 4 méthodes ---
    analysis_method = st.radio(
        "✨ Choisissez votre méthode d'analyse",
        [
            "Similarité Cosinus (Mots-clés)", 
            "Similarité Sémantique (Embeddings)", 
            "Scoring par Règles (NER)", 
            "Analyse par IA (DeepSeek)"
        ],
        index=0,
        help="""
        - **Cosinus**: Rapide, basé sur la fréquence des mots-clés.
        - **Sémantique**: Plus intelligent, comprend le sens des phrases.
        - **Règles (NER)**: Transparent, basé sur des critères que vous pouvez définir dans le code.
        - **IA DeepSeek**: Le plus puissant, analyse contextuelle complète (utilise votre clé API).
        """
    )
    
    if st.button("🔍 Analyser et Classer les CVs", type="primary", use_container_width=True, disabled=not (uploaded_files_ranking and job_description)):
        with st.spinner("🔍 Analyse en cours... Cette opération peut prendre quelques instants."):
            resumes, file_names = [], []
            for file in uploaded_files_ranking:
                text = extract_text_from_pdf(file)
                if not "Erreur" in text:
                    resumes.append(text)
                    file_names.append(file.name)
            
            scores = []
            explanations = None
            
            if analysis_method == "Similarité Cosinus (Mots-clés)":
                scores = rank_resumes_with_cosine(job_description, resumes)
            elif analysis_method == "Similarité Sémantique (Embeddings)":
                scores = rank_resumes_with_embeddings(job_description, resumes)
            elif analysis_method == "Scoring par Règles (NER)":
                scores = rank_resumes_with_ner(job_description, resumes)
            elif analysis_method == "Analyse par IA (DeepSeek)":
                ai_results = rank_resumes_with_ai(job_description, resumes, file_names)
                scores = [res["score"] for res in ai_results]
                explanations = {res["file_name"]: res["explanation"] for res in ai_results}

            if len(scores) > 0:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                
                results_df = pd.DataFrame({
                    "Rang": range(1, len(ranked_resumes) + 1),
                    "Nom du CV": [name for name, _ in ranked_resumes],
                    "Score": [f"{score * 100:.1f}%" for _, score in ranked_resumes],
                })
                
                st.markdown("### 🏆 Résultats du Classement")
                st.dataframe(results_df, use_container_width=True, hide_index=True)

                if explanations:
                    st.markdown("### 📝 Analyse détaillée par l'IA")
                    for file_name, score in ranked_resumes:
                        with st.expander(f"**{file_name}** (Score: {score * 100:.1f}%)"):
                            st.markdown(explanations[file_name])
            else:
                st.error("❌ Aucun CV n'a pu être analysé.")

# -------------------- ONGLET 2 : ANALYSE DE PROFIL --------------------
with tab2:
    st.markdown("### 📂 Importer un CV pour une analyse détaillée")
    uploaded_file_analysis = st.file_uploader(
        "Sélectionnez un CV (PDF)",
        type=["pdf"],
        accept_multiple_files=False, # Un seul fichier pour l'analyse détaillée
        key="analysis_uploader"
    )
    
    if uploaded_file_analysis:
        if st.button("🚀 Lancer l'analyse du profil", type="primary", use_container_width=True):
            with st.spinner("⏳ L'IA analyse le profil..."):
                text = extract_text_from_pdf(uploaded_file_analysis)
                if "Erreur" in text:
                    st.error(f"❌ Erreur d'extraction: {text}")
                else:
                    analysis_result = get_deepseek_analysis(text) # Assurez-vous que cette fonction est complète
                    st.markdown("### 📋 Analyse du Profil")
                    st.markdown(analysis_result)