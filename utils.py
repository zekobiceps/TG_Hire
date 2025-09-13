# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io
import json
import pandas as pd

# -------------------- Disponibilité PDF & Word --------------------
# Ce bloc vérifie si les bibliothèques d'exportation sont installées.
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
    """Initialise l'état de la session pour toutes les variables nécessaires."""
    defaults = {
        "saved_briefs": load_briefs(),
        "brief_phase": "📁 Gestion",
        "avant_brief_completed": False,
        "reunion_completed": False,
        "current_brief_name": "",
        "filtered_briefs": {},
        "ksa_matrix": pd.DataFrame(columns=["Rubrique", "Critère", "Cible / Standard attendu", "Échelle d'évaluation (1-5)", "Évaluateur"]),
        "job_descriptions_db": load_job_descriptions(),
        "manager_nom": "",
        "niveau_hierarchique": "",
        "affectation_type": "",
        "recruteur": "",
        "affectation_nom": "",
        "date_brief": datetime.today().date(),
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
        "notes_libres": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistance des briefs --------------------
def save_briefs():
    """Sauvegarde les briefs dans un fichier JSON."""
    with open("briefs.json", "w") as f:
        briefs_to_save = {}
        for name, data in st.session_state.saved_briefs.items():
            # Convertir les dataframes en dictionnaires pour la sauvegarde
            if "ksa_matrix" in data and isinstance(data["ksa_matrix"], pd.DataFrame):
                data["ksa_matrix"] = data["ksa_matrix"].to_dict('records')
            briefs_to_save[name] = data
        json.dump(briefs_to_save, f, indent=4)

def load_briefs():
    """Charge les briefs depuis un fichier JSON."""
    if os.path.exists("briefs.json"):
        with open("briefs.json", "r") as f:
            try:
                briefs = json.load(f)
                # Convertir les dictionnaires de matrice en dataframe
                for name, data in briefs.items():
                    if "ksa_matrix" in data and isinstance(data["ksa_matrix"], list):
                        briefs[name]["ksa_matrix"] = pd.DataFrame(data["ksa_matrix"])
                return briefs
            except json.JSONDecodeError:
                return {}
    return {}

# -------------------- Gestion des fiches de poste --------------------
def save_job_descriptions():
    """Sauvegarde la base de données des fiches de poste."""
    with open("job_descriptions.json", "w", encoding='utf-8') as f:
        json.dump(st.session_state.job_descriptions_db, f, indent=4, ensure_ascii=False)

def load_job_descriptions():
    """Charge la base de données des fiches de poste."""
    if os.path.exists("job_descriptions.json"):
        with open("job_descriptions.json", "r", encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def find_in_job_db(job_title):
    """Recherche des informations dans la base de données de fiches de poste."""
    for title, content in st.session_state.job_descriptions_db.items():
        if job_title.lower() in title.lower():
            return content
    return None

# -------------------- Conseils IA --------------------
def generate_checklist_advice(field_title):
    """Génère une réponse IA basée sur la catégorie, le titre et le titre du poste."""
    job_title = st.session_state.get("niveau_hierarchique", "un poste générique")
    
    # 1. Priorité à la base de données de fiches de poste
    db_content = find_in_job_db(job_title)
    if db_content:
        # Tenter d'extraire la partie pertinente du contenu de la fiche
        if "compétences" in field_title.lower() and "compétences" in db_content:
            return f"Basé sur la fiche de poste '{job_title}': {db_content['compétences']}"
        elif "tâches" in field_title.lower() and "responsabilités" in db_content:
            return f"Basé sur la fiche de poste '{job_title}': {db_content['responsabilités']}"
        # Sinon, retourner le contenu complet
        return f"Voici des informations pertinentes de la fiche de poste '{job_title}':\n\n{db_content}"

    # 2. Sinon, générer une réponse générique
    prompts = {
        "Raison de l'ouverture": f"Pour le poste de '{job_title}', est-ce une création de poste ou un remplacement ? Si c'est un remplacement, quelle est la raison du départ du prédécesseur (départ à la retraite, démission, promotion interne) ?",
        "Impact stratégique": f"En quoi le poste de '{job_title}' est-il stratégique pour l'entreprise ? Quels sont les objectifs clés et les indicateurs de performance (KPIs) qui lui seront associés ?",
        "Rattachement hiérarchique": f"À qui le futur collaborateur du poste '{job_title}' rendra-t-il compte ? Est-ce qu'il aura des subordonnés ? Quel est l'environnement de travail (matrice, équipe, etc.) ?",
        "Tâches principales": f"Quelles sont les trois tâches les plus importantes pour le poste de '{job_title}' ? Quels sont les projets majeurs sur lesquels il sera amené à travailler ?",
        "Expérience": f"Pour le poste de '{job_title}', quelle expérience minimale est requise ? Quel est le secteur d'activité idéal ? Y a-t-il des expériences spécifiques (gestion de projet, management d'équipe) qui sont indispensables ?",
        "Compétences techniques": f"Quelles sont les compétences techniques (hard skills) essentielles pour le poste de '{job_title}' ? (par exemple: maîtrise d'un logiciel spécifique, langage de programmation, etc.).",
        "Soft skills": f"Quelles sont les qualités interpersonnelles (soft skills) que vous recherchez en priorité pour ce poste de '{job_title}' ? (par exemple: esprit d'équipe, autonomie, leadership).",
        "Profil idéal": f"Pour le poste de '{job_title}', quel est le profil type ? Existe-t-il des entreprises cibles ou des secteurs d'activité similaires où l'on trouve ce type de profil ?",
        "Synonymes de poste": f"Quels sont les synonymes de titre de poste pour '{job_title}' ? (par exemple: Chef de projet = Project Manager, etc.).",
        "Canaux de recrutement": f"Où pouvons-nous trouver ce type de profil pour le poste de '{job_title}' ? (par exemple: Linkedin, Apec, jobboards, etc.).",
        "Budget et salaire": f"Quel est le budget salarial pour le poste de '{job_title}' ? Y a-t-il des primes ou des avantages sociaux ?",
    }
    return prompts.get(field_title, f"Je peux vous aider à définir la section '{field_title}' pour le poste de '{job_title}'.")

# -------------------- Filtre --------------------
def filter_briefs(briefs, month, recruteur, poste, manager):
    filtered = {}
    for name, data in briefs.items():
        match = True
        if month and data.get("date_brief", "") and data["date_brief"].split("-")[1] != month:
            match = False
        if recruteur and recruteur.lower() not in data.get("recruteur", "").lower():
            match = False
        if poste and poste.lower() not in data.get("poste_a_recruter", "").lower():
            match = False
        if manager and manager.lower() not in data.get("manager_nom", "").lower():
            match = False
        if match:
            filtered[name] = data
    return filtered

def generate_automatic_brief_name():
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d')}_{st.session_state.get('niveau_hierarchique', 'Nouveau')}"
    
def export_brief_pdf(brief_data):
    """Génère un PDF à partir des données du brief."""
    if not PDF_AVAILABLE:
        st.error("Reportlab n'est pas installé. Veuillez l'installer avec `pip install reportlab` pour utiliser cette fonction.")
        return
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Synthèse Brief")
    styles = getSampleStyleSheet()
    story = []

    # Titre principal
    story.append(Paragraph("Synthèse du Brief de recrutement", styles['Title']))
    story.append(Spacer(1, 12))

    # Informations clés
    story.append(Paragraph("<b>1. Informations clés</b>", styles['Heading2']))
    info_list = [
        ("Intitulé du poste", brief_data.get("niveau_hierarchique")),
        ("Nom du manager", brief_data.get("manager_nom")),
        ("Recruteur", brief_data.get("recruteur")),
        ("Date du brief", str(brief_data.get("date_brief"))),
    ]
    for key, value in info_list:
        story.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Avant-brief
    story.append(Paragraph("<b>2. Avant-brief (Phase 1)</b>", styles['Heading2']))
    avant_brief_data = [
        ("Raison de l'ouverture", brief_data.get("raison_ouverture")),
        ("Impact stratégique", brief_data.get("impact_strategique")),
        ("Rattachement hiérarchique", brief_data.get("rattachement")),
        ("Tâches principales", brief_data.get("taches_principales")),
        ("Expérience (Must Have)", brief_data.get("must_have_experience")),
        ("Diplômes (Must Have)", brief_data.get("must_have_diplomes")),
        ("Compétences techniques (Must Have)", brief_data.get("must_have_competences")),
        ("Soft skills (Must Have)", brief_data.get("must_have_softskills")),
        ("Expérience (Nice to Have)", brief_data.get("nice_to_have_experience")),
        ("Diplômes (Nice to Have)", brief_data.get("nice_to_have_diplomes")),
        ("Compétences techniques (Nice to Have)", brief_data.get("nice_to_have_competences")),
        ("Entreprises ou profil similaire", brief_data.get("entreprises_profil")),
        ("Synonymes du poste", brief_data.get("synonymes_poste")),
        ("Canaux à prioriser", brief_data.get("canaux_profil")),
        ("Budget et package salarial", brief_data.get("budget")),
        ("Notes libres", brief_data.get("notes_libres")),
    ]
    for key, value in avant_brief_data:
        story.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    story.append(Spacer(1, 12))

    # KSA Matrix
    story.append(Paragraph("<b>3. Matrice KSA</b>", styles['Heading2']))
    if not brief_data["ksa_matrix"].empty:
        df = brief_data["ksa_matrix"]
        data_table = [df.columns.tolist()] + df.values.tolist()
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ])
        table = Table(data_table)
        table.setStyle(table_style)
        story.append(table)
    else:
        story.append(Paragraph("Aucune donnée KSA enregistrée.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

def export_brief_word(brief_data):
    """Génère un document Word à partir des données du brief."""
    if not WORD_AVAILABLE:
        st.error("Python-docx n'est pas installé. Veuillez l'installer avec `pip install python-docx` pour utiliser cette fonction.")
        return
    
    doc = Document()
    doc.add_heading("Synthèse du Brief de recrutement", 0)

    # Informations clés
    doc.add_heading("1. Informations clés", level=1)
    doc.add_paragraph(f"Intitulé du poste : {brief_data.get('niveau_hierarchique', '')}")
    doc.add_paragraph(f"Nom du manager : {brief_data.get('manager_nom', '')}")
    doc.add_paragraph(f"Recruteur : {brief_data.get('recruteur', '')}")
    doc.add_paragraph(f"Date du brief : {str(brief_data.get('date_brief', ''))}")
    
    # Avant-brief
    doc.add_heading("2. Avant-brief (Phase 1)", level=1)
    avant_brief_fields = [
        ("Raison de l'ouverture", "raison_ouverture"),
        ("Impact stratégique", "impact_strategique"),
        ("Rattachement hiérarchique", "rattachement"),
        ("Tâches principales", "taches_principales"),
        ("Expérience (Must Have)", "must_have_experience"),
        ("Diplômes (Must Have)", "must_have_diplomes"),
        ("Compétences techniques (Must Have)", "must_have_competences"),
        ("Soft skills (Must Have)", "must_have_softskills"),
        ("Expérience (Nice to Have)", "nice_to_have_experience"),
        ("Diplômes (Nice to Have)", "nice_to_have_diplomes"),
        ("Compétences techniques (Nice to Have)", "nice_to_have_competences"),
        ("Entreprises ou profil similaire", "entreprises_profil"),
        ("Synonymes du poste", "synonymes_poste"),
        ("Canaux à prioriser", "canaux_profil"),
        ("Budget et package salarial", "budget"),
        ("Notes libres", "notes_libres"),
    ]
    for label, key in avant_brief_fields:
        doc.add_paragraph(f"{label} : {brief_data.get(key, '')}")
    
    # KSA Matrix
    doc.add_heading("3. Matrice KSA", level=1)
    if not brief_data["ksa_matrix"].empty:
        df = brief_data["ksa_matrix"]
        table = doc.add_table(df.shape[0] + 1, df.shape[1])
        # Add table headers
        for j in range(df.shape[1]):
            table.cell(0, j).text = df.columns[j]
        # Add table data
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                table.cell(i + 1, j).text = str(df.iloc[i, j])
    else:
        doc.add_paragraph("Aucune donnée KSA enregistrée.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer