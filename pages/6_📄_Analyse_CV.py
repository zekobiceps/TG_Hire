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

# --- Configuration de la clé API DeepSeek via Streamlit Secrets ---
try:
    API_KEY = st.secrets["DEEPSEEK_API_KEY"]
    if not API_KEY:
        st.error("❌ La clé API DeepSeek n'est pas configurée dans les secrets de Streamlit. Veuillez l'ajouter sous le nom 'DEEPSEEK_API_KEY'.")
except KeyError:
    API_KEY = None
    st.error("❌ Le secret 'DEEPSEEK_API_KEY' est introuvable. Veuillez le configurer.")

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="HireSense AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS personnalisée pour le thème sombre ---
st.markdown("""
    <style>
    /* Style général pour l'application */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Style pour les onglets de navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #0E1117;
        padding: 0px;
        border-radius: 4px;
        /* Suppression de la bordure blanche */
    }
    
    /* Style de base pour tous les onglets */
    .stTabs [data-baseweb="tab"] {
        background-color: #0E1117 !important;
        color: white !important;
        border-right: 1px solid white !important; /* Bordure blanche entre les onglets */
        border-radius: 0 !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        margin-right: 0 !important;
        height: auto !important;
    }
    
    /* Style pour l'onglet actif */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #FF0000 !important; /* Rouge vif pour le texte de l'onglet actif */
        background-color: #0E1117 !important;
        border: 1px solid white !important;
        border-bottom: 3px solid #FF0000 !important; /* Bordure inférieure rouge vif */
    }
    
    /* Boutons principaux */
    .stButton > button {
        background-color: #dc2626;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #b91c1c;
        transform: translateY(-2px);
    }
    
    /* Boutons secondaires */
    .stButton > button[kind="secondary"] {
        background-color: #262730;
        color: #FAFAFA;
        border: 1px solid #FF4B4B;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #3D3D4D;
        color: #FAFAFA;
    }
    
    /* Conteneurs et cartes */
    .result-card {
        background: #1E1E1E;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        border-left: 4px solid #dc2626;
        color: #FAFAFA;
    }
    
    .metric-card {
        background: #1E1E1E;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        text-align: center;
        margin: 1rem 0;
        color: #FAFAFA;
    }
    
    /* Champs de saisie */
    .stTextInput input, .stTextArea textarea, .stFileUploader label, .stSelectbox [data-baseweb="select"] > div {
        background-color: #2D2D2D !important;
        color: white !important;
        border: 1px solid #555 !important;
        border-radius: 4px !important;
        padding: 8px !important;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #FF0000;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #FF0000;
    }

    </style>
""", unsafe_allow_html=True)

# --- Fonctions de traitement des CV ---
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

def get_detailed_score_with_ai(job_description, resume_text):
    """Évalue la pertinence d'un CV en utilisant l'IA, en fournissant un score et une explication détaillée."""
    if not API_KEY:
        return {"score": 0.0, "explanation": "❌ Analyse IA impossible. Clé API non configurée."}
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

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
        "temperature": 0.0 # Vise une réponse déterministe
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        full_response_text = response_data["choices"][0]["message"]["content"].strip()
        
        # Extraire le score et l'explication
        score_match = re.search(r"Score: (\d+)%", full_response_text)
        score = int(score_match.group(1)) / 100 if score_match else 0.0
        
        explanation_parts = full_response_text.split("2. Une analyse détaillée", 1)
        explanation = explanation_parts[1].strip() if len(explanation_parts) > 1 else full_response_text
        
        return {"score": score, "explanation": explanation}
    except Exception as e:
        st.warning(f"⚠️ Erreur lors de l'évaluation par l'IA: {e}")
        return {"score": 0.0, "explanation": "❌ Analyse IA échouée. Impossible de fournir une explication détaillée."}

def rank_resumes_with_ai(job_description, resumes, file_names):
    """Classe les CV en utilisant l'IA pour évaluer la pertinence de chaque CV et fournit des explications."""
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
    """Analyse le texte du CV pour identifier les points forts et faibles en utilisant DeepSeek."""
    if not API_KEY:
        return "Analyse impossible. Veuillez configurer votre clé API."
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
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
        if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        else:
            return "❌ Réponse de l'API DeepSeek inattendue."
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Erreur de connexion à l'API DeepSeek : {e}")
        return "Analyse IA échouée. Veuillez vérifier votre connexion ou votre clé API."
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse IA : {e}")
        return "Analyse IA échouée. Veuillez réessayer."

# --- Gestion des pages via des onglets ---
tab1, tab2 = st.tabs(["📊 Classement de CVs", "🎯 Analyse de Profil"])

# --- Contenu de l'onglet Classement ---
with tab1:
    st.markdown('<div class="section-header">📄 Informations du Poste</div>', unsafe_allow_html=True)
    
    job_title = st.text_input(
        "Intitulé du poste",
        placeholder="Ex: Développeur Python Senior",
        help="Saisissez le titre du poste à pourvoir"
    )
    
    col1, col2 = st.columns([1, 1])

    with col1:
        job_description = st.text_area(
            "Description du poste",
            placeholder="Coller ou écrire la description complète du poste ici...",
            height=200,
            help="Décrivez les responsabilités, compétences requises et exigences du poste"
        )

    with col2:
        st.markdown("#### 📤 Importer des CVs")
        uploaded_files_ranking = st.file_uploader(
            "Sélectionnez les CVs (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            key="ranking_uploader",
            help="Sélectionnez un ou plusieurs fichiers PDF de CV"
        )
        
        if uploaded_files_ranking:
            st.success(f"✅ {len(uploaded_files_ranking)} CV(s) importé(s) avec succès")
            with st.expander("📋 Liste des CVs"):
                for file in uploaded_files_ranking:
                    st.write(f"• {file.name}")

    st.markdown("---")
    
    # Remplacer la case à cocher par l'option radio et le bouton d'aide
    use_ai_for_ranking = st.checkbox(
        "Utiliser l'IA de DeepSeek pour le classement", 
        value=False,
        help="""
            **Méthode du cosinus** : Par défaut, cette méthode analyse la fréquence des mots entre les CV et la description du poste pour calculer un score de similarité.

            **Utilisation de l'IA de DeepSeek** : Cochez cette option pour utiliser l'IA. Elle fournit une analyse plus détaillée et un classement plus pertinent basé sur la compréhension du contexte et des compétences. Cela utilise votre quota API.
        """
    )

    st.markdown("---")

    if st.button(
        "🔍 Analyser les CVs", 
        type="primary", 
        disabled=not (uploaded_files_ranking and job_description),
        use_container_width=True
    ):
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
                if use_ai_for_ranking:
                    scores_data = rank_resumes_with_ai(job_description, resumes, file_names)
                    scores = [data["score"] for data in scores_data]
                    explanations = {data["file_name"]: data["explanation"] for data in scores_data}
                else: # Méthode du cosinus
                    scores = rank_resumes_with_cosine(job_description, resumes)
                    explanations = None

                if len(scores) > 0:
                    ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                    
                    results_df = pd.DataFrame({
                        "Rang": range(1, len(ranked_resumes) + 1),
                        "Nom du CV": [name for name, _ in ranked_resumes],
                        "Score de correspondance": [f"{round(score * 100, 1)}%" for _, score in ranked_resumes],
                        "Score brut": [round(score, 4) for _, score in ranked_resumes]
                    })
                    
                    st.markdown('<div class="section-header">🏆 Résultats du Classement</div>', unsafe_allow_html=True)
                    
                    col1_m, col2_m, col3_m = st.columns(3)
                    with col1_m:
                        st.metric("📊 CVs analysés", len(results_df))
                    with col2_m:
                        top_score = results_df["Score brut"].max()
                        st.metric("⭐ Meilleur score", f"{top_score * 100:.1f}%")
                    with col3_m:
                        avg_score = results_df["Score brut"].mean()
                        st.metric("📈 Score moyen", f"{avg_score * 100:.1f}%")
                    
                    st.dataframe(
                        results_df.drop(columns=["Score brut"]).rename(columns={"Rang": "#", "Nom du CV": "CV", "Score de correspondance": "Score"}), 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("---")
                    st.markdown('<div class="section-header">🔍 Comment le score est-il calculé ?</div>', unsafe_allow_html=True)
                    if use_ai_for_ranking:
                        st.info("Le score est basé sur une évaluation IA. Pour une analyse détaillée, consultez les sections ci-dessous.")
                        st.markdown('<div class="section-header">📝 Analyse détaillée de chaque CV</div>', unsafe_allow_html=True)
                        for file_name, score in ranked_resumes:
                            if file_name in explanations:
                                with st.expander(f"Analyse détaillée pour : **{file_name}** (Score: {round(score * 100, 1)}%)", expanded=False):
                                    st.markdown(explanations[file_name])
                    else:
                        st.info("""
                            Le score de correspondance est basé sur la **similarité cosinus**. 
                            Cette méthode analyse la fréquence des mots et des phrases dans chaque CV par rapport à la description du poste. 
                            Un score élevé (proche de 100 %) indique une forte correspondance thématique et de compétences.
                        """)
                    
                    st.markdown("---")
                    st.markdown('<div class="section-header">💾 Exporter les Résultats</div>', unsafe_allow_html=True)
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Télécharger CSV", 
                        csv, 
                        "resultats_classement.csv", 
                        "text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("❌ Aucun score généré lors de l'analyse")
            else:
                st.error("❌ Aucun CV valide à analyser")

# --- Contenu de l'onglet Analyse de Profil ---
with tab2:
    st.markdown('<div class="section-header">📂 Importer des CVs pour analyse</div>', unsafe_allow_html=True)
    uploaded_files_analysis = st.file_uploader(
        "Sélectionnez un ou plusieurs CVs (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="analysis_uploader",
        help="Téléchargez un ou plusieurs CVs pour les analyser avec l'IA."
    )

    if uploaded_files_analysis:
        st.success(f"✅ {len(uploaded_files_analysis)} fichier(s) importé(s).")
        st.markdown("---")
        if st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True):
            if not API_KEY:
                st.error("L'analyse IA ne peut pas être effectuée car la clé API n'est pas configurée.")
            else:
                st.markdown('<div class="section-header">📋 Résultats des Analyses</div>', unsafe_allow_html=True)
                for uploaded_file in uploaded_files_analysis:
                    with st.expander(f"Analyse du CV : **{uploaded_file.name}**", expanded=True):
                        with st.spinner(f"⏳ L'IA analyse le CV '{uploaded_file.name}', veuillez patienter..."):
                            text = extract_text_from_pdf(uploaded_file)
                            if "Erreur" in text:
                                st.error(f"❌ Erreur lors de l'extraction du texte : {text}")
                            else:
                                analysis_result = get_deepseek_analysis(text)
                                col_analysis1, col_analysis2 = st.columns(2)
                                
                                # Séparer les points forts et faibles pour les colonnes
                                strong_points = ""
                                weak_points = ""
                                if "Points forts" in analysis_result and "Points faibles" in analysis_result:
                                    parts = analysis_result.split("Points faibles")
                                    strong_points = parts[0]
                                    if len(parts) > 1:
                                        weak_points = "Points faibles" + parts[1]
                                    else:
                                        weak_points = ""
                                else:
                                    # Fallback si l'IA ne suit pas le format exact
                                    st.markdown(analysis_result)

                                if strong_points or weak_points:
                                    with col_analysis1:
                                        st.markdown(f'<div class="result-card">{strong_points}</div>', unsafe_allow_html=True)
                                    with col_analysis2:
                                        st.markdown(f'<div class="result-card">{weak_points}</div>', unsafe_allow_html=True)