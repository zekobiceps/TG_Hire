import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import pickle
import re
from bs4 import BeautifulSoup

# -------------------- API --------------------
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error("Clé API DeepSeek non configurée")
    st.stop()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# -------------------- Persistence --------------------
def load_pickle(file, default):
    if os.path.exists(file):
        try:
            with open(file, "rb") as f:
                return pickle.load(f)
        except Exception:
            return default
    return default

def save_pickle(file, data):
    try:
        with open(file, "wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde {file}: {e}")

# -------------------- Initialisation --------------------
def init_session_state():
    defaults = {
        'library_entries': load_pickle("library_entries.pkl", []),
        'api_usage': {"total_tokens": 800000, "used_tokens": 0, "current_session_tokens": 0},
        'token_counter': 0,
        'magicien_reponse': "",
        'magicien_history': load_pickle("magicien_history.pkl", []),
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

# -------------------- Sauvegarde --------------------
def save_library_entries():
    save_pickle("library_entries.pkl", st.session_state.library_entries)

# -------------------- DeepSeek --------------------
def ask_deepseek(messages, max_tokens=500):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7, "max_tokens": max_tokens}
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
            return {"content": f"❌ Erreur API {response.status_code}"}
    except Exception as e:
        return {"content": f"❌ Exception: {str(e)}"}

# -------------------- Queries --------------------
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
        query_parts.append("(" + " OR ".join([f'"{c.strip()}"' for c in comp_opt.split(',')]) + ")")
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

def generate_accroche_inmail(url_linkedin, poste):
    prompt = f"Crée une accroche InMail courte et professionnelle.\nPoste: {poste}\nProfil LinkedIn: {url_linkedin}"
    messages = [{"role": "system", "content": "Tu es un expert en recrutement."},
                {"role": "user", "content": prompt}]
    return ask_deepseek(messages, max_tokens=250).get("content", "")

# -------------------- Charika Email --------------------
def get_email_from_charika(entreprise):
    """Cherche un email sur charika.ma en utilisant Google"""
    try:
        search_url = f"https://www.google.com/search?q={entreprise}+site:charika.ma"
        r = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        links = [a['href'] for a in soup.find_all('a', href=True) if "charika.ma/societe" in a['href']]
        if links:
            page = requests.get(links[0], headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", page.text)
            if emails:
                return emails[0]
    except Exception:
        return None
    return None
