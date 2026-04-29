# -*- coding: utf-8 -*-
import streamlit as st
from utils import display_commit_info, require_login

st.set_page_config(
    page_title="Gestion des Stagiaires",
    page_icon="🎓",
    layout="wide"
)

require_login()

import os
import json
import base64
import datetime
import uuid
import io
import requests
import fitz  # PyMuPDF

import pandas as pd
from PIL import Image

try:
    import gspread
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ─────────────────────────── CONFIGURATION ───────────────────────────────────
STAGIAIRES_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PwaZA9LjIQvHk0iiM-uA0ndmyVCJ2SPuNP21QzJI09k/edit"
STAGIAIRES_WORKSHEET = "Stagiaires"
DRIVE_ROOT_FOLDER_ID = st.secrets.get("DRIVE_ROOT_FOLDER_ID", "1FaoQw6aRp76M9U1VAB8Y6Hk1zaQ4VBjK")

FORMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Forms")

DOCS_TGCC = {
    "FR 20 - Fiche de renseignement": "FR 20 - PS MCH Fiche de renseignement -Stagiaire- V3 .docx (2).pdf",
    "Clause de discrétion": "Clause de discrétion stagiaire (15).pdf",
    "FI 04 - Liste des documents": "FI 04 - PS MCH LISTE DES DOCUMENTS A FOURNIR -DOSSIER STAGIAIRES-V2 (2).pdf",
}

COLONNES_SHEET = [
    "id_demande", "date_demande", "type_demande", "chantier", "responsable_demandeur",
    "fonction_demandeur", "nom_tuteur", "fonction_tuteur", "fonction_stagiaire",
    "type_stage", "duree_semaines", "date_debut", "date_fin", "missions",
    "formation_souhaitee", "experience_souhaitee", "indemnisation_min", "indemnisation_max",
    "commentaire", "nom_stagiaire", "email_stagiaire", "cv_uploaded", "formulaire_uploaded",
    "recruteur", "etat", "date_validation_rh", "valideur_rh", "drive_folder_url",
    "attestation_generee", "motif_rejet",
]

ETATS = [
    "En attente validation",
    "Validée",
    "Rejetée",
    "Mail envoyé",
    "Documents reçus",
    "Dossier conforme",
    "Attestation demandée",
    "Stage en cours",
    "Stage terminé",
]

# ─────────────────────────── HELPERS GOOGLE ──────────────────────────────────

def _build_sa_info():
    return {
        "type": st.secrets["GCP_TYPE"],
        "project_id": st.secrets["GCP_PROJECT_ID"],
        "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GCP_PRIVATE_KEY"].replace("\\n", "\n").strip(),
        "client_email": st.secrets["GCP_CLIENT_EMAIL"],
        "client_id": st.secrets["GCP_CLIENT_ID"],
        "auth_uri": st.secrets.get("GCP_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": st.secrets.get("GCP_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": st.secrets.get("GCP_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": st.secrets.get("GCP_CLIENT_CERT_URL", ""),
    }

@st.cache_resource
def _get_gspread_client():
    if not GOOGLE_AVAILABLE:
        return None
    try:
        return gspread.service_account_from_dict(_build_sa_info())
    except Exception as e:
        st.error(f"❌ Connexion Google Sheets : {e}")
        return None

@st.cache_resource
def _get_drive_service():
    if not GOOGLE_AVAILABLE:
        return None
    try:
        creds = service_account.Credentials.from_service_account_info(
            _build_sa_info(),
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"❌ Connexion Google Drive : {e}")
        return None

def _get_or_create_worksheet():
    gc = _get_gspread_client()
    if not gc:
        return None
    try:
        sh = gc.open_by_url(STAGIAIRES_SHEET_URL)
    except Exception as e:
        st.error(f"❌ Impossible d'ouvrir le Google Sheet : {e}")
        return None
    try:
        ws = sh.worksheet(STAGIAIRES_WORKSHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=STAGIAIRES_WORKSHEET, rows=500, cols=len(COLONNES_SHEET))
        ws.append_row(COLONNES_SHEET)
    return ws

def load_stagiaires() -> pd.DataFrame:
    ws = _get_or_create_worksheet()
    if ws is None:
        return pd.DataFrame(columns=COLONNES_SHEET)
    try:
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame(columns=COLONNES_SHEET)
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"❌ Chargement données : {e}")
        return pd.DataFrame(columns=COLONNES_SHEET)

def append_stagiaire(row: dict):
    ws = _get_or_create_worksheet()
    if ws is None:
        return False
    try:
        values = [str(row.get(c, "")) for c in COLONNES_SHEET]
        ws.append_row(values)
        return True
    except Exception as e:
        st.error(f"❌ Sauvegarde : {e}")
        return False

def update_stagiaire_field(id_demande: str, updates: dict):
    """Met à jour des champs d'une ligne identifiée par id_demande."""
    ws = _get_or_create_worksheet()
    if ws is None:
        return False
    try:
        records = ws.get_all_records()
        for i, rec in enumerate(records, start=2):
            if str(rec.get("id_demande", "")) == str(id_demande):
                for col_name, val in updates.items():
                    if col_name in COLONNES_SHEET:
                        col_idx = COLONNES_SHEET.index(col_name) + 1
                        ws.update_cell(i, col_idx, str(val))
                return True
        st.warning("Demande introuvable.")
        return False
    except Exception as e:
        st.error(f"❌ Mise à jour : {e}")
        return False

# ─────────────────────────── HELPERS DRIVE ───────────────────────────────────

def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    q = (f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed=false")
    res = service.files().list(q=q, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    f = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return f["id"]

def upload_files_to_folder(files: list[tuple[bytes, str, str]], folder_name: str, parent_id: str = DRIVE_ROOT_FOLDER_ID) -> tuple[str, list[str]]:
    """Crée (ou récupère) un dossier sous parent_id/année/folder_name et uploade les fichiers.
    files: list of tuples (bytes, filename, mimetype)
    Retourne (folder_id, [webViewLink,...])
    """
    service = _get_drive_service()
    if not service:
        return "", []
    try:
        annee = str(datetime.date.today().year)
        annee_id = _get_or_create_folder(service, annee, parent_id)
        folder_id = _get_or_create_folder(service, folder_name.upper(), annee_id)
        from googleapiclient.http import MediaIoBaseUpload
        links = []
        for bts, fname, mimetype in files:
            media = MediaIoBaseUpload(io.BytesIO(bts), mimetype=mimetype)
            meta = {"name": fname, "parents": [folder_id]}
            uploaded = service.files().create(body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True).execute()
            links.append(uploaded.get("webViewLink", ""))
        return folder_id, links
    except Exception as e:
        # Afficher l'ID parent pour debug si erreur de quota/permissions
        try:
            st.error(f"❌ Upload Drive (parent={parent_id}) : {e}")
        except Exception:
            pass
        return "", []

def list_folder_files(folder_id: str) -> list[dict]:
    """Retourne la liste des fichiers (id,name,webViewLink) dans un dossier."""
    service = _get_drive_service()
    if not service or not folder_id:
        return []
    try:
        q = f"'{folder_id}' in parents and trashed=false"
        res = service.files().list(q=q, fields="files(id,name,webViewLink)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        return res.get("files", [])
    except Exception as e:
        st.error(f"❌ Liste Drive : {e}")
        return []

# ─────────────────────────── HELPERS DeepSeek ────────────────────────────────

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF. Si le PDF est scanné/manuscrit, utilise l'OCR pytesseract."""
    # Essai 1 : extraction texte natif (PDF numérique)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texte = "\n".join(str(page.get_text()) for page in doc)
        if texte.strip():
            return texte
    except Exception:
        pass

    # Essai 2 : OCR via pdf2image + pytesseract (PDF scanné ou manuscrit)
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(pdf_bytes, dpi=300)
        texte_ocr = "\n".join(
            pytesseract.image_to_string(img, lang="fra+ara")
            for img in images
        )
        return texte_ocr
    except Exception:
        pass

    return ""


def pdf_to_base64_images(pdf_bytes: bytes) -> list[str]:
    """Convertit les pages d'un PDF en images base64 (pour DeepSeek vision)."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, dpi=200)
        result = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            result.append(base64.b64encode(buf.getvalue()).decode())
        return result
    except Exception:
        return []


def lire_formulaire_ia(pdf_bytes: bytes) -> dict:
    """Appelle DeepSeek pour extraire les champs du formulaire FR 19.
    Utilise la vision (images) si le texte OCR est insuffisant."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ Clé DEEPSEEK_API_KEY manquante dans les secrets.")
        return {}

    texte = extract_text_from_pdf_bytes(pdf_bytes)
    utilise_vision = len(texte.strip()) < 100  # texte trop court = formulaire scanné

    if utilise_vision:
        # Envoyer les images à DeepSeek-Vision
        b64_images = pdf_to_base64_images(pdf_bytes)
        if not b64_images:
            st.warning("⚠️ Impossible de convertir le PDF en images. Vérifiez que poppler est installé.")
            return {}
        content_parts: list = [
            {"type": "text", "text": (
                "Tu es un assistant RH. Voici les pages d'un formulaire de demande de stage TGCC (FR 19) rempli manuellement.\n"
                "Extrais les informations suivantes et retourne un JSON valide UNIQUEMENT (aucun texte autour) :\n"
                '{\n  "type_demande": "",\n  "chantier": "",\n  "responsable_demandeur": "",\n'
                '  "fonction_demandeur": "",\n  "nom_tuteur": "",\n  "fonction_tuteur": "",\n'
                '  "fonction_stagiaire": "",\n  "type_stage": "",\n  "duree_semaines": "",\n'
                '  "date_debut": "",\n  "date_fin": "",\n  "missions": "",\n'
                '  "formation_souhaitee": "",\n  "experience_souhaitee": "",\n'
                '  "indemnisation_min": "",\n  "indemnisation_max": "",\n  "commentaire": ""\n}'
            )}
        ]
        for b64 in b64_images[:3]:  # max 3 pages
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
        messages = [{"role": "user", "content": content_parts}]
        model = "deepseek-chat"  # deepseek-vision si disponible sur votre compte
    else:
        prompt = f"""Tu es un assistant RH. Voici le contenu d'un formulaire de demande de stage TGCC (FR 19).
Extrais les informations suivantes et retourne un JSON valide UNIQUEMENT (aucun texte autour) :
{{
  "type_demande": "",
  "chantier": "",
  "responsable_demandeur": "",
  "fonction_demandeur": "",
  "nom_tuteur": "",
  "fonction_tuteur": "",
  "fonction_stagiaire": "",
  "type_stage": "",
  "duree_semaines": "",
  "date_debut": "",
  "date_fin": "",
  "missions": "",
  "formation_souhaitee": "",
  "experience_souhaitee": "",
  "indemnisation_min": "",
  "indemnisation_max": "",
  "commentaire": ""
}}

Contenu du formulaire :
{texte[:4000]}
"""
        messages = [{"role": "user", "content": prompt}]
        model = "deepseek-chat"

    if not texte.strip() and not utilise_vision:
        st.warning("⚠️ Impossible d'extraire le texte du PDF.")
        return {}
    prompt = f"""Tu es un assistant RH. Voici le contenu d'un formulaire de demande de stage TGCC (FR 19).
Extrais les informations suivantes et retourne un JSON valide UNIQUEMENT (aucun texte autour) :
{{
  "type_demande": "",
  "chantier": "",
  "responsable_demandeur": "",
  "fonction_demandeur": "",
  "nom_tuteur": "",
  "fonction_tuteur": "",
  "fonction_stagiaire": "",
  "type_stage": "",
  "duree_semaines": "",
  "date_debut": "",
  "date_fin": "",
  "missions": "",
  "formation_souhaitee": "",
  "experience_souhaitee": "",
  "indemnisation_min": "",
  "indemnisation_max": "",
  "commentaire": ""
}}

Contenu du formulaire :
{texte[:4000]}
"""
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0},
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Nettoyer markdown si présent
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        st.error(f"❌ Erreur DeepSeek : {e}")
        return {}

# ─────────────────────────── HELPERS ATTESTATION ─────────────────────────────

def generer_attestation(nom_stagiaire: str, chantier: str, date_debut: str,
                         date_fin: str, type_stage: str, signature_img_bytes=None) -> bytes:
    """Superpose les informations sur le canevas PDF d'attestation."""
    canevas_path = os.path.join(FORMS_DIR, "attestation de stage canevas.pdf")
    if not os.path.exists(canevas_path):
        st.error("❌ Canevas attestation introuvable : Forms/attestation de stage canevas.pdf")
        return b""
    try:
        canevas = fitz.open(canevas_path)
        page = canevas[0]
        w, h = page.rect.width, page.rect.height

        # Informations textuelles (superposition)
        inserts = [
            (220, h * 0.42, nom_stagiaire.upper(), 12),
            (220, h * 0.48, type_stage, 12),
            (220, h * 0.54, chantier, 12),
            (160, h * 0.60, f"du {date_debut} au {date_fin}", 12),
        ]
        for x, y, text, size in inserts:
            page.insert_text((x, y), text, fontsize=size, color=(0, 0, 0))

        # Signature en bas à droite
        if signature_img_bytes:
            sig_rect = fitz.Rect(w - 200, h - 140, w - 30, h - 50)
            page.insert_image(sig_rect, stream=signature_img_bytes)

        out = io.BytesIO()
        canevas.save(out)
        return out.getvalue()
    except Exception as e:
        st.error(f"❌ Génération attestation : {e}")
        return b""

# ─────────────────────────── HELPERS RÔLE ────────────────────────────────────

def get_role() -> str:
    """Lit le rôle depuis la session. Si absent (session pré-existante),
    le redéduit depuis le dict users chargé par Home.py."""
    role = st.session_state.get("current_role", "")
    if not role:
        # Fallback : retrouver via l'email (current_user = nom) dans users dict
        users: dict = st.session_state.get("users", {})
        current_user: str = st.session_state.get("current_user", "")
        for _email, udata in users.items():
            if str(udata.get("name", "")).strip() == current_user.strip():
                role = str(udata.get("role", "recruteur")).strip().lower()
                # Mettre en cache pour la suite
                st.session_state["current_role"] = role
                break
        else:
            role = "recruteur"
    return role.lower()

def is_rh() -> bool:
    return get_role() == "rh"

# ═════════════════════════════════════════════════════════════════════════════
# PAGE PRINCIPALE
# ═════════════════════════════════════════════════════════════════════════════

st.title("🎓 Gestion des Stagiaires")
display_commit_info()

# Initialisation session
if "stagiaires_df" not in st.session_state:
    st.session_state.stagiaires_df = None
if "last_load" not in st.session_state:
    st.session_state.last_load = None

def refresh_data():
    st.session_state.stagiaires_df = load_stagiaires()
    st.session_state.last_load = datetime.datetime.now()

# Chargement initial
if st.session_state.stagiaires_df is None:
    refresh_data()

# Alertes J-7 automatiques à l'ouverture
def check_alertes_j7(df: pd.DataFrame | None):
    if df is None or df.empty or "date_fin" not in df.columns:
        return
    aujourd_hui = datetime.date.today()
    alertes = []
    for _, row in df.iterrows():
        etat = str(row.get("etat", ""))
        if etat in ("Stage terminé", "Rejetée"):
            continue
        try:
            dft = datetime.datetime.strptime(str(row["date_fin"]), "%d/%m/%Y").date()
            delta = (dft - aujourd_hui).days
            if 0 <= delta <= 7:
                alertes.append(row)
        except Exception:
            pass
    if alertes:
        st.warning(f"⚠️ **{len(alertes)} stagiaire(s)** arrivent à fin de stage dans 7 jours ou moins !")
        with st.expander("Voir les alertes J-7"):
            for row in alertes:
                st.markdown(f"**{row.get('nom_stagiaire','?')}** — Chantier : {row.get('chantier','?')} — Fin : {row.get('date_fin','?')} — Tuteur : {row.get('nom_tuteur','?')}")

check_alertes_j7(st.session_state.stagiaires_df)

col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Actualiser les données"):
        refresh_data()
        st.rerun()

_raw_df = st.session_state.stagiaires_df
df: pd.DataFrame = _raw_df if isinstance(_raw_df, pd.DataFrame) else pd.DataFrame(columns=COLONNES_SHEET)

# ─────────────────────────── ONGLETS ─────────────────────────────────────────

if is_rh():
    tabs_labels = ["📊 Tableau de Bord", "✅ Validation RH"]
else:
    tabs_labels = [
        "📝 Nouvelle Demande",
        "📊 Tableau de Bord",
        "✅ Validation RH",
        "📧 Traitement & Suivi",
        "🔔 Alertes J-7",
        "📄 Attestation de Stage",
    ]

tabs = st.tabs(tabs_labels)

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — NOUVELLE DEMANDE
# ══════════════════════════════════════════════════════════════════════════════
if not is_rh():
    with tabs[tabs_labels.index("📝 Nouvelle Demande")]:
        st.subheader("📝 Nouvelle demande de stagiaire")
        # Upload formulaire scanné (obligatoire)
        st.markdown("#### 1. Formulaire de demande scanné (FR 19) *obligatoire*")
        formulaire_file = st.file_uploader(
            "Uploader le formulaire FR 19 (PDF)", type=["pdf"], key="upload_formulaire"
        )

        # Pré-remplissage IA
        ia_data = {}
        if formulaire_file is not None:
            pdf_bytes = formulaire_file.read()
            formulaire_file.seek(0)
            col_btn, col_info = st.columns([2, 5])
            with col_btn:
                if st.button("🤖 Lecture IA — Pré-remplir le formulaire", type="secondary"):
                    with st.spinner("Analyse du formulaire en cours..."):
                        ia_data = lire_formulaire_ia(pdf_bytes)
                    if ia_data:
                        st.session_state["ia_form_data"] = ia_data
                        st.success("✅ Formulaire analysé. Les champs ont été pré-remplis.")
                        st.rerun()
            with col_info:
                st.caption("L'IA lit le PDF et pré-remplit les champs ci-dessous. Vérifiez avant de soumettre.")

        prefill = st.session_state.get("ia_form_data", {})

        st.markdown("#### 2. Informations de la demande")
        with st.form("form_nouvelle_demande"):
            c1, c2 = st.columns(2)
            with c1:
                type_demande = st.selectbox(
                    "Type de demande",
                    ["Stage PFE", "Stage conventionné", "Stage non conventionné", "Stage d'observation"],
                    index=["Stage PFE", "Stage conventionné", "Stage non conventionné", "Stage d'observation"].index(prefill.get("type_demande", "Stage PFE")) if prefill.get("type_demande") in ["Stage PFE", "Stage conventionné", "Stage non conventionné", "Stage d'observation"] else 0
                )
                chantier = st.text_input("Chantier / Direction concerné(e)", value=prefill.get("chantier", ""))
                responsable_demandeur = st.text_input("Responsable demandeur", value=prefill.get("responsable_demandeur", ""))
                fonction_demandeur = st.text_input("Fonction du demandeur", value=prefill.get("fonction_demandeur", ""))
            with c2:
                nom_tuteur = st.text_input("Nom & prénom du tuteur", value=prefill.get("nom_tuteur", ""))
                fonction_tuteur = st.text_input("Fonction du tuteur", value=prefill.get("fonction_tuteur", ""))
                fonction_stagiaire = st.text_input("Fonction attribuée au stagiaire", value=prefill.get("fonction_stagiaire", ""))
                type_stage = st.text_input("Type de stage (ex: PFE Génie Civil)", value=prefill.get("type_stage", ""))

            c3, c4 = st.columns(2)
            with c3:
                duree_semaines = st.number_input("Durée (semaines)", min_value=1, max_value=52, value=int(prefill.get("duree_semaines", 8) or 8))
                try:
                    date_debut_default = datetime.datetime.strptime(prefill.get("date_debut", ""), "%d/%m/%Y").date() if prefill.get("date_debut") else datetime.date.today()
                except Exception:
                    date_debut_default = datetime.date.today()
                date_debut = st.date_input("Date de début", value=date_debut_default)
            with c4:
                indemnisation_min = st.number_input("Indemnisation min (MAD)", min_value=0, value=int(prefill.get("indemnisation_min", 0) or 0))
                indemnisation_max = st.number_input("Indemnisation max (MAD)", min_value=0, value=int(prefill.get("indemnisation_max", 0) or 0))
                try:
                    date_fin_default = datetime.datetime.strptime(prefill.get("date_fin", ""), "%d/%m/%Y").date() if prefill.get("date_fin") else date_debut + datetime.timedelta(weeks=int(duree_semaines))
                except Exception:
                    date_fin_default = date_debut + datetime.timedelta(weeks=8)
                date_fin = st.date_input("Date de fin", value=date_fin_default)

            missions = st.text_area("Missions", value=prefill.get("missions", ""), height=80)
            formation_souhaitee = st.text_input("Formation(s) souhaitée(s)", value=prefill.get("formation_souhaitee", ""))
            experience_souhaitee = st.text_input("Expérience(s) souhaitables", value=prefill.get("experience_souhaitee", ""))
            commentaire = st.text_area("Commentaire", value=prefill.get("commentaire", ""), height=60)

            st.markdown("#### 3. CV du stagiaire")
            sourcing_interne = st.checkbox("Pas de CV — Sourcing à effectuer par le recruteur")
            cv_file = st.file_uploader("Uploader le CV (PDF)", type=["pdf"], key="upload_cv") if not sourcing_interne else None

            submitted = st.form_submit_button("✅ Soumettre la demande", type="primary")
            if submitted:
                if formulaire_file is None:
                    st.error("❌ Le formulaire scanné (FR 19) est obligatoire.")
                else:
                    id_demande = f"STG-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    row = {
                        "id_demande": id_demande,
                        "date_demande": datetime.date.today().strftime("%d/%m/%Y"),
                        "type_demande": type_demande,
                        "chantier": chantier,
                        "responsable_demandeur": responsable_demandeur,
                        "fonction_demandeur": fonction_demandeur,
                        "nom_tuteur": nom_tuteur,
                        "fonction_tuteur": fonction_tuteur,
                        "fonction_stagiaire": fonction_stagiaire,
                        "type_stage": type_stage,
                        "duree_semaines": duree_semaines,
                        "date_debut": date_debut.strftime("%d/%m/%Y"),
                        "date_fin": date_fin.strftime("%d/%m/%Y"),
                        "missions": missions,
                        "formation_souhaitee": formation_souhaitee,
                        "experience_souhaitee": experience_souhaitee,
                        "indemnisation_min": indemnisation_min,
                        "indemnisation_max": indemnisation_max,
                        "commentaire": commentaire,
                        "nom_stagiaire": "",
                        "email_stagiaire": "",
                        "cv_uploaded": "Non" if sourcing_interne else "Oui",
                        "formulaire_uploaded": "Oui",
                        "recruteur": st.session_state.get("current_user", ""),
                        "etat": "En attente validation",
                        "date_validation_rh": "",
                        "valideur_rh": "",
                        "drive_folder_url": "",
                        "attestation_generee": "Non",
                        "motif_rejet": "",
                    }
                    if append_stagiaire(row):
                        st.success(f"✅ Demande **{id_demande}** soumise avec succès.")
                        # Effacer le pré-remplissage IA
                        if "ia_form_data" in st.session_state:
                            del st.session_state["ia_form_data"]

                        # Créer le dossier YEAR / ID_DEMANDE dès la soumission (même si pas de PJ)
                        try:
                            service = _get_drive_service()
                            if service:
                                try:
                                    annee = str(datetime.date.today().year)
                                    annee_id = _get_or_create_folder(service, annee, DRIVE_ROOT_FOLDER_ID)
                                    folder_id = _get_or_create_folder(service, id_demande.upper(), annee_id)
                                    if folder_id:
                                        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
                                        update_stagiaire_field(id_demande, {"drive_folder_url": folder_url})
                                except Exception:
                                    # ne pas bloquer la soumission si la création du dossier échoue
                                    pass
                        except Exception:
                            pass

                        # Upload immédiat du formulaire (+ CV si fourni) vers Drive
                        try:
                            files_to_upload = []
                            # formulaire_file existe (obligatoire)
                            formulaire_file.seek(0)
                            files_to_upload.append((formulaire_file.read(), f"{id_demande}_formulaire.pdf", "application/pdf"))
                            if cv_file is not None:
                                cv_file.seek(0)
                                files_to_upload.append((cv_file.read(), f"{id_demande}_cv.pdf", "application/pdf"))
                            if files_to_upload:
                                # upload into DRIVE_ROOT_FOLDER_ID (the helper will create YEAR/ID if needed)
                                folder_id, links = upload_files_to_folder(files_to_upload, id_demande, parent_id=DRIVE_ROOT_FOLDER_ID)
                                if folder_id:
                                    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
                                    update_stagiaire_field(id_demande, {"drive_folder_url": folder_url})
                        except Exception:
                            # ne pas bloquer la soumission si l'upload échoue
                            pass
                        refresh_data()
                    else:
                        st.error("❌ Erreur lors de la sauvegarde.")

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — TABLEAU DE BORD
# ══════════════════════════════════════════════════════════════════════════════
with tabs[tabs_labels.index("📊 Tableau de Bord")]:
    st.subheader("📊 Tableau de bord des stagiaires")

    if df.empty:
        st.info("Aucune demande enregistrée.")
    else:
        # KPIs
        total = len(df)
        en_attente = len(df[df["etat"] == "En attente validation"])
        en_cours = len(df[df["etat"].isin(["Stage en cours", "Dossier conforme", "Mail envoyé", "Documents reçus"])])
        valides = len(df[df["etat"] == "Validée"])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total demandes", total)
        k2.metric("En attente validation", en_attente)
        k3.metric("Validées (à traiter)", valides)
        k4.metric("Stages en cours", en_cours)

        st.markdown("---")

        # Stagiaires actifs par chantier
        aujourd_hui = datetime.date.today()
        actifs = []
        for _, row in df.iterrows():
            if str(row.get("etat", "")) in ("Stage terminé", "Rejetée", "En attente validation"):
                continue
            try:
                dfd = datetime.datetime.strptime(str(row["date_debut"]), "%d/%m/%Y").date()
                dff = datetime.datetime.strptime(str(row["date_fin"]), "%d/%m/%Y").date()
                if dfd <= aujourd_hui <= dff:
                    actifs.append(row)
            except Exception:
                pass
        if actifs:
            df_actifs = pd.DataFrame(actifs)
            st.markdown("#### Stagiaires actifs par chantier")
            par_chantier = df_actifs.groupby("chantier").size().reset_index(name="Nb stagiaires actifs")
            st.dataframe(par_chantier, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Toutes les demandes")
        filtre_etat = st.multiselect("Filtrer par état", options=ETATS, default=[])
        filtre_chantier = st.text_input("Filtrer par chantier (texte)")

        df_affiche = df.copy()
        if filtre_etat:
            df_affiche = df_affiche[df_affiche["etat"].isin(filtre_etat)]
        if filtre_chantier:
            df_affiche = df_affiche[df_affiche["chantier"].str.contains(filtre_chantier, case=False, na=False)]

        cols_visible = ["id_demande", "date_demande", "nom_stagiaire", "chantier", "type_stage",
                        "date_debut", "date_fin", "responsable_demandeur", "recruteur", "etat"]
        st.dataframe(df_affiche[[c for c in cols_visible if c in df_affiche.columns]], use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — VALIDATION RH
# ══════════════════════════════════════════════════════════════════════════════
with tabs[tabs_labels.index("✅ Validation RH")]:
    st.subheader("✅ Validation des demandes — Responsable RH")

    if not is_rh():
        st.warning("🔒 Accès réservé à la Responsable RH.")
    else:
        en_attente_df = df[df["etat"] == "En attente validation"] if not df.empty else pd.DataFrame()
        if en_attente_df.empty:
            st.success("✅ Aucune demande en attente de validation.")
        else:
            for _, row in en_attente_df.iterrows():
                with st.expander(f"📋 {row['id_demande']} — {row.get('chantier','?')} — {row.get('type_stage','?')} — soumis par {row.get('recruteur','?')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Responsable :** {row.get('responsable_demandeur','')}")
                        st.markdown(f"**Tuteur :** {row.get('nom_tuteur','')} ({row.get('fonction_tuteur','')})")
                        st.markdown(f"**Fonction stagiaire :** {row.get('fonction_stagiaire','')}")
                        st.markdown(f"**Type stage :** {row.get('type_stage','')}")
                        st.markdown(f"**Période :** {row.get('date_debut','')} → {row.get('date_fin','')}")
                    with c2:
                        st.markdown(f"**Formation souhaitée :** {row.get('formation_souhaitee','')}")
                        st.markdown(f"**Missions :** {row.get('missions','')}")
                        st.markdown(f"**Indemnisation :** {row.get('indemnisation_min','')} – {row.get('indemnisation_max','')} MAD")
                        # Afficher les pièces jointes si présentes
                        folder_url = str(row.get("drive_folder_url", ""))
                        if folder_url:
                            st.markdown("**Pièces jointes transmises :**")
                            try:
                                if "folders/" in folder_url:
                                    fid = folder_url.split('folders/')[1].split('?')[0]
                                else:
                                    fid = folder_url.rstrip('/').split('/')[-1]
                                files = list_folder_files(fid)
                                if files:
                                    for f in files:
                                        name = f.get('name')
                                        link = f.get('webViewLink')
                                        st.markdown(f"- [{name}]({link})")
                                else:
                                    st.markdown("- Aucune pièce jointe trouvée dans le dossier Drive.")
                            except Exception:
                                st.markdown("- Impossible de lister les pièces jointes.")

                    # Compteur stagiaires actifs dans ce chantier
                    chantier_cible = str(row.get("chantier", ""))
                    nb_actifs_chantier = 0
                    for _, r2 in df.iterrows():
                        if str(r2.get("chantier", "")).lower() != chantier_cible.lower():
                            continue
                        if str(r2.get("etat", "")) in ("Stage terminé", "Rejetée", "En attente validation"):
                            continue
                        try:
                            dfd = datetime.datetime.strptime(str(r2["date_debut"]), "%d/%m/%Y").date()
                            dff = datetime.datetime.strptime(str(r2["date_fin"]), "%d/%m/%Y").date()
                            if dfd <= aujourd_hui <= dff:
                                nb_actifs_chantier += 1
                        except Exception:
                            pass
                    st.info(f"📍 **{nb_actifs_chantier}** stagiaire(s) actuellement actif(s) sur ce chantier.")

                    col_v, col_r = st.columns(2)
                    with col_v:
                        if st.button("✅ Valider", key=f"valider_{row['id_demande']}"):
                            update_stagiaire_field(row["id_demande"], {
                                "etat": "Validée",
                                "date_validation_rh": datetime.date.today().strftime("%d/%m/%Y"),
                                "valideur_rh": st.session_state.get("current_user", ""),
                            })
                            st.success("Demande validée !")
                            refresh_data()
                            st.rerun()
                    with col_r:
                        motif = st.text_input("Motif de rejet (obligatoire)", key=f"motif_{row['id_demande']}")
                        if st.button("❌ Rejeter", key=f"rejeter_{row['id_demande']}"):
                            if not motif.strip():
                                st.error("Veuillez saisir un motif de rejet.")
                            else:
                                update_stagiaire_field(row["id_demande"], {
                                    "etat": "Rejetée",
                                    "motif_rejet": motif,
                                })
                                st.warning("Demande rejetée.")
                                refresh_data()
                                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — TRAITEMENT & SUIVI
# ══════════════════════════════════════════════════════════════════════════════
if not is_rh():
    with tabs[tabs_labels.index("📧 Traitement & Suivi")]:
        st.subheader("📧 Traitement des demandes validées")

        valides_df = df[df["etat"].isin(["Validée", "Mail envoyé", "Documents reçus"])] if not df.empty else pd.DataFrame()
        if valides_df.empty:
            st.info("Aucune demande validée en attente de traitement.")
        else:
            ids = valides_df["id_demande"].tolist()
            sel_id = st.selectbox("Sélectionner une demande", ids)
            row = valides_df[valides_df["id_demande"] == sel_id].iloc[0]

            st.markdown(f"**Chantier :** {row.get('chantier','')} | **Période :** {row.get('date_debut','')} → {row.get('date_fin','')} | **État :** `{row.get('etat','')}`")
            st.markdown("---")

            # ── Saisie info stagiaire ───────────────────────────────────────
            st.markdown("#### 1. Informations du stagiaire")
            with st.form("form_info_stagiaire"):
                nom_stag = st.text_input("Nom & Prénom du stagiaire", value=str(row.get("nom_stagiaire", "")))
                email_stag = st.text_input("Email du stagiaire", value=str(row.get("email_stagiaire", "")))
                if st.form_submit_button("💾 Enregistrer les informations stagiaire"):
                    update_stagiaire_field(sel_id, {"nom_stagiaire": nom_stag, "email_stagiaire": email_stag})
                    st.success("Informations sauvegardées.")
                    refresh_data()

            st.markdown("---")
            # ── Canevas mail initiation ─────────────────────────────────────
            st.markdown("#### 2. Mail d'invitation au stagiaire")
            nom_s = str(row.get("nom_stagiaire", "XXXXXXXXXX")) or "XXXXXXXXXX"
            chantier_s = str(row.get("chantier", "XXXX")) or "XXXX"
            dd = str(row.get("date_debut", "XX/XX/XXXX"))
            df_ = str(row.get("date_fin", "XX/XX/XXXX"))
            resp_mail = str(row.get("responsable_demandeur", ""))

            mail_initiation = f"""**Objet : VOTRE STAGE AU SEIN DE TGCC**

Bonjour,

Suite à la validation de la DRH de la demande de stage de M. {nom_s} au sein du chantier {chantier_s} pour la période du {dd} au {df_}, merci de fournir les documents ci-joints.

*Fiche de renseignement (PJ) (bien remplie et signée par le stagiaire) dont photo récente ;
*CIN recto/verso ;
*Attestation d'assurance couvrant la période totale de votre stage ;
*Clause de discrétion légalisée ;
*Demande de stage légalisée (si stage non conventionné) ;

Merci de fournir les éléments suivants à la direction des ressources humaines.

L'attestation de stage est délivrée une fois le rapport de stage est reçu par la DRH. Nous restons à votre disposition pour toute information complémentaire.

Nous vous informons que TGCC collecte et traite vos données personnelles en vue d'assurer la gestion administrative de votre dossier de stage.
Ce traitement a fait l'objet d'une demande d'autorisation auprès de la CNDP sous le numéro : A-RH-1175/2025.
Vous pouvez vous adresser à la Direction des Ressources Humaines pour exercer vos droits d'accès, de rectification et d'opposition conformément aux dispositions de la loi 09-08. info.rh@tgcc.ma

Nous gardons contact et vous souhaitons une belle carrière.
Bienvenue au sein de TGCC"""

            st.text_area("📋 Canevas à copier (mail stagiaire + responsable en CC)", value=mail_initiation, height=320)
            st.caption(f"📎 Pièces jointes à ajouter : FR 20 (Fiche renseignement), Clause de discrétion, FI 04 (Liste documents) — disponibles dans le dossier **Forms/**")

            if str(row.get("etat", "")) == "Validée":
                if st.button("📤 Marquer le mail comme envoyé", key="mail_envoye"):
                    update_stagiaire_field(sel_id, {"etat": "Mail envoyé"})
                    st.success("État mis à jour : Mail envoyé.")
                    refresh_data()
                    st.rerun()

            st.markdown("---")
            # ── Upload documents reçus + Drive ─────────────────────────────
            st.markdown("#### 3. Upload des documents reçus du stagiaire")
            docs_uploader = st.file_uploader(
                "Uploader les documents (PDF, images)", type=["pdf", "jpg", "jpeg", "png"],
                accept_multiple_files=True, key="upload_docs_stag"
            )
            nom_stag_drive = str(row.get("nom_stagiaire", sel_id)).strip() or sel_id
            if docs_uploader and st.button("☁️ Uploader vers Google Drive", key="upload_drive"):
                with st.spinner("Upload en cours..."):
                    files_to_upload = []
                    for f_up in docs_uploader:
                        fb = f_up.read()
                        mime = "application/pdf" if f_up.name.endswith(".pdf") else "image/jpeg"
                        files_to_upload.append((fb, f_up.name, mime))
                    if files_to_upload:
                        folder_id, links = upload_files_to_folder(files_to_upload, nom_stag_drive)
                        if folder_id:
                            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
                            update_stagiaire_field(sel_id, {
                                "etat": "Documents reçus",
                                "drive_folder_url": folder_url,
                            })
                            st.success(f"✅ {len(links)} fichier(s) uploadé(s) sur Drive.")
                        refresh_data()

            st.markdown("---")
            # ── Dossier conforme → mail bienvenue ──────────────────────────
            st.markdown("#### 4. Dossier conforme")
            if str(row.get("etat", "")) in ("Documents reçus", "Mail envoyé"):
                if st.button("✅ Marquer le dossier comme conforme", key="dossier_conforme", type="primary"):
                    update_stagiaire_field(sel_id, {"etat": "Dossier conforme"})
                    st.success("Dossier marqué conforme.")
                    refresh_data()
                    st.rerun()

            if str(row.get("etat", "")) in ("Dossier conforme", "Stage en cours"):
                mail_bienvenue = f"""**Objet : Intégration du stagiaire au sein de TGCC**

Bonjour,

Nous vous informons que votre demande de stage pour la période du {dd} au {df_} a été acceptée par la Direction des Ressources Humaines.

Nous vous souhaitons la bienvenue parmi notre équipe, ainsi merci de bien vouloir vous présenter au chantier {chantier_s}.

Nous gardons contact et vous souhaitons une belle carrière.

— L'Équipe RH"""
                st.markdown("**📋 Canevas mail de bienvenue (à copier) :**")
                st.text_area("Mail bienvenue stagiaire", value=mail_bienvenue, height=220)

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — ALERTES J-7
# ══════════════════════════════════════════════════════════════════════════════
if not is_rh():
    with tabs[tabs_labels.index("🔔 Alertes J-7")]:
        st.subheader("🔔 Alertes fins de stage (J-7)")
    aujourd_hui = datetime.date.today()
    alertes_list = []
    if not df.empty:
        for _, row in df.iterrows():
            if str(row.get("etat", "")) in ("Stage terminé", "Rejetée"):
                continue
            try:
                dff = datetime.datetime.strptime(str(row["date_fin"]), "%d/%m/%Y").date()
                delta = (dff - aujourd_hui).days
                if 0 <= delta <= 7:
                    alertes_list.append((delta, row))
            except Exception:
                pass

    if not alertes_list:
        st.success("✅ Aucun stage n'arrive à échéance dans les 7 prochains jours.")
    else:
        alertes_list.sort(key=lambda x: x[0])
        for delta, row in alertes_list:
            libelle = f"**{row.get('nom_stagiaire','?')}** — {row.get('chantier','?')} — Fin dans **{delta}j** ({row.get('date_fin','?')})"
            with st.expander(libelle):
                nom_s = str(row.get("nom_stagiaire", "xxx"))
                dd = str(row.get("date_debut", ""))
                dff_s = str(row.get("date_fin", ""))
                tuteur = str(row.get("nom_tuteur", ""))

                mail_tuteur = f"""**Objet : Gestion des stagiaires au sein de TGCC**

Bonjour,

Nous vous informons que le stage de {nom_s} dont vous étiez son tuteur, prendra fin le {dff_s}.

Merci de bien compléter son dossier par les éléments suivants :
*Le formulaire d'appréciation stagiaire ;

Disponible via ce drive : https://drive.google.com/drive/u/3/folders/1FaoQw6aRp76M9U1VAB8Y6Hk1zaQ4VBjK

Cordialement"""

                st.text_area(f"📋 Canevas mail tuteur ({tuteur})", value=mail_tuteur, height=220, key=f"mail_tuteur_{row['id_demande']}")

                if st.button(f"✅ Alerte traitée pour {nom_s}", key=f"alerte_traitee_{row['id_demande']}"):
                    update_stagiaire_field(row["id_demande"], {"etat": "Stage terminé"})
                    st.success("Stage marqué comme terminé.")
                    refresh_data()
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 6 — ATTESTATION DE STAGE
# ══════════════════════════════════════════════════════════════════════════════
if not is_rh():
    with tabs[tabs_labels.index("📄 Attestation de Stage")]:
        st.subheader("📄 Attestation de stage")

        # ── Recruteur : demander une attestation ───────────────────────────────
        st.markdown("#### Demander une attestation pour un stagiaire")
        eligibles_attest = df[df["etat"].isin(["Dossier conforme", "Stage en cours", "Stage terminé"])] if not df.empty else pd.DataFrame()
        if eligibles_attest.empty:
            st.info("Aucun stagiaire éligible à une attestation (dossier conforme / stage en cours / terminé).")
        else:
            sel_attest = st.selectbox(
                "Sélectionner le stagiaire",
                eligibles_attest["id_demande"].tolist(),
                format_func=lambda x: f"{x} — {eligibles_attest[eligibles_attest['id_demande']==x]['nom_stagiaire'].values[0]}"
            )
            row_a = eligibles_attest[eligibles_attest["id_demande"] == sel_attest].iloc[0]
            st.markdown(f"**Stagiaire :** {row_a.get('nom_stagiaire','')} | **Chantier :** {row_a.get('chantier','')} | **Période :** {row_a.get('date_debut','')} → {row_a.get('date_fin','')}")

            # Générer le modèle (aperçu sans signature)
            if st.button("📄 Générer le modèle d'attestation", type="secondary"):
                pdf_bytes = generer_attestation(
                    nom_stagiaire=str(row_a.get("nom_stagiaire", "")),
                    chantier=str(row_a.get("chantier", "")),
                    date_debut=str(row_a.get("date_debut", "")),
                    date_fin=str(row_a.get("date_fin", "")),
                    type_stage=str(row_a.get("type_stage", "")),
                )
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Télécharger l'attestation (sans signature)",
                        data=pdf_bytes,
                        file_name=f"Attestation_{row_a.get('nom_stagiaire','stagiaire').replace(' ','_')}.pdf",
                        mime="application/pdf",
                    )
                    # Marquer comme "Attestation demandée" pour la RH
                    update_stagiaire_field(sel_attest, {"attestation_generee": "Demandée"})
                    st.info("📨 L'attestation est en attente de signature par la Responsable RH (onglet Validation RH).")

    # ── RH : signer et finaliser ───────────────────────────────────────────
    if is_rh():
        st.markdown("#### Attestions en attente de signature")
        a_signer = df[df["attestation_generee"] == "Demandée"] if not df.empty else pd.DataFrame()
        if a_signer.empty:
            st.info("Aucune attestation en attente de signature.")
        else:
            for _, row_s in a_signer.iterrows():
                with st.expander(f"📋 {row_s['id_demande']} — {row_s.get('nom_stagiaire','')} — {row_s.get('chantier','')}"):
                    st.markdown(f"**Période :** {row_s.get('date_debut','')} → {row_s.get('date_fin','')}")
                    st.markdown("**Signature (image) :**")
                    sig_file = st.file_uploader(
                        "Uploader l'image de signature (PNG/JPG)",
                        type=["png", "jpg", "jpeg"],
                        key=f"sig_{row_s['id_demande']}"
                    )
                    sig_bytes = sig_file.read() if sig_file else None
                    if st.button("✅ Valider et générer l'attestation signée", key=f"gen_attest_{row_s['id_demande']}"):
                        pdf_bytes = generer_attestation(
                            nom_stagiaire=str(row_s.get("nom_stagiaire", "")),
                            chantier=str(row_s.get("chantier", "")),
                            date_debut=str(row_s.get("date_debut", "")),
                            date_fin=str(row_s.get("date_fin", "")),
                            type_stage=str(row_s.get("type_stage", "")),
                            signature_img_bytes=sig_bytes,
                        )
                        if pdf_bytes:
                            update_stagiaire_field(row_s["id_demande"], {"attestation_generee": "Oui"})
                            st.success("✅ Attestation générée et signée.")
                            st.download_button(
                                "⬇️ Télécharger l'attestation signée",
                                data=pdf_bytes,
                                file_name=f"Attestation_{row_s.get('nom_stagiaire','stagiaire').replace(' ','_')}_signé.pdf",
                                mime="application/pdf",
                                key=f"dl_attest_{row_s['id_demande']}"
                            )

