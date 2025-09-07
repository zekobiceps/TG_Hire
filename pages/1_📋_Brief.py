import streamlit as st
import os
import pickle
from datetime import datetime
import re
import requests

# -------------------- Config API DeepSeek --------------------
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    DEEPSEEK_API_KEY = None
    st.warning("⚠️ Clé API DeepSeek non configurée, certaines fonctionnalités seront limitées.")

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
    try:
        if os.path.exists("saved_briefs.pkl"):
            with open("saved_briefs.pkl", "rb") as f:
                return pickle.load(f)
    except Exception as e:
        st.error(f"Erreur chargement briefs : {e}")
    return {}

def save_briefs():
    try:
        with open("saved_briefs.pkl", "wb") as f:
            pickle.dump(st.session_state.saved_briefs, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde briefs : {e}")

# -------------------- Init Session --------------------
def init_session_state():
    saved_briefs = load_saved_briefs()
    defaults = {
        "contexte_data": {item: "" for item in SIMPLIFIED_CHECKLIST["Contexte & Environnement"]},
        "missions_data": {item: "" for item in SIMPLIFIED_CHECKLIST["Missions et Responsabilités"]},
        "strategie_data": {item: "" for item in SIMPLIFIED_CHECKLIST["Stratégie de Recrutement"]},
        "valeur_data": {item: "" for item in SIMPLIFIED_CHECKLIST["Proposition de valeur candidat"]},
        "ksa_data": {k: v.copy() for k, v in KSA_STRUCTURE.items()},
        "saved_briefs": saved_briefs,
        "poste_intitule": "",
        "manager_nom": "",
        "recruteur": RECRUTEURS[0],
        "affectation_type": "Chantier",
        "affectation_nom": "",
        "current_brief_name": "",
        "commentaires": "",
        "brief_phase": "Gestion",
        "filtered_briefs": {},
        "show_filtered_results": False,
        "filtre_mois": "",
        "filtre_recruteur": "",
        "filtre_poste": "",
        "filtre_manager": "",
        "api_usage": {"total_tokens": 0, "used_tokens": 0, "current_session_tokens": 0},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# -------------------- DeepSeek Helper --------------------
def ask_deepseek(messages, max_tokens=400):
    if not DEEPSEEK_API_KEY:
        return {"content": "⚠️ API non configurée", "total_tokens": 0}

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7, "max_tokens": max_tokens}

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            result = response.json()
            return {"content": result["choices"][0]["message"]["content"], "total_tokens": result.get("usage", {}).get("total_tokens", 0)}
        return {"content": f"❌ Erreur {response.status_code}", "total_tokens": 0}
    except Exception as e:
        return {"content": f"❌ Exception : {e}", "total_tokens": 0}

# -------------------- Brief Utils --------------------
def generate_automatic_brief_name():
    date_str = datetime.now().strftime("%d%m%y")
    initials = RECRUTEURS_INITIALES.get(st.session_state.recruteur, "RC")
    poste = st.session_state.poste_intitule[:10].replace(" ", "") or "Poste"
    manager = st.session_state.manager_nom[:10].replace(" ", "") or "Manager"
    return f"{date_str}-{poste}-{manager}-{initials}"

def filter_briefs(month=None, recruteur=None, poste=None, manager=None):
    results = {}
    for name, data in st.session_state.saved_briefs.items():
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

# -------------------- UI --------------------
st.set_page_config(page_title="TG-Hire IA - Brief", page_icon="📋", layout="wide")
st.title("📋 Brief Recrutement")

brief_phase = st.radio("Phase du Brief:", ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True, key="brief_phase_selector")
st.session_state.brief_phase = brief_phase

# -------------------- Phase Gestion --------------------
if brief_phase == "📁 Gestion":
    st.subheader("Informations de base")
    col1, col2 = st.columns(2)

    with col1:
        st.session_state.poste_intitule = st.text_input("Intitulé du poste", value=st.session_state.poste_intitule)
        st.session_state.manager_nom = st.text_input("Nom du manager", value=st.session_state.manager_nom)
        st.session_state.recruteur = st.selectbox("Recruteur", RECRUTEURS, index=RECRUTEURS.index(st.session_state.recruteur))

    with col2:
        st.session_state.affectation_type = st.selectbox("Affectation", ["Chantier", "Direction"], index=0 if st.session_state.affectation_type == "Chantier" else 1)
        st.session_state.affectation_nom = st.text_input("Nom de l'affectation", value=st.session_state.affectation_nom)

    if st.session_state.poste_intitule and st.session_state.manager_nom:
        suggested = generate_automatic_brief_name()
        st.session_state.current_brief_name = st.text_input("Nom du brief", value=suggested)

    st.divider()
    st.subheader("Chargement & Templates")

    st.markdown("**Filtres de recherche**")
    st.session_state.filtre_mois = st.selectbox("Mois", [""] + [f"{i:02d}" for i in range(1, 13)])
    st.session_state.filtre_recruteur = st.selectbox("Recruteur", [""] + RECRUTEURS)
    st.session_state.filtre_poste = st.text_input("Poste", value=st.session_state.filtre_poste)
    st.session_state.filtre_manager = st.text_input("Manager", value=st.session_state.filtre_manager)

    if st.button("🔍 Rechercher briefs"):
        st.session_state.filtered_briefs = filter_briefs(st.session_state.filtre_mois, st.session_state.filtre_recruteur, st.session_state.filtre_poste, st.session_state.filtre_manager)
        st.session_state.show_filtered_results = True

    if st.session_state.show_filtered_results:
        if st.session_state.filtered_briefs:
            selected = st.selectbox("Choisir un brief", [""] + list(st.session_state.filtered_briefs.keys()))
            target_tab = st.radio("Charger dans:", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)
            if selected:
                if st.button("📂 Charger ce brief"):
                    st.session_state.update(st.session_state.filtered_briefs[selected])
                    st.session_state.brief_phase = target_tab
                    st.success(f"✅ Brief {selected} chargé")
                    st.rerun()
                if st.button("🗑️ Supprimer ce brief"):
                    st.session_state.saved_briefs.pop(selected, None)
                    save_briefs()
                    st.success(f"🗑️ Brief {selected} supprimé")
                    st.rerun()
        else:
            st.warning("Aucun brief trouvé avec ces critères.")

# -------------------- Phase Avant-brief --------------------
elif brief_phase == "🔄 Avant-brief":
    st.subheader("🔄 Avant-brief - Préparation")
    for item in SIMPLIFIED_CHECKLIST["Contexte & Environnement"]:
        st.session_state.contexte_data[item] = st.text_area(item, value=st.session_state.contexte_data.get(item, ""))
    st.session_state.commentaires = st.text_area("Commentaires libres", value=st.session_state.commentaires)

# -------------------- Phase Réunion --------------------
elif brief_phase == "✅ Réunion de brief":
    st.subheader("✅ Réunion de brief - Validation")
    for item in SIMPLIFIED_CHECKLIST["Missions et Responsabilités"]:
        st.session_state.missions_data[item] = st.text_area(item, value=st.session_state.missions_data.get(item, ""))
    st.session_state.commentaires = st.text_area("Compte-rendu réunion", value=st.session_state.commentaires)

# -------------------- Sauvegarde --------------------
if st.button("💾 Sauvegarder le brief", use_container_width=True):
    if not st.session_state.current_brief_name:
        st.session_state.current_brief_name = generate_automatic_brief_name()
    st.session_state.saved_briefs[st.session_state.current_brief_name] = {
        "poste_intitule": st.session_state.poste_intitule,
        "manager_nom": st.session_state.manager_nom,
        "recruteur": st.session_state.recruteur,
        "affectation_type": st.session_state.affectation_type,
        "affectation_nom": st.session_state.affectation_nom,
        "contexte_data": st.session_state.contexte_data,
        "missions_data": st.session_state.missions_data,
        "strategie_data": st.session_state.strategie_data,
        "valeur_data": st.session_state.valeur_data,
        "ksa_data": st.session_state.ksa_data,
        "commentaires": st.session_state.commentaires,
    }
    save_briefs()
    st.success(f"💾 Brief sauvegardé : {st.session_state.current_brief_name}")
