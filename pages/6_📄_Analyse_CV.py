import streamlit as st
import pandas as pd
import os
import io
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import uuid
from datetime import datetime
import sqlite3
import json

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="HireSense AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Database Setup ---
def init_db():
    """Initialize SQLite database with necessary tables"""
    try:
        conn = sqlite3.connect('Resume.db')
        c = conn.cursor()
        
        # Create ranking history table with proper constraints
        c.execute('''
        CREATE TABLE IF NOT EXISTS ranking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            job_title TEXT,
            description TEXT,
            results TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        st.success("✅ Base de données initialisée avec succès")
    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation de la base de données: {e}")

# --- Initialize Session State ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"

# --- Resume History Functions ---
def save_ranking_history(job_title, description, results):
    """Save resume ranking history."""
    try:
        conn = sqlite3.connect('Resume.db')
        c = conn.cursor()
        
        # Convert DataFrame to JSON string safely
        results_json = results.to_json(orient='records')
        
        # Create new history entry with proper data handling
        c.execute(
            "INSERT INTO ranking_history (timestamp, job_title, description, results) VALUES (?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                job_title if job_title else "Poste sans titre",
                description if description else "Aucune description",
                results_json
            )
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde de l'historique: {e}")
        return False

def get_history():
    """Get resume ranking history."""
    try:
        conn = sqlite3.connect('Resume.db')
        
        # Get all history records
        query = "SELECT id, timestamp, job_title, description, results FROM ranking_history ORDER BY timestamp DESC"
        history_df = pd.read_sql_query(query, conn)
        
        conn.close()
        return history_df
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération de l'historique: {e}")
        return pd.DataFrame()

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

# Add custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e40af;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-radius: 10px;
        border-left: 5px solid #1e40af;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1e40af;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0f2fe;
    }
    
    .stButton>button {
        background-color: #1e40af;
        color: white;
        font-size: 16px;
        border-radius: 8px;
        padding: 12px 24px;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #1e3a8a;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3);
    }
    
    .upload-box {
        background: #f8fafc;
        border: 2px dashed #cbd5e1;
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
        border-left: 4px solid #1e40af;
    }
    
    .sidebar-content {
        padding: 2rem 1rem;
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

def show_history_page():
    st.markdown('<div class="main-header">📊 Historique des Classements</div>', unsafe_allow_html=True)
    
    history = get_history()
    if history.empty:
        st.info("📝 Aucun historique de classement trouvé")
    else:
        for idx, row in history.iterrows():
            with st.expander(f"📋 {row.get('job_title', 'Sans titre')} - {row.get('timestamp', 'Date inconnue')}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if 'timestamp' in row and row['timestamp']:
                        st.metric("Date", str(row['timestamp']).split()[0])
                    if 'job_title' in row and row['job_title']:
                        st.metric("Poste", row['job_title'])
                
                with col2:
                    description = row.get('description', 'Aucune description')
                    st.text_area("Description du poste", value=description, height=120, disabled=True)
                    
                    try:
                        if 'results' in row and row['results']:
                            results_data = pd.read_json(row['results'])
                            if not results_data.empty:
                                # Clean column names for display
                                display_df = results_data.copy()
                                if 'Raw Score' in display_df.columns:
                                    display_df = display_df.drop(columns=['Raw Score'])
                                if 'Score brut' in display_df.columns:
                                    display_df = display_df.drop(columns=['Score brut'])
                                
                                st.dataframe(
                                    display_df, 
                                    use_container_width=True,
                                    hide_index=True
                                )
                    except Exception as e:
                        st.warning(f"⚠️ Impossible de charger les résultats: {e}")

def show_dashboard():
    st.markdown('<div class="main-header">📋 Analyse de CV</div>', unsafe_allow_html=True)

    # --- Job Information Section ---
    st.markdown('<div class="section-header">📄 Informations du Poste</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        job_title = st.text_input(
            "Intitulé du poste",
            placeholder="Ex: Développeur Python Senior",
            help="Saisissez le titre du poste à pourvoir"
        )
    
    with col2:
        status = "Prêt à analyser" if st.session_state.get("uploaded_files") else "En attente"
        st.metric("📊 Statut", status)

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
                    
                    # Visualize top candidates
                    st.markdown('<div class="section-header">📊 Top Candidats</div>', unsafe_allow_html=True)
                    top_n = min(len(results_df), 8)
                    chart_data = results_df.head(top_n).copy()
                    
                    # Create a nice bar chart
                    chart_data["Score numérique"] = chart_data["Score brut"] * 100
                    st.bar_chart(
                        chart_data.set_index("Nom du CV")["Score numérique"],
                        color="#1e40af"
                    )
                    
                    # Save ranking history
                    success = save_ranking_history(
                        job_title,
                        job_description,
                        results_df
                    )
                    
                    if success:
                        st.success("✅ Historique sauvegardé avec succès")
                    
                    # Download options
                    st.markdown('<div class="section-header">💾 Exporter les Résultats</div>', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        csv = results_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Télécharger CSV", 
                            csv, 
                            "resultats_classement.csv", 
                            "text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            results_df.to_excel(writer, index=False, sheet_name="Classement_CVs")
                        buffer.seek(0)
                        st.download_button(
                            "📥 Télécharger Excel", 
                            buffer, 
                            "resultats_classement.xlsx", 
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.error("❌ Aucun score généré lors de l'analyse")
            else:
                st.error("❌ Aucun CV valide à analyser")

# --- App Sidebar ---
def render_sidebar():
    st.sidebar.markdown("""
        <div class="sidebar-content">
            <h2 style="text-align: center; color: #1e40af; margin-bottom: 2rem;">
                📄 HireSense
            </h2>
    """, unsafe_allow_html=True)
    
    # Navigation
    if st.sidebar.button("🏠 Tableau de bord", use_container_width=True):
        st.session_state["current_page"] = "dashboard"
        st.rerun()
        
    if st.sidebar.button("📊 Historique", use_container_width=True):
        st.session_state["current_page"] = "history"
        st.rerun()
    
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    # Information
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
        <div style="padding: 1rem; background: #f0f9ff; border-radius: 10px;">
            <h4>ℹ️ Comment utiliser</h4>
            <ol style="font-size: 0.9rem; padding-left: 1.2rem;">
                <li>Saisir l'intitulé du poste</li>
                <li>Rédiger la description du poste</li>
                <li>Importer les CVs (PDF)</li>
                <li>Lancer l'analyse</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)

# --- Main App Logic ---
def main():
    # Initialize database
    init_db()
    
    render_sidebar()
    
    # Show appropriate page content
    if st.session_state["current_page"] == "dashboard":
        show_dashboard()
    elif st.session_state["current_page"] == "history":
        show_history_page()

if __name__ == "__main__":
    main()