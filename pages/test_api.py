# utils.py
# -*- coding: utf-8 -*-
import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
import io
import random

# --- IMPORTS CONDITIONNELS (CORRIGÉS) ---
# Importations standard
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# PDF (ReportLab)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    class Dummy:  # Classes factices pour éviter les erreurs Pylance/NameError si Reportlab manque
        def __init__(self, *args, **kwargs): pass
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, getSampleStyleSheet, colors = [Dummy] * 7
    A4 = None

# Word (Python-docx)
try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# Google Sheets & IA
try:
    import gspread
    from google.oauth2 import service_account
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_CLIENT_AVAILABLE = True
except ImportError:
    OPENAI_CLIENT_AVAILABLE = False

# -------------------- CONFIGURATION GOOGLE SHEETS pour les Briefs --------------------
BRIEFS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DDw-aypZ9zDwAUuL6-p4TsKBIwV3pua8O3ACw_K-bHs/edit"
BRIEFS_WORKSHEET_NAME = "Briefs"

# Entêtes de colonnes (doivent correspondre EXACTEMENT à la Ligne 1 de votre Google Sheet)
BRIEFS_HEADERS = [
    "BRIEF_NAME", "POSTE_INTITULE", "MANAGER_NOM", "RECRUTEUR", "AFFECTATION_TYPE", 
    "AFFECTATION_NOM", "DATE_BRIEF", "RAISON_OUVERTURE", "IMPACT_STRATEGIQUE", 
    "TACHES_PRINCIPALES", "MUST_HAVE_EXP", "MUST_HAVE_DIP", 
    "MUST_HAVE_COMPETENCES", "MUST_HAVE_SOFTSKILLS", "NICE_TO_HAVE_EXP", 
    "NICE_TO_HAVE_DIP", "NICE_TO_HAVE_COMPETENCES", "RATTACHEMENT", "BUDGET", 
    "ENTREPRISES_PROFIL", "SYNONYMES_POSTE", "CANAUX_PROFIL", 
    "LIEN_PROFIL_1", "LIEN_PROFIL_2", "LIEN_PROFIL_3",
    "COMMENTAIRES", "NOTES_LIBRES", "CRITERES_EXCLUSION", 
    "PROCESSUS_EVALUATION", "MANAGER_NOTES", 
    "MANAGER_COMMENTS_JSON",
    "KSA_MATRIX_JSON", "DATE_MAJ"
]

# -------------------- FONCTIONS DE GESTION GOOGLE SHEETS (CORRIGÉES POUR SECRETS GCP_) --------------------

@st.cache_resource
def get_briefs_gsheet_client():
    """Initialise et retourne le client gspread en utilisant les secrets GCP_..."""
    if not GSPREAD_AVAILABLE:
        return None
    try:
        service_account_info = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n').strip(), 
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets["GCP_CLIENT_ID"],
            "auth_uri": st.secrets["GCP_AUTH_URI"],
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_CERT_URL"],
            "client_x509_cert_url": st.secrets["GCP_CLIENT_CERT_URL"]
        }
        
        gc = gspread.service_account_from_dict(service_account_info)
        spreadsheet = gc.open_by_url(BRIEFS_SHEET_URL)
        worksheet = spreadsheet.worksheet(BRIEFS_WORKSHEET_NAME)
        return worksheet
    except KeyError as e:
        st.error(f"❌ Clé de secret manquante pour Google Sheets: {e}. Vérifiez la configuration des secrets GCP_...")
        return None
    except Exception as e:
        st.error(f"❌ Erreur de connexion/ouverture de Google Sheets: {e}")
        return None

def save_brief_to_gsheet(brief_name, brief_data):
    """Sauvegarde un brief dans Google Sheets (met à jour si existe, insère si nouveau)."""
    worksheet = get_briefs_gsheet_client()
    if worksheet is None:
        return False
    
    try:
        row_data = []
        ksa_df = brief_data.get("ksa_matrix")
        
        for header in BRIEFS_HEADERS:
            value = brief_data.get(header, "")
            
            if header == "KSA_MATRIX_JSON":
                if isinstance(ksa_df, pd.DataFrame):
                    value = ksa_df.to_json(orient='records')
                else:
                    value = ""
            
            elif header == "DATE_MAJ":
                value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            elif header in brief_data:
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                elif isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d")
                else:
                    value = str(value)
            else:
                value = ""
                
            row_data.append(value)
        
        cell = worksheet.find(brief_name, in_column=1, case_sensitive=True)
        
        LAST_COL_LETTER = col_to_letter(len(BRIEFS_HEADERS))
        
        if cell:
            range_to_update = f'A{cell.row}:{LAST_COL_LETTER}{cell.row}' 
            worksheet.update(range_to_update, [row_data])
            st.toast(f"✅ Brief '{brief_name}' mis à jour dans Google Sheets.", icon='☁️')
        else:
            worksheet.append_row(row_data)
            st.toast(f"✅ Brief '{brief_name}' enregistré dans Google Sheets.", icon='☁️')
            
        return True

    except Exception as e:
        st.error(f"❌ ÉCHEC CRITIQUE: La sauvegarde Google Sheets a échoué pour '{brief_name}'. API Error: {e}")
        return False

# -------------------- Directory for Briefs (Optionnel, peut être ignoré) --------------------
BRIEFS_DIR = "briefs"

def ensure_briefs_directory():
    """Ensure the briefs directory exists."""
    if not os.path.exists(BRIEFS_DIR):
        os.makedirs(BRIEFS_DIR)

# -------------------- Persistance (JSON locale - Désactivée si non nécessaire) --------------------
# def save_briefs():
#     """Save each brief in session_state.saved_briefs to a separate JSON file."""
#     try:
#         ensure_briefs_directory()
#         serializable_briefs = {
#             name: {
#                 key: value.to_dict() if isinstance(value, pd.DataFrame) else value
#                 for key, value in data.items()
#             }
#             for name, data in st.session_state.saved_briefs.items()
#         }
#         for brief_name, brief_data in serializable_briefs.items():
#             file_path = os.path.join(BRIEFS_DIR, f"{brief_name}.json")
#             with open(file_path, "w", encoding="utf-8") as f:
#                 json.dump(brief_data, f, indent=4, ensure_ascii=False)
#     except Exception as e:
#         st.error(f"Erreur lors de la sauvegarde locale des briefs: {e}")

def load_briefs():
    """Load all briefs exclusively from Google Sheets."""
    try:
        briefs = {}
        worksheet = get_briefs_gsheet_client()
        if worksheet:
            records = worksheet.get_all_records()
            for record in records:
                brief_name = record.get("BRIEF_NAME")
                if brief_name:
                    briefs[brief_name] = record
                    if "KSA_MATRIX_JSON" in record and record["KSA_MATRIX_JSON"]:
                        try:
                            record["ksa_matrix"] = pd.DataFrame.from_records(json.loads(record["KSA_MATRIX_JSON"]))
                        except json.JSONDecodeError:
                            record["ksa_matrix"] = pd.DataFrame()  # Fallback si JSON invalide
        return briefs
    except Exception as e:
        st.warning(f"Erreur lors du chargement des briefs depuis Google Sheets : {e}")
        return {}

# -------------------- Exportation PDF --------------------
def export_brief_pdf():
    """Exporte un brief au format PDF."""
    if not PDF_AVAILABLE or not st.session_state.current_brief_name:
        return None
    
    brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("📋 Brief Recrutement", styles['Heading1']))
    story.append(Spacer(1, 12))

    # Section 1: Identité du poste
    story.append(Paragraph("1. Identité du poste", styles['Heading2']))
    story.append(Paragraph(f"Intitulé: {brief_data.get('poste_intitule', '')}", styles['Normal']))
    story.append(Paragraph(f"Service: {brief_data.get('affectation_nom', '')}", styles['Normal']))
    story.append(Paragraph(f"Niveau Hiérarchique: {brief_data.get('niveau_hierarchique', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Type de Contrat: {brief_data.get('affectation_type', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"Localisation: {brief_data.get('rattachement', '')}", styles['Normal']))
    story.append(Paragraph(f"Budget Salaire: {brief_data.get('budget', '')}", styles['Normal']))
    story.append(Paragraph(f"Date Prise de Poste: {brief_data.get('date_brief', '')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Section 2: Contexte & Enjeux
    story.append(Paragraph("2. Contexte & Enjeux", styles['Heading2']))
    context_text = f"{brief_data.get('raison_ouverture', '')} {brief_data.get('impact_strategique', '')}"
    story.append(Paragraph(context_text, styles['Normal']))
    story.append(Spacer(1, 12))

    # Section 3: Exigences
    story.append(Paragraph("3. Exigences", styles['Heading2']))
    story.append(Paragraph(f"Expérience: {brief_data.get('must_have_experience', '')}", styles['Normal']))
    story.append(Paragraph(f"Diplômes: {brief_data.get('must_have_diplomes', '')}", styles['Normal']))
    story.append(Paragraph(f"Compétences: {brief_data.get('must_have_competences', '')}", styles['Normal']))
    story.append(Paragraph(f"Soft Skills: {brief_data.get('must_have_softskills', '')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Section 4: Matrice KSA
    story.append(Paragraph("4. Matrice KSA", styles['Heading2']))
    ksa_matrix = brief_data.get("ksa_matrix")
    if isinstance(ksa_matrix, pd.DataFrame) and not ksa_matrix.empty:
        for _, row in ksa_matrix.iterrows():
            ksa_text = f"- {row['Rubrique']}: {row['Critère']} (Question: {row['Question pour l\'entretien']}, Éval: {row['Évaluation (1-5)']})"
            story.append(Paragraph(ksa_text, styles['Normal']))
    else:
        story.append(Paragraph("Aucune donnée KSA disponible.", styles['Normal']))
    story.append(Spacer(1, 12))

    # Section 5: Stratégie Recrutement
    story.append(Paragraph("5. Stratégie Recrutement", styles['Heading2']))
    story.append(Paragraph(f"Canaux: {brief_data.get('canaux_profil', '')}", styles['Normal']))
    story.append(Paragraph(f"Critères d'exclusion: {brief_data.get('criteres_exclusion', '')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Section 6: Notes du Manager
    story.append(Paragraph("6. Notes du Manager", styles['Heading2']))
    story.append(Paragraph(brief_data.get("manager_notes", ""), styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------- Exportation Word --------------------
def export_brief_word():
    """Exporte un brief au format Word."""
    if not WORD_AVAILABLE or not st.session_state.current_brief_name:
        return None
    
    brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
    doc = Document()
    doc.add_heading("📋 Brief Recrutement", 0)

    # Section 1: Identité du poste
    doc.add_heading("1. Identité du poste", level=1)
    doc.add_paragraph(f"Intitulé: {brief_data.get('poste_intitule', '')}")
    doc.add_paragraph(f"Service: {brief_data.get('affectation_nom', '')}")
    doc.add_paragraph(f"Niveau Hiérarchique: {brief_data.get('niveau_hierarchique', 'N/A')}")
    doc.add_paragraph(f"Type de Contrat: {brief_data.get('affectation_type', 'N/A')}")
    doc.add_paragraph(f"Localisation: {brief_data.get('rattachement', '')}")
    doc.add_paragraph(f"Budget Salaire: {brief_data.get('budget', '')}")
    doc.add_paragraph(f"Date Prise de Poste: {brief_data.get('date_brief', '')}")

    # Section 2: Contexte & Enjeux
    doc.add_heading("2. Contexte & Enjeux", level=1)
    doc.add_paragraph(f"{brief_data.get('raison_ouverture', '')} {brief_data.get('impact_strategique', '')}")

    # Section 3: Exigences
    doc.add_heading("3. Exigences", level=1)
    doc.add_paragraph(f"Expérience: {brief_data.get('must_have_experience', '')}")
    doc.add_paragraph(f"Diplômes: {brief_data.get('must_have_diplomes', '')}")
    doc.add_paragraph(f"Compétences: {brief_data.get('must_have_competences', '')}")
    doc.add_paragraph(f"Soft Skills: {brief_data.get('must_have_softskills', '')}")

    # Section 4: Matrice KSA
    doc.add_heading("4. Matrice KSA", level=1)
    ksa_matrix = brief_data.get("ksa_matrix")
    if isinstance(ksa_matrix, pd.DataFrame) and not ksa_matrix.empty:
        for _, row in ksa_matrix.iterrows():
            doc.add_paragraph(f"- {row['Rubrique']}: {row['Critère']} (Question: {row['Question pour l\'entretien']}, Éval: {row['Évaluation (1-5)']})")
    else:
        doc.add_paragraph("Aucune donnée KSA disponible.")

    # Section 5: Stratégie Recrutement
    doc.add_heading("5. Stratégie Recrutement", level=1)
    doc.add_paragraph(f"Canaux: {brief_data.get('canaux_profil', '')}")
    doc.add_paragraph(f"Critères d'exclusion: {brief_data.get('criteres_exclusion', '')}")

    # Section 6: Notes du Manager
    doc.add_heading("6. Notes du Manager", level=1)
    doc.add_paragraph(brief_data.get("manager_notes", ""))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------- Génération de question IA avec DeepSeek --------------------
def generate_ai_question(prompt, concise=False):
    """Génère une question d'entretien et une réponse exemple via l'API DeepSeek."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Le module 'openai' n'est pas installé. Veuillez l'installer avec 'pip install openai'.")

    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("Clé API DeepSeek non trouvée dans st.secrets")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )

    max_tokens = 700

    context = "recruitment for a KSA (Knowledge, Skills, Abilities) matrix"
    question_type = "technical"
    skill = prompt
    role = "candidate"
    
    if "une question" in prompt and "pour évaluer" in prompt and "par" in prompt:
        parts = prompt.split("une question")
        if len(parts) > 1:
            question_type_part = parts[1].split("pour")[0].strip().lower()
            if "générale" in question_type_part:
                question_type = "general"
            elif "comportementale" in question_type_part:
                question_type = "behavioral"
            elif "situationnelle" in question_type_part:
                question_type = "situational"
            elif "technique" in question_type_part:
                question_type = "technical"
            
            skill_part = prompt.split("évaluer")
            if len(skill_part) > 1:
                skill = skill_part[1].split("par")[0].strip()
            
            role_part = prompt.split("par")
            if len(role_part) > 1:
                role = role_part[1].strip()

    if question_type == "behavioral":
        context += ", using the STAR method (Situation, Task, Action, Result)"
    elif question_type == "situational":
        context += ", presenting a hypothetical scenario"
    elif question_type == "general":
        context += ", focusing on overall experience"

    full_prompt = (
        f"Dans le contexte de {context}, génère une {question_type} question d'entretien pour évaluer : {skill} by a {role}. "
        f"Adapte la question au domaine spécifié (ex. recrutement ou BTP) si applicable. "
        f"Retourne une réponse exemple pertinente. "
        f"Assure-toi que la réponse corresponde au type de question (ex. STAR pour comportementale, scénario pour situationnelle). "
        f"Utilise uniquement ce format :\n"
        f"Question: [votre question]\n"
        f"Réponse: [exemple de réponse]"
    )
    
    if concise:
        full_prompt = (
            f"Génère une question d'entretien et une réponse très concise et directe pour évaluer le critère : '{skill}'. "
            f"La question doit être {question_type} et la réponse ne doit pas dépasser 50 mots. "
            f"Format : 'Question: [votre question]\nRéponse: [réponse concise]'"
        )
        max_tokens = 150

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.7,
        max_tokens=max_tokens
    )

    result = response.choices[0].message.content.strip()
    if result.startswith("- Question:"):
        result = result.replace("- Question:", "Question:", 1)
    if "Réponse: Réponse:" in result:
        result = result.replace("Réponse: Réponse:", "Réponse:")
    
    return result

# -------------------- Test de connexion DeepSeek --------------------
def test_deepseek_connection():
    """Teste la connexion à l'API DeepSeek."""
    try:
        from openai import OpenAI
        api_key = st.secrets.get("DEEPSEEK_API_KEY")
        if not api_key:
            st.error("Clé API DeepSeek non trouvée dans st.secrets")
            return False
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Test de connexion"}],
            max_tokens=1
        )
        st.success("✅ Connexion à DeepSeek réussie !")
        return True
    except Exception as e:
        st.error(f"❌ Erreur de connexion à DeepSeek : {e}")
        return False

# -------------------- Génération de contenu avec DeepSeek --------------------
def deepseek_generate(prompt, max_tokens=2000, temperature=0.7):
    """Génère du contenu via l'API DeepSeek."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Le module 'openai' n'est pas installé. Veuillez l'installer avec 'pip install openai'.")

    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("Clé API DeepSeek non trouvée dans st.secrets")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content

# -------------------- Exemples contextuels --------------------
def get_example_for_field(section_title, field_title):
    """Retourne un exemple contextuel pour un champ donné, adapté au BTP."""
    examples = {
        "Contexte du poste": {
            "Raison de l'ouverture": "Remplacement d’un départ en retraite sur un chantier majeur",
            "Impact stratégique": "Assurer la gestion des projets BTP stratégiques de l’entreprise",
            "Tâches principales": "Gestion de chantier complexe, coordination d’équipe sur site, suivi des normes de sécurité BTP",
        },
        "Must-have (Indispensables)": {
            "Expérience": "5 ans d’expérience dans le secteur BTP sur des chantiers similaires",
            "Connaissances / Diplômes / Certifications": "Diplôme en génie civil, certification CACES pour engins de chantier",
            "Compétences / Outils": "Maîtrise d'AutoCAD et de la gestion de projet BTP",
            "Soft skills / aptitudes comportementales": "Leadership sur terrain et rigueur en sécurité",
        },
        "Nice-to-have (Atouts)": {
            "Expérience additionnelle": "Projets internationaux de BTP ou multi-sites",
            "Diplômes / Certifications valorisantes": "Certification LEED pour le BTP durable",
            "Compétences complémentaires": "Connaissance en BIM pour modélisation de chantiers",
        },
        "Conditions et contraintes": {
            "Localisation": "Chantier principal à Paris avec 20% de télétravail",
            "Budget recrutement": "Salaire entre 40k et 50k€ + primes",
        },
        "Sourcing et marché": {
            "Entreprises où trouver ce profil": "Vinci, Bouygues, Eiffage",
            "Synonymes / intitulés proches": "Conducteur de Travaux, Ingénieur Chantier",
            "Canaux à utiliser": "LinkedIn pour profils BTP, jobboards comme Batiweb",
        },
        "Profils pertinents": {
            "Lien profil 1": "https://linkedin.com/in/exemple-btp",
            "Lien profil 2": "https://linkedin.com/in/exemple-btp-2",
            "Lien profil 3": "https://linkedin.com/in/exemple-btp-3",
        },
        "Notes libres": {
            "Points à discuter ou à clarifier avec le manager": "Clarifier les délais du projet",
            "Case libre": "Note sur les priorités du chantier",
        }
    }
    return examples.get(section_title, {}).get(field_title, "Exemple non disponible")

# -------------------- Génération de nom de brief automatique --------------------
def generate_automatic_brief_name():
    """
    Generate a unique brief name based on the position title, manager name, and date.
    Uses session_state values if available, otherwise defaults to a generic name.
    """
    poste = st.session_state.get("poste_intitule", "Poste")
    manager = st.session_state.get("manager_nom", "Manager")
    date_str = st.session_state.get("date_brief", datetime.today()).strftime("%Y%m%d")
    
    base_name = f"{poste}_{manager}_{date_str}"
    
    saved_briefs = st.session_state.get("saved_briefs", {})
    counter = 1
    brief_name = base_name
    while brief_name in saved_briefs:
        brief_name = f"{base_name}_{counter}"
        counter += 1
    
    return brief_name

# -------------------- Conversion de colonne --------------------
def col_to_letter(col_index):
    """Convertit l'index de colonne (base 1) en lettre Excel (e.g., 1 -> A, 27 -> AA)"""
    letter = ''
    while col_index > 0:
        col_index, remainder = divmod(col_index - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter