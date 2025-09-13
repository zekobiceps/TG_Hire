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
from docx.shared import Inches

# -------------------- Disponibilité PDF & Word --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Enregistrer une police qui gère les caractères spéciaux
    registerFont(TTFont('Vera', 'Vera.ttf'))
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
        "saved_briefs": {},
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
        with open("job_descriptions.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.saved_job_descriptions, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des fiches de poste: {e}")

def load_job_descriptions():
    """Charge les fiches de poste depuis job_descriptions.json."""
    try:
        with open("job_descriptions.json", "r", encoding="utf-8") as f:
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
            return "- Proposer des canaux de sourcing pertinents (réseaux sociaux, job boards spécialisés, salons)."
    return ""

def generate_automatic_brief_name():
    """Génère un nom de brief automatique basé sur la date et l'intitulé du poste."""
    now = datetime.now()
    job_title = st.session_state.get("poste_intitule", "Nouveau")
    if not job_title:
        job_title = "Nouveau"
    return f"{now.strftime('%Y-%m-%d')}_{job_title.replace(' ', '_')}"

def filter_briefs(search_term):
    """Filtre les briefs sauvegardés en fonction d'un terme de recherche."""
    search_term = search_term.lower()
    filtered = {}
    for name, data in st.session_state.saved_briefs.items():
        if search_term in name.lower():
            filtered[name] = data
        else:
            # Recherche dans les valeurs du brief
            for value in data.values():
                if isinstance(value, str) and search_term in value.lower():
                    filtered[name] = data
                    break
    return filtered

# -------------------- Gestion de la Bibliothèque de fiches de poste --------------------
LIBRARY_FILE = "job_library.json"

def load_library():
    """Charge les fiches de poste depuis le fichier de la bibliothèque."""
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_library(library_data):
    """Sauvegarde les fiches de poste dans le fichier de la bibliothèque."""
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(library_data, f, indent=4, ensure_ascii=False)

# -------------------- Fonctions d'exportation --------------------
def export_brief_pdf():
    """Crée un PDF du brief et le retourne en buffer."""
    if not PDF_AVAILABLE:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = []

        # Titre
        story.append(Paragraph(f"<b>Brief de Recrutement : {st.session_state.current_brief_name}</b>", styles['Heading1']))
        story.append(Spacer(1, 12))

        # Informations générales
        story.append(Paragraph("<b>1. Informations Générales</b>", styles['Heading2']))
        data = [
            ["Poste", st.session_state.get("poste_intitule", "")],
            ["Service", st.session_state.get("service", "")],
            ["Localisation", st.session_state.get("localisation", "")],
            ["Recruteur", st.session_state.get("recruteur", "")],
            ["Manager", st.session_state.get("manager_nom", "")],
            ["Type de contrat", st.session_state.get("type_contrat", "")],
            ["Budget Salarial", st.session_state.get("budget_salaire", "")],
            ["Date de prise de poste", str(st.session_state.get("date_prise_poste", ""))],
        ]
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Vera-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Vera'),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ])
        t = Table(data, colWidths=[100, 400])
        t.setStyle(table_style)
        story.append(t)
        story.append(Spacer(1, 12))

        # Contexte et Enjeux
        story.append(Paragraph("<b>2. Contexte et Enjeux</b>", styles['Heading2']))
        context_data = [
            ["Raison de l'ouverture", st.session_state.get("raison_ouverture", "")],
            ["Impact Stratégique", st.session_state.get("impact_strategique", "")],
            ["Rattachement", st.session_state.get("rattachement", "")],
            ["Tâches Principales", st.session_state.get("taches_principales", "")],
        ]
        t = Table(context_data, colWidths=[150, 350])
        t.setStyle(table_style)
        story.append(t)
        story.append(Spacer(1, 12))

        # Critères du profil
        story.append(Paragraph("<b>3. Critères du profil</b>", styles['Heading2']))
        profil_data = [
            ["Catégorie", "Must-have", "Nice-to-have"],
            ["Expérience", st.session_state.get("must_have_experience", ""), st.session_state.get("nice_to_have_experience", "")],
            ["Diplômes", st.session_state.get("must_have_diplomes", ""), st.session_state.get("nice_to_have_diplomes", "")],
            ["Compétences", st.session_state.get("must_have_competences", ""), st.session_state.get("nice_to_have_competences", "")],
            ["Soft Skills", st.session_state.get("must_have_softskills", ""), ""],
        ]
        profil_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Vera-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Vera'),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ])
        t = Table(profil_data, colWidths=[100, 200, 200])
        t.setStyle(profil_style)
        story.append(t)
        story.append(Spacer(1, 12))

        # Matrice KSA
        if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
            story.append(Paragraph("<b>4. Matrice KSA</b>", styles['Heading2']))
            data_ksa = [st.session_state.ksa_matrix.columns.tolist()] + st.session_state.ksa_matrix.values.tolist()
            ksa_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF4B4B')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Vera-Bold'),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Vera'),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ])
            t = Table(data_ksa, colWidths=[100, 100, 150, 75, 75])
            t.setStyle(ksa_style)
            story.append(t)
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF : {e}")
        return None

def export_brief_word():
    """Crée un document Word du brief et le retourne en buffer."""
    if not WORD_AVAILABLE:
        return None
    
    try:
        doc = Document()
        
        # Style pour les titres
        h1_style = doc.styles['Heading 1']
        h1_style.font.name = 'Calibri'
        h1_style.font.size = Pt(16)
        h1_style.font.bold = True
        
        h2_style = doc.styles['Heading 2']
        h2_style.font.name = 'Calibri'
        h2_style.font.size = Pt(14)
        h2_style.font.bold = True
        
        # Titre principal
        title = doc.add_paragraph(f"Brief de Recrutement : {st.session_state.get('current_brief_name', 'Nouveau Brief')}")
        title.style = h1_style
        
        # --- SECTION 1: Informations Générales
        doc.add_heading("1. Informations Générales", level=2)
        info_table = doc.add_table(rows=0, cols=2)
        info_table.style = 'Table Grid'
        
        brief_info = {
            "Poste": st.session_state.get("poste_intitule", ""),
            "Service": st.session_state.get("service", ""),
            "Localisation": st.session_state.get("localisation", ""),
            "Recruteur": st.session_state.get("recruteur", ""),
            "Manager": st.session_state.get("manager_nom", ""),
            "Type de contrat": st.session_state.get("type_contrat", ""),
            "Budget Salarial": st.session_state.get("budget_salaire", ""),
            "Date de prise de poste": str(st.session_state.get("date_prise_poste", ""))
        }
        for key, value in brief_info.items():
            if value:
                row_cells = info_table.add_row().cells
                row_cells[0].text = key
                row_cells[1].text = value
                
        # --- SECTION 2: Contexte & Enjeux
        doc.add_heading("2. Contexte & Enjeux", level=2)
        context_fields = [
            ("Raison de l'ouverture", "raison_ouverture"),
            ("Impact Stratégique", "impact_strategique"),
            ("Rattachement", "rattachement"),
            ("Tâches Principales", "taches_principales")
        ]
        for title, key in context_fields:
            if st.session_state.get(key):
                doc.add_paragraph(f"<b>{title}:</b> {st.session_state[key]}", style="Normal")._element.xml_string()

        # --- SECTION 3: Critères du profil
        doc.add_heading("3. Critères du profil", level=2)
        profil_table = doc.add_table(rows=1, cols=3)
        profil_table.style = 'Table Grid'
        hdr_cells = profil_table.rows[0].cells
        hdr_cells[0].text = "Catégorie"
        hdr_cells[1].text = "Must-have"
        hdr_cells[2].text = "Nice-to-have"
        
        profil_data = [
            ("Expérience", "must_have_experience", "nice_to_have_experience"),
            ("Diplômes", "must_have_diplomes", "nice_to_have_diplomes"),
            ("Compétences", "must_have_competences", "nice_to_have_competences"),
            ("Soft Skills", "must_have_softskills", "")
        ]
        for cat, must, nice in profil_data:
            row_cells = profil_table.add_row().cells
            row_cells[0].text = cat
            row_cells[1].text = st.session_state.get(must, "")
            row_cells[2].text = st.session_state.get(nice, "")
        doc.add_paragraph()

        # --- SECTION 4: Matrice KSA
        if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
            doc.add_heading("4. Matrice KSA", level=2)
            ksa_table = doc.add_table(rows=1, cols=5)
            ksa_table.style = 'Table Grid'
            
            hdr_cells = ksa_table.rows[0].cells
            hdr_cells[0].text = "Rubrique"
            hdr_cells[1].text = "Critère"
            hdr_cells[2].text = "Cible / Standard attendu"
            hdr_cells[3].text = "Échelle d'évaluation"
            hdr_cells[4].text = "Évaluateur"
            
            for index, row in st.session_state.ksa_matrix.iterrows():
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
    except Exception as e:
        st.error(f"Erreur lors de la génération du document Word : {e}")
        return None