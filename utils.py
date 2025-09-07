# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io
import re
import requests

# -------------------- Disponibilité PDF & Word --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# -------------------- Checklist simplifiée --------------------
SIMPLIFIED_CHECKLIST = {
    "Contexte du Poste et Environnement": [
        "Pourquoi ce poste est-il ouvert?",
        "Fourchette budgétaire (entre X et Y)",
        "Date de prise de poste souhaitée",
        "Équipe (taille, composition)",
        "Manager (poste, expertise, style)",
        "Collaborations internes/externes",
        "Lieux de travail et déplacements"
    ],
    "Missions et Responsabilités": [
        "Mission principale du poste",
        "Objectifs à atteindre (3-5 maximum)",
        "Sur quoi la performance sera évaluée?",
        "3-5 Principales tâches quotidiennes",
        "2 Tâches les plus importantes/critiques",
        "Outils informatiques à maitriser"
    ],
    "Profil et Formation": [
        "Expérience minimum requise",
        "Formation/diplôme nécessaire"
    ],
    "Stratégie de Recrutement": [
        "Pourquoi recruter maintenant?",
        "Difficultés anticipées",
        "Mot-clés cruciaux (CV screening)",
        "Canaux de sourcing prioritaires",
        "Plans B : Autres postes, Revoir certains critères...",
        "Exemple d'un profil cible sur LinkedIn",
        "Processus de sélection étape par étape"
    ]
}

# -------------------- Templates de Brief --------------------
BRIEF_TEMPLATES = {
    "Template standard": {
        "Contexte": {
            "Objectifs": {"valeur": "Définir clairement les besoins", "importance": 3},
            "Budget": {"valeur": "Selon projet", "importance": 2},
        },
        "Profil recherché": {
            "Compétences techniques": {"valeur": "Ex: Autocad, Robot Structural Analysis", "importance": 3},
            "Soft skills": {"valeur": "Esprit d’équipe, autonomie", "importance": 2},
        },
    },
    "Template direction": {
        "Contexte": {
            "Objectifs": {"valeur": "Alignement avec stratégie groupe", "importance": 3},
            "Budget": {"valeur": "Validé par direction", "importance": 2},
        },
        "Profil recherché": {
            "Compétences techniques": {"valeur": "Leadership, gestion multi-projets", "importance": 3},
            "Soft skills": {"valeur": "Communication, stratégie", "importance": 2},
        },
    },
}

# -------------------- Initialisation Session --------------------
def init_session_state():
    """Initialise les variables de session par défaut"""
    defaults = {
        "poste_intitule": "",
        "manager_nom": "",
        "recruteur": "",
        "affectation_type": "Chantier",
        "affectation_nom": "",
        "current_brief_name": "",
        "saved_briefs": {},
        "filtered_briefs": {},
        "show_filtered_results": False,
        "brief_data": {},
        "ksa_data": {},
        "comment_libre": "",
        "library_entries": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistence --------------------
def save_briefs():
    """Sauvegarde des briefs en fichier pickle"""
    with open("briefs.pkl", "wb") as f:
        pickle.dump(st.session_state.saved_briefs, f)

def load_briefs():
    """Chargement des briefs depuis pickle"""
    if os.path.exists("briefs.pkl"):
        with open("briefs.pkl", "rb") as f:
            return pickle.load(f)
    return {}

def save_library_entries():
    """Sauvegarde de la bibliothèque"""
    with open("library_entries.pkl", "wb") as f:
        pickle.dump(st.session_state.library_entries, f)

def load_library_entries():
    """Chargement de la bibliothèque"""
    if os.path.exists("library_entries.pkl"):
        with open("library_entries.pkl", "rb") as f:
            return pickle.load(f)
    return []

# -------------------- Brief --------------------
def generate_automatic_brief_name():
    """Génère un nom automatique pour un brief"""
    poste = st.session_state.get("poste_intitule", "Poste")
    manager = st.session_state.get("manager_nom", "Manager")
    recruteur = st.session_state.get("recruteur", "Recruteur")
    date = datetime.now().strftime("%Y%m%d")
    return f"{poste}_{manager}_{recruteur}_{date}"

def filter_briefs(saved_briefs, month=None, recruteur=None, poste=None, manager=None):
    """Filtrer les briefs existants"""
    results = {}
    for name, data in saved_briefs.items():
        if month and month not in name:
            continue
        if recruteur and data.get("recruteur") != recruteur:
            continue
        if poste and poste.lower() not in data.get("poste_intitule", "").lower():
            continue
        if manager and manager.lower() not in data.get("manager_nom", "").lower():
            continue
        results[name] = data
    return results

# -------------------- Conseils IA --------------------
def generate_checklist_advice(category, item):
    """Génère des conseils simplifiés (placeholder IA)"""
    conseils = {
        "Pourquoi ce poste est-il ouvert?": "- Clarifier le départ ou création de poste\n- Identifier l'urgence\n- Relier au contexte business",
        "Mission principale du poste": "- Décrire en une phrase claire\n- Lier aux objectifs stratégiques\n- Éviter les tâches trop détaillées",
        "Objectifs à atteindre (3-5 maximum)": "- Formuler en SMART\n- Limiter à 3-5\n- Mesurables et précis",
    }
    return conseils.get(item, f"- Fournir des détails pratiques pour {item}\n- Exemple concret\n- Piège à éviter")

# -------------------- Export PDF --------------------
def export_brief_pdf():
    """Exporte le brief courant en PDF (si reportlab dispo)"""
    if not PDF_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Brief Recrutement", styles['Heading1']))
    story.append(Spacer(1, 20))

    infos = [
        ["Poste", st.session_state.get("poste_intitule", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"]
    ]
    table = Table(infos, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    if "brief_data" in st.session_state:
        for cat, items in st.session_state["brief_data"].items():
            story.append(Paragraph(cat, styles['Heading2']))
            for item, data in items.items():
                val = data.get("valeur", "") if isinstance(data, dict) else str(data)
                if val:
                    story.append(Paragraph(f"<b>{item}:</b> {val}", styles['Normal']))
            story.append(Spacer(1, 15))

    if "ksa_data" in st.session_state:
        for cat, comps in st.session_state["ksa_data"].items():
            story.append(Paragraph(cat, styles['Heading2']))
            for comp, details in comps.items():
                story.append(Paragraph(f"- {comp} ({details})", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------- Export Word --------------------
def export_brief_word():
    """Exporte le brief courant en Word (si python-docx dispo)"""
    if not WORD_AVAILABLE:
        return None

    doc = Document()
    doc.add_heading("Brief Recrutement", 0)

    infos = {
        "Poste": st.session_state.get("poste_intitule", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Affectation": f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"
    }
    for k, v in infos.items():
        doc.add_paragraph(f"{k}: {v}")

    if "brief_data" in st.session_state:
        for cat, items in st.session_state["brief_data"].items():
            doc.add_heading(cat, level=1)
            for item, data in items.items():
                val = data.get("valeur", "") if isinstance(data, dict) else str(data)
                if val:
                    doc.add_paragraph(f"{item}: {val}")

    if "ksa_data" in st.session_state:
        for cat, comps in st.session_state["ksa_data"].items():
            doc.add_heading(cat, level=2)
            for comp, details in comps.items():
                doc.add_paragraph(f"{comp}: {details}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
