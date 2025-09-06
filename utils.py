import streamlit as st
import requests
import json
import time
from datetime import datetime
import pandas as pd
import os
import pickle
import re
import io
import webbrowser
from urllib.parse import quote

# Imports optionnels pour l'export PDF/Word
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Inches
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# Configuration de l'API DeepSeek
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception as e:
    st.error("Clé API non configurée.")
    st.stop()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# -------------------- Constantes --------------------
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

KSA_MODEL = {
    "Knowledge (Connaissances)": [
        "Ex. Connaissance du droit du travail",
        "Ex. Connaissance des outils ATS"
    ],
    "Skills (Savoir-faire)": [
        "Ex. Conduite d'entretien structuré",
        "Ex. Rédaction d'annonces attractives",
        "Ex. Négociation avec candidats"
    ],
    "Abilities (Aptitudes)": [
        "Ex. Analyse et synthèse",
        "Ex. Résilience face aux refus",
        "Ex. Gestion du stress"
    ]
}

# -------------------- Gestion des données locales --------------------
def load_saved_briefs():
    try:
        if os.path.exists("saved_briefs.pkl"):
            with open("saved_briefs.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return {}

def load_sourcing_history():
    try:
        if os.path.exists("sourcing_history.pkl"):
            with open("sourcing_history.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return []

def save_sourcing_history():
    try:
        with open("sourcing_history.pkl", "wb") as f:
            pickle.dump(st.session_state.sourcing_history, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde historique: {e}")

def load_library_entries():
    try:
        if os.path.exists("library_entries.pkl"):
            with open("library_entries.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return []

def save_library_entries():
    try:
        with open("library_entries.pkl", "wb") as f:
            pickle.dump(st.session_state.library_entries, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde bibliothèque: {e}")

def generate_automatic_brief_name():
    now = datetime.now()
    date_str = f"{now.strftime('%d')}/{now.strftime('%m')}/{now.strftime('%y')}"
    poste = st.session_state.get('poste_intitule', '').replace(' ', '-').lower()
    manager = st.session_state.get('manager_nom', '').replace(' ', '-').lower()
    recruteur = st.session_state.get('recruteur', '').lower()
    affectation = st.session_state.get('affectation_nom', '').replace(' ', '-').lower()
    return f"{date_str}-{poste}-{manager}-{recruteur}-{affectation}"

def init_session_state():
    saved_briefs = load_saved_briefs()
    sourcing_history = load_sourcing_history()
    library_entries = load_library_entries()

    defaults = {
        'brief_data': {category: {item: {"valeur": "", "importance": 3} for item in items} for category, items in SIMPLIFIED_CHECKLIST.items()},
        'ksa_data': {},
        'current_brief_name': "",
        'poste_intitule': "",
        'manager_nom': "",
        'recruteur': "Zakaria",
        'affectation_type': "Chantier",
        'affectation_nom': "",
        'saved_briefs': saved_briefs,
        'sourcing_history': sourcing_history,
        'library_entries': library_entries,
        'api_usage': {
            "total_tokens": 800000,
            "used_tokens": 0,
            "current_session_tokens": 0
        },
        'token_counter': 0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_briefs():
    try:
        with open("saved_briefs.pkl", "wb") as f:
            pickle.dump(st.session_state.saved_briefs, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")

# -------------------- DeepSeek API --------------------
def ask_deepseek(messages, max_tokens=500, response_format="text"):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    if response_format == "tableau" and messages:
        messages[-1]["content"] += "\n\nRéponds OBLIGATOIREMENT sous forme de tableau markdown avec des colonnes appropriées."

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)

            # 🔥 Mise à jour des compteurs
            st.session_state.api_usage["used_tokens"] += total_tokens
            st.session_state.api_usage["current_session_tokens"] += total_tokens
            st.session_state["token_counter"] = st.session_state.get("token_counter", 0) + total_tokens

            return {
                "content": result["choices"][0]["message"]["content"],
                "total_tokens": total_tokens
            }
        else:
            return {"content": f"❌ Erreur {response.status_code}", "total_tokens": 0}

    except Exception as e:
        return {"content": f"❌ Erreur: {str(e)}", "total_tokens": 0}
