import streamlit as st
try:
    import gspread
except ImportError:
    st.error("❌ La bibliothèque 'gspread' n'est pas installée. Installez-la avec 'pip install gspread'.")
    st.stop()
import os
import pandas as pd
from datetime import datetime
import importlib.util
import json
import tempfile

# --- CONFIGURATION GOOGLE SHEETS ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit"
WORKSHEET_NAME = "Cartographie"

# Chemin du projet pour la gestion des CV
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(utils)
    utils.init_session_state()
except Exception as e:
    st.error(f"❌ Erreur lors du chargement de utils.py : {e}. Vérifiez que ce fichier existe.")
    if "cartographie_data" not in st.session_state:
        st.session_state.cartographie_data = {}

# -------------------- Dossier pour les CV --------------------
CV_DIR = os.path.join(PROJECT_ROOT, "cvs")
if not os.path.exists(CV_DIR):
    try:
        os.makedirs(CV_DIR, exist_ok=True)
    except Exception as e:
        st.error(f"❌ Erreur lors de la création du dossier {CV_DIR}: {e}")

# -------------------- FONCTION D'AUTHENTIFICATION CORRIGÉE --------------------
def get_gsheet_client():
    """Authentification simplifiée et renforcée"""
    try:
        import gspread
        from google.oauth2 import service_account
        import json

        # 1. Récupérer et nettoyer la clé privée
        private_key = st.secrets["GCP_PRIVATE_KEY"].strip()

        # 2. Construire l'objet d'information du compte de service
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
            "private_key": private_key,
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "token_uri": st.secrets["GCP_TOKEN_URI"],
        }

        # 3. Créer les credentials en utilisant la méthode recommandée par Google
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        # 4. Créer le client gspread
        gc = gspread.authorize(credentials)

        st.sidebar.success("✅ Authentification Google Sheets réussie!")
        return gc

    except Exception as e:
        st.error(f"❌ Erreur d'authentification détaillée : {str(e)}")
        return None
# -------------------- FONCTIONS GOOGLE SHEETS --------------------
@st.cache_data(ttl=600)
def load_data_from_sheet():
    """Charge toutes les données de la feuille Google Sheets et les organise par quadrant."""
    try:
        gc = get_gsheet_client()
        if not gc:
            st.warning("⚠️ Impossible de se connecter à Google Sheets")
            return {
                "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [],
                "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
            }
        
        # Ouvrir la feuille Google Sheets
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        rows = worksheet.get_all_records()
        
        # Organiser les données par quadrant
        data = {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [],
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }
        
        for row in rows:
            quadrant = row.get('Quadrant', '').strip()
            if quadrant in data:
                data[quadrant].append({
                    "date": row.get("Date", "N/A"),
                    "nom": row.get("Nom", "N/A"),
                    "poste": row.get("Poste", "N/A"),
                    "entreprise": row.get("Entreprise", "N/A"),
                    "linkedin": row.get("Linkedin", "N/A"),
                    "notes": row.get("Notes", ""),
                    "cv_path": row.get("CV_Path", None)
                })
        
        st.sidebar.success(f"✅ Données chargées: {sum(len(v) for v in data.values())} candidats")
        return data
        
    except Exception as e:
        st.error(f"❌ Échec du chargement des données depuis Google Sheets : {e}")
        return {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [],
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }

def save_to_google_sheet(quadrant, entry):
    """Sauvegarde les données d'un candidat dans Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
            
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        # Préparer les données pour la nouvelle ligne
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
        
        # Ajouter la nouvelle ligne
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Échec de l'enregistrement dans Google Sheets : {e}")
        return False

# -------------------- INITIALISATION --------------------
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data_from_sheet()

# -------------------- INTERFACE UTILISATEUR --------------------
st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🗺️ Cartographie des talents (Google Sheets)")


# Bouton de test de connexion
# Dans votre sidebar, remplacez le bouton de test par :
def debug_secrets():
    st.write("=== VÉRIFICATION DES SECRETS ===")
    
    # Vérifier chaque secret
    secrets_to_check = ['GCP_TYPE', 'GCP_PROJECT_ID', 'GCP_PRIVATE_KEY', 'GCP_CLIENT_EMAIL']
    
    for secret in secrets_to_check:
        if secret in st.secrets:
            value = st.secrets[secret]
            if secret == 'GCP_PRIVATE_KEY':
                st.write(f"✅ {secret}: Présent ({len(value)} caractères)")
                st.write(f"   Début: {value[:30]}")
                st.write(f"   Fin: {value[-30:]}")
                if "BEGIN PRIVATE KEY" in value and "END PRIVATE KEY" in value:
                    st.success("   Format de clé correct")
                else:
                    st.error("   ❌ Format de clé INCORRECT")
            else:
                st.write(f"✅ {secret}: {value}")
        else:
            st.error(f"❌ {secret}: Manquant")

# Appelez cette fonction dans votre bouton de test

# -------------------- Onglets --------------------
tab1, tab2 = st.tabs(["Gestion des candidats", "Vue globale"])

# -------------------- Onglet 1 : Gestion des candidats --------------------
with tab1:
    quadrant_choisi = st.selectbox("Quadrant:", list(st.session_state.cartographie_data.keys()), key="carto_quadrant")
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
            
            if save_to_google_sheet(quadrant_choisi, entry):
                st.success(f"✅ {nom} ajouté à {quadrant_choisi} (Google Sheets).")
                # Recharger les données
                st.cache_data.clear()
                st.session_state.cartographie_data = load_data_from_sheet()
                st.rerun()
        else:
            st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

    st.divider()
    st.subheader("🔍 Rechercher un candidat")
    search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")
    
    filtered_cands = [
        cand for cand in st.session_state.cartographie_data.get(quadrant_choisi, [])[::-1]
        if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
    ]
    
    st.subheader(f"📋 Candidats dans : {quadrant_choisi} ({len(filtered_cands)})")
    
    if not filtered_cands:
        st.info("Aucun candidat correspondant dans ce quadrant.")
    else:
        for i, cand in enumerate(filtered_cands):
            with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
                st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
                st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
                st.write(f"**Notes :** {cand.get('notes', '')}")
                
                cv_local_path = cand.get('cv_path')
                full_cv_path = os.path.join(CV_DIR, os.path.basename(cv_local_path)) if cv_local_path else None
                
                if full_cv_path and os.path.exists(full_cv_path):
                    st.write(f"**CV :** {os.path.basename(full_cv_path)}")
                    try:
                        with open(full_cv_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Télécharger CV",
                                data=f,
                                file_name=os.path.basename(full_cv_path),
                                mime="application/pdf" if full_cv_path.lower().endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"download_cv_{quadrant_choisi}_{i}"
                            )
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la lecture du fichier CV : {e}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Supprimer CV local", key=f"delete_carto_{quadrant_choisi}_{i}"):
                        if full_cv_path and os.path.exists(full_cv_path):
                            try:
                                os.remove(full_cv_path)
                                st.success("✅ CV local supprimé. (L'entrée dans Google Sheets n'est pas affectée)")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la suppression du CV local: {e}")
                        else:
                            st.warning("⚠️ Aucun CV local à supprimer pour ce candidat.")
                
                with col2:
                    export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {os.path.basename(cand.get('cv_path', 'Aucun'))}"
                    st.download_button(
                        "⬇️ Exporter (Texte)",
                        data=export_text,
                        file_name=f"cartographie_{cand['nom']}.txt",
                        mime="text/plain",
                        key=f"download_carto_{quadrant_choisi}_{i}"
                    )

    st.subheader("📤 Exporter toute la cartographie")
    if st.button("⬇️ Exporter en CSV (Global)"):
        all_data = []
        for quad, cands in st.session_state.cartographie_data.items():
            for cand in cands:
                cand_copy = cand.copy()
                cand_copy['quadrant'] = quad
                all_data.append(cand_copy)
        
        df = pd.DataFrame(all_data)
        csv_data = df.to_csv(index=False)
        
        st.download_button(
            "Télécharger CSV",
            data=csv_data,
            file_name="cartographie_talents.csv",
            mime="text/csv",
            key="export_csv"
        )

# -------------------- Onglet 2 : Vue globale --------------------
with tab2:
    st.subheader("📊 Vue globale de la cartographie")
    try:
        import plotly.express as px
        counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
        
        if sum(counts.values()) > 0:
            df_counts = pd.DataFrame(list(counts.items()), columns=['Quadrant', 'Count'])
            fig = px.pie(
                df_counts,
                names='Quadrant',
                values='Count',
                title="Répartition des candidats par quadrant",
                color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
            )
            st.plotly_chart(fig)
        else:
            st.info("Aucun candidat dans la cartographie pour l'instant.")
            
    except ImportError:
        st.warning("⚠️ La bibliothèque Plotly n'est pas installée. Le dashboard n'est pas disponible. Installez Plotly avec 'pip install plotly'.")