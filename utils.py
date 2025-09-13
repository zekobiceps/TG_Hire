# -*- coding: utf-8 -*-
import streamlit as st
import os
import json
import io
import pandas as pd
from datetime import datetime
import requests

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
    defaults = {
        "manager_nom": "",
        "niveau_hierarchique": "",
        "affectation_type": "",
        "recruteur": "",
        "affectation_nom": "",
        "date_brief": "",
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
        "budget": "",
        "commentaires": "",
        "notes_libres": "",
        "profil_links": ["", "", ""],
        "ksa_data": {},
        "ksa_matrix": pd.DataFrame(),
        "saved_briefs": {},
        "current_brief_name": "",
        "filtered_briefs": {},
        "brief_type": "Brief",
        "avant_brief_completed": False,
        "reunion_completed": False,
        "reunion_step": 1,
        "saved_job_descriptions": {},
        "temp_extracted_data": None,
        "temp_job_title": "",
        "canaux_prioritaires": [],
        "criteres_exclusion": "",
        "processus_evaluation": "",
        "manager_comments": {},
        "manager_notes": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistence --------------------
def save_briefs():
    """Sauvegarde les briefs dans briefs.json"""
    with open("briefs.json", "w") as f:
        json.dump(st.session_state.saved_briefs, f, indent=4, default=str)

def load_briefs():
    """Charge les briefs depuis briefs.json"""
    try:
        with open("briefs.json", "r") as f:
            data = json.load(f)
            # Convertir ksa_matrix en DataFrame si présent
            for brief_name, brief_data in data.items():
                if "ksa_matrix" in brief_data and brief_data["ksa_matrix"]:
                    brief_data["ksa_matrix"] = pd.DataFrame(brief_data["ksa_matrix"])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_job_descriptions():
    """Sauvegarde les fiches de poste dans job_descriptions.json"""
    with open("job_descriptions.json", "w") as f:
        json.dump(st.session_state.saved_job_descriptions, f, indent=4)

def load_job_descriptions():
    """Charge les fiches de poste depuis job_descriptions.json"""
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
        if month and month != "" and data.get("date_brief", "").split("-")[1] != month:
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
        ["Intitulé", st.session_state.get("niveau_hierarchique", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Type", st.session_state.get("brief_type", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"],
        ["Date", str(st.session_state.get("date_brief", ""))]
    ]
    story.append(Table(infos, colWidths=[150, 300], style=[("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(Spacer(1, 15))

    # --- SECTION 2: Contexte
    story.append(Paragraph("2. Contexte & Enjeux", styles['Heading2']))
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "taches_principales"]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 3: Exigences
    story.append(Paragraph("3. Exigences", styles['Heading2']))
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 4: Sourcing
    story.append(Paragraph("4. Sourcing", styles['Heading2']))
    for field in ["entreprises_profil", "synonymes_poste", "canaux_profil"]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 5: Conditions
    story.append(Paragraph("5. Conditions", styles['Heading2']))
    for field in ["budget", "commentaires", "notes_libres"]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 6: Profils
    story.append(Paragraph("6. Profils Pertinents", styles['Heading2']))
    for i, link in enumerate(st.session_state.get("profil_links", ["", "", ""]), 1):
        if link:
            story.append(Paragraph(f"**Profil {i}:** {link}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 7: Matrice KSA
    story.append(Paragraph("7. Matrice KSA", styles['Heading2']))
    if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
        header = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle (1-5)", "Évaluateur"]
        table_data = [header] + st.session_state.ksa_matrix.values.tolist()
        story.append(Table(table_data, style=[('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.grey)]))
    story.append(Spacer(1, 15))

    # --- SECTION 8: Stratégie Recrutement
    story.append(Paragraph("8. Stratégie Recrutement", styles['Heading2']))
    for field in ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {value}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 9: Notes Manager
    story.append(Paragraph("9. Notes du Manager", styles['Heading2']))
    if st.session_state.get("manager_notes"):
        story.append(Paragraph(f"**Notes Générales:** {st.session_state.manager_notes}", styles['Normal']))
        story.append(Spacer(1, 5))
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in st.session_state.get("manager_comments", {}) and st.session_state.manager_comments[comment_key]:
            story.append(Paragraph(f"**Commentaire {i}:** {st.session_state.manager_comments[comment_key]}", styles['Normal']))
            story.append(Spacer(1, 5))

    # Générer le PDF
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
    for label, value in [
        ["Intitulé", st.session_state.get("niveau_hierarchique", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Type", st.session_state.get("brief_type", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"],
        ["Date", str(st.session_state.get("date_brief", ""))]
    ]:
        row = info_table.add_row().cells
        row[0].text = label
        row[1].text = value
    doc.add_paragraph()

    # --- SECTION 2: Contexte
    doc.add_heading("2. Contexte & Enjeux", level=2)
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "taches_principales"]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 3: Exigences
    doc.add_heading("3. Exigences", level=2)
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 4: Sourcing
    doc.add_heading("4. Sourcing", level=2)
    for field in ["entreprises_profil", "synonymes_poste", "canaux_profil"]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 5: Conditions
    doc.add_heading("5. Conditions", level=2)
    for field in ["budget", "commentaires", "notes_libres"]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 6: Profils
    doc.add_heading("6. Profils Pertinents", level=2)
    for i, link in enumerate(st.session_state.get("profil_links", ["", "", ""]), 1):
        if link:
            doc.add_paragraph(f"Profil {i}: {link}")
    doc.add_paragraph()

    # --- SECTION 7: Matrice KSA
    doc.add_heading("7. Matrice KSA", level=2)
    if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
        ksa_table = doc.add_table(rows=1, cols=5)
        ksa_table.autofit = True
        header_cells = ksa_table.rows[0].cells
        header_labels = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle (1-5)", "Évaluateur"]
        for i, label in enumerate(header_labels):
            header_cells[i].text = label
        for _, row in st.session_state.ksa_matrix.iterrows():
            row_cells = ksa_table.add_row().cells
            for i, col in enumerate(["Rubrique", "Critère", "Cible / Standard attendu", "Échelle d'évaluation (1-5)", "Évaluateur"]):
                row_cells[i].text = str(row[col])
    doc.add_paragraph()

    # --- SECTION 8: Stratégie Recrutement
    doc.add_heading("8. Stratégie Recrutement", level=2)
    for field in ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {value}")
    doc.add_paragraph()

    # --- SECTION 9: Notes Manager
    doc.add_heading("9. Notes du Manager", level=2)
    if st.session_state.get("manager_notes"):
        doc.add_paragraph(f"Notes Générales: {st.session_state.manager_notes}")
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in st.session_state.get("manager_comments", {}) and st.session_state.manager_comments[comment_key]:
            doc.add_paragraph(f"Commentaire {i}: {st.session_state.manager_comments[comment_key]}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -------------------- Génération nom automatique --------------------
def generate_automatic_brief_name():
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d')}_{st.session_state.get('niveau_hierarchique', 'Nouveau')}"