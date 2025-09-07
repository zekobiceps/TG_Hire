import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import pickle
import re

# -------------------- Configuration API DeepSeek --------------------
try:
    DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "demo-key")
except Exception:
    DEEPSEEK_API_KEY = "demo-key"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# -------------------- Checklist & KSA --------------------
SIMPLIFIED_CHECKLIST = {
    "Contexte & Environnement": [
        "Pourquoi ce poste est-il ouvert?",
        "Fourchette budgétaire (ex: 1000-2000)",
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
        "Principales tâches quotidiennes (3-5 max)",
        "2 Tâches les plus importantes/critiques",
        "Outils informatique à maîtriser"
    ],
    "Stratégie de Recrutement": [
        "Pourquoi recruter maintenant?",
        "Difficultés anticipées",
        "Mot-clés cruciaux (CV screening)",
        "Canaux de sourcing prioritaires",
        "Processus de sélection étape par étape",
        "Plans B : Autres postes, Revoir certains critères...",
        "Exemple d'un profil cible sur LinkedIn"
    ],
    "Proposition de valeur candidat": [
        "Avantages principaux du poste",
        "Opportunités de développement",
        "Éléments différenciants de l'entreprise",
        "Points forts de l'environnement de travail"
    ]
}

KSA_STRUCTURE = {
    "Knowledge (Connaissances)": [],
    "Skills (Savoir-faire)": [],
    "Abilities (Aptitudes)": []
}

RECRUTEURS = ["Zakaria", "Sara", "Jalal", "Bouchra"]
RECRUTEURS_INITIALES = {"Zakaria": "ZM", "Sara": "SR", "Jalal": "JL", "Bouchra": "BC"}

# -------------------- Persistence --------------------
def load_saved_briefs():
    if os.path.exists("saved_briefs.pkl"):
        try:
            with open("saved_briefs.pkl", "rb") as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_briefs():
    try:
        with open("saved_briefs.pkl", "wb") as f:
            pickle.dump(st.session_state.saved_briefs, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde briefs: {e}")

# -------------------- Init session --------------------
def init_session_state():
    defaults = {
        'contexte_data': {item: "" for item in SIMPLIFIED_CHECKLIST["Contexte & Environnement"]},
        'missions_data': {item: "" for item in SIMPLIFIED_CHECKLIST["Missions et Responsabilités"]},
        'strategie_data': {item: "" for item in SIMPLIFIED_CHECKLIST["Stratégie de Recrutement"]},
        'valeur_data': {item: "" for item in SIMPLIFIED_CHECKLIST["Proposition de valeur candidat"]},
        'ksa_data': {k: [] for k in KSA_STRUCTURE},
        'current_brief_name': "",
        'poste_intitule': "",
        'manager_nom': "",
        'recruteur': RECRUTEURS[0],
        'affectation_type': "Chantier",
        'affectation_nom': "",
        'commentaires': "",
        'saved_briefs': load_saved_briefs(),
        'api_usage': {"total_tokens": 800000, "used_tokens": 0, "current_session_tokens": 0},
        'current_messages': [],
        'brief_phase': "📁 Gestion",
        'advice_visibility': {},
        'current_advice': None,
        'current_category': None,
        'current_item': None,
        'show_advice_buttons': True,
        'filtre_mois': "",
        'filtre_recruteur': "",
        'filtre_poste': "",
        'filtre_manager': "",
        'filtered_briefs': {},
        'show_filtered_results': False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- DeepSeek --------------------
def ask_deepseek(messages, max_tokens=500):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7, "max_tokens": max_tokens}
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            st.session_state.api_usage["used_tokens"] += usage.get("total_tokens", 0)
            st.session_state.api_usage["current_session_tokens"] += usage.get("total_tokens", 0)
            return {"content": result["choices"][0]["message"]["content"]}
        return {"content": f"❌ Erreur API {response.status_code}"}
    except Exception as e:
        return {"content": f"❌ Exception: {e}"}

# -------------------- Helpers --------------------
def generate_automatic_brief_name():
    date_str = datetime.now().strftime("%d%m%y")
    recruteur_initials = RECRUTEURS_INITIALES.get(st.session_state.recruteur, "RC")
    poste_short = st.session_state.poste_intitule[:10].replace(" ", "") if st.session_state.poste_intitule else "Poste"
    manager_short = st.session_state.manager_nom[:10].replace(" ", "") if st.session_state.manager_nom else "Manager"
    return f"{date_str}-{poste_short}-{manager_short}-{recruteur_initials}"

def filter_briefs(month_filter=None, recruteur_filter=None, poste_filter=None, manager_filter=None):
    results = {}
    for name, data in st.session_state.saved_briefs.items():
        if month_filter and month_filter not in name:
            continue
        if recruteur_filter and data.get("recruteur") != recruteur_filter:
            continue
        if poste_filter and poste_filter.lower() not in data.get("poste_intitule", "").lower():
            continue
        if manager_filter and manager_filter.lower() not in data.get("manager_nom", "").lower():
            continue
        results[name] = data
    return results

# -------------------- App --------------------
init_session_state()
st.set_page_config(page_title="TG-Hire IA - Assistant Recrutement", page_icon="🤖", layout="wide")

st.sidebar.title("🤖 TG-Hire IA")
page = st.sidebar.radio("Navigation", ["📋 Brief", "🔍 Sourcing", "👥 Entretien", "📊 Candidats", "📄 Analyse CV"])

if page == "📋 Brief":
    st.title("📋 Brief Recrutement")
    brief_phase = st.radio("Phase du Brief:", ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)
    st.session_state.brief_phase = brief_phase

    # -------------------- Phase Gestion --------------------
    if brief_phase == "📁 Gestion":
        st.header("📁 Gestion du Brief")
        st.text_input("Intitulé du poste:", key="poste_intitule")
        st.text_input("Nom du manager:", key="manager_nom")
        st.selectbox("Recruteur:", RECRUTEURS, key="recruteur")
        st.text_input("Nom affectation:", key="affectation_nom")

        if st.button("💾 Sauvegarder"):
            name = generate_automatic_brief_name()
            st.session_state.current_brief_name = name
            st.session_state.saved_briefs[name] = {
                "poste_intitule": st.session_state.poste_intitule,
                "manager_nom": st.session_state.manager_nom,
                "recruteur": st.session_state.recruteur,
                "affectation_nom": st.session_state.affectation_nom,
                "contexte_data": st.session_state.contexte_data,
                "missions_data": st.session_state.missions_data,
                "strategie_data": st.session_state.strategie_data,
                "valeur_data": st.session_state.valeur_data,
                "ksa_data": st.session_state.ksa_data,
                "commentaires": st.session_state.commentaires
            }
            save_briefs()
            st.success(f"Brief sauvegardé: {name}")

    # -------------------- Phase Avant-brief / Réunion --------------------
    else:
        st.header(f"{brief_phase}")
        sections = {
            "Contexte & Environnement": st.session_state.contexte_data,
            "Missions et Responsabilités": st.session_state.missions_data,
            "Stratégie de Recrutement": st.session_state.strategie_data,
            "Proposition de valeur candidat": st.session_state.valeur_data
        }
        selected = st.selectbox("Section:", list(sections.keys()))
        for item in SIMPLIFIED_CHECKLIST[selected]:
            st.text_area(item, key=f"{selected}_{item}")

        # Matrice KSA
        st.subheader("📊 Matrice KSA")
        for cat in KSA_STRUCTURE:
            with st.expander(cat, expanded=True):
                for i, comp in enumerate(st.session_state.ksa_data.get(cat, [])):
                    st.text_input("Compétence", value=comp["competence"], key=f"{cat}_comp_{i}")

elif page == "🔍 Sourcing":
    st.title("🔍 Outils de Sourcing")
    st.info("En cours...")

elif page == "👥 Entretien":
    st.title("👥 Assistant IA")
    st.info("En cours...")

elif page == "📊 Candidats":
    st.title("📊 Suivi des Candidats")
    st.info("En cours...")

elif page == "📄 Analyse CV":
    st.title("📄 Analyse de CV")
    st.info("En cours...")
