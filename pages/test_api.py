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

# Imports pour la méthode sémantique
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
    try:
        pdf = PdfReader(file)
        text = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
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
        return {"scores": cosine_similarities}
    except Exception as e:
        st.error(f"❌ Erreur Cosinus: {e}")
        return {"scores": []}

# --- MÉTHODE 2 : WORD EMBEDDINGS ---
def rank_resumes_with_embeddings(job_description, resumes):
    try:
        jd_embedding = embedding_model.encode(job_description, convert_to_tensor=True)
        resume_embeddings = embedding_model.encode(resumes, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(jd_embedding, resume_embeddings)
        return {"scores": cosine_scores.flatten().cpu().numpy()}
    except Exception as e:
        st.error(f"❌ Erreur Sémantique : {e}")
        return {"scores": []}

# --- ANALYSE PAR REGEX ---
def regex_analysis(text):
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

# --- NOUVEAUTÉ : SCORING PAR RÈGLES RENVOYANT LA LOGIQUE ---
def rank_resumes_with_rules(job_description, resumes, file_names):
    jd_entities = regex_analysis(job_description)
    results = []
    
    TECH_SKILL_WEIGHT = 10
    EXPERIENCE_WEIGHT = 20
    
    for i, resume_text in enumerate(resumes):
        resume_entities = regex_analysis(resume_text)
        current_score = 0
        
        logic = {}
        
        common_tech_skills = set(jd_entities["Compétences Techniques"]) & set(resume_entities["Compétences Techniques"])
        score_from_tech = len(common_tech_skills) * TECH_SKILL_WEIGHT
        current_score += score_from_tech
        logic['Compétences Techniques trouvées'] = f"{list(common_tech_skills)} (+{score_from_tech} pts)"

        required_exp = jd_entities.get("Années d'expérience détectées", 0)
        candidate_exp = resume_entities.get("Années d'expérience détectées", 0)
        score_from_exp = 0
        if required_exp > 0 and candidate_exp >= required_exp:
            score_from_exp = EXPERIENCE_WEIGHT
            current_score += score_from_exp
        logic['Expérience'] = f"{candidate_exp} ans détectés vs {required_exp} requis (+{score_from_exp} pts)"

        results.append({
            "file_name": file_names[i],
            "score": current_score,
            "logic": logic
        })

    max_possible_score = len(jd_entities["Compétences Techniques"]) * TECH_SKILL_WEIGHT
    if jd_entities.get("Années d'expérience détectées", 0) > 0:
        max_possible_score += EXPERIENCE_WEIGHT

    if max_possible_score > 0:
        for res in results:
            res["score"] /= max_possible_score
            
    return results

# --- MÉTHODE 4 : ANALYSE PAR IA ---
def get_detailed_score_with_ai(job_description, resume_text):
    if not API_KEY: return {"score": 0.0, "explanation": "❌ Analyse IA impossible. Clé API non configurée."}
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
    return {"scores": [d["score"] for d in scores_data], "explanations": {d["file_name"]: d["explanation"] for d in scores_data}}

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
    # --- NOUVEAUTÉ : Retour de la disposition en colonnes ---
    col1, col2 = st.columns([2, 1])
    with col1:
        job_title = st.text_input("Intitulé du poste", placeholder="Ex: Chef de projet GED")
        job_description = st.text_area("Description du poste", height=200, key="jd_ranking", placeholder="Collez la description complète du poste ici...")
    with col2:
        st.markdown("#### 📤 Importer des CVs")
        uploaded_files_ranking = st.file_uploader("Importer des CVs", type=["pdf"], accept_multiple_files=True, key="ranking_uploader")
    
    st.markdown("---")
    
    analysis_method = st.radio(
        "✨ Choisissez votre méthode de classement",
        ["Similarité Cosinus (Mots-clés)", "Similarité Sémantique (Embeddings)", "Scoring par Règles (Regex)", "Analyse par IA (DeepSeek)"],
        index=0, help="Consultez l'onglet 'Guide des Méthodes'."
    )

    if st.button("🔍 Analyser et Classer", type="primary", use_container_width=True, disabled=not (uploaded_files_ranking and job_description)):
        resumes, file_names = [], []
        with st.spinner("Lecture des fichiers PDF..."):
            for file in uploaded_files_ranking:
                text = extract_text_from_pdf(file)
                if not "Erreur" in text:
                    resumes.append(text)
                    file_names.append(file.name)
        
        with st.spinner("Analyse des CVs en cours..."):
            results, explanations, logic = None, None, None
            if analysis_method == "Analyse par IA (DeepSeek)":
                results = rank_resumes_with_ai(job_description, resumes, file_names)
                explanations = results.get("explanations")
            elif analysis_method == "Scoring par Règles (Regex)":
                rule_results = rank_resumes_with_rules(job_description, resumes, file_names)
                results = {"scores": [r["score"] for r in rule_results]}
                logic = {r["file_name"]: r["logic"] for r in rule_results}
            elif analysis_method == "Similarité Sémantique (Embeddings)":
                results = rank_resumes_with_embeddings(job_description, resumes)
            else: # Cosinus par défaut
                results = rank_resumes_with_cosine(job_description, resumes)

            scores = results.get("scores", [])
            if scores:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                results_df = pd.DataFrame(ranked_resumes, columns=["Nom du CV", "Score brut"])
                results_df["Rang"] = range(1, len(results_df) + 1)
                results_df["Score"] = results_df["Score brut"].apply(lambda x: f"{x*100:.1f}%")
                
                st.markdown("### 🏆 Résultats du Classement")
                st.dataframe(results_df[["Rang", "Nom du CV", "Score"]], use_container_width=True, hide_index=True)
                
                # --- NOUVEAUTÉ : Affichage de la logique de scoring pour Regex ---
                if logic:
                    st.markdown("### 🧠 Logique de Scoring (Règles)")
                    for _, row in results_df.iterrows():
                        file_name = row["Nom du CV"]
                        with st.expander(f"Détail du score pour : **{file_name}**"):
                            st.json(logic.get(file_name, "Aucun détail disponible."))

                if explanations:
                    st.markdown("### 📝 Analyse détaillée par l'IA")
                    for _, row in results_df.iterrows():
                        file_name = row["Nom du CV"]
                        score = row["Score brut"]
                        with st.expander(f"Analyse pour : **{file_name}** (Score: {score*100:.1f}%)"):
                            st.markdown(explanations.get(file_name, "Aucune explication disponible."))

# --- ONGLET ANALYSE DE PROFIL ---
with tab2:
    st.markdown("### 📂 Importer un ou plusieurs CVs pour une analyse individuelle")
    # --- NOUVEAUTÉ : Correction du bug, on peut uploader plusieurs fichiers ---
    uploaded_files_analysis = st.file_uploader("Importer des CVs", type=["pdf"], key="analysis_uploader", accept_multiple_files=True)
    
    # --- NOUVEAUTÉ : Les 4 méthodes sont disponibles ---
    analysis_type_single = st.selectbox(
        "Type d'analyse souhaité",
        ("Analyse par IA (DeepSeek)", "Analyse par Regex (Extraction d'entités)", "Score Sémantique", "Score Cosinus")
    )
    # --- NOUVEAUTÉ : Explications sous le menu déroulant ---
    captions = {
        "Analyse par IA (DeepSeek)": "Analyse qualitative (points forts/faibles) par un LLM. Consomme vos tokens !",
        "Analyse par Regex (Extraction d'entités)": "Extrait des informations structurées (compétences, etc.) sur la base de mots-clés.",
        "Score Sémantique": "Calcule un score de pertinence basé sur le sens des phrases (nécessite une description de poste).",
        "Score Cosinus": "Calcule un score de pertinence basé sur les mots-clés (nécessite une description de poste)."
    }
    st.caption(captions.get(analysis_type_single))

    # --- NOUVEAUTÉ : On demande la description de poste si nécessaire ---
    job_desc_single = ""
    if "Score" in analysis_type_single:
        job_desc_single = st.text_area("Description du poste pour le calcul du score", height=150, key="jd_single")

    if uploaded_files_analysis and st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True):
        # --- NOUVEAUTÉ : Boucle pour analyser tous les fichiers ---
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
                        elif "Score Sémantique" in analysis_type_single:
                            if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                            else:
                                score = rank_resumes_with_embeddings(job_desc_single, [text])["scores"][0]
                                st.metric("Score de Pertinence Sémantique", f"{score*100:.1f}%")
                        elif "Score Cosinus" in analysis_type_single:
                            if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                            else:
                                score = rank_resumes_with_cosine(job_desc_single, [text])["scores"][0]
                                st.metric("Score de Pertinence Cosinus", f"{score*100:.1f}%")
                        else: # Analyse IA par défaut
                            analysis_result = get_deepseek_analysis(text)
                            st.markdown(analysis_result)

# --- ONGLET GUIDE DES MÉTHODES ---
with tab3:
    st.header("📖 Comprendre les Méthodes d'Analyse")
    st.markdown("Chaque méthode a ses propres forces et faiblesses. Voici un guide pour vous aider à choisir la plus adaptée à votre besoin.")
    
    # --- NOUVEAUTÉ : Explications beaucoup plus détaillées ---
    st.subheader("1. Similarité Cosinus (Basée sur les Mots-clés)")
    st.markdown("""
    - **Principe** : Cette méthode transforme le CV et l'annonce en listes de mots-clés, puis compte combien de mots importants sont communs aux deux documents.
    - **Comment ça marche ?** Elle utilise un modèle mathématique (TF-IDF) pour donner plus de poids aux mots rares et importants (comme "archivage") qu'aux mots très courants (comme "le", "de"). Le score représente la similarité de ces "sacs de mots-clés".
    - **Idéal pour** : Un premier tri très rapide et grossier.
    - **Avantages** : ✅ Extrêmement rapide, ne nécessite aucune IA externe.
    - **Limites** : ❌ Ne comprend absolument pas le contexte ou les synonymes. Pour lui, "GED" (Gestion Électronique de Documents) et "EDMS" (Electronic Document Management System) sont deux termes complètement différents.
    """)
    
    st.subheader("2. Similarité Sémantique (Basée sur les Embeddings)")
    st.markdown("""
    - **Principe** : Utilise un modèle de langage pré-entraîné (ici, `Sentence-BERT`) pour convertir les phrases en vecteurs numériques qui représentent leur signification.
    - **Comment ça marche ?** Au lieu de comparer des mots, on compare la "direction" de ces vecteurs dans un espace à plusieurs dimensions. Deux vecteurs qui pointent dans la même direction représentent des idées sémantiquement similaires.
    - **Idéal pour** : Obtenir un score de pertinence plus intelligent qui comprend les nuances du langage.
    - **Avantages** : ✅ Comprend le contexte, les synonymes et les concepts similaires. C'est un excellent équilibre entre vitesse et intelligence.
    - **Limites** : ❌ Un peu plus lente que la méthode cosinus car elle fait appel à un modèle de deep learning.
    """)

    st.subheader("3. Scoring par Règles (Basé sur Regex)")
    st.markdown("""
    - **Principe** : Imite la façon dont un recruteur humain lit un CV en cherchant des informations spécifiques. On définit des règles claires (ex: "trouver ces compétences", "vérifier les années d'expérience") et on attribue des points.
    - **Comment ça marche ?** Le code utilise des expressions régulières (Regex) pour rechercher des mots-clés précis et des schémas de texte (comme "X ans d'expérience") dans le CV. Un score est ensuite calculé en fonction de ce qui a été trouvé.
    - **Idéal pour** : Des postes où les critères sont très clairs et objectifs (ex: "doit avoir la compétence X et plus de 5 ans d'expérience").
    - **Avantages** : ✅ Totalement transparent (le détail du score peut être affiché), 100% personnalisable et sans dépendances complexes.
    - **Limites** : ❌ Très rigide. Si une compétence est formulée différemment de ce qui est prévu dans les règles, elle ne sera pas détectée.
    """)
    
    st.subheader("4. Analyse par IA (Basée sur un LLM)")
    st.markdown("""
    - **Principe** : C'est la méthode la plus avancée. On envoie le CV et l'annonce à un grand modèle de langage (ici, DeepSeek), en lui demandant d'agir comme un expert en recrutement et de donner son avis.
    - **Comment ça marche ?** L'IA lit et comprend les deux textes dans leur intégralité, puis utilise sa vaste connaissance pour évaluer la pertinence, identifier les forces et les faiblesses, et formuler une explication détaillée.
    - **Idéal pour** : Obtenir une analyse fine et contextuelle, similaire à celle d'un premier entretien.
    - **Avantages** : ✅ La plus précise et la plus "humaine". Comprend les nuances, l'expérience implicite et peut fournir des explications de haute qualité.
    - **Limites** : ❌ La plus lente, et chaque analyse **consomme vos tokens !**
    """)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🔧 Configuration")
    if st.button("Test Connexion API DeepSeek"):
        if API_KEY:
            try:
                response = requests.get("https://api.deepseek.com/v1/models", headers={"Authorization": f"Bearer {API_KEY}"})
                st.success("✅ Connexion API réussie") if response.status_code == 200 else st.error(f"❌ Erreur de connexion ({response.status_code})")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        else:
            st.error("❌ Clé API non configurée")