import streamlit as st
from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
)

# ---------------- INIT ----------------
init_session_state()
st.set_page_config(page_title="TG-Hire IA - Brief Wizard", page_icon="🤖", layout="wide")

if "step" not in st.session_state:
    st.session_state.step = 1

total_steps = 10
progress = int((st.session_state.step / total_steps) * 100)
st.progress(progress, text=f"Étape {st.session_state.step}/{total_steps}")

# ---------------- CONSEIL BUTTON ----------------
def conseil_button(label, category=None, item=None, key=None):
    col1, col2 = st.columns([6, 1])
    with col1:
        value = st.text_area(label, key=key)
    with col2:
        if st.button("💡", key=f"btn_{key}"):
            st.session_state[f"advice_{key}"] = generate_checklist_advice(category, item or label)
    if st.session_state.get(f"advice_{key}"):
        st.info(st.session_state[f"advice_{key}"])
    return value

# ---------------- KSA SECTION ----------------
def render_ksa_section():
    st.subheader("📊 Matrice KSA")
    categories = ["Knowledge", "Skills", "Abilities"]

    for cat in categories:
        with st.expander(cat, expanded=False):
            if cat not in st.session_state.ksa_data:
                st.session_state.ksa_data[cat] = {}

            new_comp = st.text_input(f"Ajouter {cat}", key=f"new_{cat}")
            if st.button(f"➕ Ajouter {cat}", key=f"btn_add_{cat}") and new_comp:
                st.session_state.ksa_data[cat][new_comp] = {
                    "niveau": "Intermédiaire",
                    "priorite": "Indispensable",
                    "evaluateur": "Recruteur",
                    "score": 0,
                    "texte": ""
                }
                st.rerun()

            for comp, details in list(st.session_state.ksa_data[cat].items()):
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
                with col1:
                    st.write(f"📝 {comp}")
                with col2:
                    st.session_state.ksa_data[cat][comp]["niveau"] = st.selectbox(
                        "Niveau",
                        ["Débutant", "Intermédiaire", "Expert"],
                        index=["Débutant", "Intermédiaire", "Expert"].index(details.get("niveau", "Intermédiaire")),
                        key=f"niv_{cat}_{comp}"
                    )
                with col3:
                    st.session_state.ksa_data[cat][comp]["priorite"] = st.selectbox(
                        "Priorité",
                        ["Indispensable", "Souhaitable"],
                        index=["Indispensable", "Souhaitable"].index(details.get("priorite", "Indispensable")),
                        key=f"prio_{cat}_{comp}"
                    )
                with col4:
                    st.session_state.ksa_data[cat][comp]["evaluateur"] = st.selectbox(
                        "Évaluateur",
                        ["Recruteur", "Manager", "Les deux"],
                        index=["Recruteur", "Manager", "Les deux"].index(details.get("evaluateur", "Recruteur")),
                        key=f"eval_{cat}_{comp}"
                    )
                with col5:
                    st.session_state.ksa_data[cat][comp]["score"] = st.number_input(
                        "Score", min_value=0, max_value=5, value=int(details.get("score") or 0),
                        key=f"score_{cat}_{comp}"
                    )
                with col6:
                    if st.button("🗑️", key=f"del_{cat}_{comp}"):
                        del st.session_state.ksa_data[cat][comp]
                        st.rerun()

# ---------------- STEP DISPATCH ----------------
if st.session_state.step == 1:
    st.header("📌 Étape 1 : Fiche Identité du Poste")
    st.text_input("Intitulé du poste", key="poste_intitule")
    st.text_input("Nom du manager", key="manager_nom")
    st.text_input("Recruteur", key="recruteur")
    st.selectbox("Affectation", ["Chantier", "Siège"], key="affectation_type")
    st.text_input("Nom de l’affectation", key="affectation_nom")
    st.date_input("Date du Brief", key="date_brief")

elif st.session_state.step == 2:
    st.header("📌 Étape 2 : Contexte & Enjeux")
    conseil_button("Raison ouverture", "Contexte", "Pourquoi ce poste est-il ouvert?", key="raison_ouverture")
    conseil_button("Impact stratégique", "Contexte", "Impact stratégique du poste", key="impact_strategique")
    st.text_area("Rattachement hiérarchique", key="rattachement")
    st.text_area("Défis principaux", key="defis_principaux")

elif st.session_state.step == 3:
    st.header("📌 Étape 3 : Recherches Marché")
    st.text_area("Benchmark salaire", key="benchmark_salaire")
    st.text_area("Disponibilité profils", key="disponibilite_profils")
    st.text_area("Concurrents directs", key="concurrents_directs")
    st.text_area("Spécificités sectorielles", key="specificites_sectorielles")

elif st.session_state.step == 4:
    st.header("📌 Étape 4 : Questions Manager")
    conseil_button("Quelle situation récente a montré le besoin de ce poste ?", "Questions", None, key="q1_manager")
    conseil_button("Qu'est-ce qui différencie un bon d'un excellent candidat ?", "Questions", None, key="q2_manager")
    conseil_button("Quel échec passé ce poste doit-il éviter de reproduire ?", "Questions", None, key="q3_manager")

elif st.session_state.step == 5:
    st.header("📌 Étape 5 : Incidents Critiques")
    st.subheader("Réussite exceptionnelle")
    st.text_area("Contexte", key="reussite_contexte")
    st.text_area("Actions", key="reussite_actions")
    st.text_area("Résultat", key="reussite_resultat")
    st.subheader("Échec significatif")
    st.text_area("Contexte", key="echec_contexte")
    st.text_area("Causes", key="echec_causes")
    st.text_area("Impact", key="echec_impact")

elif st.session_state.step == 6:
    st.header("📌 Étape 6 : Questions Comportementales")
    st.text_area("Comment le candidat devrait-il gérer [situation difficile] ?", key="comp_q1")
    st.text_area("Réponse attendue", key="comp_rep1")
    st.text_area("Compétences évaluées", key="comp_eval1")

elif st.session_state.step == 7:
    st.header("📌 Étape 7 : Validation Matrice KSA")
    render_ksa_section()

elif st.session_state.step == 8:
    st.header("📌 Étape 8 : Stratégie Recrutement")
    st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation"], key="canaux_prioritaires")
    st.text_area("Critères d’exclusion", key="criteres_exclusion")
    st.text_area("Processus d’évaluation (détails)", key="processus_evaluation")

elif st.session_state.step == 9:
    st.header("📌 Étape 9 : Synthèse & Scoring")
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("poste_intitule", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Date": str(st.session_state.get("date_brief", "")),
    })

    st.subheader("📊 Calcul automatique du Score Global")
    score_missions = 3.9 * 0.25
    score_competences = 4.1 * 0.40
    score_manager = 4.2 * 0.20
    score_formation = 3.8 * 0.15
    score_total = score_missions + score_competences + score_manager + score_formation
    st.metric("Score Global Cible", f"{score_total:.2f}/5")

elif st.session_state.step == 10:
    st.header("📌 Étape 10 : Plan d’Action & Export")
    st.text_area("Prochaines étapes", key="prochaines_etapes")
    st.text_area("Responsables", key="responsables")
    st.text_area("Délais", key="delais")
    st.text_area("Points bloquants", key="points_blocants")

    st.subheader("📄 Export du Brief complet")
    col1, col2 = st.columns(2)
    with col1:
        if PDF_AVAILABLE:
            pdf_buf = export_brief_pdf()
            if pdf_buf:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buf, file_name="brief.pdf", mime="application/pdf")
        else:
            st.info("⚠️ PDF non dispo (pip install reportlab)")
    with col2:
        if WORD_AVAILABLE:
            word_buf = export_brief_word()
            if word_buf:
                st.download_button(
                    "⬇️ Télécharger Word", data=word_buf,
                    file_name="brief.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")

# ---------------- NAVIGATION ----------------
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.session_state.step > 1:
        if st.button("⬅️ Précédent"):
            st.session_state.step -= 1
            st.rerun()
with col3:
    if st.session_state.step < total_steps:
        if st.button("Suivant ➡️"):
            st.session_state.step += 1
            st.rerun()
