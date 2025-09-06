import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import pickle
import re
import io
import pyperclip  # ✅ pour copier correctement
from urllib.parse import quote

# -------------------- Optionnels PDF / Word --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# -------------------- API DeepSeek --------------------
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error("Clé API DeepSeek non configurée dans .streamlit/secrets.toml")
    st.stop()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# -------------------- Checklist LEDR simplifiée --------------------
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
    "Compétences - Modèle KSA": [],
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

# -------------------- Modèle KSA --------------------
KSA_MODEL = {
    "Knowledge (Connaissances)": ["Ex. Connaissance du droit du travail"],
    "Skills (Savoir-faire)": ["Ex. Conduite d'entretien structuré"],
    "Abilities (Aptitudes)": ["Ex. Gestion du stress"]
}

# -------------------- Initialisation Session --------------------
def init_session_state():
    """Initialise tous les états nécessaires"""
    defaults = {
        'saved_briefs': {},
        'sourcing_history': [],
        'library_entries': [],
        'api_usage': {
            "total_tokens": 800000,
            "used_tokens": 0,
            "current_session_tokens": 0
        },
        'token_counter': 0,
        'current_messages': [],
        'magicien_reponse': "",
        'boolean_query': "",
        'xray_query': "",
        'cse_query': "",
        'scraper_result': "",
        'scraper_emails': set(),
        'inmail_message': "",
        'perm_result': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# -------------------- Sauvegardes --------------------
def save_library_entries():
    """Sauvegarde la bibliothèque"""
    try:
        with open("library_entries.pkl", "wb") as f:
            pickle.dump(st.session_state.library_entries, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde bibliothèque: {e}")

# -------------------- API DeepSeek --------------------
def ask_deepseek(messages, max_tokens=500, response_format="text"):
    """Appelle l'API DeepSeek et met à jour le compteur de tokens"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    if response_format == "tableau" and messages:
        messages[-1]["content"] += "\nRéponds obligatoirement en tableau markdown."

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=40)
        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)

            # 🔥 Mise à jour des compteurs
            st.session_state.api_usage["used_tokens"] += total_tokens
            st.session_state.api_usage["current_session_tokens"] += total_tokens
            st.session_state["token_counter"] += total_tokens

            return {"content": result["choices"][0]["message"]["content"], "total_tokens": total_tokens}
        else:
            return {"content": f"❌ Erreur API {response.status_code}", "total_tokens": 0}
    except Exception as e:
        return {"content": f"❌ Exception: {str(e)}", "total_tokens": 0}

# -------------------- Générateurs de requêtes --------------------
def generate_boolean_query(poste, synonymes, comp_oblig, comp_opt, exclusions, localisation, secteur):
    """Construit une requête Boolean"""
    query_parts = []
    if poste:
        poste_part = f'("{poste}"'
        if synonymes:
            for syn in synonymes.split(','):
                poste_part += f' OR "{syn.strip()}"'
        poste_part += ")"
        query_parts.append(poste_part)
    if comp_oblig:
        for c in comp_oblig.split(','):
            query_parts.append(f'"{c.strip()}"')
    if comp_opt:
        opt = "(" + " OR ".join([f'"{c.strip()}"' for c in comp_opt.split(',')]) + ")"
        query_parts.append(opt)
    if localisation:
        query_parts.append(f'"{localisation}"')
    if secteur:
        query_parts.append(f'"{secteur}"')

    query = " AND ".join(query_parts)
    if exclusions:
        for e in exclusions.split(','):
            query += f' NOT "{e.strip()}"'
    return query

def generate_xray_query(site, poste, mots_cles, localisation):
    """Construit une requête X-Ray Google"""
    site_urls = {"LinkedIn": "site:linkedin.com/in/", "GitHub": "site:github.com"}
    query = site_urls.get(site, "site:linkedin.com/in/") + " "
    if poste:
        query += f'"{poste}" '
    if mots_cles:
        for mot in mots_cles.split(','):
            query += f'"{mot.strip()}" '
    if localisation:
        query += f'"{localisation}" '
    return query.strip()

def generate_accroche_inmail(url_linkedin, poste):
    """Accroche InMail courte"""
    prompt = f"""
    Crée une accroche InMail courte et professionnelle.
    Poste: {poste}
    Profil LinkedIn: {url_linkedin}
    """
    messages = [
        {"role": "system", "content": "Tu es un expert en recrutement. Crée des messages engageants et courts."},
        {"role": "user", "content": prompt}
    ]
    return ask_deepseek(messages, max_tokens=250).get("content", "")

# -------------------- Utilitaire Copier --------------------
def copy_to_clipboard(text):
    """Copie une chaîne dans le presse-papier"""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        st.error(f"Erreur copie: {e}")
        return False
# -------------------- Export Brief en PDF --------------------
def export_brief_pdf():
    """Exporte le brief en PDF"""
    if not PDF_AVAILABLE:
        st.error("Module reportlab non installé. Utilisez : pip install reportlab")
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Titre
        story.append(Paragraph("Brief Recrutement", styles['Heading1']))
        story.append(Spacer(1, 20))

        # Infos principales
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

        # Sections
        if "brief_data" in st.session_state:
            for cat, items in st.session_state["brief_data"].items():
                story.append(Paragraph(cat, styles['Heading2']))
                for item, data in items.items():
                    if isinstance(data, dict):
                        val = data.get("valeur", "")
                    else:
                        val = str(data)
                    if val:
                        story.append(Paragraph(f"<b>{item}:</b> {val}", styles['Normal']))
                story.append(Spacer(1, 15))

        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erreur PDF: {e}")
        return None


# -------------------- Export Brief en Word --------------------
def export_brief_word():
    """Exporte le brief en Word"""
    if not WORD_AVAILABLE:
        st.error("Module python-docx non installé. Utilisez : pip install python-docx")
        return None

    try:
        doc = Document()
        doc.add_heading("Brief Recrutement", 0)

        # Infos principales
        infos = {
            "Poste": st.session_state.get("poste_intitule", ""),
            "Manager": st.session_state.get("manager_nom", ""),
            "Recruteur": st.session_state.get("recruteur", ""),
            "Affectation": f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"
        }
        for k, v in infos.items():
            doc.add_paragraph(f"{k}: {v}")

        # Sections
        if "brief_data" in st.session_state:
            for cat, items in st.session_state["brief_data"].items():
                doc.add_heading(cat, level=1)
                for item, data in items.items():
                    if isinstance(data, dict):
                        val = data.get("valeur", "")
                    else:
                        val = str(data)
                    if val:
                        doc.add_paragraph(f"{item}: {val}")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erreur Word: {e}")
        return None
