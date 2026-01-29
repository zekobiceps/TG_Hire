import streamlit as st
import streamlit.components.v1 as components
import os
import io
import pandas as pd
from datetime import datetime
import importlib.util

# --- IMPORTS POUR GOOGLE API ---
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
except ImportError:
    st.error("❌ Bibliothèques Google API manquantes. Exécutez : pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    st.stop()

try:
    import gspread
except ImportError:
    st.error("❌ La bibliothèque 'gspread' n'est pas installée. Installez-la avec 'pip install gspread'.")
    st.stop()
    
# --- CONFIGURATION GOOGLE ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QLC_LzwQU5eKLRcaDglLd6csejLZSs1aauYFwzFk0ac/edit"
WORKSHEET_NAME = "Cartographie"
# --- ID DU DOSSIER GOOGLE DRIVE POUR LES CVS ---
GOOGLE_DRIVE_FOLDER_ID = "1mWh1k2A72YI2H0DEabe5aIC6vSAP5aFQ" 

# --- GESTION DES CHEMINS (uniquement pour 'utils.py') ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "utils.py"))
try:
    spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("Impossible de créer un spec valide pour utils.py")
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

# -------------------- FONCTION D'UPLOAD SUR GOOGLE DRIVE --------------------
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
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
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
            q_raw = str(row.get('Quadrant', '')).strip()
            quadrant = quadrant_mapping.get(q_raw, q_raw)
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

def delete_from_google_sheet(quadrant: str, cand: dict) -> bool:
    """Supprime un candidat du Google Sheet en se basant sur Quadrant, Date, Nom, Poste, Entreprise.
    Retourne True si la suppression a réussi."""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)

        # Récupérer toutes les valeurs (inclut l'entête en 1ère ligne)
        all_values = worksheet.get_all_values()
        if not all_values:
            return False
        headers = all_values[0]

        # Créer un index des colonnes
        def idx(col_name: str) -> int:
            return headers.index(col_name) if col_name in headers else -1

        idx_quadrant = idx('Quadrant')
        idx_date = idx('Date')
        idx_nom = idx('Nom')
        idx_poste = idx('Poste')
        idx_entreprise = idx('Entreprise')

        # Normaliser les champs recherchés
        target = {
            'Quadrant': str(quadrant).strip(),
            'Date': str(cand.get('date', '')).strip(),
            'Nom': str(cand.get('nom', '')).strip(),
            'Poste': str(cand.get('poste', '')).strip(),
            'Entreprise': str(cand.get('entreprise', '')).strip(),
        }

        # Chercher la première ligne correspondante (à partir de la 2e ligne)
        for row_idx in range(1, len(all_values)):
            row = all_values[row_idx]
            def safe_get(i):
                return str(row[i]).strip() if 0 <= i < len(row) and i >= 0 else ''

            if (
                safe_get(idx_quadrant) == target['Quadrant'] and
                safe_get(idx_date) == target['Date'] and
                safe_get(idx_nom) == target['Nom'] and
                safe_get(idx_poste) == target['Poste'] and
                safe_get(idx_entreprise) == target['Entreprise']
            ):
                # gspread est 1-based pour delete_rows (inclut l'entête)
                worksheet.delete_rows(row_idx + 1)
                return True
        return False
    except Exception as e:
        st.error(f"❌ Échec de la suppression dans Google Sheets : {e}")
        return False

def update_in_google_sheet(quadrant: str, original_cand: dict, updated_fields: dict) -> bool:
    """Met à jour les informations d'un candidat dans Google Sheets.
    On identifie la ligne par Quadrant, Date, Nom, Poste, Entreprise, puis on met à jour les colonnes fournies.
    updated_fields attend des clés parmi: 'Nom', 'Poste', 'Entreprise', 'Linkedin', 'Notes', 'CV_Link'.
    Retourne True si au moins une colonne a été mise à jour.
    """
    try:
        gc = get_gsheet_client()
        if not gc:
            return False
        sh = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(WORKSHEET_NAME)

        all_values = worksheet.get_all_values()
        if not all_values:
            return False
        headers = all_values[0]

        def idx(col_name: str) -> int:
            return headers.index(col_name) if col_name in headers else -1

        # indices des colonnes clés d'identification
        idx_quadrant = idx('Quadrant')
        idx_date = idx('Date')
        idx_nom = idx('Nom')
        idx_poste = idx('Poste')
        idx_entreprise = idx('Entreprise')

        target = {
            'Quadrant': str(quadrant).strip(),
            'Date': str(original_cand.get('date', '')).strip(),
            'Nom': str(original_cand.get('nom', '')).strip(),
            'Poste': str(original_cand.get('poste', '')).strip(),
            'Entreprise': str(original_cand.get('entreprise', '')).strip(),
        }

        row_found = -1
        for row_idx in range(1, len(all_values)):
            row = all_values[row_idx]
            def safe_get(i):
                return str(row[i]).strip() if 0 <= i < len(row) and i >= 0 else ''
            if (
                safe_get(idx_quadrant) == target['Quadrant'] and
                safe_get(idx_date) == target['Date'] and
                safe_get(idx_nom) == target['Nom'] and
                safe_get(idx_poste) == target['Poste'] and
                safe_get(idx_entreprise) == target['Entreprise']
            ):
                row_found = row_idx + 1  # gspread est 1-based
                break

        if row_found == -1:
            return False

        # indices des colonnes éditables
        editable_cols = {
            'Nom': idx('Nom'),
            'Poste': idx('Poste'),
            'Entreprise': idx('Entreprise'),
            'Linkedin': idx('Linkedin'),
            'Notes': idx('Notes'),
            'CV_Link': idx('CV_Link'),
        }

        updated_any = False
        for key, col_index in editable_cols.items():
            if key in updated_fields and col_index >= 0:
                value = str(updated_fields.get(key, '')).strip()
                worksheet.update_cell(row_found, col_index + 1, value)
                updated_any = True

        return updated_any
    except Exception as e:
        st.error(f"❌ Échec de la mise à jour dans Google Sheets : {e}")
        return False

# -------------------- INITIALISATION --------------------
if "cartographie_data" not in st.session_state:
    st.session_state.cartographie_data = load_data_from_sheet()

# -------------------- INTERFACE UTILISATEUR --------------------
st.set_page_config(page_title="TG-Hire IA - Cartographie", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()

st.title("🗺️ Cartographie des talents")

# Affichage du commit
try:
    utils.display_commit_info()
except Exception:
    pass

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
tab1, tab2 = st.tabs(["Gestion des candidats", "Guide des quadrants"])

with tab1:
    # Si on a demandé un scroll vers un élément spécifique (après clic Modifier)
    if st.session_state.get('scroll_to'):
        anchor_target = st.session_state.get('scroll_to')
        components.html(
            f"""
            <script>
            const el = parent.document.getElementById('{anchor_target}');
            if (el) {{ el.scrollIntoView({{behavior: 'auto', block: 'start'}}); }}
            </script>
            """,
            height=0,
        )
        del st.session_state['scroll_to']
    st.subheader("➕ Ajouter un candidat")
    
    left_col, right_col = st.columns([2,1])
    with left_col:
        col1, col2, col3, col4 = st.columns(4)
        with col1: nom = st.text_input("Nom du candidat", key="carto_nom")
        with col2: poste = st.text_input("Poste", key="carto_poste")
        with col3: entreprise = st.text_input("Entreprise", key="carto_entreprise")
        with col4: linkedin = st.text_input("Lien LinkedIn", key="carto_linkedin")
        # Deuxième rangée: Notes | Upload CV | Quadrant d'ajout
        c_notes, c_cv, c_quad = st.columns([2,1,1])
        with c_notes:
            notes = st.text_area("Notes / Observations", key="carto_notes", height=100)
        with c_cv:
            cv_file = st.file_uploader("Télécharger CV", type=["pdf", "docx"], key="carto_cv")
        with c_quad:
            quadrant_ajout = st.selectbox("Quadrant", list(st.session_state.cartographie_data.keys()), key="carto_quadrant_add")

        if st.button("💾 Ajouter à la cartographie", type="primary", width="stretch", key="btn_add_carto"):
            if nom and poste:
                cv_link = None
                if cv_file:
                    # --- LA MODIFICATION EST ICI ---
                    # Récupérer l'extension du fichier original (ex: .pdf)
                    _, file_extension = os.path.splitext(cv_file.name)
                    # Créer le nom du fichier en utilisant uniquement le nom du candidat
                    cv_filename = f"{nom}{file_extension}"
                    
                    cv_link = upload_cv_to_drive(cv_filename, cv_file)
                
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "nom": nom, "poste": poste,
                    "entreprise": entreprise, "linkedin": linkedin, "notes": notes, "cv_link": cv_link
                }
                
                if save_to_google_sheet(quadrant_ajout, entry):
                    st.success(f"✅ {nom} ajouté à {quadrant_ajout}.")
                    st.cache_data.clear()
                    st.session_state.cartographie_data = load_data_from_sheet()
                    st.rerun()
            else:
                st.warning("⚠️ Merci de remplir au minimum Nom + Poste")

    with right_col:
        # Graphique répartition des candidats par quadrant (déplacé de l'ancien onglet Vue globale)
        try:
            import plotly.express as px
            total_profils = sum(len(v) for v in st.session_state.cartographie_data.values())
            counts = {k: len(st.session_state.cartographie_data[k]) for k in st.session_state.cartographie_data.keys()}
            if sum(counts.values()) > 0:
                df_counts = pd.DataFrame(list(counts.items()), columns=['Quadrant', 'Nombre'])
                df_counts = df_counts[df_counts['Nombre'] > 0]
                st.subheader(f"Répartition des candidats par quadrant ({total_profils} profils)")
                fig = px.pie(
                    df_counts,
                    names='Quadrant',
                    values='Nombre',
                    color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
                )
                # Afficher pourcentage + valeur (valeur en gras) à l'intérieur
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+value',
                    texttemplate='%{percent}<br><b>%{value}</b>',
                    hovertemplate='<b>%{label}</b><br>Nombre: %{value}<br>Pourcentage: %{percent}<extra></extra>',
                    textfont=dict(size=18)
                )
                fig.update_layout(legend_font_size=16)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucun candidat dans la cartographie pour l'instant.")
        except ImportError:
            st.warning("⚠️ Plotly n'est pas installé. Installez-le avec 'pip install plotly'.")

    st.divider()
    st.subheader("🔍 Rechercher un candidat")
    search_cols = st.columns([1,2])
    with search_cols[0]:
        quadrants = ["Tout"] + list(st.session_state.cartographie_data.keys())
        quadrant_recherche = st.selectbox("Quadrant à rechercher", quadrants, key="carto_quadrant_search")
    with search_cols[1]:
        search_term = st.text_input("Rechercher par nom ou poste", key="carto_search")

    # Construire la source de recherche (supporte "Tout") et inclure le quadrant d'origine
    if quadrant_recherche == "Tout":
        source_list = []
        for quad, cands in st.session_state.cartographie_data.items():
            for cand in cands[::-1]:
                c = cand.copy()
                c['quadrant'] = quad
                source_list.append(c)
    else:
        source_list = []
        for cand in st.session_state.cartographie_data.get(quadrant_recherche, [])[::-1]:
            c = cand.copy()
            c['quadrant'] = quadrant_recherche
            source_list.append(c)

    filtered_cands = [
        cand for cand in source_list
        if not search_term or search_term.lower() in cand['nom'].lower() or search_term.lower() in cand['poste'].lower()
    ]

    st.subheader(f"📋 Candidats dans : {quadrant_recherche} ({len(filtered_cands)})")
    
    if not filtered_cands:
        st.info("Aucun candidat correspondant dans ce quadrant.")
    else:
        for i, cand in enumerate(filtered_cands):
            edit_key = f"edit_carto_flag_{quadrant_recherche}_{i}"
            anchor_id = f"cand_{quadrant_recherche}_{i}"
            st.markdown(f"<div id='{anchor_id}'></div>", unsafe_allow_html=True)
            with st.expander(f"{cand['nom']} - {cand['poste']} ({cand['date']})", expanded=st.session_state.get(edit_key, False)):
                st.write(f"**Entreprise :** {cand.get('entreprise', 'Non spécifiée')}")
                st.write(f"**LinkedIn :** {cand.get('linkedin', 'Non spécifié')}")
                st.write(f"**Notes :** {cand.get('notes', '')}")
                
                cv_drive_link = cand.get('cv_link')
                if cv_drive_link and cv_drive_link.startswith('http'):
                    st.markdown(f"**CV :** [Ouvrir depuis Google Drive]({cv_drive_link})", unsafe_allow_html=True)
                
                # Bouton de suppression à la place de l'export texte
                col_a, col_b = st.columns([1,1])
                with col_a:
                    if st.button("🗑️ Supprimer ce candidat", key=f"delete_carto_{quadrant_recherche}_{i}"):
                        origin_quad = cand.get('quadrant', quadrant_recherche)
                        ok = delete_from_google_sheet(origin_quad, cand)
                        if ok:
                            st.success("✅ Candidat supprimé de la cartographie.")
                            st.cache_data.clear()
                            st.session_state.cartographie_data = load_data_from_sheet()
                            rerun_fn = getattr(st, "experimental_rerun", None)
                            if callable(rerun_fn):
                                rerun_fn()
                            else:
                                st.rerun()
                        else:
                            st.error("❌ Impossible de trouver/supprimer ce candidat dans Google Sheets.")
                with col_b:
                    if st.button("✏️ Modifier ce candidat", key=f"edit_carto_btn_{quadrant_recherche}_{i}"):
                        st.session_state[edit_key] = True
                        st.session_state['scroll_to'] = anchor_id

                # Afficher le formulaire de modification directement sous le bloc, et ouvrir l'expander
                if st.session_state.get(edit_key, False):
                    st.markdown("**Modifier les informations du candidat**")
                    with st.form(f"form_edit_{quadrant_recherche}_{i}", clear_on_submit=False):
                        # Disposition en 3 colonnes pour les champs principaux
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            nom_edit = st.text_input("Nom", value=str(cand.get('nom','')), key=f"edit_nom_{quadrant_recherche}_{i}")
                            linkedin_edit = st.text_input("Lien LinkedIn", value=str(cand.get('linkedin','')), key=f"edit_linkedin_{quadrant_recherche}_{i}")
                        with ec2:
                            poste_edit = st.text_input("Poste", value=str(cand.get('poste','')), key=f"edit_poste_{quadrant_recherche}_{i}")
                            notes_edit = st.text_area("Notes", value=str(cand.get('notes','')), height=100, key=f"edit_notes_{quadrant_recherche}_{i}")
                        with ec3:
                            entreprise_edit = st.text_input("Entreprise", value=str(cand.get('entreprise','')), key=f"edit_entreprise_{quadrant_recherche}_{i}")
                            cv_edit_file = st.file_uploader("Nouveau CV (PDF ou DOCX)", type=["pdf","docx"], key=f"edit_cv_{quadrant_recherche}_{i}")
                        submitted = st.form_submit_button("💾 Enregistrer les modifications")
                        if submitted:
                            updated = {
                                'Nom': nom_edit,
                                'Poste': poste_edit,
                                'Entreprise': entreprise_edit,
                                'Linkedin': linkedin_edit,
                                'Notes': notes_edit,
                            }
                            # Upload CV si fourni
                            if cv_edit_file is not None:
                                _, file_extension = os.path.splitext(cv_edit_file.name)
                                cv_filename = f"{nom_edit}{file_extension}"
                                new_link = upload_cv_to_drive(cv_filename, cv_edit_file)
                                if new_link:
                                    updated['CV_Link'] = new_link
                            origin_quad = cand.get('quadrant', quadrant_recherche)
                            ok = update_in_google_sheet(origin_quad, cand, updated)
                            if ok:
                                st.success("✅ Candidat mis à jour.")
                                st.session_state[edit_key] = False
                                st.cache_data.clear()
                                st.session_state.cartographie_data = load_data_from_sheet()
                                rerun_fn = getattr(st, "experimental_rerun", None)
                                if callable(rerun_fn):
                                    rerun_fn()
                                else:
                                    st.rerun()
                            else:
                                st.error("❌ Mise à jour impossible (ligne introuvable ou erreur).")

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