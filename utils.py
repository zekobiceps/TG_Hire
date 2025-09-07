import streamlit as st
import os
import pickle
from datetime import datetime

# -------------------- Session --------------------
def init_session_state():
    """Initialise les variables de session par défaut"""
    defaults = {
        "poste_intitule": "",
        "manager_nom": "",
        "recruteur": "Zakaria",
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
    date = datetime.now().strftime("%Y%m%d")
    return f"{poste}_{manager}_{date}"

def filter_briefs(saved_briefs, month=None, recruteur=None, poste=None, manager=None):
    """Filtrer les briefs existants"""
    results = {}
    for name, data in saved_briefs.items():
        if month and not name.startswith(month):
            continue
        if recruteur and data.get("recruteur") != recruteur:
            continue
        if poste and data.get("poste_intitule") != poste:
            continue
        if manager and data.get("manager_nom") != manager:
            continue
        results[name] = data
    return results

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

# -------------------- Checklist simplifiée --------------------
SIMPLIFIED_CHECKLIST = {
    "Contexte": ["Objectifs", "Budget"],
    "Profil recherché": ["Compétences techniques", "Soft skills"],
}
# 1. Ajouter utils.py corrigé
git add utils.py

# 2. Commit clair
git commit -m "fix(utils): ajout de BRIEF_TEMPLATES et SIMPLIFIED_CHECKLIST pour prise en charge des briefs"

# 3. Push vers GitHub
git push origin main
