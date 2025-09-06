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

# Imports optionnels pour l'export PDF/Word
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

# Configuration API DeepSeek
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error("Clé API DeepSeek non configurée dans .streamlit/secrets.toml")
    st.stop()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# -------------------- Session State --------------------
def init_session_state():
    """Initialise les variables globales de session"""
    defaults = {
        "library_entries": [],
        "sourcing_history": [],
        "saved_briefs": {},
        "api_usage": {
            "total_tokens": 800000,
            "used_tokens": 0,
            "current_session_tokens": 0
        },
        "token_counter": 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# -------------------- Fichiers persistants --------------------
def save_library_entries():
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
        messages[-1]["content"] += "\n\nRéponds OBLIGATOIREMENT sous forme de tableau markdown."

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
            st.session_state["token_counter"] += total_tokens

            return {
                "content": result["choices"][0]["message"]["content"],
                "total_tokens": total_tokens
            }
        else:
            return {"content": f"❌ Erreur {response.status_code}", "total_tokens": 0}
    except Exception as e:
        return {"content": f"❌ Erreur: {str(e)}", "total_tokens": 0}

# -------------------- Générateurs --------------------
def generate_boolean_query(poste, synonymes, competences_obligatoires, competences_optionnelles, exclusions, localisation, secteur):
    """Construit une requête Boolean"""
    query_parts = []
    if poste:
        poste_part = f'("{poste}"'
        if synonymes:
            for syn in synonymes.split(","):
                poste_part += f' OR "{syn.strip()}"'
        poste_part += ")"
        query_parts.append(poste_part)

    if competences_obligatoires:
        for comp in competences_obligatoires.split(","):
            query_parts.append(f'"{comp.strip()}"')

    if competences_optionnelles:
        opt_part = "(" + " OR ".join([f'"{c.strip()}"' for c in competences_optionnelles.split(",")]) + ")"
        query_parts.append(opt_part)

    if localisation:
        query_parts.append(f'"{localisation}"')
    if secteur:
        query_parts.append(f'"{secteur}"')

    query = " AND ".join(query_parts)

    if exclusions:
        for excl in exclusions.split(","):
            query += f' NOT "{excl.strip()}"'

    return query

def generate_xray_query(site, poste, mots_cles, localisation):
    """Construit une requête X-Ray Google"""
    site_urls = {
        "LinkedIn": "site:linkedin.com/in/",
        "GitHub": "site:github.com",
        "Indeed": "site:indeed.com"
    }
    query = f"{site_urls.get(site, 'site:linkedin.com/in/')} "
    if poste:
        query += f'"{poste}" '
    if mots_cles:
        query += " ".join([f'"{mot.strip()}"' for mot in mots_cles.split(",")])
    if localisation:
        query += f'"{localisation}"'
    return query.strip()

def generate_accroche_inmail(url_linkedin, poste):
    """Génère une accroche InMail personnalisée"""
    prompt = f"""
    Crée une accroche InMail percutante pour contacter un candidat sur LinkedIn.
    Poste à pourvoir: {poste}
    Profil LinkedIn: {url_linkedin}
    L'accroche doit être courte (4-5 lignes max), professionnelle mais chaleureuse,
    et toujours orientée recrutement RH.
    """
    messages = [
        {"role": "system", "content": "Tu es un expert en recrutement RH. Crée des messages courts et engageants."},
        {"role": "user", "content": prompt}
    ]
    response = ask_deepseek(messages, max_tokens=300)
    return response["content"] if "content" in response else "Erreur de génération"
