import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import pickle
import re
import io
import pyperclip
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

# -------------------- Templates de briefs --------------------
BRIEF_TEMPLATES = {
    "Template Vide": {
        category: {item: {"valeur": "", "importance": 3} for item in items}
        for category, items in SIMPLIFIED_CHECKLIST.items()
    }
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
        'perm_result': [],
        'poste_intitule': "",
        'manager_nom': "",
        'recruteur': "Zakaria",
        'affectation_type': "Chantier",
        'affectation_nom': "",
        'brief_data': {},
        'ksa_data': {},
        'comment_libre': "",
        'current_brief_name': "",
        'filtered_briefs': {},
        'show_filtered_results': False
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

def save_briefs():
    """Sauvegarde les briefs"""
    try:
        with open("saved_briefs.pkl", "wb") as f:
            pickle.dump(st.session_state.saved_briefs, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde briefs: {e}")

# -------------------- Génération nom automatique --------------------
def generate_automatic_brief_name():
    """Génère un nom automatique de brief"""
    now = datetime.now()
    return f"{now.strftime('%d-%m-%y')}-{st.session_state.poste_intitule or 'poste'}"

# -------------------- Filtrer briefs --------------------
def filter_briefs(saved_briefs, filter_month=None, filter_recruteur=None,
                  filter_poste=None, filter_manager=None):
    """Filtre les briefs enregistrés"""
    filtered = {}
    for name, data in saved_briefs.items():
        if filter_poste and filter_poste.lower() not in data.get("poste_intitule", "").lower():
            continue
        if filter_manager and filter_manager.lower() not in data.get("manager_nom", "").lower():
            continue
        if filter_recruteur and filter_recruteur.lower() != data.get("recruteur", "").lower():
            continue
        filtered[name] = data
    return filtered

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

            st.session_state.api_usage["used_tokens"] += total_tokens
            st.session_state.api_usage["current_session_tokens"] += total_tokens
            st.session_state["token_counter"] += total_tokens

            return {"content": result["choices"][0]["message"]["content"], "total_tokens": total_tokens}
        else:
            return {"content": f"❌ Erreur API {response.status_code}", "total_tokens": 0}
    except Exception as e:
        return {"content": f"❌ Exception: {str(e)}", "total_tokens": 0}

# -------------------- Générateurs --------------------
def generate_boolean_query(poste, synonymes, comp_oblig, comp_opt, exclusions, localisation, secteur):
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

def generate_annonce(poste, competences):
    prompt = f"""
    Crée une annonce d'emploi attractive et concise pour le poste de {poste}.
    Compétences clés: {competences}
    """
    messages = [
        {"role": "system", "content": "Tu es un expert en rédaction d'annonces d'emploi."},
        {"role": "user", "content": prompt}
    ]
    return ask_deepseek(messages, max_tokens=600).get("content", "")

def generate_accroche_inmail(url_linkedin, poste):
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

# -------------------- Export PDF / Word --------------------
def export_brief_pdf():
    return None  # Implémentation possible si besoin

def export_brief_word():
    return None  # Implémentation possible si besoin

# -------------------- Copier --------------------
def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        st.error(f"Erreur copie: {e}")
        return False
