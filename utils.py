# -*- coding: utf-8 -*-
import streamlit as st
import os
import pickle
from datetime import datetime
import io

# -------------------- Disponibilité PDF & Word --------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# -------------------- Initialisation Session --------------------
def init_session_state():
    defaults = {
        "poste_intitule": "",
        "service": "",
        "niveau_hierarchique": "",
        "type_contrat": "",
        "localisation": "",
        "budget_salaire": "",
        "date_prise_poste": "",
        "recruteur": "",
        "manager_nom": "",
        "affectation_type": "",
        "affectation_nom": "",
        "ksa_data": {},
        "saved_briefs": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -------------------- Persistence --------------------
def save_briefs():
    with open("briefs.pkl", "wb") as f:
        pickle.dump(st.session_state.saved_briefs, f)

def load_briefs():
    if os.path.exists("briefs.pkl"):
        with open("briefs.pkl", "rb") as f:
            return pickle.load(f)
    return {}

# -------------------- Conseils IA --------------------
def generate_checklist_advice(category, item):
    conseils = {
        "Pourquoi ce poste est-il ouvert?": "- Clarifier le départ ou création de poste\n- Identifier l'urgence\n- Relier au contexte business",
        "Impact stratégique du poste": "- Détailler la valeur ajoutée stratégique\n- Relier aux objectifs de l’entreprise",
    }
    return conseils.get(item, f"- Fournir des détails pratiques pour {item}\n- Exemple concret\n- Piège à éviter")

# -------------------- EXPORT PDF --------------------
def export_brief_pdf():
    if not PDF_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("📋 Brief Recrutement", styles['Heading1']))
    story.append(Spacer(1, 20))

    # --- SECTION 1: Identité
    story.append(Paragraph("1. Identité du poste", styles['Heading2']))
    infos = [
        ["Intitulé", st.session_state.get("poste_intitule", "")],
        ["Service", st.session_state.get("service", "")],
        ["Niveau hiérarchique", st.session_state.get("niveau_hierarchique", "")],
        ["Contrat", st.session_state.get("type_contrat", "")],
        ["Localisation", st.session_state.get("localisation", "")],
        ["Budget", st.session_state.get("budget_salaire", "")],
        ["Date prise poste", str(st.session_state.get("date_prise_poste", ""))],
        ["Recruteur", st.session_state.get("recruteur", "")],
        ["Manager", st.session_state.get("manager_nom", "")],
        ["Affectation", f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}"]
    ]
    story.append(Table(infos, colWidths=[150, 300],
                       style=[("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(Spacer(1, 15))

    # --- SECTION 2: Contexte
    story.append(Paragraph("2. Contexte & Enjeux", styles['Heading2']))
    for field in ["raison_ouverture", "impact_strategique", "rattachement", "defis_principaux"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 3: Recherches
    story.append(Paragraph("3. Recherches Marché", styles['Heading2']))
    for field in ["benchmark_salaire", "disponibilite_profils", "concurrents_directs", "specificites_sectorielles"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 4: Questions manager
    story.append(Paragraph("4. Questions Manager", styles['Heading2']))
    for field in ["q1_manager", "q2_manager", "q3_manager"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 5: Incidents critiques
    story.append(Paragraph("5. Incidents Critiques", styles['Heading2']))
    for field in ["reussite_contexte", "reussite_actions", "reussite_resultat", "echec_contexte", "echec_causes", "echec_impact"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 6: Comportementales
    story.append(Paragraph("6. Questions Comportementales", styles['Heading2']))
    for field in ["comp_q1", "comp_rep1", "comp_eval1"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 7: KSA
    story.append(Paragraph("7. Matrice KSA", styles['Heading2']))
    for cat, comps in st.session_state.get("ksa_data", {}).items():
        story.append(Paragraph(f"{cat}", styles['Heading3']))
        for comp, details in comps.items():
            story.append(Paragraph(f"- {comp} ({details})", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 8: Stratégie
    story.append(Paragraph("8. Stratégie Recrutement", styles['Heading2']))
    for field in ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 9: Synthèse
    story.append(Paragraph("9. Synthèse & Scoring", styles['Heading2']))
    story.append(Paragraph("Score global cible calculé automatiquement.", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- SECTION 10: Plan d’action
    story.append(Paragraph("10. Plan d’Action & Calendrier", styles['Heading2']))
    for field in ["prochaines_etapes", "responsables", "delais", "points_blocants", "date_lancement", "date_limite_candidatures", "dates_entretiens", "date_decision_finale"]:
        if field in st.session_state:
            story.append(Paragraph(f"- {field.replace('_',' ').title()} : {st.session_state[field]}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------- EXPORT WORD --------------------
def export_brief_word():
    if not WORD_AVAILABLE:
        return None

    doc = Document()
    doc.add_heading("📋 Brief Recrutement", 0)

    # Identité
    doc.add_heading("1. Identité du poste", level=1)
    for k in ["poste_intitule","service","niveau_hierarchique","type_contrat","localisation","budget_salaire","date_prise_poste","recruteur","manager_nom","affectation_type","affectation_nom"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # Contexte
    doc.add_heading("2. Contexte & Enjeux", level=1)
    for k in ["raison_ouverture","impact_strategique","rattachement","defis_principaux"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # Recherches
    doc.add_heading("3. Recherches Marché", level=1)
    for k in ["benchmark_salaire","disponibilite_profils","concurrents_directs","specificites_sectorielles"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # Questions Manager
    doc.add_heading("4. Questions Manager", level=1)
    for k in ["q1_manager","q2_manager","q3_manager"]:
        doc.add_paragraph(st.session_state.get(k,""))

    # Incidents
    doc.add_heading("5. Incidents Critiques", level=1)
    for k in ["reussite_contexte","reussite_actions","reussite_resultat","echec_contexte","echec_causes","echec_impact"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # Comportementales
    doc.add_heading("6. Questions Comportementales", level=1)
    for k in ["comp_q1","comp_rep1","comp_eval1"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # KSA
    doc.add_heading("7. Matrice KSA", level=1)
    for cat, comps in st.session_state.get("ksa_data", {}).items():
        doc.add_heading(cat, level=2)
        for comp, details in comps.items():
            doc.add_paragraph(f"- {comp} ({details})")

    # Stratégie
    doc.add_heading("8. Stratégie Recrutement", level=1)
    for k in ["canaux_prioritaires","criteres_exclusion","processus_evaluation"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    # Synthèse
    doc.add_heading("9. Synthèse & Scoring", level=1)
    doc.add_paragraph("Score global cible calculé automatiquement.")

    # Plan d’action
    doc.add_heading("10. Plan d’Action & Calendrier", level=1)
    for k in ["prochaines_etapes","responsables","delais","points_blocants","date_lancement","date_limite_candidatures","dates_entretiens","date_decision_finale"]:
        doc.add_paragraph(f"{k.replace('_',' ').title()} : {st.session_state.get(k,'')}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
