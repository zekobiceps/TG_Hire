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

        # --- NOUVEAUTÉ : Extraction de la logique pour la sémantique ---
        logic = {}
        jd_sentences = job_description.split('.')
        jd_sent_embeddings = embedding_model.encode(jd_sentences, convert_to_tensor=True)

        for i, resume_text in enumerate(resumes):
            resume_sentences = resume_text.split('.')
            resume_sent_embeddings = embedding_model.encode(resume_sentences, convert_to_tensor=True)
            
            # Trouver les phrases les plus similaires
            similarity_matrix = util.pytorch_cos_sim(resume_sent_embeddings, jd_sent_embeddings)
            best_matches = {}
            for sent_idx, jd_sent in enumerate(jd_sentences):
                if len(jd_sent.strip()) > 10: # Ignorer les phrases trop courtes
                    best_match_score, best_match_idx = torch.max(similarity_matrix[:, sent_idx], dim=0)
                    if best_match_score > 0.6: # Seuil de pertinence
                         best_matches[jd_sent.strip()] = resume_sentences[best_match_idx].strip()
            logic[file_names[i]] = {"Phrases les plus pertinentes correspondantes (Annonce -> CV)": best_matches}

        return {"scores": scores, "logic": logic}
    except Exception as e:
        st.error(f"❌ Erreur Sémantique : {e}")
        return {"scores": [], "logic": {}}

# --- ANALYSE PAR REGEX AMÉLIORÉE (AVEC CALCUL D'EXPÉRIENCE) ---
def regex_analysis(text):
    text_lower = text.lower()
    
    # --- NOUVEAUTÉ : Calcul d'expérience basé sur les dates ---
    total_experience_months = 0
    # Cherche des formats comme "MM/AAAA - MM/AAAA" ou "Mois AAAA - Mois AAAA"
    date_ranges = re.findall(r'(\d{2}/\d{4})\s*-\s*(\d{2}/\d{4})|([a-zA-Z]+\.?\s+\d{4})\s*-\s*([a-zA-Z]+\.?\s+\d{4})', text)
    
    for match in date_ranges:
        try:
            start_str, end_str = match[0] or match[2], match[1] or match[3]
            # Gérer "aujourd'hui" ou "à ce jour"
            if "aujourd'hui" in end_str.lower() or "jour" in end_str.lower():
                end_date = datetime.now()
            else:
                end_date = datetime.strptime(end_str.replace('.',''), '%m/%Y' if '/' in start_str else '%b %Y')

            start_date = datetime.strptime(start_str.replace('.',''), '%m/%Y' if '/' in start_str else '%b %Y')
            
            duration = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            total_experience_months += duration
        except Exception:
            continue # Ignorer les dates mal formatées

    total_experience_years = round(total_experience_months / 12)

    # ... (Le reste de l'extraction des compétences et diplômes reste identique) ...
    education_level = 0
    edu_patterns = {5: r'bac\s*\+\s*5|master|ingénieur', 3: r'bac\s*\+\s*3|licence', 2: r'bac\s*\+\s*2|bts|dut', 0: r'baccalauréat'}
    for level, pattern in edu_patterns.items():
        if re.search(pattern, text_lower):
            education_level = level
            break
            
    skills = []
    profile_section_match = re.search(r"profil recherché\s*:(.*?)(?:\n\n|\Z)", text_lower, re.DOTALL | re.IGNORECASE)
    if profile_section_match:
        profile_section = profile_section_match.group(1)
        words = re.findall(r'\b[a-zA-ZÀ-ÿ-]{4,}\b', profile_section)
        stop_words = ["profil", "recherché", "maîtrise", "bonne", "expérience", "esprit", "basé", "casablanca", "missions", "principales", "confirmée"]
        skills = [word for word in words if word not in stop_words]

    return {
        "Niveau d'études": education_level,
        "Années d'expérience calculées": total_experience_years,
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
        
        common_skills = set(jd_entities["Compétences clés extraites"]) & set(resume_text.lower().split())
        score_from_skills = len(common_skills) * SKILL_WEIGHT
        current_score += score_from_skills
        logic['Compétences correspondantes'] = f"{list(common_skills)} (+{score_from_skills} pts)"

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
tab1, tab2, tab3 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil", "📖 Guide des Méthodes"])

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
        ["Méthode Cosinus (Mots-clés)", "Méthode Sémantique (Embeddings)", "Scoring par Règles (Regex)", "Analyse par IA (DeepSeek)"],
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
            results, explanations, logic = {}, None, None
            if analysis_method == "Analyse par IA (DeepSeek)":
                results = rank_resumes_with_ai(job_description, resumes, file_names)
                explanations = results.get("explanations")
            elif analysis_method == "Scoring par Règles (Regex)":
                rule_results = rank_resumes_with_rules(job_description, resumes, file_names)
                results = {"scores": [r["score"] for r in rule_results]}
                logic = {r["file_name"]: r["logic"] for r in rule_results}
            elif analysis_method == "Méthode Sémantique (Embeddings)":
                results = rank_resumes_with_embeddings(job_description, resumes)
            else: # Cosinus
                results = rank_resumes_with_cosine(job_description, resumes, file_names)
                logic = results.get("logic")

            scores = results.get("scores", [])
            if scores is not None and len(scores) > 0:
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                results_df = pd.DataFrame(ranked_resumes, columns=["Nom du CV", "Score brut"])
                results_df["Rang"] = range(1, len(results_df) + 1)
                results_df["Score"] = results_df["Score brut"].apply(lambda x: f"{x*100:.1f}%")
                
                st.markdown("### 🏆 Résultats du Classement")
                st.dataframe(results_df[["Rang", "Nom du CV", "Score"]], use_container_width=True, hide_index=True)
                
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

    if uploaded_files_analysis and st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True, key="btn_single_analysis"):
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
                                score = rank_resumes_with_embeddings(job_desc_single, [text])["scores"][0]
                                st.metric("Score de Pertinence Sémantique", f"{score*100:.1f}%")
                        elif "Méthode Cosinus" in analysis_type_single:
                            if not job_desc_single: st.warning("Veuillez fournir une description de poste.")
                            else:
                                score = rank_resumes_with_cosine(job_desc_single, [text], [uploaded_file.name])["scores"][0]
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