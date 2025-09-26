import streamlit as st
import os
import sqlite3
import pandas as pd
from datetime import datetime
import importlib.util

# --- NOUVEAU: Import gspread pour Google Sheets ---
# Assurez-vous d'avoir exécuté 'pip install gspread'
try:
    import gspread 
except ImportError:
    st.error("❌ La bibliothèque 'gspread' n'est pas installée. Veuillez l'installer avec 'pip install gspread'.")
    # Définit une fonction de remplacement pour éviter un crash si l'import échoue
    def save_to_google_sheet(quadrant, entry):
        st.warning("⚠️ L'enregistrement sur Google Sheets est désactivé (gspread manquant).")
        return False

# --- CONFIGURATION GOOGLE SHEETS (VOS VALEURS) ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit" 
WORKSHEET_NAME = "Cartographie" # Nom de l'onglet exact dans votre feuille

# Utiliser le répertoire actuel comme base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
os.chdir(PROJECT_ROOT)

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# -------------------- Dossier pour les CV --------------------
CV_DIR = os.path.join(PROJECT_ROOT, "cvs")
if not os.path.exists(CV_DIR):
    try:
        os.makedirs(CV_DIR, exist_ok=True)
    except Exception as e:
        st.error(f"❌ Erreur lors de la création du dossier {CV_DIR} à {os.path.abspath(CV_DIR)}: {e}")

# -------------------- Base de données SQLite --------------------
DB_FILE = os.path.join(PROJECT_ROOT, "cartographie.db")

def check_table_exists():
    """Vérifie si la table candidats existe dans la base."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidats'")
        exists = c.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        st.error(f"❌ Erreur lors de la vérification de la table candidats dans {DB_FILE}: {e}")
        return False

def init_db():
    """Initialise la base de données et crée la table candidats si nécessaire."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS candidats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quadrant TEXT,
                date TEXT,
                nom TEXT,
                poste TEXT,
                entreprise TEXT,
                linkedin TEXT,
                notes TEXT,
                cv_path TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation de {DB_FILE} à {os.path.abspath(DB_FILE)}: {e}")

# Initialiser la base de données
if not os.path.exists(DB_FILE) or not check_table_exists():
    init_db()

# Charger les données depuis SQLite
def load_data():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT quadrant, date, nom, poste, entreprise, linkedin, notes, cv_path FROM candidats")
        rows = c.fetchall()
        conn.close()
        data = {
            "🌟 Haut Potentiel": [],
            "💎 Rare & stratégique": [],
            "⚡ Rapide à mobiliser": [],
            "📚 Facilement disponible": []
        }
        for row in rows:
            quadrant, date, nom, poste, entreprise, linkedin, notes, cv_path = row
            data[quadrant].append({
                "date": date,
                "nom": nom,
                "poste": poste,
                "entreprise": entreprise,
                "linkedin": linkedin,
                "notes": notes,
                "cv_path": cv_path
            })
        return data
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données depuis {DB_FILE}: {e}")
        return {
            "🌟 Haut Potentiel": [],
            "💎 Rare & stratégique": [],
            "⚡ Rapide à mobiliser": [],
            "📚 Facilement disponible": []
        }

# Sauvegarder un candidat dans SQLite
def save_candidat(quadrant, entry):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO candidats (quadrant, date, nom, poste, entreprise, linkedin, notes, cv_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quadrant,
            entry["date"],
            entry["nom"],
            entry["poste"],
            entry["entreprise"],
            entry["linkedin"],
            entry["notes"],
            entry["cv_path"]
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde du candidat dans {DB_FILE}: {e}")

# Supprimer un candidat de SQLite
def delete_candidat(quadrant, index):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM candidats WHERE quadrant = ? ORDER BY date DESC LIMIT 1 OFFSET ?", (quadrant, index))
        result = c.fetchone()
        if result:
            candidate_id = result[0]
            c.execute("DELETE FROM candidats WHERE id = ?", (candidate_id,))
            conn.commit()
        else:
            st.warning("⚠️ Candidat non trouvé dans la base.")
        conn.close()
    except Exception as e:
        st.error(f"❌ Erreur lors de la suppression du candidat dans {DB_FILE}: {e}")

# -------------------- FONCTION GOOGLE SHEETS --------------------
def save_to_google_sheet(quadrant, entry):
    """Sauvegarde les données d'un candidat dans Google Sheets via gspread et st.secrets."""
    # S'assure que gspread est disponible et que la clé est dans secrets
    if 'gspread' not in globals() or "gcp_service_account" not in st.secrets:
         return False
         
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        # Le format de la ligne DOIT correspond à l'ordre de vos colonnes dans Google Sheets
        row_data = [
            quadrant,
            entry["date"],
            entry["nom"],
            entry["poste"],
            entry["entreprise"],
            entry["linkedin"],
            entry["notes"],
            os.path.basename(entry["cv_path"]) if entry["cv_path"] else "N/A"
        ]
        
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Échec de l'enregistrement dans Google Sheets. Vérifiez la configuration (URL, onglet, et partage). Erreur : {e}")
        return False
        
# Initialiser les données dans session_state
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data()

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🗺️ Cartographie des talents")

# -------------------- Onglets --------------------
tab1, tab2 = st.tabs(["Gestion des candidats", "Vue globale"])

# -------------------- Onglet 1 : Gestion des candidats --------------------
with tab1:
    
    # Choix quadrant
    quadrant_choisi = st.selectbox("Quadrant:", list(st.session_state.cartographie_data.keys()), key="carto_quadrant")
    
    # Ajout candidat
    st.subheader("➕ Ajouter un candidat")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nom = st.text_input("Nom du candidat", key="carto_nom")
    with col2:
        poste = st.text_input("Poste", key="carto_poste")
    with col3:
        entreprise = st.text_input("Entreprise", key="carto_entreprise")
    with col4:
        linkedin = st.text_input("Lien LinkedIn", key="carto_linkedin")
    notes = st.text_area("Notes / Observations", key="carto_notes", height=100)
    cv_file = st.file_uploader("Télécharger CV (PDF ou DOCX)", type=["pdf", "docx"], key="carto_cv")

    if st.button("💾 Ajouter à la cartographie", type="primary", use_container_width=True, key="btn_add_carto"):
        if nom and poste:
            cv_path = None
            if cv_file:
                try:
                    cv_filename = f"{nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cv_file.name}"
                    cv_path = os.path.join(CV_DIR, cv_filename)
                    with open(cv_path, "wb") as f:
                        f.write(cv_file.read())
                except Exception as e:
                    st.error(f"❌ Erreur lors de la sauvegarde du CV dans {cv_path}: {e}")
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "nom": nom,
                "poste": poste,
                "entreprise": entreprise,
                "linkedin": linkedin,
                "notes": notes,
                "cv_path": cv_path
            }
            
            # 1. Sauvegarde dans Streamlit/SQLite
            st.session_state.cartographie_data[quadrant_choisi].append(entry)
            save_candidat(quadrant_choisi, entry)
            st.success(f"✅ {nom} ajouté à {quadrant_choisi} (base locale).")
            
            # 2. Sauvegarde dans Google Sheets
            if save_to_google_sheet(quadrant_choisi, entry):
                st.success("✅ Données également exportées dans Google Sheets.")

            # Rerun pour recharger les données filtrées si un ajout a eu lieu
            st.rerun() 
        else:
            st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

    st.divider()
    
    # -------------------- Recherche --------------------
    st.subheader("🔍 Rechercher un candidat")
    search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")
    
    # Filtrage des candidats pour l'affichage
    filtered_cands = [
        cand for cand in st.session_state.cartographie_data[quadrant_choisi][::-1]
        if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
    ]
    
    # Affichage données
    st.subheader(f"📋 Candidats dans : {quadrant_choisi}")
    if not filtered_cands:
        st.info("Aucun candidat correspondant dans ce quadrant.")
    else:
        for i, cand in enumerate(filtered_cands):
            with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
                st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
                st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
                st.write(f"**Notes :** {cand.get('notes', '')}")
                if cand.get('cv_path') and os.path.exists(cand['cv_path']):
                    st.write(f"**CV :** {os.path.basename(cand['cv_path'])}")
                    with open(cand['cv_path'], "rb") as f:
                        st.download_button(
                            label="⬇️ Télécharger CV",
                            data=f,
                            file_name=os.path.basename(cand['cv_path']),
                            mime="application/pdf" if cand['cv_path'].endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_cv_{quadrant_choisi}_{i}"
                        )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Supprimer", key=f"delete_carto_{quadrant_choisi}_{i}"):
                        # Trouver l'index dans la liste originale non filtrée (ordre inverse)
                        original_index = len(st.session_state.cartographie_data[quadrant_choisi]) - 1 - st.session_state.cartographie_data[quadrant_choisi][::-1].index(cand)
                        
                        if cand.get('cv_path') and os.path.exists(cand['cv_path']):
                            try:
                                os.remove(cand['cv_path'])
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la suppression du CV dans {cand['cv_path']}: {e}")
                                
                        st.session_state.cartographie_data[quadrant_choisi].pop(original_index)
                        delete_candidat(quadrant_choisi, original_index)
                        st.success("✅ Candidat supprimé")
                        st.rerun()
                with col2:
                    export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {os.path.basename(cand['cv_path']) if cand.get('cv_path') else 'Aucun'}"
                    st.download_button(
                        "⬇️ Exporter",
                        data=export_text,
                        file_name=f"cartographie_{cand['nom']}.txt",
                        mime="text/plain",
                        key=f"download_carto_{quadrant_choisi}_{i}"
                    )

    # Export global
    st.subheader("📤 Exporter toute la cartographie")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬇️ Exporter en CSV"):
            all_data = []
            for quad, cands in st.session_state.cartographie_data.items():
                for cand in cands:
                    cand_copy = cand.copy()
                    cand_copy['quadrant'] = quad
                    all_data.append(cand_copy)
            df = pd.DataFrame(all_data)
            st.download_button(
                "Télécharger CSV",
                df.to_csv(index=False),
                file_name="cartographie_talents.csv",
                mime="text/csv",
                key="export_csv"
            )
    with col2:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button(
                    "⬇️ Exporter la base SQLite",
                    data=f,
                    file_name="cartographie.db",
                    mime="application/octet-stream",
                    key="export_db"
                )
        else:
            st.warning(f"⚠️ Base de données {DB_FILE} non trouvée.")
            
# -------------------- Onglet 2 : Vue globale --------------------
with tab2:
    st.subheader("📊 Vue globale de la cartographie")
    try:
        import plotly.express as px
        counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
        if sum(counts.values()) > 0:
            fig = px.pie(
                names=list(counts.keys()),
                values=list(counts.values()),
                title="Répartition des candidats par quadrant",
                color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
            )
            st.plotly_chart(fig)
        else:
            st.info("Aucun candidat dans la cartographie pour l'instant.")
    except ImportError:
        st.warning("⚠️ La bibliothèque Plotly n'est pas installée. Le dashboard n'est pas disponible. Installez Plotly avec 'pip install plotly'.")