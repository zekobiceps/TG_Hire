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

# Imports pour les méthodes sémantiques et NER
from sentence_transformers import SentenceTransformer, util
import spacy
import spacy.cli # <-- NOUVEL IMPORT pour le téléchargement automatique
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

# --- NOUVELLE FONCTION ROBUSTE POUR CHARGER LE MODÈLE SPACY ---
@st.cache_resource
def load_spacy_model():
    """Charge le modèle spaCy. S'il n'est pas trouvé, le télécharge automatiquement."""
    model_name = "fr_core_news_sm"
    try:
        # On essaie de charger le modèle
        nlp = spacy.load(model_name)
    except OSError:
        # Si le modèle n'est pas trouvé, on le télécharge
        st.info(f"Téléchargement du modèle spaCy '{model_name}'... (Cette opération n'a lieu qu'une seule fois)")
        spacy.cli.download(model_name)
        nlp = spacy.load(model_name)
    return nlp

@st.cache_resource
def load_embedding_model():
    """Charge le modèle SentenceTransformer une seule fois."""
    return SentenceTransformer('all-MiniLM-L6-v2')

# Charger les modèles au démarrage
# La gestion des erreurs est maintenant à l'intérieur de la fonction
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

def rank_resumes_with_cosine(job_description, resumes):
    """Classe les CV en fonction de leur similarité avec la description de poste en utilisant la similarité cosinus."""
    try:
        documents = [job_description] + resumes
        vectorizer = TfidfVectorizer().fit_transform(documents)
        vectors = vectorizer.toarray()
        job_description_vector = vectors[0]
        resume_vectors = vectors[1:]
        cosine_similarities = cosine_similarity([job_description_vector], resume_vectors).flatten()
        return cosine_similarities
    except Exception as e:
        st.error(f"❌ Erreur lors du classement des CVs: {e}")
        return []

def rank_resumes_with_embeddings(job_description, resumes):
    """Classe les CVs en utilisant la similarité sémantique (Sentence-BERT)."""
    try:
        jd_embedding = embedding_model.encode(job_description, convert_to_tensor=True)
        resume_embeddings = embedding_model.encode(resumes, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(jd_embedding, resume_embeddings)
        return cosine_scores.flatten().cpu().numpy()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse sémantique : {e}")
        return []

def ner_analysis(text):
    """Analyse un texte avec NER pour extraire des entités."""
    if not nlp: return {}
    doc = nlp(text.lower())
    SKILLS_TECH = ["ged", "edms", "archivage", "dématérialisation", "numérisation", "sap", "aconex", "oracle", "jira"]
    SKILLS_SOFT = ["gestion de projet", "communication", "leadership", "rigueur", "analyse", "collaboration", "animation d'équipe"]
    
    found_tech = {skill for skill in SKILLS_TECH if skill in doc.text}
    found_soft = {skill for skill in SKILLS_SOFT if skill in doc.text}
    experience_match = re.search(r"(\d+)\s*(ans|années)\s*d'expérience", doc.text)
    experience = int(experience_match.group(1)) if experience_match else 0
    
    return {
        "Compétences Techniques": list(found_tech),
        "Compétences Comportementales": list(found_soft),
        "Années d'expérience détectées": experience
    }

def rank_resumes_with_ner(job_description, resumes):
    """Classe les CVs en utilisant un scoring basé sur les règles et la NER."""
    jd_entities = ner_analysis(job_description)
    scores = []
    for resume_text in resumes:
        resume_entities = ner_analysis(resume_text)
        current_score = 0
        common_tech = set(jd_entities["Compétences Techniques"]) & set(resume_entities["Compétences Techniques"])
        current_score += len(common_tech) * 10
        if resume_entities["Années d'expérience détectées"] >= jd_entities.get("Années d'expérience détectées", 7):
            current_score += 20
        scores.append(current_score)
    max_possible_score = len(jd_entities["Compétences Techniques"]) * 10 + 20
    normalized_scores = [s / max_possible_score for s in scores] if max_possible_score > 0 else [0.0] * len(scores)
    return normalized_scores

def get_detailed_score_with_ai(job_description, resume_text):
    """Évalue la pertinence d'un CV en utilisant l'IA, en fournissant un score et une explication détaillée."""
    if not API_KEY:
        return {"score": 0.0, "explanation": "❌ Analyse IA impossible. Clé API non configurée."}
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    prompt = f"""
    En tant qu'expert en recrutement, évalue la pertinence du CV suivant pour la description de poste donnée.
    Fournis ta réponse en deux parties distinctes et clairement identifiées.
    1. Un score de correspondance en pourcentage (par exemple, "Score: 85%").
    2. Une analyse détaillée en points, expliquant pourquoi ce score a été attribué. Détaille ce qui est pertinent (points forts) et ce qui manque pour un match parfait à 100% (points à améliorer).
    ---
    Description du poste:
    {job_description}
    ---
    Texte du CV:
    {resume_text}
    ---
    Ton score est:
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional recruiter assistant. Your output must be a score in percentage followed by a detailed analysis."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": 0.0
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        full_response_text = response_data["choices"][0]["message"]["content"].strip()
        score_match = re.search(r"Score: (\d+)%", full_response_text)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        explanation_parts = full_response_text.split("2. Une analyse détaillée", 1)
        explanation = "2. Une analyse détaillée" + explanation_parts[1].strip() if len(explanation_parts) > 1 else full_response_text
        return {"score": score, "explanation": explanation}
    except Exception as e:
        st.warning(f"⚠️ Erreur lors de l'évaluation par l'IA: {e}")
        return {"score": 0.0, "explanation": "❌ Analyse IA échouée. Impossible de fournir une explication détaillée."}

def rank_resumes_with_ai(job_description, resumes, file_names):
    """Classe les CV en utilisant l'IA pour évaluer la pertinence de chaque CV et fournit des explications."""
    scores_data = []
    progress_bar = st.progress(0)
    for i, resume_text in enumerate(resumes):
        detailed_response = get_detailed_score_with_ai(job_description, resume_text)
        scores_data.append({
            "file_name": file_names[i],
            "score": detailed_response["score"],
            "explanation": detailed_response["explanation"]
        })
        progress_bar.progress((i + 1) / len(resumes))
    return scores_data

def get_deepseek_analysis(text):
    """Analyse le texte du CV pour identifier les points forts et faibles en utilisant DeepSeek."""
    if not API_KEY:
        return "Analyse impossible. Veuillez configurer votre clé API."
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    prompt = f"""
    En tant qu'expert en recrutement, analyse le CV suivant.
    Identifie les points forts et les points faibles de ce candidat.
    Fournis une réponse structurée en français, avec un point pour chaque élément, sous les titres "Points forts" et "Points faibles".
    Voici le texte du CV :
    {text}
    """
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional recruiter assistant."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse IA : {e}")
        return "Analyse IA échouée. Veuillez réessayer."

# -------------------- Interface Utilisateur --------------------
st.title("📄 Analyseur de CVs Intelligent")

tab1, tab2, tab3 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil", "📖 Guide des Méthodes"])

# -------------------- Onglet Classement --------------------
with tab1:
    st.markdown("### 📄 Informations du Poste")
    job_description = st.text_area("Description du poste", placeholder="Coller ou écrire la description...", height=200, key="jd_ranking")

    st.markdown("#### 📤 Importer des CVs")
    uploaded_files_ranking = st.file_uploader("Sélectionnez les CVs (PDF)", type=["pdf"], accept_multiple_files=True, key="ranking_uploader")
    
    st.markdown("---")
    
    analysis_method = st.radio(
        "✨ Choisissez votre méthode de classement",
        ["Similarité Cosinus (Mots-clés)", "Similarité Sémantique (Embeddings)", "Scoring par Règles (NER)", "Analyse par IA (DeepSeek)"],
        index=0, help="Consultez l'onglet 'Guide des Méthodes' pour plus de détails."
    )

    if st.button("🔍 Analyser et Classer", type="primary", use_container_width=True, disabled=not (uploaded_files_ranking and job_description)):
        with st.spinner("🔍 Analyse des CVs en cours..."):
            resumes, file_names, error_files = [], [], []
            for file in uploaded_files_ranking:
                text = extract_text_from_pdf(file)
                if "Erreur" in text:
                    error_files.append(file.name)
                else:
                    resumes.append(text)
                    file_names.append(file.name)
            
            if error_files:
                st.warning(f"⚠️ {len(error_files)} fichier(s) non traité(s): {', '.join(error_files)}")
            
            if resumes:
                scores, explanations = [], None
                if analysis_method == "Analyse par IA (DeepSeek)":
                    scores_data = rank_resumes_with_ai(job_description, resumes, file_names)
                    scores = [data["score"] for data in scores_data]
                    explanations = {data["file_name"]: data["explanation"] for data in scores_data}
                elif analysis_method == "Scoring par Règles (NER)":
                    scores = rank_resumes_with_ner(job_description, resumes)
                elif analysis_method == "Similarité Sémantique (Embeddings)":
                    scores = rank_resumes_with_embeddings(job_description, resumes)
                else: # Cosinus par défaut
                    scores = rank_resumes_with_cosine(job_description, resumes)

                if len(scores) > 0:
                    ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                    
                    results_df = pd.DataFrame({
                        "Rang": range(1, len(ranked_resumes) + 1),
                        "Nom du CV": [name for name, _ in ranked_resumes],
                        "Score de correspondance": [f"{round(score * 100, 1)}%" for _, score in ranked_resumes],
                        "Score brut": [round(score, 4) for _, score in ranked_resumes]
                    })
                    
                    st.markdown("### 🏆 Résultats du Classement")
                    
                    col1_m, col2_m, col3_m = st.columns(3)
                    with col1_m:
                        st.metric("📊 CVs analysés", len(results_df))
                    with col2_m:
                        top_score = results_df["Score brut"].max()
                        st.metric("⭐ Meilleur score", f"{top_score * 100:.1f}%")
                    with col3_m:
                        avg_score = results_df["Score brut"].mean()
                        st.metric("📈 Score moyen", f"{avg_score * 100:.1f}%")
                    
                    st.dataframe(results_df.drop(columns=["Score brut"]), use_container_width=True, hide_index=True)
                    
                    if explanations:
                        st.markdown("### 📝 Analyse détaillée de chaque CV")
                        for file_name, score in ranked_resumes:
                            if file_name in explanations:
                                with st.expander(f"Analyse pour : **{file_name}** (Score: {round(score * 100, 1)}%)", expanded=False):
                                    st.markdown(explanations[file_name])
                    
                    st.markdown("---")
                    st.markdown("### 💾 Exporter les Résultats")
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Télécharger CSV", csv, "resultats_classement.csv", "text/csv", use_container_width=True)
                else:
                    st.error("❌ Aucun score généré lors de l'analyse")
            else:
                st.error("❌ Aucun CV valide à analyser")

# -------------------- Onglet Analyse de Profil --------------------
with tab2:
    st.markdown("### 📂 Importer un CV pour une analyse individuelle")
    uploaded_file_analysis = st.file_uploader("Sélectionnez un CV (PDF)", type=["pdf"], key="analysis_uploader")
    
    analysis_type_single = st.selectbox(
        "Type d'analyse souhaité",
        ("Analyse par IA (Points forts/faibles)", "Analyse par NER (Extraction d'entités)")
    )
    
    if uploaded_file_analysis and st.button("🚀 Lancer l'analyse du profil", type="primary", use_container_width=True):
        with st.spinner("⏳ Analyse en cours..."):
            text = extract_text_from_pdf(uploaded_file_analysis)
            if "Erreur" in text:
                st.error(f"❌ {text}")
            else:
                st.markdown("### 📋 Résultat de l'Analyse")
                if analysis_type_single == "Analyse par IA (Points forts/faibles)":
                    analysis_result = get_deepseek_analysis(text)
                    col_analysis1, col_analysis2 = st.columns(2)
                    strong_points, weak_points = "", ""
                    if "Points forts" in analysis_result and "Points faibles" in analysis_result:
                        parts = analysis_result.split("Points faibles")
                        strong_points = parts[0]
                        if len(parts) > 1:
                            weak_points = "Points faibles" + parts[1]
                    else:
                        st.markdown(analysis_result)

                    if strong_points or weak_points:
                        with col_analysis1:
                            st.info("**Points forts**")
                            st.markdown(strong_points)
                        with col_analysis2:
                            st.warning("**Points faibles**")
                            st.markdown(weak_points)
                else:
                    entities = ner_analysis(text)
                    st.info("**Entités extraites par la méthode NER**")
                    st.json(entities)

# -------------------- Onglet Guide des Méthodes --------------------
with tab3:
    st.header("📖 Comprendre les Méthodes d'Analyse")
    st.markdown("Chaque méthode a ses propres forces et faiblesses. Voici un guide pour vous aider à choisir la plus adaptée à votre besoin.")

    st.subheader("1. Similarité Cosinus (Basée sur les Mots-clés)")
    st.markdown("- **Principe** : Compare la fréquence des mots exacts entre le CV et l'annonce.")
    st.markdown("- **Avantages** : ✅ Très rapide.")
    st.markdown("- **Limites** : ❌ Ne comprend pas le contexte. 'Gestion de projet' et 'management de projet' sont deux choses différentes pour lui.")
    
    st.subheader("2. Similarité Sémantique (Basée sur les Embeddings)")
    st.markdown("- **Principe** : Utilise une IA pour transformer les phrases en vecteurs de sens, puis compare ces vecteurs.")
    st.markdown("- **Avantages** : ✅ Comprend le contexte et les synonymes ('GED' et 'EDMS' sont similaires).")
    st.markdown("- **Limites** : ❌ Un peu plus lente que la méthode cosinus.")

    st.subheader("3. Scoring par Règles (Basé sur la NER)")
    st.markdown("- **Principe** : Extrait des informations précises (compétences, années d'expérience) et applique un score basé sur des règles que vous définissez.")
    st.markdown("- **Avantages** : ✅ Totalement transparent et personnalisable.")
    st.markdown("- **Limites** : ❌ Ne fonctionne bien que si les règles sont bien définies et peut manquer des informations non prévues.")
    
    st.subheader("4. Analyse par IA (Basée sur un LLM)")
    st.markdown("- **Principe** : Envoie le CV et l'annonce à un grand modèle de langage (DeepSeek) qui agit comme un expert en recrutement.")
    st.markdown("- **Avantages** : ✅ La plus précise, comprend les nuances et fournit une explication détaillée.")
    st.markdown("- **Limites** : ❌ La plus lente et **consomme vos tokens !**")

# -------------------- Section latérale --------------------
with st.sidebar:
    st.markdown("### 📊 Statistiques")
    total_cvs_analyzed = len(uploaded_files_ranking) if uploaded_files_ranking else 0
    st.metric("CVs chargés pour le classement", total_cvs_analyzed)
    
    st.markdown("---")
    st.markdown("### 🔧 Configuration")
    if st.button("Test Connexion API DeepSeek"):
        if API_KEY:
            try:
                response = requests.get("https://api.deepseek.com/v1/models", headers={"Authorization": f"Bearer {API_KEY}"})
                if response.status_code == 200:
                    st.success("✅ Connexion API réussie")
                else:
                    st.error(f"❌ Erreur de connexion API ({response.status_code})")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        else:
            st.error("❌ Clé API non configurée")