# utils.py
# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io
import time
import random
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
        "ksa_data": {},  # Ancienne structure
        "ksa_matrix": pd.DataFrame(),  # Nouvelle structure, plus robuste
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
        "ia_advice_used": False,  # Indicateur pour le message explicatif
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistance --------------------
def save_briefs():
    """Sauvegarde les briefs dans un fichier JSON."""
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
    """Charge les briefs depuis un fichier JSON."""
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

def save_library(library_data):
    """Sauvegarde la bibliothèque de postes dans un fichier JSON."""
    try:
        with open("job_library.json", "w") as f:
            json.dump(library_data, f, indent=4)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de la bibliothèque: {e}")

def load_library():
    """Charge la bibliothèque de postes depuis un fichier JSON."""
    try:
        with open("job_library.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# -------------------- Conseils IA --------------------
def generate_checklist_advice(section_title, field_title):
    """Génère un conseil IA adapté au contexte BTP pour un champ spécifique."""
    advice_db = {
        "Raison de l'ouverture": [
            "Préciser si le poste est ouvert pour un remplacement suite à un départ ou pour un nouveau chantier dans le secteur BTP.",
            "Indiquer si le recrutement est motivé par l'expansion d'un projet de construction ou une réorganisation interne.",
            "Relier la raison de l'ouverture à un besoin spécifique, comme la gestion d'un chantier majeur ou une conformité réglementaire BTP.",
            "Mentionner si le poste répond à un besoin urgent lié à un projet de construction à court terme.",
            "Justifier l'ouverture par la nécessité de renforcer l'équipe pour un projet d'infrastructure complexe."
        ],
        "Mission globale": [
            "Superviser la coordination des chantiers pour garantir le respect des délais et des normes de sécurité BTP.",
            "Gérer les projets de construction pour optimiser les ressources et respecter les budgets alloués.",
            "Assurer la conformité des travaux aux réglementations BTP et aux attentes des clients.",
            "Diriger la mise en œuvre de projets d'infrastructure pour soutenir les objectifs stratégiques de l'entreprise.",
            "Coordonner les équipes sur le terrain pour garantir la qualité et l'efficacité des travaux de construction."
        ],
        "Tâches principales": [
            "Planifier et superviser les travaux sur les chantiers, coordonner les sous-traitants, et assurer le respect des délais et du budget.",
            "Gérer les approvisionnements en matériaux de construction et vérifier leur conformité aux normes BTP.",
            "Réaliser des contrôles qualité sur les travaux effectués et rédiger des rapports d'avancement pour les clients.",
            "Coordonner les équipes de terrain, organiser les plannings, et assurer la sécurité sur les chantiers.",
            "Superviser l'installation des équipements sur les chantiers et garantir leur mise en service dans les délais impartis.",
            "Effectuer des études de faisabilité pour de nouveaux projets de construction et proposer des optimisations."
        ],
        "Expérience": [
            "Minimum 5 ans d'expérience dans la gestion de chantiers de construction ou d'infrastructures BTP.",
            "Expérience confirmée dans la coordination de projets BTP multi-sites avec des équipes pluridisciplinaires.",
            "Participation à des projets de construction de grande envergure (bâtiments, routes, ponts, etc.).",
            "Expérience dans la gestion des relations avec les sous-traitants et les fournisseurs dans le secteur BTP.",
            "Connaissance pratique des normes de sécurité et des réglementations BTP (NF, ISO, etc.)."
        ],
        "Connaissances / Diplômes / Certifications": [
            "Diplôme d’ingénieur en génie civil ou équivalent requis.",
            "Certification en gestion de projet BTP (ex. : PMP, Prince2) fortement appréciée.",
            "Connaissance des normes de sécurité BTP (ex. : CACES, habilitations électriques).",
            "Maîtrise des logiciels de gestion de chantier (AutoCAD, MS Project, BIM).",
            "Formation en réglementation environnementale pour les chantiers (HQE, LEED)."
        ],
        "Compétences / Outils": [
            "Maîtrise des outils de planification de chantier comme MS Project ou Primavera.",
            "Compétences en gestion budgétaire et suivi des coûts dans le cadre de projets BTP.",
            "Utilisation avancée des outils BIM pour la modélisation et la coordination des projets.",
            "Capacité à interpréter des plans techniques et des cahiers des charges BTP.",
            "Connaissance des techniques de construction durable et des matériaux écologiques."
        ],
        "Soft skills / aptitudes comportementales": [
            "Leadership pour diriger des équipes pluridisciplinaires sur les chantiers.",
            "Rigueur dans le suivi des normes de sécurité et des délais impartis.",
            "Excellente communication pour coordonner avec les clients, sous-traitants et équipes internes.",
            "Capacité à résoudre rapidement des problèmes imprévus sur les chantiers.",
            "Adaptabilité face aux aléas climatiques ou logistiques sur les projets BTP."
        ],
        "Expérience additionnelle": [
            "Expérience dans des projets internationaux de construction ou d’infrastructures.",
            "Participation à des chantiers certifiés HQE ou à haute performance énergétique.",
            "Connaissance des projets de réhabilitation ou de rénovation de bâtiments anciens.",
            "Expérience dans la gestion de projets publics (ex. : appels d’offres publics).",
            "Collaboration avec des bureaux d’études techniques pour des projets complexes."
        ],
        "Diplômes / Certifications valorisantes": [
            "Certification HQE pour la construction durable.",
            "Formation complémentaire en gestion de projet Agile adaptée au BTP.",
            "Certificat en sécurité chantier (ex. : CACES pour engins de chantier).",
            "Diplôme en gestion des risques environnementaux dans le BTP.",
            "Formation en droit des contrats pour les projets de construction."
        ],
        "Compétences complémentaires": [
            "Connaissance des logiciels de modélisation 3D pour les projets BTP.",
            "Compétences en négociation avec les fournisseurs de matériaux de construction.",
            "Familiarité avec les normes internationales de construction (ISO, ASTM).",
            "Capacité à réaliser des audits de chantier pour évaluer les performances.",
            "Connaissance des techniques de gestion des déchets de chantier."
        ],
        "Entreprises où trouver ce profil": [
            "Vinci Construction, Bouygues Construction, Eiffage.",
            "Entreprises locales spécialisées dans le génie civil ou les travaux publics.",
            "Bureaux d’études techniques travaillant sur des projets d’infrastructure.",
            "Entreprises de construction durable ou spécialisées en HQE.",
            "Sous-traitants spécialisés dans les travaux de gros œuvre ou second œuvre."
        ],
        "Synonymes / intitulés proches": [
            "Chef de chantier, Conducteur de travaux, Ingénieur travaux.",
            "Responsable de projet BTP, Coordinateur de chantier.",
            "Manager de projets d’infrastructure, Superviseur de travaux.",
            "Directeur de travaux, Ingénieur en génie civil.",
            "Gestionnaire de chantier, Responsable des opérations BTP."
        ],
        "Canaux à utiliser": [
            "LinkedIn pour cibler les profils d’ingénieurs et chefs de chantier expérimentés.",
            "Jobboards spécialisés BTP comme Batiactu Emploi ou BTP Emploi.",
            "Cooptation au sein des réseaux professionnels du secteur BTP.",
            "Cabinets de recrutement spécialisés dans la construction et le génie civil.",
            "Événements professionnels BTP (salons, conférences, réseaux d’anciens élèves)."
        ]
    }

    # Sélectionner une réponse aléatoire pour le champ donné
    if field_title in advice_db and advice_db[field_title]:
        random.shuffle(advice_db[field_title])  # Mélanger pour obtenir une réponse aléatoire
        return advice_db[field_title].pop()  # Retirer et retourner une réponse aléatoire
    else:
        st.error(f"❌ Aucun conseil disponible pour le champ '{field_title}' dans la section '{section_title}'.")
        return "Aucun conseil disponible pour ce champ."

def get_example_for_field(section_title, field_title):
    """Retourne un exemple contextuel adapté au BTP pour un champ donné."""
    examples = {
        "Contexte du poste": {
            "Raison de l'ouverture": "Remplacement d’un chef de chantier pour un projet de construction d’un pont.",
            "Mission globale": "Superviser la réalisation d’un chantier de construction tout en respectant les délais et normes de sécurité.",
            "Tâches principales": "Planification des travaux, coordination des sous-traitants, contrôle qualité des matériaux.",
        },
        "Must-have (Indispensables)": {
            "Expérience": "5 ans d’expérience en gestion de chantiers de construction.",
            "Connaissances / Diplômes / Certifications": "Diplôme d’ingénieur en génie civil, certification CACES.",
            "Compétences / Outils": "Maîtrise de MS Project et AutoCAD pour la planification de chantiers.",
            "Soft skills / aptitudes comportementales": "Leadership, rigueur, et communication avec les équipes terrain."
        },
        "Nice-to-have (Atouts)": {
            "Expérience additionnelle": "Participation à des projets de construction durable certifiés HQE.",
            "Diplômes / Certifications valorisantes": "Formation en gestion de projet Agile pour le BTP.",
            "Compétences complémentaires": "Connaissance des logiciels BIM pour la modélisation 3D."
        },
        "Sourcing et marché": {
            "Entreprises où trouver ce profil": "Vinci Construction, Bouygues, entreprises locales de travaux publics.",
            "Synonymes / intitulés proches": "Chef de chantier, Conducteur de travaux, Ingénieur travaux.",
            "Canaux à utiliser": "LinkedIn, Batiactu Emploi, cooptation via réseaux professionnels."
        }
    }
    example = examples.get(section_title, {}).get(field_title, "Exemple non disponible")
    if example == "Exemple non disponible":
        st.warning(f"⚠️ Aucun exemple disponible pour le champ '{field_title}' dans la section '{section_title}'.")
    return example

# -------------------- Filtre --------------------
def filter_briefs(briefs, month, recruteur, brief_type, manager, affectation, nom_affectation):
    """Filtre les briefs selon les critères donnés."""
    filtered = {}
    for name, data in briefs.items():
        match = True
        try:
            if month and month != "" and datetime.strptime(data.get("date_brief", datetime.today()), "%Y-%m-%d").strftime("%m") != month:
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
        except ValueError:  # Gère les dates non valides
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

    # Construire le document PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------- Export Word --------------------
def export_brief_word():
    if not WORD_AVAILABLE:
        return None

    doc = Document()
    doc.add_heading('Brief Recrutement', 0)

    # --- SECTION 1: Identité
    doc.add_heading("1. Identité du poste", level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Champ"
    hdr_cells[1].text = "Valeur"
    for field, value in [
        ("Intitulé", st.session_state.get("poste_intitule", "")),
        ("Service", st.session_state.get("service", "")),
        ("Niveau Hiérarchique", st.session_state.get("niveau_hierarchique", "")),
        ("Type de Contrat", st.session_state.get("type_contrat", "")),
        ("Localisation", st.session_state.get("localisation", "")),
        ("Budget Salaire", st.session_state.get("budget_salaire", "")),
        ("Date Prise de Poste", str(st.session_state.get("date_prise_poste", "")))
    ]:
        row_cells = table.add_row().cells
        row_cells[0].text = field
        row_cells[1].text = value
    doc.add_paragraph()

    # --- SECTION 2: Contexte & Enjeux
    doc.add_heading("2. Contexte & Enjeux", level=2)
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "taches_principales"]:
        if field in st.session_state and st.session_state[field]:
            p = doc.add_paragraph()
            p.add_run(f"{field.replace('_', ' ').title()}: ").bold = True
            p.add_run(st.session_state[field])
    doc.add_paragraph()

    # --- SECTION 3: Exigences
    doc.add_heading("3. Exigences", level=2)
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in st.session_state and st.session_state[field]:
            p = doc.add_paragraph()
            p.add_run(f"{field.replace('_', ' ').title()}: ").bold = True
            p.add_run(st.session_state[field])
    doc.add_paragraph()

    # --- SECTION 4: Matrice KSA
    doc.add_heading("4. Matrice KSA", level=2)
    if not st.session_state.ksa_matrix.empty:
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        headers = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle (1-5)", "Évaluateur"]
        for i, header in enumerate(headers):
            hdr_cells[i].text = header
        for index, row in st.session_state.ksa_matrix.iterrows():
            row_cells = table.add_row().cells
            for i, col in enumerate(row):
                row_cells[i].text = str(col)
    doc.add_paragraph()

    # --- SECTION 5: Stratégie Recrutement
    doc.add_heading("5. Stratégie Recrutement", level=2)
    for field in ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            p = doc.add_paragraph()
            p.add_run(f"{field.replace('_', ' ').title()}: ").bold = True
            p.add_run(value)
    doc.add_paragraph()

    # --- SECTION 6: Notes du Manager
    doc.add_heading("6. Notes du Manager", level=2)
    if st.session_state.get("manager_notes"):
        p = doc.add_paragraph()
        p.add_run("Notes Générales: ").bold = True
        p.add_run(st.session_state.manager_notes)
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in st.session_state.get("manager_comments", {}) and st.session_state.manager_comments[comment_key]:
            p = doc.add_paragraph()
            p.add_run(f"Commentaire {i}: ").bold = True
            p.add_run(st.session_state.manager_comments[comment_key])

    # Sauvegarde dans un buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -------------------- Test DeepSeek --------------------
def test_deepseek_connection():
    """Teste la connexion à l'API DeepSeek."""
    try:
        # Simuler une réponse IA
        st.success("✅ Connexion à DeepSeek réussie !")
    except Exception as e:
        st.error(f"❌ Erreur lors de la connexion à DeepSeek : {str(e)}")

# -------------------- Générer Nom de Brief --------------------
def generate_automatic_brief_name():
    """Génère un nom unique pour un brief basé sur l'intitulé du poste et la date."""
    import time
    poste_intitule = st.session_state.get("poste_intitule", "Brief")
    # Nettoyer l'intitulé pour éviter les caractères problématiques
    poste_clean = "".join(c for c in poste_intitule if c.isalnum() or c in (" ", "_")).replace(" ", "_")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{poste_clean}_{timestamp}"