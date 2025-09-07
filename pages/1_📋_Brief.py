# -*- coding: utf-8 -*-
import streamlit as st
import json
from datetime import date

# -------- Import Utils --------
from utils import (
    init_session_state,
    save_briefs,
    load_briefs,
    export_brief_pdf,
    export_brief_word,
    PDF_AVAILABLE,
    WORD_AVAILABLE
)

# -------- INIT SESSION --------
def init_custom_session():
    defaults = {
        "current_brief_name": "",
        "saved_briefs": {},
        "identite_poste": {
            "Intitulé": "",
            "Service": "",
            "Niveau hiérarchique": "",
            "Type de contrat": "",
            "Localisation": "",
            "Budget salaire": "",
            "Date de prise de poste": ""
        },
        "contexte": {
            "Raison ouverture": "",
            "Impact stratégique": "",
            "Rattachement": "",
            "Défis principaux": ""
        },
        "recherches": {
            "Benchmark salaire": "",
            "Disponibilité profils": "",
            "Concurrents directs": "",
            "Spécificités sectorielles": ""
        },
        "questions_manager": [],
        "incidents": {
            "Réussite exceptionnelle": {"Contexte": "", "Actions": "", "Résultat": ""},
            "Échec significatif": {"Contexte": "", "Causes": "", "Impact": ""}
        },
        "questions_comportementales": [],
        "ksa_matrix": {"knowledge": [], "skills": [], "abilities": []},
        "strategie": {"canaux_prioritaires": [], "criteres_exclusion": [], "processus_evaluation": []},
        "plan_action": {"prochaines_etapes": [], "responsables": {}, "delais": {}, "points_blocants": []},
        "calendrier": {"date_lancement": "", "date_limite_candidatures": "", "dates_entretiens": [], "date_decision_finale": ""},
        "date_brief": date.today(),
        "affectation_type": "Chantier",
        "affectation_nom": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()  # utils
init_custom_session()  # custom

st.set_page_config(page_title="TG-Hire IA - Brief Recrutement", page_icon="📋", layout="wide")

# -------- NAVIGATION --------
tabs = st.tabs(["📁 Gestion", "🔄 Avant-brief", "✅ Réunion", "📊 Synthèse"])

# -------- ONGLET GESTION --------
with tabs[0]:
    st.header("📁 Gestion des Briefs")
    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Nom du Brief (auto si vide)", key="current_brief_name")
        st.text_input("Recruteur", key="recruteur_gestion")
        st.text_input("Manager", key="manager_gestion")
        st.text_input("Intitulé du poste", key="poste_intitule_gestion")
        st.date_input("📅 Date du brief", key="date_brief")

        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.session_state.affectation_type = st.selectbox("Affectation", ["Chantier", "Siège"], key="affectation_type")
        with col_aff2:
            st.session_state.affectation_nom = st.text_input("Nom de l’affectation", key="affectation_nom")

        if st.button("💾 Sauvegarder le brief", use_container_width=True, type="primary"):
            name = st.session_state.current_brief_name or f"Brief_{date.today()}"
            data = dict(
                identite_poste=st.session_state.identite_poste,
                contexte=st.session_state.contexte,
                recherches=st.session_state.recherches,
                questions_manager=st.session_state.questions_manager,
                incidents=st.session_state.incidents,
                questions_comportementales=st.session_state.questions_comportementales,
                ksa_matrix=st.session_state.ksa_matrix,
                strategie=st.session_state.strategie,
                plan_action=st.session_state.plan_action,
                calendrier=st.session_state.calendrier,
                recruteur=st.session_state.recruteur_gestion,
                manager=st.session_state.manager_gestion,
                poste=st.session_state.poste_intitule_gestion,
                date_brief=str(st.session_state.date_brief),
                affectation_type=st.session_state.affectation_type,
                affectation_nom=st.session_state.affectation_nom
            )
            st.session_state.saved_briefs[name] = data
            save_briefs()
            st.success(f"✅ Brief sauvegardé sous le nom : {name}")

    with col2:
        st.subheader("📂 Import / Export")
        st.session_state.saved_briefs = load_briefs()

        if st.session_state.saved_briefs:
            choix = st.selectbox("Choisir un brief", [""] + list(st.session_state.saved_briefs.keys()))
            if choix:
                if st.button("📂 Charger"):
                    for k, v in st.session_state.saved_briefs[choix].items():
                        st.session_state[k] = v
                    st.success(f"✅ Brief '{choix}' chargé")
                if st.button("⬇️ Exporter en JSON"):
                    export_data = json.dumps(st.session_state.saved_briefs[choix], indent=2, ensure_ascii=False)
                    st.download_button("Télécharger JSON", data=export_data,
                                       file_name=f"{choix}.json", mime="application/json")

# -------- ONGLET AVANT-BRIEF --------
with tabs[1]:
    st.header("🔄 Avant-brief (Préparation)")
    with st.expander("📋 Identité du poste", expanded=False):
        for key in st.session_state.identite_poste:
            st.session_state.identite_poste[key] = st.text_input(key, st.session_state.identite_poste[key], key=f"identite_{key}")
    with st.expander("🎯 Contexte", expanded=False):
        for key in st.session_state.contexte:
            st.session_state.contexte[key] = st.text_area(key, st.session_state.contexte[key], key=f"contexte_{key}")
    with st.expander("📚 Recherches marché", expanded=False):
        for key in st.session_state.recherches:
            st.session_state.recherches[key] = st.text_area(key, st.session_state.recherches[key], key=f"recherche_{key}")

# -------- ONGLET REUNION --------
with tabs[2]:
    st.header("✅ Réunion de brief (Validation)")
    with st.expander("❓ Questions manager"):
        new_q = st.text_input("Ajouter une question", key="new_question_manager")
        if st.button("➕ Ajouter", key="btn_add_qmanager"):
            if new_q:
                st.session_state.questions_manager.append(new_q)
        st.write(st.session_state.questions_manager)

    with st.expander("🎭 Incidents critiques"):
        for k, fields in st.session_state.incidents.items():
            st.markdown(f"**{k}**")
            for f in fields:
                st.session_state.incidents[k][f] = st.text_area(
                    f, st.session_state.incidents[k][f], key=f"incident_{k}_{f}"
                )

    with st.expander("🔍 Questions comportementales"):
        q = st.text_input("Question", key="qc_question")
        r = st.text_area("Réponse attendue", key="qc_reponse")
        if st.button("➕ Ajouter Q°", key="btn_add_qc"):
            st.session_state.questions_comportementales.append({"question": q, "reponse_attendue": r})
        st.write(st.session_state.questions_comportementales)

    with st.expander("📊 Matrice KSA"):
        cat = st.selectbox("Catégorie", ["knowledge", "skills", "abilities"], key="ksa_cat")
        comp = st.text_input("Compétence", key="ksa_comp")
        niv = st.slider("Niveau requis (1-5)", 1, 5, 3, key="ksa_niv")
        imp = st.slider("Importance (%)", 0, 20, 5, key="ksa_imp")
        eval = st.selectbox("Évaluateur", ["Recruteur", "Manager", "Les deux"], key="ksa_eval")
        if st.button("➕ Ajouter compétence", key="btn_add_ksa"):
            st.session_state.ksa_matrix[cat].append(
                {"competence": comp, "niveau": niv, "importance": imp/100, "evaluateur": eval}
            )
        st.write(st.session_state.ksa_matrix)

    with st.expander("⚙️ Stratégie recrutement"):
        st.session_state.strategie["canaux_prioritaires"] = st.text_area(
            "Canaux prioritaires", ", ".join(st.session_state.strategie["canaux_prioritaires"]), key="strat_canaux"
        ).split(",")
        st.session_state.strategie["criteres_exclusion"] = st.text_area(
            "Critères d’exclusion", ", ".join(st.session_state.strategie["criteres_exclusion"]), key="strat_exclu"
        ).split(",")

# -------- ONGLET SYNTHÈSE --------
with tabs[3]:
    st.header("📊 Synthèse & Scoring global")

    def calculer_score_reference():
        total, poids_total = 0, 0
        for comp in st.session_state.ksa_matrix["knowledge"] + st.session_state.ksa_matrix["skills"]:
            total += comp["niveau"] * comp["importance"]
            poids_total += comp["importance"]
        for comp in st.session_state.ksa_matrix["abilities"]:
            total += comp["niveau"] * comp["importance"]
            poids_total += comp["importance"]
        return total / poids_total if poids_total > 0 else 0

    score = calculer_score_reference()
    st.metric("Score de référence", f"{score:.2f}/5")

    st.subheader("📝 Plan d’action")
    st.session_state.plan_action["prochaines_etapes"] = st.text_area(
        "Prochaines étapes", "\n".join(st.session_state.plan_action["prochaines_etapes"]), key="plan_etapes"
    ).split("\n")

    st.subheader("📅 Calendrier")
    st.session_state.calendrier["date_lancement"] = st.date_input("Date lancement", key="date_lancement")
    st.session_state.calendrier["date_limite_candidatures"] = st.date_input("Date limite candidatures", key="date_limite")

    # -------- EXPORT PDF/WORD --------
    st.subheader("📄 Export du Brief complet")

    col1, col2 = st.columns(2)
    with col1:
        if PDF_AVAILABLE:
            pdf_buf = export_brief_pdf()
            if pdf_buf:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buf,
                                   file_name=f"{st.session_state.current_brief_name}.pdf", mime="application/pdf")
        else:
            st.info("⚠️ PDF non dispo (pip install reportlab)")

    with col2:
        if WORD_AVAILABLE:
            word_buf = export_brief_word()
            if word_buf:
                st.download_button("⬇️ Télécharger Word", data=word_buf,
                                   file_name=f"{st.session_state.current_brief_name}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")
