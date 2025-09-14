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
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    # Create ranking history table
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

# --- Initialize Session State ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"

# --- Resume History Functions ---
def save_ranking_history(job_title, description, results):
    """Save resume ranking history."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    # Create new history entry
    c.execute(
        "INSERT INTO ranking_history (timestamp, job_title, description, results) VALUES (?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job_title,
            description,
            results.to_json()
        )
    )
    
    conn.commit()
    conn.close()

def get_history():
    """Get resume ranking history."""
    conn = sqlite3.connect('Resume.db')
    
    # Get all history records
    query = "SELECT id, timestamp, job_title, description, results FROM ranking_history ORDER BY timestamp DESC"
    history_df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    return history_df

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
        return text.strip() if text else "No readable text found."
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def rank_resumes(job_description, resumes):
    """Ranks resumes based on their similarity to the job description."""
    documents = [job_description] + resumes
    vectorizer = TfidfVectorizer().fit_transform(documents)
    vectors = vectorizer.toarray()
    job_description_vector = vectors[0]
    resume_vectors = vectors[1:]
    cosine_similarities = cosine_similarity([job_description_vector], resume_vectors).flatten()
    return cosine_similarities

# Add custom CSS for better styling
st.markdown("""
    <style>
        .stButton>button {
            background-color: #1e90ff;
            color: white;
            font-size: 16px;
            border-radius: 5px;
            padding: 10px;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #4682b4;
        }
        .sidebar .sidebar-content {
            padding: 20px;
        }
        .stTextInput>div>div>input {
            font-size: 16px;
            border-radius: 5px;
        }
        .stTextArea>div>div>textarea {
            font-size: 16px;
            border-radius: 5px;
        }
        .stTabs>div>div>button {
            font-size: 18px;
            font-weight: bold;
            color: #1e90ff;
        }
        .stTabs>div>div>button:hover {
            color: #4682b4;
        }
        .stExpander>div>div>button {
            font-size: 16px;
            font-weight: bold;
            color: #1e90ff;
        }
    </style>
""", unsafe_allow_html=True)

def show_history_page():
    st.title("📊 Ranking History")
    st.markdown("### View your previous resume ranking sessions")
    
    history = get_history()
    if history.empty:
        st.info("📝 No ranking history found")
    else:
        for idx, row in history.iterrows():
            with st.expander(f"Job: {row['job_title']} - {row['timestamp']}"):
                st.text_area("Job Description", value=row["description"], height=100, disabled=True, key=f"job_desc_{idx}")
                try:
                    results = pd.read_json(row["results"])
                    st.dataframe(results.drop(columns=["Raw Score"]) if "Raw Score" in results.columns else results, 
                               hide_index=True)
                except:
                    st.warning("⚠ Error loading results data")

def show_dashboard():
    # Title with gradient effect using HTML
    st.markdown("""
        <h2 style="
            background: -webkit-linear-gradient(45deg, #1FA2FF, #12D8FA);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            text-align: center;
            font-size: 2.5rem;">
            🚀 Welcome to HireSense AI
        </h2>
    """, unsafe_allow_html=True)

    st.markdown("### ")

    # --- Job Information Section ---
    with st.container():
        st.subheader("📄 Job Information")
        st.markdown("Fill in the job details to start screening candidates.")
        job_title = st.text_input("Job Title", placeholder="e.g., Trainee Engineer", label_visibility="visible")

    st.markdown("---")

    # --- Job Description & Resume Upload ---
    st.subheader("📋 Job Description & 📂 Resume Upload")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        job_description = st.text_area(
            "Job Description",
            placeholder="Paste or write the full job description here...",
            height=220,
            key="job_desc"
        )

    with col2:
        st.markdown("#### Upload Resumes")
        uploaded_files = st.file_uploader(
            "Select PDF resumes",
            type=["pdf"],
            accept_multiple_files=True,
            key="resume_files"
        )

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} resume(s) uploaded successfully")

    st.markdown("---")

    # Optional: Next step / action button
    st.markdown("### Ready to rank candidates?")

    # --- Processing & Ranking ---
    if st.button("🔍 Rank Resumes", disabled=not (uploaded_files and job_description)):
        with st.spinner("🔍 Processing resumes..."):
            resumes = []
            file_names = []
            error_files = []
            
            # Process each resume
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                if "Error extracting text" in text:
                    error_files.append(file.name)
                else:
                    resumes.append(text)
                    file_names.append(file.name)
            
            if error_files:
                st.warning(f"⚠ Could not process {len(error_files)} files: {', '.join(error_files)}")
            
            if resumes:
                scores = rank_resumes(job_description, resumes)
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                
                # Create results dataframe
                results_df = pd.DataFrame({
                    "Rank": range(1, len(ranked_resumes) + 1),
                    "Resume Name": [name for name, _ in ranked_resumes],
                    "Match Score": [f"{round(score * 100, 1)}%" for _, score in ranked_resumes],
                    "Raw Score": [round(score, 4) for _, score in ranked_resumes]
                })
                
                # Display results
                st.subheader("🏆 Ranked Resumes")
                st.dataframe(results_df.drop(columns=["Raw Score"]), hide_index=True)
                
                # Visualize top candidates
                st.subheader("📊 Top Candidates Visualization")
                top_n = min(len(results_df), 10)  # Show top 10 or all if less than 10
                chart_data = results_df.head(top_n).copy()
                st.bar_chart(chart_data.set_index("Resume Name")["Raw Score"])
                
                # Save ranking history
                save_ranking_history(
                    job_title if job_title else "Unnamed Job",
                    job_description,
                    results_df
                )
                
                # Download options
                col1, col2 = st.columns(2)
                with col1:
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV", csv, "ranked_resumes.csv", "text/csv")
                with col2:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        results_df.to_excel(writer, index=False)
                    buffer.seek(0)
                    st.download_button("📥 Download Excel", buffer, "ranked_resumes.xlsx", 
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.error("❌ No valid resumes to process")

# --- App Sidebar ---
def render_sidebar():
    st.sidebar.markdown("""
<h2 style="
    text-align: center;
    font-weight: bold;
    font-size: 48px;
    background: linear-gradient(90deg, #4CAF50, #2196F3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
">
    HireSense AI
</h2>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 Navigation")
    
    if st.sidebar.button("🏠 Dashboard", use_container_width=True):
        st.session_state["current_page"] = "dashboard"
        st.rerun()
        
    if st.sidebar.button("📊 History", use_container_width=True):
        st.session_state["current_page"] = "history"
        st.rerun()

# --- Global Footer (outside sidebar) ---
def render_footer():
    st.markdown("""
        <style>
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #f1f1f1;
            color: #555;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            border-top: 1px solid #ccc;
        }
        </style>
        <div class="footer">
            © 2025 AI HireSense AI
        </div>
    """, unsafe_allow_html=True)

# --- Main App Logic ---
def main():
    # Initialize database
    init_db()
    
    render_sidebar()
    
    # Landing page
    st.markdown("""
<h1 style='
    text-align: left;
    font-weight: bold;
    font-size: 48px;
    background: linear-gradient(90deg, #4CAF50, #2196F3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
'>
📄 Welcome to HireSense AI
</h1>
    """, unsafe_allow_html=True)
    
    st.subheader("Your AI-powered hiring assistant")

    st.markdown("""
    ### 🚀 Why Use HireSense AI?
    - 🔍 **Intelligent Resume Matching**: Find candidates who truly match your job criteria.
    - ⚡ **Boost Efficiency**: Save hours of manual screening.
    - 📈 **Data-Driven Ranking**: Make fair, unbiased decisions.
    - 🧾 **Track & Compare**: Store ranking history for better long-term hiring strategy.
    """)

    # Advanced section
    st.markdown("### 🛠️ Advanced Features")
    st.markdown("""
    - 🧠 **AI-Powered Resume Parsing**
    - 📊 **Similarity Score Visualizations**
    - 💾 **Exportable Reports**
    - 🗂️ **Job Description Templates**
    """)

    st.markdown("---")

    # Show appropriate page content
    if st.session_state["current_page"] == "dashboard":
        show_dashboard()
    elif st.session_state["current_page"] == "history":
        show_history_page()

if __name__ == "__main__":
    main()