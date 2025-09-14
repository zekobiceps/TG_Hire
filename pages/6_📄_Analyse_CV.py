import streamlit as st
import pandas as pd
import io
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="HireSense AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Resume Processing Functions ---
def extract_text_from_pdf(file):
    """Extracts text from an uploaded PDF file."""
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
    """Ranks resumes based on their similarity to the job description."""
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

# Add custom CSS for better styling with 'rouge vif' buttons
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #dc2626; /* Bright red text */
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
        background-color: #dc2626; /* Bright red button color */
        color: white;
        font-size: 16px;
        border-radius: 8px;
        padding: 12px 24px;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #b91c1c; /* Darker red on hover */
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    }
    
    .upload-box {
        background: #fafafa;
        border: 2px dashed #e5e5e5;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
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
    
    .error-message {
        background-color: #fee2e2;
        border: 1px solid #fecaca;
        color: #dc2626;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-message {
        background-color: #d1fae5;
        border: 1px solid #a7f3d0;
        color: #065f46;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header">📋 Analyse de CV</div>', unsafe_allow_html=True)

    # --- Job Information Section ---
    st.markdown('<div class="section-header">📄 Informations du Poste</div>', unsafe_allow_html=True)
    
    job_title = st.text_input(
        "Intitulé du poste",
        placeholder="Ex: Développeur Python Senior",
        help="Saisissez le titre du poste à pourvoir"
    )
    
    # --- Job Description & Resume Upload ---
    st.markdown('<div class="section-header">📝 Description de Poste & 📂 CVs</div>', unsafe_allow_html=True)

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
        uploaded_files = st.file_uploader(
            "Sélectionnez les CVs (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Sélectionnez un ou plusieurs fichiers PDF de CV"
        )
        
        if uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files
            st.success(f"✅ {len(uploaded_files)} CV(s) importé(s) avec succès")
            
            # Afficher un aperçu des fichiers
            with st.expander("📋 Liste des CVs"):
                for file in uploaded_files:
                    st.write(f"• {file.name}")

    st.markdown("---")

    # --- Processing & Ranking ---
    if st.button(
        "🔍 Analyser les CVs", 
        type="primary", 
        disabled=not (uploaded_files and job_description),
        use_container_width=True
    ):
        with st.spinner("🔍 Analyse des CVs en cours..."):
            resumes = []
            file_names = []
            error_files = []
            
            # Process each resume
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                if "Erreur" in text or "Error" in text:
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
                    
                    # Create results dataframe
                    results_df = pd.DataFrame({
                        "Rang": range(1, len(ranked_resumes) + 1),
                        "Nom du CV": [name for name, _ in ranked_resumes],
                        "Score de correspondance": [f"{round(score * 100, 1)}%" for _, score in ranked_resumes],
                        "Score brut": [round(score, 4) for _, score in ranked_resumes]
                    })
                    
                    # Display results
                    st.markdown('<div class="section-header">🏆 Résultats du Classement</div>', unsafe_allow_html=True)
                    
                    # Metrics row
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 CVs analysés", len(results_df))
                    with col2:
                        top_score = results_df["Score brut"].max()
                        st.metric("⭐ Meilleur score", f"{top_score * 100:.1f}%")
                    with col3:
                        avg_score = results_df["Score brut"].mean()
                        st.metric("📈 Score moyen", f"{avg_score * 100:.1f}%")
                    
                    # Results table
                    st.dataframe(
                        results_df.drop(columns=["Score brut"]).rename(columns={
                            "Rang": "#",
                            "Nom du CV": "CV",
                            "Score de correspondance": "Score"
                        }), 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Download options
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

if __name__ == "__main__":
    main()