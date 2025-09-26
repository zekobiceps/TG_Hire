import streamlit as st
import os
import pandas as pd
from datetime import datetime
import importlib.util

# --- NOUVELLES IMPORTATIONS POUR LA MÉTHODE DE SECOURS (oauth2client) ---
try:
    import gspread 
    # Cette librairie est nécessaire pour la méthode de secours compatible avec les anciens gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    st.error("❌ Les bibliothèques 'gspread' ou 'oauth2client' ne sont pas installées. Veuillez vérifier vos dépendances.")
    # Fonction de remplacement pour éviter un crash
    def save_to_google_sheet(quadrant, entry):
        st.warning("⚠️ L'enregistrement sur Google Sheets est désactivé.")
        return False

# --- CONFIGURATION GOOGLE SHEETS (VOS VALEURS) ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit" 
WORKSHEET_NAME = "Cartographie" 

# Chemin du projet pour la gestion des CV
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
# Attention : os.chdir(PROJECT_ROOT) peut causer des problèmes sur Streamlit Cloud si non nécessaire.
# Si vous avez besoin de changer de répertoire, assurez-vous que c'est bien la racine de votre projet.
# Pour le reste du code, on utilise des chemins absolus (CV_DIR).

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(utils)
    # -------------------- Init session --------------------
    utils.init_session_state()
except Exception as e:
    st.error(f"❌ Erreur lors du chargement de utils.py : {e}. Vérifiez que ce fichier existe.")
    # Fallback pour init_session_state si utils échoue (pour ne pas crasher)
    if "cartographie_data" not in st.session_state:
        st.session_state.cartographie_data = {}

# -------------------- Dossier pour les CV --------------------
CV_DIR = os.path.join(PROJECT_ROOT, "cvs")
if not os.path.exists(CV_DIR):
    try:
        os.makedirs(CV_DIR, exist_ok=True)
    except Exception as e:
        st.error(f"❌ Erreur lors de la création du dossier {CV_DIR}: {e}")

# -------------------- FONCTION D'AUTHENTIFICATION RÉUTILISABLE (Corrigée) --------------------
def get_gsheet_client():
    """Authentifie et retourne le client gspread en utilisant oauth2client et st.secrets."""
    if "gcp_service_account" not in st.secrets:
        st.error("❌ La clé 'gcp_service_account' n'est pas configurée dans secrets.toml.")
        return None
        
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    try:
        # Cette méthode est plus tolérante aux erreurs de formatage TOML/JSON
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"❌ Erreur critique d'authentification Google Sheets. Vérifiez le format de la clé privée (doit être sur une seule ligne dans les secrets Streamlit). Erreur : {e}")
        return None


# -------------------- FONCTIONS GOOGLE SHEETS --------------------

@st.cache_data(ttl=600)
def load_data_from_sheet():
    """Charge toutes les données de la feuille Google Sheets et les organise par quadrant."""
    # S'assure que gspread est importé
    if 'gspread' not in globals():
        return {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [], 
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }
    
    try:
        # Utilise la fonction d'authentification résiliente
        gc = get_gsheet_client()
        if not gc: return {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [], 
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }
        
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        rows = worksheet.get_all_records()
        
        data = {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [], 
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }
        
        for row in rows:
            quadrant = row.get('Quadrant') 
            
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
        
        return data
        
    except Exception as e:
        # La connexion a réussi, mais l'ouverture/lecture a échoué (ex: nom de feuille incorrect, droits)
        st.error(f"❌ Échec du chargement des données depuis Google Sheets (Vérifiez l'URL de la feuille ou les permissions). Erreur : {e}")
        return {
            "🌟 Haut Potentiel": [], "💎 Rare & stratégique": [], 
            "⚡ Rapide à mobiliser": [], "📚 Facilement disponible": []
        }


def save_to_google_sheet(quadrant, entry):
    """Sauvegarde les données d'un candidat dans Google Sheets."""
    if 'gspread' not in globals():
         return False
         
    try:
        gc = get_gsheet_client()
        if not gc:
            # Affiche pourquoi le client n'est pas obtenu (l'erreur est dans get_gsheet_client)
            st.warning("⚠️ Échec d'obtention du client Google Sheets (voir les erreurs d'authentification ci-dessus).")
            return False

        # --- LIGNE DE DÉBOGAGE TEMPORAIRE ---
        st.info(f"Connexion réussie au client gspread (Tentative d'écriture dans : {WORKSHEET_NAME})")
        # ------------------------------------

        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        # L'ordre doit correspondre à vos colonnes Sheets : Quadrant, Date, Nom, Poste, Entreprise, Linkedin, Notes, CV_Path
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
        st.error(f"❌ Échec de l'enregistrement dans Google Sheets. Erreur : {e}")
        return False
        
# Initialiser/Charger les données
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data_from_sheet()

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Cartographie",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🗺️ Cartographie des talents (Google Sheets)")

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
            
            # Sauvegarde dans Google Sheets (UNIQUE SOURCE)
            if save_to_google_sheet(quadrant_choisi, entry):
                st.success(f"✅ {nom} ajouté à {quadrant_choisi} (Google Sheets).")
                # Invalide le cache pour forcer le rechargement
                load_data_from_sheet.clear()

            # Rechargement des données
            st.rerun() 
            
        else:
            st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

    st.divider()
    
    # -------------------- Recherche et Affichage --------------------
    st.subheader("🔍 Rechercher un candidat")
    search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")
    
    # Filtrage des candidats (en ordre inverse, le plus récent en premier)
    filtered_cands = [
        cand for cand in st.session_state.cartographie_data.get(quadrant_choisi, [])[::-1]
        if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
    ]
    
    # Affichage données
    st.subheader(f"📋 Candidats dans : {quadrant_choisi} ({len(filtered_cands)})")
    if not filtered_cands:
        st.info("Aucun candidat correspondant dans ce quadrant.")
    else:
        for i, cand in enumerate(filtered_cands):
            with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=False):
                st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
                st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
                st.write(f"**Notes :** {cand.get('notes', '')}")
                
                # Gestion des CV locaux
                cv_local_path = cand.get('cv_path')
                # Utilise os.path.join pour reconstruire le chemin correctement
                full_cv_path = os.path.join(CV_DIR, cv_local_path) if cv_local_path and not os.path.isabs(cv_local_path) else cv_local_path

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
                    # Bouton pour la suppression du CV local
                    if st.button("🗑️ Supprimer CV local", key=f"delete_carto_{quadrant_choisi}_{i}"):
                        if full_cv_path and os.path.exists(full_cv_path):
                            try:
                                os.remove(full_cv_path)
                                st.success("✅ CV local supprimé. (L'entrée dans Google Sheets n'est pas affectée)")
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la suppression du CV local: {e}")
                        else:
                            st.warning("⚠️ Aucun CV local à supprimer pour ce candidat.")
                        st.rerun() 
                        
                with col2:
                    export_text = f"Nom: {cand['nom']}\nPoste: {cand['poste']}\nEntreprise: {cand['entreprise']}\nLinkedIn: {cand.get('linkedin', '')}\nNotes: {cand['notes']}\nCV: {os.path.basename(cand.get('cv_path', 'Aucun'))}"
                    st.download_button(
                        "⬇️ Exporter (Texte)",
                        data=export_text,
                        file_name=f"cartographie_{cand['nom']}.txt",
                        mime="text/plain",
                        key=f"download_carto_{quadrant_choisi}_{i}"
                    )

    # Export global
    st.subheader("📤 Exporter toute la cartographie")
    if st.button("⬇️ Exporter en CSV (Global)"):
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
            
# -------------------- Onglet 2 : Vue globale --------------------
with tab2:
    st.subheader("📊 Vue globale de la cartographie")
    try:
        import plotly.express as px
        counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
        if sum(counts.values()) > 0:
            import pandas as pd
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