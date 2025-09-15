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

#-------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
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
        # Ajoutez d'autres sections si nécessaire
    }

    # Sélectionner une réponse aléatoire pour la section et le champ donné
    section_advice = advice_db.get(section_title, {})
    field_advice = section_advice.get(field_title, [])
    if field_advice:
        random.shuffle(field_advice)  # Mélanger pour obtenir une réponse aléatoire
        return field_advice.pop()  # Retirer et retourner une réponse aléatoire
    else:
        return "Pas de conseil disponible."

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
            return "- Détailler la valeur ajoutée stratégique du poste.\n- Relier les missions aux objectifs de l'entreprise."
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

def get_example_for_field(section_title, field_title):
    """Retourne un exemple contextuel pour un champ donné, adapté au BTP."""
    examples = {
        "Contexte du poste": {
            "Raison de l'ouverture": [
                "Remplacement d’un chef de projet senior parti à la retraite, pour assurer la continuité sur un grand chantier de réhabilitation urbaine.",
                "Création d'un poste pour un nouveau projet d'infrastructure ferroviaire d’envergure nationale.",
                "Évolution interne due à l'ouverture d'une nouvelle agence régionale spécialisée en construction durable.",
                "Renforcement de l'équipe pour répondre à l'augmentation des appels d'offres en génie civil.",
                "Remplacement d’un départ pour soutenir la livraison des projets de l’entreprise en respectant les délais.",
                "Création d’un poste stratégique pour piloter la transition vers les méthodes de construction modulaire.",
                "Optimisation des ressources en créant un poste pour superviser plusieurs petits chantiers simultanément.",
                "Soutien à la croissance de l'activité dans le secteur des travaux publics.",
                "Réorganisation interne visant à séparer les fonctions de gestion et de terrain pour plus d'efficacité.",
                "Réaffectation pour une mission temporaire sur un chantier de construction spécifique avec des contraintes environnementales strictes.",
                "Besoin urgent de recrutement pour un poste-clé de gestion de projet BTP en raison d’un pic d’activité saisonnier.",
                "Positionnement sur un nouveau marché, comme les bâtiments à énergie positive (BEPOS), nécessitant une expertise dédiée.",
            ],
            "Mission globale": [
                "Assurer la gestion complète et stratégique des projets de construction résidentielle, de la conception à la réception.",
                "Coordonner les équipes et les sous-traitants sur différents chantiers pour optimiser la logistique et les délais.",
                "Garantir la conformité et la sécurité des travaux en cours, tout en respectant les budgets et les spécifications techniques.",
                "Piloter les phases de conception et de réalisation de projets d'infrastructures complexes (ponts, routes, etc.).",
                "Assurer la bonne exécution des contrats de sous-traitance et la gestion des litiges éventuels.",
                "Représenter l'entreprise sur le terrain et auprès des clients pour maintenir une communication fluide et efficace.",
                "Superviser les audits de qualité et de sécurité sur l'ensemble des chantiers et mettre en place des actions correctives.",
                "Développer et mettre en œuvre de nouvelles méthodes de travail pour améliorer la productivité sur les chantiers.",
                "Assurer le suivi financier, administratif et technique des projets en cours.",
                "Anticiper et résoudre les problématiques techniques ou de planning qui pourraient survenir.",
                "Contribuer activement au développement commercial de l'entreprise en participant aux phases d'avant-vente et de réponse aux appels d'offres.",
                "Former et encadrer les équipes de terrain pour garantir la montée en compétences et le respect des procédures.",
            ],
            "Tâches principales": [
                "Gestion de budget, suivi des plannings, coordination des équipes de chantier, respect des normes de sécurité.",
                "Supervision des travaux de terrassement, de fondation et de gros œuvre.",
                "Négociation des contrats avec les fournisseurs et sous-traitants pour optimiser les coûts.",
                "Rédaction des rapports d’avancement de projet et présentation aux parties prenantes.",
                "Mise en place et suivi des procédures de contrôle qualité sur le chantier.",
                "Gestion des permis de construire et autres démarches administratives.",
                "Supervision des phases de second œuvre (électricité, plomberie, menuiserie, etc.).",
                "Utilisation de logiciels de gestion de projet BTP (type MS Project, Primavera).",
                "Coordination des levées de réserves et réception des ouvrages.",
                "Préparation des chantiers, y compris l'installation des bases de vie et des équipements de sécurité.",
                "Gestion des ressources humaines sur le chantier (embauche, formation, gestion des conflits).",
                "Réalisation des études techniques et des métrés pour la préparation des devis.",
            ],
        },
        "Must-have (Indispensables)": {
            "Expérience": [
                "5 à 7 ans d’expérience en conduite de travaux pour des projets de logements collectifs.",
                "Minimum 10 ans d'expérience en gestion de projets de génie civil.",
                "Expérience avérée en direction de chantiers complexes et en gestion d'équipes pluridisciplinaires.",
                "Expérience réussie dans le pilotage de projets de réhabilitation lourde.",
                "Au moins 5 ans d’expérience en gestion budgétaire et suivi de la rentabilité de chantiers.",
                "Solide expérience en management de sous-traitants et en négociation de contrats.",
                "Expérience significative dans un rôle de maîtrise d'ouvrage ou maîtrise d'œuvre.",
                "Expérience dans les chantiers publics avec une bonne connaissance des procédures administratives.",
                "Au moins 8 ans d’expérience dans des projets de construction de bâtiments industriels.",
                "Expérience en gestion de projets d'infrastructures routières ou autoroutières.",
                "Expérience sur des projets avec une forte composante environnementale (HQE, BREEAM).",
                "Expérience en gestion de projets de désamiantage ou de déconstruction.",
            ],
            "Connaissances / Diplômes / Certifications": [
                "Diplôme d'ingénieur en génie civil ou équivalent.",
                "Master en gestion de projets, de préférence spécialisé en BTP.",
                "Certification PMP (Project Management Professional) ou équivalent.",
                "Solides connaissances en normes de sécurité BTP (EPI, CACES, etc.).",
                "Connaissance des réglementations environnementales (RT2012, RE2020).",
                "Maîtrise des techniques de construction traditionnelles et innovantes.",
                "Formation en gestion des risques et en droit de la construction.",
                "Certification en BIM (Building Information Modeling) appréciée.",
                "Connaissance des codes des marchés publics pour les projets d’infrastructures.",
                "Compétences en lecture de plans techniques et en interprétation de cahiers des charges.",
                "Connaissance approfondie des matériaux de construction et de leurs propriétés.",
                "Certification en management de la qualité (ISO 9001).",
            ],
            "Compétences / Outils": [
                "Maîtrise d'AutoCAD, Revit, et des logiciels de planification (MS Project, Primavera).",
                "Expertise en gestion budgétaire et en suivi des coûts de chantier.",
                "Compétences avancées en négociation avec les fournisseurs et sous-traitants.",
                "Aisance dans l'utilisation d'outils de communication collaborative (Teams, Slack) pour les équipes de chantier.",
                "Maîtrise des logiciels de modélisation 3D (BIM) pour la coordination des travaux.",
                "Capacité à utiliser des outils de suivi de chantier sur mobile ou tablette.",
                "Compétence en gestion de la chaîne d'approvisionnement (supply chain) BTP.",
                "Savoir-faire en rédaction de rapports techniques et de synthèse.",
                "Aptitude à interpréter des données analytiques pour optimiser les performances de chantier.",
                "Maîtrise des outils de gestion électronique de documents (GED).",
                "Compétences en management de la performance et en résolution de problèmes.",
                "Connaissance des outils de cartographie et de levé topographique.",
            ],
            "Soft skills / aptitudes comportementales": [
                "Leadership naturel sur le terrain et capacité à motiver les équipes.",
                "Rigueur et organisation pour gérer des projets complexes avec de multiples intervenants.",
                "Excellente communication pour interagir avec les clients, les architectes et les équipes.",
                "Autonomie et proactivité pour anticiper les problèmes et trouver des solutions.",
                "Capacité à travailler sous pression et à respecter des délais serrés.",
                "Sens de l'écoute et de l'empathie pour gérer les conflits d'équipe.",
                "Esprit d'analyse et de synthèse pour prendre des décisions rapides et éclairées.",
                "Résilience et capacité à s'adapter aux aléas d'un chantier.",
                "Intégrité et sens des responsabilités vis-à-vis des normes de sécurité.",
                "Créativité pour proposer des solutions innovantes aux défis techniques.",
                "Esprit d'équipe et de collaboration.",
                "Orienté résultats et axé sur la satisfaction client.",
            ],
        },
        "Nice-to-have (Atouts)": {
            "Expérience additionnelle": [
                "Expérience sur des projets internationaux, notamment en Afrique ou au Moyen-Orient.",
                "Expérience en gestion de projets multi-sites, avec une coordination à distance.",
                "Connaissance des projets de BTP à forte composante numérique ou technologique (smart buildings).",
                "Expérience dans le pilotage de projets de construction en bois ou autres matériaux biosourcés.",
                "Participation à la construction de bâtiments labellisés (Passivhaus, etc.).",
                "Expérience en conduite de travaux pour des projets de rénovation énergétique.",
                "Expérience dans une grande entreprise de BTP ou un cabinet d'ingénierie.",
                "Expérience en pilotage de la sécurité et prévention des risques professionnels.",
                "Maîtrise de la gestion de projets de démolition.",
                "Expérience sur des chantiers avec des contraintes environnementales particulières (zones protégées).",
                "Expérience en gestion de projets de réhabilitation du patrimoine historique.",
                "Expérience dans l'implémentation de nouvelles technologies sur les chantiers.",
            ],
            "Diplômes / Certifications valorisantes": [
                "Certification LEED ou BREEAM pour le BTP durable.",
                "Formation ou certification en management de la qualité (ISO 9001).",
                "Master spécialisé en gestion des risques ou en ingénierie environnementale.",
                "Certification professionnelle en gestion de projets Agile.",
                "Formation en droit de la construction ou en marchés publics.",
                "Certification en efficacité énergétique (auditeur énergétique).",
                "Formation à la prévention des risques professionnels (SST, etc.).",
                "Certification en maquettes numériques (BIM).",
                "Diplôme complémentaire en urbanisme ou en aménagement du territoire.",
                "Formation à l'utilisation de drones pour le suivi de chantier.",
                "Certification en éco-construction ou matériaux durables.",
                "Diplôme en management et leadership.",
            ],
            "Compétences complémentaires": [
                "Connaissance approfondie du Building Information Modeling (BIM) et des méthodes de travail collaboratives.",
                "Compétences en gestion environnementale des chantiers (gestion des déchets, économie circulaire).",
                "Maîtrise d'une deuxième langue, en particulier l'anglais technique.",
                "Compétences en gestion de la relation client pour des projets BTP.",
                "Sensibilité à la gestion de l'innovation et des technologies émergentes dans le secteur.",
                "Capacité à former et à accompagner des équipes dans l'utilisation de nouvelles technologies.",
                "Compétences en communication visuelle pour la présentation des projets (infographies, schémas).",
                "Connaissances en conception de bâtiments à faible impact carbone.",
                "Compétences en gestion de projet avec des méthodes agiles adaptées au BTP.",
                "Capacité à réaliser des estimations de coûts et des analyses de rentabilité.",
                "Compétences en gestion de crise sur un chantier.",
                "Bonne connaissance du marché de la sous-traitance locale.",
            ],
        },
        "Sourcing et marché": {
            "Entreprises où trouver ce profil": [
                "Vinci Construction, Bouygues Construction, Eiffage.",
                "Spie Batignolles, NGE, Fayat Group.",
                "Entreprises de taille moyenne spécialisées en génie civil.",
                "Cabinets d'ingénierie conseil en bâtiment et travaux publics.",
                "Promoteurs immobiliers et sociétés d'aménagement.",
                "Grandes entreprises de services énergétiques (Engie, EDF).",
                "Entreprises spécialisées en réhabilitation ou rénovation énergétique.",
                "Sociétés de construction métallique ou en bois.",
                "Agences d'architecture avec une branche de maîtrise d'œuvre.",
                "Bureaux de contrôle technique (Apave, Socotec, etc.).",
                "Acteurs spécialisés dans les infrastructures de transport.",
                "Entreprises du secteur public et parapublic.",
            ],
            "Synonymes / intitulés proches": [
                "Ingénieur Travaux, Chef de Chantier, Conducteur de Travaux Principal.",
                "Directeur de projet BTP, Responsable d'affaires BTP.",
                "Ingénieur en génie civil, Ingénieur structure.",
                "Chargé de projet construction, Coordonnateur de chantier.",
                "Responsable technique, Chef d'agence BTP.",
                "Responsable de programme immobilier.",
                "Ingénieur d'études de prix.",
                "Métreur-vérificateur.",
                "Ingénieur de méthodes.",
                "Chargé de clientèle BTP.",
                "Responsable de la sécurité et de la prévention sur chantier.",
                "Ingénieur en efficacité énergétique des bâtiments.",
            ],
            "Canaux à utiliser": [
                "LinkedIn Recruiter pour cibler les profils BTP.",
                "Jobboards spécialisés : Bati-Actu, BatiJob, Construire-Emploi.",
                "Cabinets de recrutement spécialisés dans le secteur de la construction.",
                "Réseaux professionnels et événements du BTP (salons, conférences).",
                "Cooptation par les employés actuels.",
                "Réseaux sociaux professionnels comme Viadeo ou Xing (en fonction de la localisation).",
                "Sites des grandes écoles d'ingénieurs (ESTP, INSA, Arts et Métiers).",
                "Forums et communautés en ligne dédiés aux professionnels du BTP.",
                "Partenariats avec des organismes de formation (CFA BTP).",
                "Missions de stage ou d'apprentissage pour détecter les jeunes talents.",
                "Agences d'intérim spécialisées dans le BTP.",
                "Campagnes publicitaires ciblées sur des plateformes comme Facebook Ads.",
            ],
        },
        "Profils pertinents": {
            "Lien profil 1": ["https://www.linkedin.com/in/profil-exemple-btp1", "https://www.linkedin.com/in/nom-profil-a-rechercher", "https://www.linkedin.com/in/expert-genie-civil"],
            "Lien profil 2": ["https://www.linkedin.com/in/profil-exemple-btp2", "https://www.linkedin.com/in/responsable-travaux-seniors", "https://www.linkedin.com/in/manager-chantier"],
            "Lien profil 3": ["https://www.linkedin.com/in/profil-exemple-btp3", "https://www.linkedin.com/in/ingenieur-batiment-durable", "https://www.linkedin.com/in/architecte-chef-de-projet"],
        },
        "Notes libres": {
            "Points à discuter ou à clarifier avec le manager": [
                "Préciser le niveau de responsabilité sur la gestion du budget du chantier.",
                "Discuter de la tolérance à l'égard des retards imprévus.",
                "Clarifier la structure hiérarchique et les interdépendances avec les autres départements.",
                "Aborder les perspectives d'évolution de carrière et de formation continue.",
                "Valider le périmètre exact des missions et des projets à gérer.",
                "Définir les indicateurs de performance clés (KPI) attendus pour le poste.",
                "Se renseigner sur la culture d'entreprise et les valeurs de l'équipe.",
                "Évaluer la charge de travail et l'équilibre entre vie professionnelle et vie personnelle.",
                "Demander des détails sur les outils et technologies à disposition.",
                "Confirmer le processus de recrutement et les étapes suivantes.",
            ],
            "Case libre": [
                "Le candidat idéal devra avoir une forte capacité à motiver ses équipes sur des chantiers complexes.",
                "L'entreprise recherche un profil ayant une expertise en construction modulaire.",
                "Les compétences en gestion de projet Agile sont un atout majeur pour ce poste.",
                "Le futur collaborateur devra être autonome et capable de prendre des initiatives sur le terrain.",
                "Ce poste requiert une bonne résistance au stress en raison des délais serrés et des imprévus.",
                "Le candidat doit être prêt à se déplacer régulièrement entre les différents chantiers de la région.",
                "Une expérience en gestion de la sécurité sur les chantiers est un critère non-négociable.",
                "Le poste implique une collaboration étroite avec les équipes de conception et d'études.",
                "Ce rôle est clé pour l'entreprise et s'inscrit dans un plan de croissance à long terme.",
                "La maîtrise du néerlandais serait un plus en raison de partenariats internationaux.",
            ],
        },
    }
    
    # Sélectionner un exemple aléatoire
    section_examples = examples.get(section_title, {})
    field_examples = section_examples.get(field_title, [])
    if field_examples:
        return random.choice(field_examples)
    else:
        return "Exemple non disponible."

# -------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
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

# -------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
    advice_db = {
        "Contexte du poste": {
            "Raison de l'ouverture": [
                "- Clarifier si remplacement pour un chantier en cours, création pour un nouveau projet BTP ou évolution interne due à une promotion.",
                "- Identifier le niveau d'urgence lié aux délais de construction et à la priorisation des sites.",
                "- Expliquer le contexte stratégique dans le secteur BTP, comme un nouveau contrat de travaux publics.",
                "- Préciser si le poste est une création pour renforcer l'équipe sur un grand chantier ou une réaffectation pour optimiser les ressources.",
                "- Relier le poste à la stratégie globale de l'entreprise en matière de développement durable dans le BTP."
            ],
            # ... (rest of advice_db remains unchanged)
        }
        # ... (other sections unchanged)
    }

# -------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
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

# -------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
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

# -------------------- Réponse IA aléatoire --------------------
def generate_checklist_advice(section_title, field_title):
    # Liste d'exemples de conseils pour chaque champ, adaptés au contexte BTP
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
    }

    # Sélectionner une réponse aléatoire pour la section et le champ donné
    import random
    section_advice = advice_db.get(section_title, {})
    field_advice = section_advice.get(field_title, [])
    if field_advice:
        return random.choice(field_advice)  # Sélectionner un conseil aléatoire sans modifier la liste
    else:
        return "Pas de conseil disponible."