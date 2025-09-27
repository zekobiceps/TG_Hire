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

# -------------------- FONCTION D'AUTHENTIFICATION --------------------
def get_gsheet_client():
    """Authentifie avec Google Sheets - Version simplifiée"""
    try:
        # Méthode directe avec les secrets
        service_account_info = {
            "type": "service_account",
            "project_id": "astute-anchor-418600",
            "private_key_id": "a746bd2519769b7e7bf4068b1874c415f9c94fab",
            "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDdHmkxnpHOs55A
YX1lDjh8sFJ5q4EVeXa4ATrCO6EgU2GJWmmCKIUH/D5/HK7L8GBZUuYIucFBD+8n
S3TZw6+n8P+TGGWuhrmyjCRgKUg8ZUmeRs+qjH0E1D65uxbUCf3L9K74dvqPDKav
JLwI9RG6Uxq17zer4lsWM89gDqzvpBoMphg6/N4jwPC/ctT1636PsHHEykCRCiKh
tIqho4F0ZKdmtL3GT9YwHrePZi89gn12idWWFZSCe/z++4Ca1GBN37Qe7acow16f
mvNEobYkq+4EGOc0r2bRxSojBp3H7V3TD0rN9hPx1HL3BRKIkpGOMdKvfkv9zPU7
POxcV0PvAgMBAAECggEALFQk7aQnAgPjZW/F9kTwERs+JZM66SW1JbVlZLwUlMjy
hFlCTqw140Bv/QawikUR48ZpRHWM5zC9Fqkbb266H9aCPiiFdgQfZUqQHlEYYLdD
l34FsuDATYAJZS27KV4pacKPc1NS7uuv3Ovl4HvVBoATmkavZ/+UmDJh0BWRGOdz
QN6BPy3L/7J6xeqLpX7PEPQue1pOpfwgM52XZqy4yf7cttZKK4AoDKSnLrU8SG7s
Tz1+dheAyOyrzQE4PyR6jFglLAbOKUYkNt9YkIw1zkLD+TaRw/oZLbBqGhMV50VI
PSDjgC6gFjQuZr+FOThP3crmzOulikOVuetUesESeQKBgQDy7n3YF2wZXP5wvrDk
smAEaR+7HB3nr849rkeLuGreKwdyIPVqTz40h9U4TpSHRGTUAnKHuSxB4k9T5xSU
0nU6vnBfubooBE+UoRUtf+sxrp7Z8qIFn7Mmde9aeI2IOO4TYnzj0n8Xw7rvaKXR
5rwaNXvRZHoEs2xKE9dJ5tnD9wKBgQDpA4a9S6KOA8RQCxkGNmw48xxuEWDkgGs1
l+t4go3JafgFFTX6ZRGA/EMmAZK6/KX46LN/3mmVVUGuHfOewyU3BaUY8a+6QerD
UghrNxo2vzSAS+hwRIaeflm/Di6xJZnLcKg2gL9gFOGXN7SgFUi2kolQpeT8nflw
T1lt7S8RyQKBgQDTKwypMnL8+SET0C7kHUnpi5fRhfdY1jFo3H3ErmH3DWBDjPLH
nmpsL0bg0y25B3K9+AKmiAg4nQhn3o69btQIZFI6Y6+16Ulj4UIPcwp2/VuICKle
ShvoasvM0M32g8Yvg4UcZHWlqrZsNYMummsYPTWMJtMKEw0mt2iFDO5usQKBgQCk
C4qBnE0eBELiQ13jxM7eLTHXv75iQJK50XHCjs85fLRTB8LPvPXcxDyV9keSAyrq
GRG+NRxKORKbfZS1MhfyK7Q24nhf/eZEim1I5is7XdOde1NyLpxD2xpd6qMurhUf
Z/nVHUEeaLUFm/87MKDXgETSFWkn/CPPUN3aCUC5GQKBgQDtopFYi66sm8syKTPb
i6C5MCs04HWLKtwq3iwzk6u20/KpkU77/mDk/er/3zWHB43eBy559qGRIiCRw6VW
uI6iW8UDB1hkw8D6ww0X67IxTG4LQsRXEyi2u/0J8GjMPCksZWDm/vIbbiHTIBdg
xFSCq2ZVavwXRLKlCTQjBS8E0A==
-----END PRIVATE KEY-----""",
            "client_email": "tg-hire@astute-anchor-418600.iam.gserviceaccount.com",
            "client_id": "105746123909483274099",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/tg-hire%40astute-anchor-418600.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }
        
        gc = gspread.service_account_from_dict(service_account_info)
        st.success("✅ Authentification Google Sheets réussie (méthode directe)")
        return gc
        
    except Exception as e:
        st.error(f"❌ Échec de l'authentification Google Sheets. Erreur : {e}")
        return None
# -------------------- FONCTIONS GOOGLE SHEETS --------------------
@st.cache_data(ttl=600)
def load_data_from_sheet():
    """Charge toutes les données de la feuille Google Sheets et les organise par quadrant."""
    try:
        gc = get_gsheet_client()
        if not gc:
            return {
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
        st.error(f"❌ Échec du chargement des données depuis Google Sheets. Vérifiez les permissions d'accès et le nom de l'onglet. Erreur : {e}")
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
                load_data_from_sheet.clear()
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