import sys, os
import streamlit as st
from datetime import datetime
import json

# ✅ permet d'accéder à utils.py à la racine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    load_briefs,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
    generate_automatic_brief_name,
)

# ---------------- FONCTIONS MANQUANTES ----------------
def conseil_button(titre, categorie, conseil, key):
    """Crée un bouton avec conseil pour un champ"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_area(titre, key=key)
    with col2:
        if st.button("💡", key=f"btn_{key}"):
            st.session_state[key] = generate_checklist_advice(categorie, titre)
            st.rerun()

def render_ksa_section():
    """Affiche la section KSA (Knowledge, Skills, Abilities)"""
    st.info("Matrice des compétences requises (KSA)")
    
    if "ksa_data" not in st.session_state:
        st.session_state.ksa_data = {
            "Connaissances": {},
            "Compétences": {},
            "Aptitudes": {}
        }
    
    with st.expander("➕ Ajouter une compétence"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_cat = st.selectbox("Catégorie", ["Connaissances", "Compétences", "Aptitudes"], key="new_cat")
        with col2:
            new_comp = st.text_input("Compétence", key="new_comp")
        with col3:
            new_score = st.slider("Importance", 1, 5, 3, key="new_score")
        
        if st.button("Ajouter", key="add_comp"):
            if new_comp:
                st.session_state.ksa_data[new_cat][new_comp] = {"score": new_score}
                st.success(f"✅ {new_comp} ajouté à {new_cat}")
                st.rerun()
    
    for categorie, competences in st.session_state.ksa_data.items():
        with st.expander(f"{categorie} ({len(competences)})"):
            if competences:
                for comp, details in competences.items():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{comp}**")
                    with col2:
                        st.write(f"Importance: {details.get('score', 'N/A')}/5")
                    with col3:
                        if st.button("🗑️", key=f"del_{categorie}_{comp}"):
                            del st.session_state.ksa_data[categorie][comp]
                            st.rerun()
            else:
                st.info("Aucune compétence définie")

# ---------------- INIT ----------------
init_session_state()
st.set_page_config(page_title="TG-Hire IA - Brief", page_icon="🤖", layout="wide")

if "brief_phase" not in st.session_state:
    st.session_state.brief_phase = "📁 Gestion"

if "reunion_step" not in st.session_state:
    st.session_state.reunion_step = 1

if "filtered_briefs" not in st.session_state:
    st.session_state.filtered_briefs = {}

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

# Définir les onglets avec leurs icônes et leurs labels
onglets = {
    "📁 Gestion": "Gestion",
    "🔄 Avant-brief": "Avant-brief",
    "✅ Réunion de brief": "Réunion de brief",
    "📝 Synthèse": "Synthèse"
}

# Style CSS pour le menu de navigation et les boutons
st.markdown("""
    <style>
    /* Réduire le padding par défaut de Streamlit pour les entêtes */
    .st-emotion-cache-18ni7ap {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    .st-emotion-cache-h5h60a {
        padding-bottom: 0rem;
    }
    
    /* Cache les onglets par défaut de Streamlit */
    .st-emotion-cache-16ya5a5 {
        display: none !important;
    }

    /* Style pour les boutons de navigation personnalisés */
    .nav-button button {
        background-color: transparent !important;
        color: rgba(255, 255, 255, 0.6) !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        margin-right: -10px; /* Rapproche les boutons */
        border-radius: 0px !important;
    }

    /* Style pour le bouton actif (l'onglet sélectionné) */
    .active-nav-button button {
        color: white !important;
        font-weight: bold !important;
        border-bottom: 3px solid #ff4b4b !important; /* Ligne rouge */
    }
    
    /* Style pour les boutons avec un fond spécifique (Sauvegarder, Rechercher) */
    .stButton > button {
        border: none !important;
        background-color: transparent !important;
        color: #fff !important;
    }

    /* Styles pour les boutons Sauvegarder et Rechercher */
    div[data-testid="stForm"] .stButton > button {
        background-color: #6a1b9a !important;
        border: 1px solid #6a1b9a !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Le bouton "Rechercher" est souvent le premier d'un formulaire */
    div[data-testid="stForm"] .stButton:first-of-type > button {
        background-color: #6a1b9a !important;
        color: white !important;
        border: 1px solid #6a1b9a !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Créer un conteneur horizontal pour les boutons de navigation
with st.container():
    cols = st.columns(len(onglets) + 1)
    
    for i, (icone, label) in enumerate(onglets.items()):
        with cols[i]:
            if st.session_state.brief_phase == icone:
                st.button(f"{icone} {label}", key=f"tab_{i}", help="Onglet actif", use_container_width=True)
                st.markdown(f'<div class="active-nav-button"><button></button></div>', unsafe_allow_html=True)
            else:
                if st.button(f"{icone} {label}", key=f"tab_{i}", use_container_width=True):
                    st.session_state.brief_phase = icone
                    st.rerun()

st.markdown("<hr style='border:1px solid #ff4b4b; margin-top: -10px;'>", unsafe_allow_html=True)

# ---------------- ONGLET GESTION ----------------
if st.session_state.brief_phase == "📁 Gestion":
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        st.subheader("Informations de base")
        
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Intitulé du poste *", key="poste_intitule")
            st.text_input("Nom du manager *", key="manager_nom")
        with col2:
            st.text_input("Poste à recruter", key="niveau_hierarchique")
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
        with col3:
            st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type")
            st.text_input("Nom de l'affectation", key="affectation_nom")
        
        st.date_input("Date du Brief *", key="date_brief")

        # --- SAUVEGARDE
        if st.button("💾 Sauvegarder le Brief", type="primary", use_container_width=True):
            if not all([st.session_state.poste_intitule, st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                if "saved_briefs" not in st.session_state:
                    st.session_state.saved_briefs = {}
                
                st.session_state.saved_briefs[brief_name] = {
                    "poste_intitule": st.session_state.poste_intitule,
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "date_brief": str(st.session_state.date_brief),
                    "niveau_hierarchique": st.session_state.niveau_hierarchique,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                    "impact_strategique": st.session_state.get("impact_strategique", ""),
                    "rattachement": st.session_state.get("rattachement", ""),
                    "defis_principaux": st.session_state.get("defis_principaux", ""),
                    "ksa_data": st.session_state.get("ksa_data", {})
                }
                save_briefs()
                st.success(f"✅ Brief '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name

    with col_side:
        st.subheader("Recherche & Chargement")
        
        # --- RECHERCHE & CHARGEMENT (2 colonnes)
        col1, col2 = st.columns(2)
        with col1:
            months = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            month = st.selectbox("Mois", months)
            poste = st.text_input("Poste")
        with col2:
            recruteur = st.selectbox("Recruteur", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="search_recruteur")
            manager = st.text_input("Manager")
            affectation = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="search_affectation")

        if st.button("🔎 Rechercher", type="secondary", use_container_width=True):
            briefs = load_briefs()
            st.session_state.filtered_briefs = filter_briefs(briefs, month, recruteur, poste, manager, affectation)
            if st.session_state.filtered_briefs:
                st.info(f"ℹ️ {len(st.session_state.filtered_briefs)} brief(s) trouvé(s).")
            else:
                st.error("❌ Aucun brief trouvé avec ces critères.")

        if st.session_state.filtered_briefs:
            st.subheader("Résultats de recherche")
            for name, data in st.session_state.filtered_briefs.items():
                with st.expander(f"📌 {name}"):
                    st.write(f"**Poste:** {data.get('poste_intitule', '')}")
                    st.write(f"**Manager:** {data.get('manager_nom', '')}")
                    st.write(f"**Recruteur:** {data.get('recruteur', '')}")
                    st.write(f"**Affectation:** {data.get('affectation_type', '')} - {data.get('affectation_nom', '')}")
                    st.write(f"**Date:** {data.get('date_brief', '')}")
                    
                    colA, colB = st.columns(2)
                    with colA:
                        if st.button(f"📂 Charger", key=f"load_{name}"):
                            safe_keys = [k for k in data.keys() if k not in ['ksa_data'] or data[k]]
                            for k in safe_keys:
                                if k in data and data[k]:
                                    st.session_state[k] = data[k]
                            st.session_state.current_brief_name = name
                            st.success(f"✅ Brief '{name}' chargé avec succès!")
                            st.rerun()
                    with colB:
                        if st.button(f"🗑️ Supprimer", key=f"del_{name}"):
                            all_briefs = load_briefs()
                            if name in all_briefs:
                                del all_briefs[name]
                                st.session_state.saved_briefs = all_briefs
                                save_briefs()
                                if name in st.session_state.filtered_briefs:
                                    del st.session_state.filtered_briefs[name]
                                st.warning(f"❌ Brief '{name}' supprimé.")
                                st.rerun()

# ---------------- AVANT-BRIEF ----------------
elif st.session_state.brief_phase == "🔄 Avant-brief":
    st.subheader("🔄 Avant-brief (Préparation)")
    st.info("Remplissez les informations préparatoires avant la réunion avec le manager.")

    conseil_button("Raison ouverture", "Contexte", "Pourquoi ce poste est-il ouvert?", key="raison_ouverture")
    conseil_button("Impact stratégique", "Contexte", "Impact stratégique du poste", key="impact_strategique")
    st.text_area("Rattachement hiérarchique", key="rattachement")
    st.text_area("Défis principaux", key="defis_principaux")

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_name = st.session_state.current_brief_name
            st.session_state.saved_briefs[brief_name].update({
                "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                "impact_strategique": st.session_state.get("impact_strategique", ""),
                "rattachement": st.session_state.get("rattachement", ""),
                "defis_principaux": st.session_state.get("defis_principaux", "")
            })
            save_briefs()
            st.success("✅ Modifications sauvegardées")
        else:
            st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

# ---------------- RÉUNION (Wizard interne) ----------------
elif st.session_state.brief_phase == "✅ Réunion de brief":
    st.subheader("✅ Réunion de brief avec le Manager")

    total_steps = 4
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("1️⃣ Incidents Critiques")
        st.text_area("Réussite exceptionnelle - Contexte", key="reussite_contexte")
        st.text_area("Réussite exceptionnelle - Actions", key="reussite_actions")
        st.text_area("Réussite exceptionnelle - Résultat", key="reussite_resultat")
        st.text_area("Échec significatif - Contexte", key="echec_contexte")
        st.text_area("Échec significatif - Causes", key="echec_causes")
        st.text_area("Échec significatif - Impact", key="echec_impact")

    elif step == 2:
        st.subheader("2️⃣ Questions Comportementales")
        st.text_area("Comment le candidat devrait-il gérer [situation difficile] ?", key="comp_q1")
        st.text_area("Réponse attendue", key="comp_rep1")
        st.text_area("Compétences évaluées", key="comp_eval1")

    elif step == 3:
        st.subheader("3️⃣ Validation Matrice KSA")
        render_ksa_section()

    elif step == 4:
        st.subheader("4️⃣ Stratégie Recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion")
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation")

        if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                brief_name = st.session_state.current_brief_name
                st.session_state.saved_briefs[brief_name].update({
                    "ksa_data": st.session_state.get("ksa_data", {})
                })
                save_briefs()
                st.success("✅ Données de réunion sauvegardées")
            else:
                st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

    # ---- Navigation wizard ----
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if step > 1:
            if st.button("⬅️ Précédent"):
                st.session_state.reunion_step -= 1
                st.rerun()
    with col3:
        if step < total_steps:
            if st.button("Suivant ➡️"):
                st.session_state.reunion_step += 1
                st.rerun()

# ---------------- SYNTHÈSE ----------------
elif st.session_state.brief_phase == "📝 Synthèse":
    st.subheader("📝 Synthèse du Brief")
    
    if "current_brief_name" in st.session_state:
        st.success(f"Brief actuel: {st.session_state.current_brief_name}")
    
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("poste_intitule", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Affectation": f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}",
        "Date": str(st.session_state.get("date_brief", "")),
        "Raison ouverture": st.session_state.get("raison_ouverture", ""),
        "Impact stratégique": st.session_state.get("impact_strategique", ""),
        "Défis principaux": st.session_state.get("defis_principaux", ""),
    })

    st.subheader("📊 Calcul automatique du Score Global")
    score_total = 0
    count = 0
    if "ksa_data" in st.session_state:
        for cat, comps in st.session_state.ksa_data.items():
            for comp, details in comps.items():
                score_total += int(details.get("score") or 0)
                count += 1
    score_global = (score_total / count) if count else 0
    st.metric("Score Global Cible", f"{score_global:.2f}/5")

    if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state:
            save_briefs()
            st.success("✅ Brief final confirmé et sauvegardé")
        else:
            st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")

    # -------- EXPORT PDF/WORD --------
    st.subheader("📄 Export du Brief complet")
    col1, col2 = st.columns(2)
    with col1:
        if PDF_AVAILABLE:
            if "current_brief_name" in st.session_state:
                pdf_buf = export_brief_pdf()
                if pdf_buf:
                    st.download_button("⬇️ Télécharger PDF", data=pdf_buf,
                                     file_name=f"{st.session_state.current_brief_name}.pdf", mime="application/pdf")
            else:
                st.info("ℹ️ Créez d'abord un brief pour l'exporter")
        else:
            st.info("⚠️ PDF non dispo (pip install reportlab)")
    with col2:
        if WORD_AVAILABLE:
            if "current_brief_name" in st.session_state:
                word_buf = export_brief_word()
                if word_buf:
                    st.download_button("⬇️ Télécharger Word", data=word_buf,
                                     file_name=f"{st.session_state.current_brief_name}.docx",
                                     mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            else:
                st.info("ℹ️ Créez d'abord un brief pour l'exporter")
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")