# utils.py
# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io
import json
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

# -------------------- Disponibilité PDF & Word --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# -------------------- Initialisation Session --------------------
def init_session_state():
    """Initialise l'état de la session Streamlit avec des valeurs par défaut."""
    defaults = {
        "poste_intitule": "",
        "service": "",
        "niveau_hierarchique": "",
        "type_contrat": "",
        "localisation": "",
        "budget_salaire": "",
        "date_prise_poste": "",
        "recruteur": "",
        "manager_nom": "",
        "affectation_type": "",
        "affectation_nom": "",
        "raison_ouverture": "",
        "impact_strategique": "",
        "rattachement": "",
        "taches_principales": "",
        "must_have_experience": "",
        "must_have_diplomes": "",
        "must_have_competences": "",
        "must_have_softskills": "",
        "nice_to_have_experience": "",
        "nice_to_have_diplomes": "",
        "nice_to_have_competences": "",
        "entreprises_profil": "",
        "synonymes_poste": "",
        "canaux_profil": "",
        "commentaires": "",
        "notes_libres": "",
        "profil_links": ["", "", ""],
        "ksa_data": {}, # Ancienne structure
        "ksa_matrix": pd.DataFrame(), # Nouvelle structure, plus robuste
        "saved_briefs": load_briefs(),
        "current_brief_name": None,
        "filtered_briefs": {},
        "show_filtered_results": False,
        "brief_data": {},
        "comment_libre": "",
        "brief_phase": "Gestion",
        "saved_job_descriptions": {},
        "temp_extracted_data": None,
        "temp_job_title": "",
        "canaux_prioritaires": [],
        "criteres_exclusion": "",
        "processus_evaluation": "",
        "manager_comments": {},
        "manager_notes": "",
        "job_library": load_library(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistance --------------------
def save_briefs():
    """Sauvegarde les briefs dans un fichier pickle."""
    try:
        # Convertir le DataFrame en une structure sérialisable
        serializable_briefs = {
            name: {
                key: value.to_dict() if isinstance(value, pd.DataFrame) else value
                for key, value in data.items()
            }
            for name, data in st.session_state.saved_briefs.items()
        }
        with open("briefs.json", "w") as f:
            json.dump(serializable_briefs, f, indent=4)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des briefs: {e}")

def load_briefs():
    """Charge les briefs depuis un fichier pickle."""
    try:
        with open("briefs.json", "r") as f:
            data = json.load(f)
            # Reconvertir les dictionnaires en DataFrames
            loaded_briefs = {
                name: {
                    key: pd.DataFrame.from_dict(value) if key == "ksa_matrix" else value
                    for key, value in brief_data.items()
                }
                for name, brief_data in data.items()
            }
            return loaded_briefs
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_job_descriptions():
    """Sauvegarde les fiches de poste dans job_descriptions.json."""
    try:
        with open("job_descriptions.json", "w") as f:
            json.dump(st.session_state.saved_job_descriptions, f, indent=4)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des fiches de poste: {e}")

def load_job_descriptions():
    """Charge les fiches de poste depuis job_descriptions.json."""
    try:
        with open("job_descriptions.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# -------------------- Conseils IA --------------------
def generate_checklist_advice(category, item):
    """Génère un conseil IA pour les champs du brief."""
    if "contexte" in category.lower():
        if "Raison" in item:
            return "- Clarifier si remplacement, création ou évolution interne.\n- Identifier le niveau d'urgence.\n- Relier au contexte business."
        elif "Mission" in item or "impact" in item:
            return "- Détailler la valeur ajoutée stratégique du poste.\n- Relier les missions aux objectifs de l’entreprise."
        elif "Tâches" in item:
            return "- Lister les tâches principales avec des verbes d'action concrets.\n- Inclure les responsabilités clés et les livrables attendus."
    elif "must-have" in category.lower() or "nice-to-have" in category.lower():
        if "Expérience" in item:
            return "- Spécifier le nombre d'années d'expérience requis et le secteur d'activité ciblé.\n- Mentionner les types de projets ou de missions spécifiques."
        elif "Diplômes" in item or "Connaissances" in item:
            return "- Indiquer les diplômes, certifications ou formations indispensables.\n- Préciser les connaissances techniques ou réglementaires nécessaires."
        elif "Compétences" in item or "Outils" in item:
            return "- Suggérer des compétences techniques (hard skills) et des outils à maîtriser.\n- Exemple : 'Maîtrise de Python', 'Expertise en gestion de projet Agile'."
        elif "Soft skills" in item:
            return "- Suggérer des aptitudes comportementales clés.\n- Exemple : 'Leadership', 'Communication', 'Rigueur', 'Autonomie'."
    elif "sourcing" in category.lower():
        if "Entreprises" in item:
            return "- Suggérer des entreprises similaires ou concurrents où trouver des profils.\n- Exemples : 'Entreprises du secteur de la construction', 'Startups technologiques'."
        elif "Synonymes" in item:
            return "- Suggérer des titres de poste alternatifs pour la recherche.\n- Exemples : 'Chef de projet', 'Project Manager', 'Responsable de programme'."
        elif "Canaux" in item:
            return "- Proposer des canaux de sourcing pertinents.\n- Exemples : 'LinkedIn', 'Jobboards spécialisés', 'Cooptation', 'Chasse de tête'."
    elif "conditions" in category.lower():
        if "Localisation" in item or "Rattachement" in item:
            return "- Préciser l'emplacement exact du poste, la possibilité de télétravail et la fréquence des déplacements."
        elif "Budget" in item:
            return "- Indiquer une fourchette de salaire réaliste et les avantages ou primes éventuelles."
    elif "profils" in category.lower():
        return "- Ajouter des URLs de profils LinkedIn ou autres sources pertinentes."
    elif "notes" in category.lower():
        if "Points à discuter" in item or "Commentaires" in item:
            return "- Proposer des questions pour clarifier le brief avec le manager.\n- Exemple : 'Priorité des compétences', 'Culture d'équipe'."
        elif "Case libre" in item or "Notes libres" in item:
            return "- Suggérer des points additionnels à considérer.\n- Exemple : 'Points de motivation spécifiques pour ce poste'."
    return f"- Fournir des détails pratiques pour {item}\n- Exemple concret\n- Piège à éviter"

# -------------------- Filtre --------------------
def filter_briefs(briefs, month, recruteur, brief_type, manager, affectation, nom_affectation):
    """Filtre les briefs selon les critères donnés."""
    filtered = {}
    for name, data in briefs.items():
        match = True
        try:
            if month and month != "" and datetime.strptime(data.get("date_brief", datetime.today), "%Y-%m-%d").strftime("%m") != month:
                match = False
            if recruteur and recruteur != "" and recruteur.lower() not in data.get("recruteur", "").lower():
                match = False
            if brief_type and brief_type != "" and data.get("brief_type", "") != brief_type:
                match = False
            if manager and manager != "" and manager.lower() not in data.get("manager_nom", "").lower():
                match = False
            if affectation and affectation != "" and data.get("affectation_type", "") != affectation:
                match = False
            if nom_affectation and nom_affectation != "" and nom_affectation.lower() not in data.get("affectation_nom", "").lower():
                match = False
            if match:
                filtered[name] = data
        except ValueError: # Gère les dates non valides
            continue
    return filtered

# -------------------- Export PDF --------------------
def export_brief_pdf():
    if not PDF_AVAILABLE:
        return None
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("📋 Brief Recrutement", styles['Heading1']))
    story.append(Spacer(1, 20))

    # --- SECTION 1: Identité
    story.append(Paragraph("1. Identité du poste", styles['Heading2']))
    infos = [
        ["Intitulé", st.session_state.get("poste_intitule", "")],
        ["Service", st.session_state.get("service", "")],
        ["Niveau Hiérarchique", st.session_state.get("niveau_hierarchique", "")],
        ["Type de Contrat", st.session_state.get("type_contrat", "")],
        ["Localisation", st.session_state.get("localisation", "")],
        ["Budget Salaire", st.session_state.get("budget_salaire", "")],
        ["Date Prise de Poste", str(st.session_state.get("date_prise_poste", ""))]
    ]
    story.append(Table(infos, colWidths=[150, 300], style=[("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(Spacer(1, 15))

    # --- SECTION 2: Contexte & Enjeux
    story.append(Paragraph("2. Contexte & Enjeux", styles['Heading2']))
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "taches_principales"]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 3: Exigences
    story.append(Paragraph("3. Exigences", styles['Heading2']))
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 4: Matrice KSA
    story.append(Paragraph("4. Matrice KSA", styles['Heading2']))
    if not st.session_state.ksa_matrix.empty:
        header = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle (1-5)", "Évaluateur"]
        table_data = [header] + st.session_state.ksa_matrix.values.tolist()
        t = Table(table_data, style=[('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.grey)])
        story.append(t)
    story.append(Spacer(1, 15))

    # --- SECTION 5: Stratégie Recrutement
    story.append(Paragraph("5. Stratégie Recrutement", styles['Heading2']))
    strategy_fields = ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]
    for field in strategy_fields:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            story.append(Paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {value}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 6: Notes du Manager
    story.append(Paragraph("6. Notes du Manager", styles['Heading2']))
    if st.session_state.get("manager_notes"):
        story.append(Paragraph(f"<b>Notes Générales:</b> {st.session_state.manager_notes}", styles['Normal']))
        story.append(Spacer(1, 5))
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in st.session_state.get("manager_comments", {}) and st.session_state.manager_comments[comment_key]:
            story.append(Paragraph(f"<b>Commentaire {i}:</b> {st.session_state.manager_comments[comment_key]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------- Export Word --------------------
def export_brief_word():
    if not WORD_AVAILABLE:
        return None

    doc = Document()
    doc.add_heading("📋 Brief Recrutement", 0)

    # --- SECTION 1: Identité
    doc.add_heading("1. Identité du poste", level=2)
    info_table = doc.add_table(rows=0, cols=2)
    info_table.autofit = True
    for label, value in [
        ["Intitulé", st.session_state.get("poste_intitule", "")],
        ["Service", st.session_state.get("service", "")],
        ["Niveau Hiérarchique", st.session_state.get("niveau_hierarchique", "")],
        ["Type de Contrat", st.session_state.get("type_contrat", "")],
        ["Localisation", st.session_state.get("localisation", "")],
        ["Budget Salaire", st.session_state.get("budget_salaire", "")],
        ["Date Prise de Poste", str(st.session_state.get("date_prise_poste", ""))]
    ]:
        row_cells = info_table.add_row().cells
        row_cells[0].text = label
        row_cells[1].text = value
    doc.add_paragraph()

    # --- SECTION 2: Contexte & Enjeux
    doc.add_heading("2. Contexte & Enjeux", level=2)
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "taches_principales"]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 3: Exigences
    doc.add_heading("3. Exigences", level=2)
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 4: Matrice KSA
    doc.add_heading("4. Matrice KSA", level=2)
    if not st.session_state.ksa_matrix.empty:
        ksa_table = doc.add_table(rows=1, cols=5)
        ksa_table.autofit = True
        header_cells = ksa_table.rows[0].cells
        header_labels = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle (1-5)", "Évaluateur"]
        for i, label in enumerate(header_labels):
            header_cells[i].text = label
        for _, row in st.session_state.ksa_matrix.iterrows():
            row_cells = ksa_table.add_row().cells
            row_cells[0].text = str(row["Rubrique"])
            row_cells[1].text = str(row["Critère"])
            row_cells[2].text = str(row["Cible / Standard attendu"])
            row_cells[3].text = str(row["Échelle d'évaluation (1-5)"])
            row_cells[4].text = str(row["Évaluateur"])
    doc.add_paragraph()

    # --- SECTION 5: Stratégie Recrutement
    doc.add_heading("5. Stratégie Recrutement", level=2)
    strategy_fields = ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]
    for field in strategy_fields:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            doc.add_paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {value}")
    doc.add_paragraph()

    # --- SECTION 6: Notes du Manager
    doc.add_heading("6. Notes du Manager", level=2)
    if st.session_state.get("manager_notes"):
        doc.add_paragraph(f"<b>Notes Générales:</b> {st.session_state.manager_notes}")
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in st.session_state.get("manager_comments", {}) and st.session_state.manager_comments[comment_key]:
            doc.add_paragraph(f"<b>Commentaire {i}:</b> {st.session_state.manager_comments[comment_key]}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
    
def generate_automatic_brief_name():
    """Génère un nom de brief automatique basé sur la date et l'intitulé du poste."""
    now = datetime.now()
    job_title = st.session_state.get("poste_intitule", "Nouveau")
    return f"{now.strftime('%Y-%m-%d')}_{job_title.replace(' ', '_')}"

# -------------------- Gestion de la Bibliothèque de fiches de poste --------------------
LIBRARY_FILE = "job_library.json"

def load_library():
    """Charge les fiches de poste depuis le fichier de la bibliothèque."""
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_library(library_data):
    """Sauvegarde les fiches de poste dans le fichier de la bibliothèque."""
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(library_data, f, indent=4, ensure_ascii=False)

# -------------------- Pré-rédaction IA avec DeepSeek --------------------
def get_ai_pre_redaction(fiche_data):
    """Génère une pré-rédaction synthétique avec DeepSeek API via OpenAI client."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Le module 'openai' n'est pas installé. Veuillez l'installer avec 'pip install openai'.")

    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("Clé API DeepSeek non trouvée dans st.secrets")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"  # Compatible OpenAI
    )

    prompt = (
        f"Synthétise les informations de cette fiche de poste en une version courte et concise. "
        f"Modifie uniquement les sections suivantes :\n"
        f"- Mission globale : une phrase courte.\n"
        f"- Tâches principales : 5-6 missions courtes en bullet points.\n"
        f"- Must have : liste des exigences essentielles complètes en bullet points.\n"
        f"- Nice to have : liste des exigences optionnelles complètes en bullet points.\n"
        f"Ne touche pas aux autres sections. Utilise un format markdown clair pour chaque section.\n"
        f"Fiche de poste :\n{fiche_data}"
    )

    response = client.chat.completions.create(
        model="deepseek-chat",  # Modèle DeepSeek principal
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )

    return response.choices[0].message.content