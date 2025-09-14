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

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="HireSense AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Configuration de la base de données ---
def init_db():
    """Initialise la base de données SQLite avec les tables nécessaires."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    # Créer la table des utilisateurs
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        name TEXT,
        job_title TEXT,
        company TEXT,
        date_joined TEXT,
        last_login TEXT
    )
    ''')
    
    # Créer la table de l'historique de classement
    c.execute('''
    CREATE TABLE IF NOT EXISTS ranking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        job_title TEXT,
        description TEXT,
        results TEXT,
        FOREIGN KEY (email) REFERENCES users (email)
    )
    ''')
    
    conn.commit()
    conn.close()

# --- Initialisation de l'état de la session ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None
    st.session_state["user_name"] = None
    st.session_state["profile_tab"] = "profile"
    st.session_state["current_page"] = "login"  # Page par défaut : login, register, dashboard, profile

# --- Fonctions de sécurité ---
def hash_password(password, salt=None):
    """Hashe un mot de passe pour le stockage."""
    if salt is None:
        salt = uuid.uuid4().hex
    hashed = hashlib.sha256(salt.encode() + password.encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(stored_password, provided_password):
    """Vérifie un mot de passe stocké par rapport à celui fourni par l'utilisateur."""
    try:
        salt, hashed = stored_password.split('$')
        return hashed == hashlib.sha256(salt.encode() + provided_password.encode()).hexdigest()
    except (ValueError, IndexError):
        return False

# --- Fonctions de gestion des utilisateurs ---
def save_user(email, password, name=""):
    """Enregistre un nouvel utilisateur dans la base de données."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute("SELECT email FROM users WHERE email = ?", (email,))
    if c.fetchone():
        conn.close()
        return False  # L'utilisateur existe déjà
    
    hashed_password = hash_password(password)
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
        (email, hashed_password, name, "", "", current_date, current_date)
    )
    
    conn.commit()
    conn.close()
    return True

def authenticate_user(email, password):
    """Authentifie un utilisateur avec son email et son mot de passe."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute("SELECT password FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return False
    
    stored_password = result[0]
    
    if verify_password(stored_password, password):
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET last_login = ? WHERE email = ?", (current_date, email))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def update_profile(email, name, job_title, company):
    """Met à jour les informations du profil utilisateur."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute(
        "UPDATE users SET name = ?, job_title = ?, company = ? WHERE email = ?",
        (name, job_title, company, email)
    )
    
    conn.commit()
    conn.close()
    return True

def get_user_profile(email):
    """Récupère les données du profil utilisateur."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute(
        "SELECT email, name, job_title, company, date_joined, last_login FROM users WHERE email = ?",
        (email,)
    )
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        return None
    
    return {
        "email": result[0],
        "name": result[1],
        "job_title": result[2],
        "company": result[3],
        "date_joined": result[4],
        "last_login": result[5]
    }

def change_password(email, current_password, new_password):
    """Change le mot de passe d'un utilisateur."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute("SELECT password FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return False, "Utilisateur non trouvé"
    
    stored_password = result[0]
    
    if not verify_password(stored_password, current_password):
        conn.close()
        return False, "Le mot de passe actuel est incorrect"
    
    hashed_password = hash_password(new_password)
    
    c.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
    conn.commit()
    conn.close()
    
    return True, "Mot de passe changé avec succès"

# --- Fonctions de l'historique ---
def save_ranking_history(email, job_title, description, results):
    """Sauvegarde l'historique de classement des CV pour l'utilisateur."""
    conn = sqlite3.connect('Resume.db')
    c = conn.cursor()
    
    c.execute(
        "INSERT INTO ranking_history (email, timestamp, job_title, description, results) VALUES (?, ?, ?, ?, ?)",
        (
            email,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            job_title,
            description,
            results.to_json()
        )
    )
    
    conn.commit()
    conn.close()

def get_user_history(email):
    """Récupère l'historique de classement des CV pour l'utilisateur."""
    conn = sqlite3.connect('Resume.db')
    
    query = "SELECT id, timestamp, job_title, description, results FROM ranking_history WHERE email = ? ORDER BY timestamp DESC"
    history_df = pd.read_sql_query(query, conn, params=(email,))
    
    conn.close()
    
    return history_df

# --- Fonctions de traitement des CV ---
def extract_text_from_pdf(file):
    """Extrait le texte d'un fichier PDF téléchargé."""
    try:
        pdf = PdfReader(file)
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip() if text else "Aucun texte lisible trouvé."
    except Exception as e:
        return f"Erreur lors de l'extraction du texte : {str(e)}"

def rank_resumes(job_description, resumes):
    """Classe les CV en fonction de leur similarité avec la description de poste."""
    documents = [job_description] + resumes
    vectorizer = TfidfVectorizer().fit_transform(documents)
    vectors = vectorizer.toarray()
    job_description_vector = vectors[0]
    resume_vectors = vectors[1:]
    cosine_similarities = cosine_similarity([job_description_vector], resume_vectors).flatten()
    return cosine_similarities

# --- Style CSS personnalisé ---
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

# --- Navigation principale ---
def show_login_page():
    st.sidebar.title("📝 Connexion Utilisateur")
    st.sidebar.markdown("### Veuillez entrer vos identifiants pour vous connecter.")
    
    login_email = st.sidebar.text_input("📧 Email", key="login_email", placeholder="Entrez votre email")
    login_password = st.sidebar.text_input("🔑 Mot de passe", type="password", key="login_password", placeholder="Entrez votre mot de passe")
    
    st.sidebar.markdown("---")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔐 Se connecter", use_container_width=True):
            if authenticate_user(login_email, login_password):
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = login_email
                profile = get_user_profile(login_email)
                st.session_state["user_name"] = profile["name"]
                st.session_state["current_page"] = "dashboard"
                st.rerun()
            else:
                st.sidebar.error("❌ Email ou mot de passe invalide")
    
    with col2:
        if st.button("📝 S'inscrire", use_container_width=True):
            st.session_state["current_page"] = "register"
            st.rerun()

def show_register_page():
    st.sidebar.title("📝 Inscription Utilisateur")
    st.sidebar.markdown("### Créez un nouveau compte pour commencer.")
    
    reg_email = st.sidebar.text_input("📧 Email*", key="reg_email", placeholder="Entrez votre email")
    reg_name = st.sidebar.text_input("👤 Nom complet", key="reg_name", placeholder="Entrez votre nom complet")
    reg_password = st.sidebar.text_input("🔑 Mot de passe*", type="password", key="reg_password", placeholder="Entrez votre mot de passe")
    reg_confirm_password = st.sidebar.text_input("🔑 Confirmer le mot de passe*", type="password", key="reg_confirm_password", placeholder="Confirmez votre mot de passe")
    
    st.sidebar.markdown("---")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("✅ S'inscrire", use_container_width=True):
            if not reg_email or not reg_password:
                st.sidebar.error("❌ L'email et le mot de passe sont requis")
            elif "@" not in reg_email or "." not in reg_email:
                st.sidebar.error("❌ Format d'email invalide")
            elif reg_password != reg_confirm_password:
                st.sidebar.error("❌ Les mots de passe ne correspondent pas")
            else:
                if save_user(reg_email, reg_password, reg_name):
                    st.sidebar.success("✅ Inscription réussie ! Vous pouvez maintenant vous connecter.")
                    st.session_state["current_page"] = "login"
                    st.rerun()
                else:
                    st.sidebar.warning("⚠ Email déjà enregistré. Veuillez vous connecter.")
                    st.session_state["current_page"] = "login"
                    st.rerun()
    
    with col2:
        if st.button("↩️ Retour à la connexion", use_container_width=True):
            st.session_state["current_page"] = "login"
            st.rerun()

def show_profile_page():
    st.title("👤 Profil Utilisateur")
    st.markdown("### Gérez vos informations de profil et vos préférences.")
    
    profile = get_user_profile(st.session_state["user_email"])
    if not profile:
        st.error("❌ Erreur lors du chargement des données du profil")
        return
    
    profile_tab, password_tab, history_tab = st.tabs(["✏️ Modifier le profil", "🔐 Changer le mot de passe", "📊 Historique"])
    
    with profile_tab:
        st.subheader("Informations personnelles")
        
        name = st.text_input("Nom complet", value=profile["name"] if profile["name"] else "")
        job_title = st.text_input("Titre du poste", value=profile["job_title"] if profile["job_title"] else "")
        company = st.text_input("Entreprise", value=profile["company"] if profile["company"] else "")
        
        if st.button("💾 Sauvegarder le profil"):
            if update_profile(profile["email"], name, job_title, company):
                st.session_state["user_name"] = name
                st.success("✅ Profil mis à jour avec succès !")
                st.rerun()
            else:
                st.error("❌ Erreur lors de la mise à jour du profil")
    
    with password_tab:
        st.subheader("Changer le mot de passe")
        
        current_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_new_password = st.text_input("Confirmer le nouveau mot de passe", type="password")
        
        if st.button("🔄 Mettre à jour le mot de passe"):
            if not current_password or not new_password or not confirm_new_password:
                st.error("❌ Tous les champs sont requis")
            elif new_password != confirm_new_password:
                st.error("❌ Les nouveaux mots de passe ne correspondent pas")
            else:
                success, message = change_password(profile["email"], current_password, new_password)
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
    
    with history_tab:
        st.subheader("Historique de classement des CV")
        
        history = get_user_history(profile["email"])
        if history.empty:
            st.info("📝 Aucun historique de classement trouvé")
        else:
            for idx, row in history.iterrows():
                with st.expander(f"Offre : {row['job_title']} - {row['timestamp']}"):
                    st.text_area("Description de l'offre", value=row["description"], height=100, disabled=True, key=f"job_desc_{idx}")
                    try:
                        results = pd.read_json(row["results"])
                        st.dataframe(results, hide_index=True)
                    except:
                        st.warning("⚠ Erreur lors du chargement des résultats.")

def show_dashboard():
    welcome_name = st.session_state["user_name"] or st.session_state["user_email"]

    st.markdown("""
        <h2 style="
            background: -webkit-linear-gradient(45deg, #1FA2FF, #12D8FA);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            text-align: center;
            font-size: 2.5rem;">
            🚀 Bienvenue sur HireSense AI
        </h2>
    """, unsafe_allow_html=True)

    st.markdown(f"<div style='text-align:center; font-size:18px;'>Heureux de vous revoir, <b style='color:#4CAF50'>{welcome_name}</b> 👋</div>", unsafe_allow_html=True)
    st.markdown("### ")

    with st.container():
        st.subheader("📄 Informations sur l'offre d'emploi")
        st.markdown("Remplissez les détails du poste pour commencer à trier les candidats.")
        job_title = st.text_input("Titre du poste", placeholder="Exemple : Ingénieur Stagiaire", label_visibility="visible")

    st.markdown("---")

    st.subheader("📋 Description de l'offre et 📂 Téléchargement des CV")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        job_description = st.text_area(
            "Description de l'offre",
            placeholder="Collez ou écrivez la description complète de l'offre ici...",
            height=220,
            key="job_desc"
        )

    with col2:
        st.markdown("#### Télécharger les CV")
        uploaded_files = st.file_uploader(
            "Sélectionnez les CV au format PDF",
            type=["pdf"],
            accept_multiple_files=True,
            key="resume_files"
        )

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} CV(s) téléchargé(s) avec succès")

    st.markdown("---")

    st.markdown("### Prêt à classer les candidats ?")

    if st.button("🔍 Classer les CV", disabled=not (uploaded_files and job_description)):
        with st.spinner("🔍 Traitement des CV en cours..."):
            resumes = []
            file_names = []
            error_files = []
            
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                if "Erreur lors de l'extraction" in text:
                    error_files.append(file.name)
                else:
                    resumes.append(text)
                    file_names.append(file.name)
            
            if error_files:
                st.warning(f"⚠ Impossible de traiter {len(error_files)} fichier(s) : {', '.join(error_files)}")
            
            if resumes:
                scores = rank_resumes(job_description, resumes)
                ranked_resumes = sorted(zip(file_names, scores), key=lambda x: x[1], reverse=True)
                
                results_df = pd.DataFrame({
                    "Rang": range(1, len(ranked_resumes) + 1),
                    "Nom du CV": [name for name, _ in ranked_resumes],
                    "Score de correspondance": [f"{round(score * 100, 1)}%" for _, score in ranked_resumes],
                    "Score brut": [round(score, 4) for _, score in ranked_resumes]
                })
                
                st.subheader("🏆 CV Classés")
                st.dataframe(results_df.drop(columns=["Score brut"]), hide_index=True)
                
                st.subheader("📊 Visualisation des meilleurs candidats")
                top_n = min(len(results_df), 10)
                chart_data = results_df.head(top_n).copy()
                st.bar_chart(chart_data.set_index("Nom du CV")["Score brut"])
                
                save_ranking_history(
                    st.session_state["user_email"],
                    job_title if job_title else "Offre sans titre",
                    job_description,
                    results_df
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Télécharger en CSV", csv, "cv_classes.csv", "text/csv")
                with col2:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        results_df.to_excel(writer, index=False)
                    buffer.seek(0)
                    st.download_button("📥 Télécharger en Excel", buffer, "cv_classes.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.error("❌ Aucun CV valide à traiter")

# --- Barre latérale de l'application ---
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
    
    if st.session_state["authenticated"]:
        st.sidebar.subheader(f"👤 {st.session_state['user_email']}")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📱 Navigation")
        
        if st.sidebar.button("🏠 Tableau de bord", use_container_width=True):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
            
        if st.sidebar.button("👤 Mon profil", use_container_width=True):
            st.session_state["current_page"] = "profile"
            st.rerun()
            
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = None
            st.session_state["user_name"] = None
            st.session_state["current_page"] = "login"
            st.sidebar.success("👋 Déconnexion réussie !")
            st.rerun()

# --- Pied de page global (hors de la barre latérale) ---
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

# --- Logique principale de l'application ---
def main():
    init_db()
    
    render_sidebar()
    
    if not st.session_state.get("authenticated", False):
        st.markdown("""
<h1 style='
    text-align: left;
    font-weight: bold;
    font-size: 48px;
    background: linear-gradient(90deg, #4CAF50, #2196F3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
'>
📄 Bienvenue sur HireSense AI
</h1>
""", unsafe_allow_html=True)
        st.subheader("Votre assistant de recrutement alimenté par l'IA")

        st.markdown("""
        ### 🚀 Pourquoi utiliser HireSense AI ?
        - 🔍 **Correspondance intelligente des CV** : Trouvez les candidats qui correspondent vraiment à vos critères.
        - ⚡ **Gagnez en efficacité** : Économisez des heures de tri manuel.
        - 📈 **Classement basé sur les données** : Prenez des décisions équitables et impartiales.
        - 🧾 **Suivi et comparaison** : Conservez l'historique de vos analyses pour une meilleure stratégie d'embauche.
        """)

        st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.session_state["current_page"] == "login":
                show_login_page()
        with col2:
            if st.session_state["current_page"] == "register":
                show_register_page()
    
    else:
        if st.session_state["current_page"] == "dashboard":
            show_dashboard()
        elif st.session_state["current_page"] == "profile":
            show_profile_page()

if __name__ == "__main__":
    main()