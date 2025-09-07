# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
from io import BytesIO

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
            "Compétences techniques": {
                "valeur": "Ex: Autocad, Robot Structural Analysis",
                "importance": 3,
            },
            "Soft skills": {"valeur": "Esprit d’équipe, autonomie", "importance": 2},
        },
    },
    "Template direction": {
        "Contexte": {
            "Objectifs": {
                "valeur": "Alignement avec stratégie groupe",
                "importance": 3,
            },
            "Budget": {"valeur": "Validé par direction", "importance": 2},
        },
        "Profil recherché": {
            "Compétences techniques": {
                "valeur": "Leadership, gestion multi-projets",
                "importance": 3,
            },
            "Soft skills": {"valeur": "Communication, stratégie", "importance": 2},
        },
    },
}

# -------------------- Checklist simplifiée --------------------
SIMPLIFIED_CHECKLIST = {
    "Contexte": ["Objectifs", "Budget"],
    "Profil recherché": ["Compétences techniques", "Soft skills"],
}

# -------------------- Disponibilité PDF & Word --------------------
try:
    import reportlab
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# -------------------- Export PDF --------------------
def export_brief_pdf():
    """Exporte le brief courant en PDF (si reportlab dispo)"""
    if not PDF_AVAILABLE:
        return None

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Brief Recrutement : {st.session_state.get('current_brief_name', '')}")

    c.setFont("Helvetica", 12)
    y = height - 100
    c.drawString(50, y, f"Poste : {st.session_state.get('poste_intitule', '')}")
    y -= 20
    c.drawString(50, y, f"Manager : {st.session_state.get('manager_nom', '')}")
    y -= 20
    c.drawString(50, y, f"Recruteur : {st.session_state.get('recruteur', '')}")
    y -= 20
    c.drawString(50, y, f"Affectation : {st.session_state.get('affectation_type', '')} - {st.session_state.get('affectation_nom', '')}")

    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Données du brief :")
    c.setFont("Helvetica", 11)
    y -= 20

    for cat, items in st.session_state.get("brief_data", {}).items():
        c.drawString(50, y, f"- {cat}")
        y -= 15
        for it, val in items.items():
            c.drawString(70, y, f"{it}: {val.get('valeur', '')} (importance: {val.get('importance', '')})")
            y -= 15
            if y < 100:  # Nouvelle page si trop bas
                c.showPage()
                y = height - 100

    # ➕ Export de la matrice KSA
    if st.session_state.get("ksa_data"):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Matrice KSA :")
        y -= 20
        c.setFont("Helvetica", 11)
        for cat, comps in st.session_state["ksa_data"].items():
            c.drawString(50, y, f"{cat}")
            y -= 15
            for comp, details in comps.items():
                c.drawString(70, y, f"{comp} | Niv: {details.get('niveau','')} | Prio: {details.get('priorite','')} | Eval: {details.get('evaluateur','')}")
                y -= 15
                if y < 100:
                    c.showPage()
                    y = height - 100

    c.save()
    buffer.seek(0)
    return buffer

# -------------------- Export Word --------------------
def export_brief_word():
    """Exporte le brief courant en Word (si python-docx dispo)"""
    if not WORD_AVAILABLE:
        return None

    from docx import Document

    doc = Document()
    doc.add_heading(f"Brief Recrutement : {st.session_state.get('current_brief_name', '')}", 0)

    doc.add_paragraph(f"Poste : {st.session_state.get('poste_intitule', '')}")
    doc.add_paragraph(f"Manager : {st.session_state.get('manager_nom', '')}")
    doc.add_paragraph(f"Recruteur : {st.session_state.get('recruteur', '')}")
    doc.add_paragraph(f"Affectation : {st.session_state.get('affectation_type', '')} - {st.session_state.get('affectation_nom', '')}")

    doc.add_heading("Données du brief", level=1)
    for cat, items in st.session_state.get("brief_data", {}).items():
        doc.add_heading(cat, level=2)
        for it, val in items.items():
            doc.add_paragraph(f"{it}: {val.get('valeur', '')} (importance: {val.get('importance', '')})")

    # ➕ Export matrice KSA
    if st.session_state.get("ksa_data"):
        doc.add_heading("Matrice KSA", level=1)
        for cat, comps in st.session_state["ksa_data"].items():
            doc.add_heading(cat, level=2)
            for comp, details in comps.items():
                doc.add_paragraph(f"{comp} | Niv: {details.get('niveau','')} | Prio: {details.get('priorite','')} | Eval: {details.get('evaluateur','')}")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -------------------- Section KSA interactive --------------------
def render_ksa_section():
    """Affiche et gère la matrice KSA"""
    st.subheader("📊 Matrice KSA (Knowledge / Skills / Abilities)")

    if "ksa_data" not in st.session_state or not st.session_state.ksa_data:
        st.session_state.ksa_data = {
            "Knowledge (Connaissances)": {},
            "Skills (Savoir-faire)": {},
            "Abilities (Aptitudes)": {}
        }

    for category in st.session_state.ksa_data.keys():
        st.markdown(f"### {category}")

        col1, col2 = st.columns([3, 1])
        with col1:
            new_comp = st.text_input(f"Ajouter une compétence pour {category}", key=f"new_{category}")
        with col2:
            if st.button("➕ Ajouter", key=f"add_{category}"):
                if new_comp:
                    st.session_state.ksa_data[category][new_comp] = {
                        "niveau": "Intermédiaire",
                        "priorite": "Indispensable",
                        "evaluateur": "Manager"
                    }
                    st.rerun()

        to_delete = None
        for comp, details in st.session_state.ksa_data[category].items():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            with col1:
                st.write(f"🔹 {comp}")
            with col2:
                st.session_state.ksa_data[category][comp]["niveau"] = st.selectbox(
                    "Niveau",
                    ["Débutant", "Intermédiaire", "Expert"],
                    index=["Débutant", "Intermédiaire", "Expert"].index(details.get("niveau", "Intermédiaire")),
                    key=f"{category}_{comp}_niv"
                )
            with col3:
                st.session_state.ksa_data[category][comp]["priorite"] = st.selectbox(
                    "Priorité",
                    ["Indispensable", "Souhaitable"],
                    index=["Indispensable", "Souhaitable"].index(details.get("priorite", "Indispensable")),
                    key=f"{category}_{comp}_prio"
                )
            with col4:
                st.session_state.ksa_data[category][comp]["evaluateur"] = st.selectbox(
                    "Évaluateur",
                    ["Manager", "Recruteur", "Les deux"],
                    index=["Manager", "Recruteur", "Les deux"].index(details.get("evaluateur", "Manager")),
                    key=f"{category}_{comp}_eval"
                )
            with col5:
                if st.button("🗑️", key=f"del_{category}_{comp}"):
                    to_delete = comp
        if to_delete:
            del st.session_state.ksa_data[category][to_delete]
            st.rerun()
