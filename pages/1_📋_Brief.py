import streamlit as st
import json
import os
from datetime import date

# ---------------- INIT SESSION STATE ----------------
def init_session():
    defaults = {
        "step": 1,
        "current_brief_name": "",
        "saved_briefs": {},
        "identite_poste": {
            "intitule": "",
            "service": "",
            "niveau_hierarchique": "",
            "type_contrat": "",
            "localisation": "",
            "budget_salaire": "",
            "date_prise_poste": ""
        },
        "contexte": {
            "raison_ouverture": "",
            "impact_strategique": "",
            "rattachement": "",
            "defis_principaux": ""
        },
        "recherches": {
            "benchmark_salaire": "",
            "disponibilite_profils": "",
            "concurrents_directs": "",
            "specificites_sectorielles": ""
        },
        "questions_manager": [],
        "incidents": {
            "reussite_exceptionnelle": {"contexte": "", "actions": "", "resultat": ""},
            "echec_significatif": {"contexte": "", "causes": "", "impact": ""}
        },
        "questions_comportementales": [],
        "ksa_matrix": {"knowledge": [], "skills": [], "abilities": []},
        "strategie": {"canaux_prioritaires": [], "criteres_exclusion": [], "processus_evaluation": []},
        "plan_action": {"prochaines_etapes": [], "responsables": {}, "delais": {}, "points_blocants": []},
        "calendrier": {"date_lancement": "", "date_limite_candidatures": "", "dates_entretiens": [], "date_decision_finale": ""}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

st.set_page_config(page_title="TG-Hire IA - Brief Recrutement", page_icon="📋", layout="wide")

# ---------------- GESTION ONGLET ----------------
tab1, tab2 = st.tabs(["📁 Gestion", "🧩 Brief Structuré"])

# --------- ONGLET GESTION ---------
with tab1:
    st.header("📁 Gestion des Briefs")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Nom du Brief (automatique si vide)", key="current_brief_name")
        st.text_input("Recruteur", key="recruteur_gestion")
        st.text_input("Manager", key="manager_gestion")
        st.text_input("Intitulé du poste", key="poste_intitule_gestion")

        if st.button("💾 Sauvegarder le brief", use_container_width=True, type="primary"):
            name = st.session_state.current_brief_name or f"Brief_{date.today()}"
            data = {
                "identite_poste": st.session_state.identite_poste,
                "contexte": st.session_state.contexte,
                "recherches": st.session_state.recherches,
                "questions_manager": st.session_state.questions_manager,
                "incidents": st.session_state.incidents,
                "questions_comportementales": st.session_state.questions_comportementales,
                "ksa_matrix": st.session_state.ksa_matrix,
                "strategie": st.session_state.strategie,
                "plan_action": st.session_state.plan_action,
                "calendrier": st.session_state.calendrier,
                "recruteur": st.session_state.recruteur_gestion,
                "manager": st.session_state.manager_gestion,
                "poste": st.session_state.poste_intitule_gestion
            }
            st.session_state.saved_briefs[name] = data
            with open("briefs.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.saved_briefs, f, ensure_ascii=False, indent=2)
            st.success(f"✅ Brief sauvegardé sous le nom : {name}")

    with col2:
        st.subheader("📂 Import / Export")
        if os.path.exists("briefs.json"):
            with open("briefs.json", "r", encoding="utf-8") as f:
                st.session_state.saved_briefs = json.load(f)

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

# --------- ONGLET BRIEF STRUCTURÉ ---------
with tab2:
    st.header("🧩 Brief Structuré - Wizard")
    total_steps = 10
    progress = st.session_state.step / total_steps
    st.progress(progress)
    st.write(f"Étape {st.session_state.step}/{total_steps}")

    # SECTION PAR ÉTAPE
    if st.session_state.step == 1:
        st.subheader("Fiche Identité")
        for key in st.session_state.identite_poste:
            st.session_state.identite_poste[key] = st.text_input(
                key.replace("_", " ").capitalize(), st.session_state.identite_poste[key]
            )

    elif st.session_state.step == 2:
        st.subheader("Contexte & Enjeux")
        for key in st.session_state.contexte:
            st.session_state.contexte[key] = st.text_area(
                key.replace("_", " ").capitalize(), st.session_state.contexte[key]
            )

    elif st.session_state.step == 3:
        st.subheader("Recherches Marché")
        for key in st.session_state.recherches:
            st.session_state.recherches[key] = st.text_area(
                key.replace("_", " ").capitalize(), st.session_state.recherches[key]
            )

    elif st.session_state.step == 4:
        st.subheader("Questions Manager")
        new_q = st.text_input("Ajouter une question")
        if st.button("➕ Ajouter question"):
            if new_q:
                st.session_state.questions_manager.append(new_q)
        st.write(st.session_state.questions_manager)

    elif st.session_state.step == 5:
        st.subheader("Incidents Critiques")
        for k, fields in st.session_state.incidents.items():
            st.markdown(f"**{k.replace('_', ' ').capitalize()}**")
            for f in fields:
                st.session_state.incidents[k][f] = st.text_area(f, st.session_state.incidents[k][f])

    elif st.session_state.step == 6:
        st.subheader("Questions Comportementales")
        q = st.text_input("Question")
        r = st.text_area("Réponse attendue")
        if st.button("➕ Ajouter Q° comportementale"):
            st.session_state.questions_comportementales.append({"question": q, "reponse_attendue": r})
        st.write(st.session_state.questions_comportementales)

    elif st.session_state.step == 7:
        st.subheader("Matrice KSA")
        cat = st.selectbox("Catégorie", ["knowledge", "skills", "abilities"])
        comp = st.text_input("Compétence")
        niv = st.slider("Niveau requis (1-5)", 1, 5, 3)
        imp = st.slider("Importance (%)", 0, 20, 5)
        eval = st.selectbox("Évaluateur", ["Recruteur", "Manager", "Les deux"])
        if st.button("➕ Ajouter compétence"):
            st.session_state.ksa_matrix[cat].append(
                {"competence": comp, "niveau": niv, "importance": imp / 100, "evaluateur": eval}
            )
        st.write(st.session_state.ksa_matrix)

    elif st.session_state.step == 8:
        st.subheader("Stratégie Recrutement")
        st.session_state.strategie["canaux_prioritaires"] = st.text_area(
            "Canaux prioritaires (séparés par virgule)",
            ", ".join(st.session_state.strategie["canaux_prioritaires"])
        ).split(",")
        st.session_state.strategie["criteres_exclusion"] = st.text_area(
            "Critères d’exclusion",
            ", ".join(st.session_state.strategie["criteres_exclusion"])
        ).split(",")

    elif st.session_state.step == 9:
        st.subheader("Scoring & Synthèse")
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

    elif st.session_state.step == 10:
        st.subheader("Plan d’Action & Calendrier")
        st.session_state.plan_action["prochaines_etapes"] = st.text_area(
            "Prochaines étapes", "\n".join(st.session_state.plan_action["prochaines_etapes"])
        ).split("\n")
        st.session_state.calendrier["date_lancement"] = st.date_input("Date lancement")
        st.session_state.calendrier["date_limite_candidatures"] = st.date_input("Date limite candidatures")

    # NAVIGATION
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.step > 1:
            if st.button("⬅️ Précédent"):
                st.session_state.step -= 1
                st.experimental_rerun()
    with col2:
        if st.session_state.step < total_steps:
            if st.button("➡️ Suivant"):
                st.session_state.step += 1
                st.experimental_rerun()
