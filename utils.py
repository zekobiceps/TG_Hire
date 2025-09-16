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
def generate_checklist_advice(section_title, field_title):
    """Génère un conseil IA pour les champs du brief."""
    advice_db = {
        "Contexte du poste": {
            "Raison de l'ouverture": [
                "- Clarifier si remplacement pour un chantier en cours, création pour un nouveau projet BTP ou évolution interne due à une promotion.",
                "- Identifier le niveau d'urgence lié aux délais de construction et à la priorisation des sites.",
                "- Expliquer le contexte stratégique dans le secteur BTP, comme un nouveau contrat de travaux publics.",
                "- Préciser si le poste est une création pour renforcer l'équipe sur un grand chantier ou une réaffectation pour optimiser les ressources.",
                "- Relier le poste à la stratégie globale de l'entreprise en matière de développement durable dans le BTP."
            ],
            "Mission globale": [
                "- La mission globale consiste à diriger l'équipe de gestion de chantier pour optimiser les processus de construction et respecter les normes de sécurité.",
                "- Le rôle consiste à améliorer l'efficacité sur les sites en supervisant les projets BTP complexes et en maintenant les délais et le budget.",
                "- Superviser la transformation des chantiers et les projets d'innovation pour soutenir la compétitivité dans le BTP.",
                "- Assurer le bon déroulement des travaux en maintenant un équilibre entre qualité, coûts et respect des normes environnementales.",
                "- Garantir une communication fluide entre les équipes de terrain et les parties prenantes pour maximiser l'impact du projet BTP."
            ],
            "Tâches principales": [
                "- Piloter le process de recrutement pour des profils BTP, définir la stratégie de sourcing sur les chantiers, interviewer les candidats, gérer les entretiens, effectuer le reporting.",
                "- Superviser la gestion des équipes sur site, organiser des formations sécurité, garantir la conformité aux normes BTP, coordonner les projets transversaux.",
                "- Planifier les objectifs trimestriels pour les chantiers, analyser les données de coûts, optimiser les performances des équipes, préparer les rapports de performance.",
                "- Coordonner les efforts entre les départements BTP, gérer les budgets de matériaux, superviser les ressources humaines sur site, suivre les projets et tâches assignées.",
                "- Assurer la planification des travaux, organiser des sessions de formation aux normes de sécurité, coordonner les activités de développement des talents en BTP."
            ]
        },
        "Must-have (Indispensables)": {
            "Expérience": [
                "- Spécifier le nombre d'années d'expérience requis dans le BTP et le secteur des chantiers.",
                "- Mentionner les types de projets similaires, comme la gestion de grands travaux publics ou de construction résidentielle."
            ],
            "Connaissances / Diplômes / Certifications": [
                "- Indiquer les diplômes exigés en génie civil ou BTP, certifications comme Habilitation Électrique ou CACES.",
                "- Préciser les connaissances en normes de sécurité (ISO 45001) ou réglementaires (RT 2012 pour le BTP)."
            ],
            "Compétences / Outils": [
                "- Suggérer des compétences techniques comme la maîtrise d'AutoCAD, Revit ou logiciels de gestion de chantier.",
                "- Exemple : 'Expertise en gestion de projet BTP avec méthodes Agile adaptées aux chantiers'."
            ],
            "Soft skills / aptitudes comportementales": [
                "- Suggérer des aptitudes comme 'Leadership sur terrain', 'Rigueur en sécurité', 'Communication avec sous-traitants', 'Autonomie en gestion de crises'."
            ]
        },
        "Nice-to-have (Atouts)": {
            "Expérience additionnelle": [
                "- Ex. projets internationaux de BTP ou multi-sites avec coordination de grands chantiers."
            ],
            "Diplômes / Certifications valorisantes": [
                "- Certifications supplémentaires comme LEED pour le développement durable en BTP."
            ],
            "Compétences complémentaires": [
                "- Compétences en BIM (Building Information Modeling) ou en gestion environnementale des chantiers."
            ]
        },
        "Sourcing et marché": {
            "Entreprises où trouver ce profil": [
                "- Suggérer des entreprises concurrentes dans le BTP comme Bouygues, Vinci ou Eiffage."
            ],
            "Synonymes / intitulés proches": [
                "- Titres alternatifs comme 'Chef de Chantier', 'Ingénieur Travaux', 'Conducteur de Travaux BTP'."
            ],
            "Canaux à utiliser": [
                "- Proposer LinkedIn pour profils BTP, jobboards spécialisés (Batiweb), cooptation sur chantiers, réseaux professionnels du BTP."
            ]
        }
    }

    # Sélectionner une réponse aléatoire pour la section et le champ donné
    section_advice = advice_db.get(section_title, {})
    field_advice = section_advice.get(field_title, [])
    if field_advice:
        return random.choice(field_advice)  # Sélectionner un conseil aléatoire sans modifier la liste
    else:
        return "Pas de conseil disponible."

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
        header = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle d'évaluation (1-5)", "Évaluateur"]
        table_data = [header]
        for _, row in st.session_state.ksa_matrix.iterrows():
            table_data.append([
                str(row.get("Rubrique", "")),
                str(row.get("Critère", "")),
                str(row.get("Cible / Standard attendu", "")),
                str(row.get("Échelle d'évaluation (1-5)", "")),
                str(row.get("Évaluateur", ""))
            ])
        t = Table(table_data, style=[('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.grey)])
        story.append(t)
    else:
        story.append(Paragraph("Aucune donnée KSA disponible.", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 5: Stratégie Recrutement (emoji removed)
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

    # --- SECTION 4: Matrice KSA
    doc.add_heading("4. Matrice KSA", level=2)
    if not st.session_state.ksa_matrix.empty:
        ksa_table = doc.add_table(rows=1, cols=5)
        ksa_table.autofit = True
        header_cells = ksa_table.rows[0].cells
        header_labels = ["Rubrique", "Critère", "Cible / Standard attendu", "Échelle d'évaluation (1-5)", "Évaluateur"]
        for i, label in enumerate(header_labels):
            header_cells[i].text = label
        for _, row in st.session_state.ksa_matrix.iterrows():
            row_cells = ksa_table.add_row().cells
            row_cells[0].text = str(row.get("Rubrique", ""))
            row_cells[1].text = str(row.get("Critère", ""))
            row_cells[2].text = str(row.get("Cible / Standard attendu", ""))
            row_cells[3].text = str(row.get("Échelle d'évaluation (1-5)", ""))
            row_cells[4].text = str(row.get("Évaluateur", ""))
    else:
        doc.add_paragraph("Aucune donnée KSA disponible.")
    doc.add_paragraph()

    # --- SECTION 5: Stratégie Recrutement (emoji removed)
    doc.add_heading("5. Stratégie Recrutement", level=2)
    strategy_fields = ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]
    for field in strategy_fields:
        if field in st.session_state and st.session_state[field]:
            value = ", ".join(st.session_state[field]) if field == "canaux_prioritaires" else st.session_state[field]
            doc.add_paragraph(f"{field.replace('_', ' ').title()}: {value}")
    doc.add_paragraph()

    # --- SECTION 6: Notes du Manager
    doc.add_heading("6. Notes du Manager", level=2)
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
        from openai import OpenAI  # type: ignore
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

# -------------------- Génération de question IA avec DeepSeek --------------------
def generate_ai_question(prompt):
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

    max_tokens = 500  # Augmentation de la taille de la réponse pour éviter la troncature

    context = "recruitment for a KSA (Knowledge, Skills, Abilities) matrix"
    question_type = "technical"
    skill = prompt
    role = "candidate"
    if "une question" in prompt and "pour évaluer" in prompt and "par" in prompt:
        question_type_part = prompt.split("une question")[1].split("pour")[0].strip().lower()
        if "générale" in question_type_part:
            question_type = "general"
        elif "comportementale" in question_type_part:
            question_type = "behavioral"
        elif "situationnelle" in question_type_part:
            question_type = "situational"
        elif "technique" in question_type_part:
            question_type = "technical"
        skill = prompt.split("évaluer")[1].split("par")[0].strip()
        role = prompt.split("par")[1].strip()

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
        from openai import OpenAI  # type: ignore
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

# -------------------- Exemples contextuels --------------------
def get_example_for_field(section_title, field_title):
    """Retourne un exemple contextuel pour un champ donné, adapté au BTP."""
    examples = {
        "Contexte du poste": {
            "Raison de l'ouverture": "Remplacement d’un départ en retraite sur un chantier majeur",
            "Mission globale": "Assurer la gestion des projets BTP stratégiques de l’entreprise",
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
        "Sourcing et marché": {
            "Entreprises où trouver ce profil": "Vinci, Bouygues, Eiffage",
            "Synonymes / intitulés proches": "Conducteur de Travaux, Ingénieur Chantier",
            "Canaux à utiliser": "LinkedIn pour profils BTP, jobboards comme Batiweb",
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
    
    # Create a base name
    base_name = f"{poste}_{manager}_{date_str}"
    
    # Ensure uniqueness by appending a counter if the name already exists
    saved_briefs = st.session_state.get("saved_briefs", {})
    counter = 1
    brief_name = base_name
    while brief_name in saved_briefs:
        brief_name = f"{base_name}_{counter}"
        counter += 1
    
    return brief_name