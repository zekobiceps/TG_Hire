import streamlit as st
# --- NOUVEAUX IMPORTS POUR GOOGLE DRIVE ---
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    import io
except ImportError:
    st.error("❌ Bibliothèques Google API manquantes. Exécutez : pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    st.stop()

try:
    import gspread
except ImportError:
    st.error("❌ La bibliothèque 'gspread' n'est pas installée. Installez-la avec 'pip install gspread'.")
    st.stop()
    
import os
import pandas as pd
from datetime import datetime
import importlib.util

# --- CONFIGURATION GOOGLE ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit"
WORKSHEET_NAME = "Cartographie"
# --- ID DU DOSSIER GOOGLE DRIVE POUR LES CVS ---
# !!! VÉRIFIEZ BIEN QUE CET ID EST CELUI DU DOSSIER DANS LE DRIVE PARTAGÉ !!!
GOOGLE_DRIVE_FOLDER_ID = "1mWh1k2A72YI2H0DEabe5aIC6vSAP5aFQ" 

# --- GESTION DES CHEMINS (uniquement pour 'utils.py') ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "utils.py"))
try:
    spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    utils.init_session_state()
except Exception as e:
    st.error(f"❌ Erreur lors du chargement de utils.py : {e}. Vérifiez que ce fichier existe.")
    if "cartographie_data" not in st.session_state:
        st.session_state.cartographie_data = {}

# -------------------- FONCTIONS D'AUTHENTIFICATION --------------------
def get_google_credentials():
    """Crée les identifiants à partir des secrets Streamlit."""
    try:
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets.get("GCP_PRIVATE_KEY_ID", ""),
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'),
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets.get("GCP_CLIENT_ID", ""),
            "auth_uri": st.secrets.get("GCP_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets.get("GCP_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": st.secrets.get("GCP_CLIENT_CERT_URL", "")
        }
        return service_account.Credentials.from_service_account_info(service_account_info)
    except Exception as e:
        st.error(f"❌ Erreur de format des secrets Google: {e}")
        return None

def get_gsheet_client():
    """Authentification pour Google Sheets."""
    try:
        creds = get_google_credentials()
        if creds:
            scoped_creds = creds.with_scopes([
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ])
            gc = gspread.Client(auth=scoped_creds)
            gc.open_by_url(GOOGLE_SHEET_URL)
            return gc
    except Exception as e:
        st.error(f"❌ Erreur d'authentification Google Sheets: {str(e)}")
    return None

def get_drive_service():
    """Authentification pour Google Drive."""
    try:
        creds = get_google_credentials()
        if creds:
            scoped_creds = creds.with_scopes(["https://www.googleapis.com/auth/drive"])
            service = build('drive', 'v3', credentials=scoped_creds)
            return service
    except Exception as e:
        st.error(f"❌ Erreur d'authentification Google Drive: {str(e)}")
    return None

# -------------------- FONCTION D'UPLOAD SUR GOOGLE DRIVE (CORRIGÉE) --------------------
def upload_cv_to_drive(file_name, file_object):
    """Envoie un fichier CV sur Google Drive et retourne son lien partageable."""
    try:
        drive_service = get_drive_service()
        if not drive_service:
            st.error("❌ Connexion à Google Drive impossible.")
            return None

        file_metadata = {
            'name': file_name,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        file_content = io.BytesIO(file_object.getvalue())
        
        media = MediaIoBaseUpload(file_content, mimetype=file_object.type, resumable=True)
        
        # --- LE CORRECTIF EST ICI ---
        # Ajout de supportsAllDrives=True pour que l'API cherche dans les Drives Partagés
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True  # <-- CETTE LIGNE CORRIGE L'ERREUR 404
        ).execute()
        
        st.success(f"✅ CV '{file_name}' uploadé sur Google Drive.")
        return file.get('webViewLink')

    except Exception as e:
        st.error(f"❌ Échec de l'upload sur Google Drive : {e}")
        st.warning("⚠️ Vérifiez que l'ID du dossier est correct et que le compte de service est bien 'Gestionnaire de contenu' du Drive Partagé.")
        return None

# -------------------- FONCTIONS GOOGLE SHEETS --------------------
@st.cache_data(ttl=600)
def load_data_from_sheet():
    """Charge toutes les données de la feuille Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc:
            st.warning("⚠️ Impossible de se connecter à Google Sheets")
            return { "🔍 Profils Identifiés": [], "✅ Candidats Qualifiés": [], "🚀 Talents d'Avenir": [], "💎 Profils Stratégiques": [] }
        
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        rows = worksheet.get_all_records()
        
        data = { "🔍 Profils Identifiés": [], "✅ Candidats Qualifiés": [], "🚀 Talents d'Avenir": [], "💎 Profils Stratégiques": [] }
        
        quadrant_mapping = {
            "🌟 Haut Potentiel": "🚀 Talents d'Avenir",
            "💎 Rare & stratégique": "💎 Profils Stratégiques", 
            "⚡ Rapide à mobiliser": "✅ Candidats Qualifiés",
            "📚 Facilement disponible": "🔍 Profils Identifiés"
        }
        
        for row in rows:
            quadrant = quadrant_mapping.get(row.get('Quadrant', '').strip(), row.get('Quadrant', '').strip())
            if quadrant in data:
                data[quadrant].append({
                    "date": row.get("Date", "N/A"),
                    "nom": row.get("Nom", "N/A"),
                    "poste": row.get("Poste", "N/A"),
                    "entreprise": row.get("Entreprise", "N/A"),
                    "linkedin": row.get("Linkedin", "N/A"),
                    "notes": row.get("Notes", ""),
                    "cv_link": row.get("CV_Link", None)
                })
        
        total_candidats = sum(len(v) for v in data.values())
        st.sidebar.success(f"✅ Données chargées: {total_candidats} candidats")
        return data
        
    except Exception as e:
        st.error(f"❌ Échec du chargement des données depuis Google Sheets : {e}")
        return { "🔍 Profils Identifiés": [], "✅ Candidats Qualifiés": [], "🚀 Talents d'Avenir": [], "💎 Profils Stratégiques": [] }

def save_to_google_sheet(quadrant, entry):
    """Sauvegarde un candidat dans Google Sheets avec le lien du CV."""
    try:
        gc = get_gsheet_client()
        if not gc: return False
            
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        row_data = [
            quadrant, entry["date"], entry["nom"], entry["poste"],
            entry["entreprise"], entry["linkedin"], entry["notes"],
            entry["cv_link"] if entry["cv_link"] else "N/A"
        ]
        
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Échec de l'enregistrement dans Google Sheets : {e}")
        return False

# -------------------- INITIALISATION --------------------
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data_from_sheet()

# -------------------- INTERFACE UTILISATEUR --------------------
st.set_page_config(page_title="TG-Hire IA - Cartographie", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")
st.title("🗺️ Cartographie des talents")

if st.sidebar.button("🔍 Tester les connexions Google (Débug)"):
    st.sidebar.write("=== DÉBOGAGE CONNEXIONS GOOGLE ===")
    st.sidebar.write("1. Test d'authentification Sheets...")
    gc = get_gsheet_client()
    if gc: st.sidebar.success("✅ Authentification Google Sheets OK!")
    else: st.sidebar.error("❌ Échec authentification Google Sheets.")
    
    st.sidebar.write("2. Test d'authentification Drive...")
    drive_service = get_drive_service()
    if drive_service: st.sidebar.success("✅ Authentification Google Drive OK!")
    else: st.sidebar.error("❌ Échec authentification Google Drive.")

# -------------------- Onglets --------------------
tab1, tab2, tab3 = st.tabs(["Gestion des candidats", "Vue globale", "Guide des quadrants"])

with tab1:
    quadrant_choisi = st.selectbox("Quadrant:", list(st.session_state.cartographie_data.keys()), key="carto_quadrant")
    st.subheader("➕ Ajouter un candidat")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: nom = st.text_input("Nom du candidat", key="carto_nom")
    with col2: poste = st.text_input("Poste", key="carto_poste")
    with col3: entreprise = st.text_input("Entreprise", key="carto_entreprise")
    with col4: linkedin = st.text_input("Lien LinkedIn", key="carto_linkedin")
    
    notes = st.text_area("Notes / Observations", key="carto_notes", height=100)
    cv_file = st.file_uploader("Télécharger CV (PDF ou DOCX)", type=["pdf", "docx"], key="carto_cv")

    if st.button("💾 Ajouter à la cartographie", type="primary", use_container_width=True, key="btn_add_carto"):
        if nom and poste:
            cv_link = None
            if cv_file:
                cv_filename = f"{nom.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}_{cv_file.name}"
                cv_link = upload_cv_to_drive(cv_filename, cv_file)
            
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "nom": nom, "poste": poste,
                "entreprise": entreprise, "linkedin": linkedin, "notes": notes, "cv_link": cv_link
            }
            
            if save_to_google_sheet(quadrant_choisi, entry):
                st.success(f"✅ {nom} ajouté à {quadrant_choisi}.")
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
                
                cv_drive_link = cand.get('cv_link')
                if cv_drive_link and cv_drive_link.startswith('http'):
                    st.markdown(f"**CV :** [Ouvrir depuis Google Drive]({cv_drive_link})", unsafe_allow_html=True)
                
                export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {cand.get('cv_link', 'Aucun')}"
                st.download_button(
                    "⬇️ Exporter (Texte)", data=export_text,
                    file_name=f"cartographie_{cand['nom']}.txt", mime="text/plain",
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
        csv_data = df.to_csv(index=False).encode('utf-8')
        
        st.download_button("Télécharger CSV", data=csv_data, file_name="cartographie_talents.csv", mime="text/csv", key="export_csv")

with tab2:
    total_profils = sum(len(v) for v in st.session_state.cartographie_data.values())
    st.subheader(f"📊 Vue globale de la cartographie ({total_profils} profils)")
    
    try:
        import plotly.express as px
        counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
        
        if sum(counts.values()) > 0:
            df_counts = pd.DataFrame(list(counts.items()), columns=['Quadrant', 'Nombre'])
            fig = px.pie(df_counts, names='Quadrant', values='Nombre', title="Répartition des candidats par quadrant",
                         color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"])
            fig.update_traces(hovertemplate='<b>%{label}</b><br>Nombre: %{value}<br>Pourcentage: %{percent}<extra></extra>')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun candidat dans la cartographie pour l'instant.")
            
    except ImportError:
        st.warning("⚠️ La bibliothèque Plotly n'est pas installée. Le dashboard n'est pas disponible. Installez Plotly avec 'pip install plotly'.")

with tab3:
    st.subheader("📚 Guide des quadrants de la cartographie")
    st.markdown("""
    ### 1. 🔍 Profils Identifiés
    **Il s'agit de notre vivier de sourcing fondamental.** Cette catégorie rassemble les talents prometteurs repérés sur le marché qui correspondent à nos métiers. Ils n'ont pas encore été contactés mais représentent la base de nos futures recherches.

    ### 2. ✅ Candidats Qualifiés  
    **Ce sont les profils identifiés avec qui un premier contact positif a été établi.** Leur intérêt est validé et leurs compétences clés correspondent à nos besoins. Ils forment notre vivier de talents "chaud", prêts à être mobilisés pour un processus de recrutement.

    ### 3. 🚀 Talents d'Avenir
    **Cette catégorie regroupe les profils à fort potentiel d'évolution, de leadership ou d'innovation.** Plus que leurs compétences actuelles, nous ciblons ici leur capacité à devenir les leaders et les experts de demain. Ce sont nos investissements pour le futur.

    ### 4. 💎 Profils Stratégiques
    **Le sommet de notre cartographie.** Ce groupe exclusif contient les experts rares et les leaders confirmés dont les compétences sont critiques pour notre avantage concurrentiel. L'approche est directe, personnalisée et prioritaire.
    """)