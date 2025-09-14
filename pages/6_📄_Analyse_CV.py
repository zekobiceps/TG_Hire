import streamlit as st
import pandas as pd
import io
import requests
import json
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time

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

# --- CSS personnalisée ---
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #dc2626;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-radius: 10px;
        border-left: 5px solid #dc2626;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #dc2626;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #fecaca;
    }
    .stButton>button {
        background-color: #dc2626;
        color: white;
        font-size: 16px;
        border-radius: 8px;
        padding: 12px 24px;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #b91c1c;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    }
    .result-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #dc2626;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f8f9fa;
        border-radius: 8px 8px 0 0;
        padding: 12px 20px;
        font-size: 16px;
        color: #dc2626;
        border: 1px solid #e5e5e5;
        border-bottom: none;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #fecaca;
    }
    .stTabs [aria-selected="true"] {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
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

def rank_resumes(job_description, resumes):
    """Classe les CV en fonction de leur similarité avec la description de poste."""
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
st.markdown('<div class="main-header">📋 HireSense IA</div>', unsafe_allow_html=True)
st.markdown("---")
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
                scores = rank_resumes(job_description, resumes)
                
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