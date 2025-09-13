# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io
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
        "ksa_data": {},
        "saved_briefs": {},
        "current_brief_name": None,
        "filtered_briefs": {},
        "show_filtered_results": False,
        "brief_data": {},
        "comment_libre": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistence --------------------
def save_briefs():
    with open("briefs.pkl", "wb") as f:
        pickle.dump(st.session_state.saved_briefs, f)

def load_briefs():
    if os.path.exists("briefs.pkl"):
        with open("briefs.pkl", "rb") as f:
            return pickle.load(f)
    return {}

# -------------------- Conseils IA (MIS À JOUR) --------------------
def generate_checklist_advice(category, item):
    """Génère un conseil IA pour les champs du brief."""
    
    if "Contexte" in category:
        if "Raison" in item:
            return "- Clarifier le départ ou la création de poste.\n- Identifier le niveau d'urgence.\n- Relier au contexte business."
        elif "Mission" in item:
            return "- Détailler la valeur ajoutée stratégique du poste.\n- Relier les missions aux objectifs de l’entreprise."
        elif "Tâches" in item:
            return "- Lister les tâches principales avec des verbes d'action concrets.\n- Inclure les responsabilités clés et les livrables attendus."

    elif "Must-have" in category or "Nice-to-have" in category:
        if "Expérience" in item:
            return "- Spécifier le nombre d'années d'expérience requis et le secteur d'activité ciblé.\n- Mentionner les types de projets ou de missions spécifiques."
        elif "Diplômes" in item or "Connaissances" in item:
            return "- Indiquer les diplômes, certifications ou formations indispensables.\n- Préciser les connaissances techniques ou réglementaires nécessaires."
        elif "Compétences" in item or "Outils" in item:
            return "- L'IA suggère des compétences techniques (hard skills) et des outils à maîtriser absolument.\n- Exemple : 'Maîtrise de Power BI', 'Expertise en gestion de projet Agile'."
        elif "Soft skills" in item:
            return "- L'IA suggère des aptitudes comportementales clés pour ce poste.\n- Exemple : 'Leadership', 'Communication', 'Rigueur', 'Autonomie'."

    elif "Sourcing" in category:
        if "Entreprises" in item:
            return "- L'IA suggère des entreprises similaires ou des concurrents où trouver des profils pertinents.\n- Exemples : 'Entreprises du secteur de l'énergie', 'Startups technologiques'."
        elif "Synonymes" in item:
            return "- L'IA suggère des titres de poste alternatifs pour la recherche sur LinkedIn et les jobboards.\n- Exemples : 'Chef de projet', 'Project Manager', 'Responsable de programme'."
        elif "Canaux" in item:
            return "- L'IA propose une liste de canaux de sourcing pertinents.\n- Exemples : 'LinkedIn', 'Jobboards spécialisés', 'Cooptation', 'Chasse de tête'."
            
    elif "Conditions" in category:
        if "Localisation" in item:
            return "- Préciser l'emplacement exact du poste, la possibilité de télétravail et la fréquence des déplacements."
        elif "Budget" in item:
            return "- Indiquer une fourchette de salaire réaliste et les avantages ou primes éventuelles."
    
    elif "Notes" in category:
        if "Points à discuter" in item:
            return "- L'IA propose des questions pour clarifier le brief avec le manager.\n- Exemple : 'Priorité des compétences', 'Culture d'équipe'."
        elif "Case libre" in item:
            return "- L'IA suggère des points additionnels à considérer.\n- Exemple : 'Points de motivation spécifiques pour ce poste'."

    return f"- Fournir des détails pratiques pour {item}\n- Exemple concret\n- Piège à éviter"


# -------------------- Filtre --------------------
def filter_briefs(briefs, month, recruteur, poste, manager):
    filtered = {}
    for name, data in briefs.items():
        match = True
        if month and data.get("date_brief", "")[5:7] != month:
            match = False
        if recruteur and recruteur.lower() not in data.get("recruteur", "").lower():
            match = False
        if poste and poste.lower() not in data.get("poste_intitule", "").lower():
            match = False
        if manager and manager.lower() not in data.get("manager_nom", "").lower():
            match = False
        if match:
            filtered[name] = data
    return filtered


# -------------------- Export PDF --------------------
def export_brief_pdf():
    if not PDF_AVAILABLE:
        return None

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

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
        ["Niveau hiérarchique", st.session_state.get("niveau_hierarchique", "")],
        ["Contrat", st.session_state.get("type_contrat", "")],
        ["Localisation", st.session_state.get("localisation", "")],
        ["Budget", st.session_state.get("budget_salaire", "")],
        ["Date prise poste", str(st.session_state.get("date_prise_poste", ""))],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"]
    ]
    story.append(Table(infos, colWidths=[150, 300], style=[("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(Spacer(1, 15))

    # --- SECTION 2: Contexte
    story.append(Paragraph("2. Contexte & Enjeux", styles['Heading2']))
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "defis_principaux"]:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))
    
    # --- SECTION 3: Réunion
    story.append(Paragraph("3. Incidents Critiques & Questions", styles['Heading2']))
    reunion_fields = ["reussite_contexte", "reussite_actions", "reussite_resultat", "echec_contexte", "echec_causes", "echec_impact", "comp_q1", "comp_rep1", "comp_eval1"]
    for field in reunion_fields:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # --- SECTION 4: Matrice KSA
    story.append(Paragraph("4. Matrice KSA", styles['Heading2']))
    ksa_data_list = []
    for cat, comps in st.session_state.get("ksa_data", {}).items():
        for comp, details in comps.items():
            ksa_data_list.append([
                cat,
                comp,
                details.get("niveau", ""),
                details.get("priorite", ""),
                details.get("evaluateur", ""),
                str(details.get("score", "")),
                details.get("texte", "")
            ])
    if ksa_data_list:
        header = ["Catégorie", "Compétence", "Niveau", "Priorité", "Évaluateur", "Score", "Description"]
        table_data = [header] + ksa_data_list
        story.append(Table(table_data, style=[('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.grey)]))
    story.append(Spacer(1, 15))

    # --- SECTION 5: Stratégie Recrutement
    story.append(Paragraph("5. Stratégie Recrutement", styles['Heading2']))
    strategy_fields = ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]
    for field in strategy_fields:
        if field in st.session_state and st.session_state[field]:
            story.append(Paragraph(f"**{field.replace('_', ' ').title()}:** {st.session_state[field]}", styles['Normal']))
            story.append(Spacer(1, 5))
    story.append(Spacer(1, 15))

    # Générer le PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------- EXPORT WORD --------------------
def export_brief_word():
    if not WORD_AVAILABLE:
        return None

    from docx import Document
    from docx.shared import Inches

    doc = Document()
    doc.add_heading("📋 Brief Recrutement", 0)

    # --- SECTION 1: Identité
    doc.add_heading("1. Identité du poste", level=2)
    info_table = doc.add_table(rows=0, cols=2)
    for label, value in [
        ["Intitulé", st.session_state.get("poste_intitule", "")],
        ["Service", st.session_state.get("service", "")],
        ["Niveau hiérarchique", st.session_state.get("niveau_hierarchique", "")],
        ["Contrat", st.session_state.get("type_contrat", "")],
        ["Localisation", st.session_state.get("localisation", "")],
        ["Budget", st.session_state.get("budget_salaire", "")],
        ["Date prise poste", str(st.session_state.get("date_prise_poste", ""))],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"]
    ]:
        row = info_table.add_row().cells
        row[0].text = label
        row[1].text = value
    doc.add_paragraph()

    # --- SECTION 2: Contexte
    doc.add_heading("2. Contexte & Enjeux", level=2)
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "defis_principaux"]:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()
    
    # --- SECTION 3: Réunion
    doc.add_heading("3. Incidents Critiques & Questions", level=2)
    reunion_fields = ["reussite_contexte", "reussite_actions", "reussite_resultat", "echec_contexte", "echec_causes", "echec_impact", "comp_q1", "comp_rep1", "comp_eval1"]
    for field in reunion_fields:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    # --- SECTION 4: Matrice KSA
    doc.add_heading("4. Matrice KSA", level=2)
    ksa_table = doc.add_table(rows=1, cols=6)
    ksa_table.autofit = True
    header_cells = ksa_table.rows[0].cells
    header_labels = ["Catégorie", "Compétence", "Niveau", "Priorité", "Évaluateur", "Score"]
    for i, label in enumerate(header_labels):
        header_cells[i].text = label

    for cat, comps in st.session_state.get("ksa_data", {}).items():
        for comp, details in comps.items():
            row_cells = ksa_table.add_row().cells
            row_cells[0].text = cat
            row_cells[1].text = comp
            row_cells[2].text = details.get("niveau", "")
            row_cells[3].text = details.get("priorite", "")
            row_cells[4].text = details.get("evaluateur", "")
            row_cells[5].text = str(details.get("score", ""))
    doc.add_paragraph()

    # --- SECTION 5: Stratégie Recrutement
    doc.add_heading("5. Stratégie Recrutement", level=2)
    strategy_fields = ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]
    for field in strategy_fields:
        if field in st.session_state and st.session_state[field]:
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {st.session_state[field]}")
    doc.add_paragraph()

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_automatic_brief_name():
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d')}_{st.session_state.get('niveau_hierarchique', 'Nouveau')}"