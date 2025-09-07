import sys, os
import streamlit as st  # nécessaire avant tout appel à st

# Ajoute la racine du projet (où est utils.py) dans le path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
)

# ---------------- INIT ----------------
st.set_page_config(page_title="TG-Hire IA - Brief", page_icon="🤖", layout="wide")

init_session_state()

if "brief_phase" not in st.session_state:
    st.session_state.brief_phase = "📁 Gestion"
if "reunion_step" not in st.session_state:
    st.session_state.reunion_step = 1

# ---------------- CONSEIL BUTTON ----------------
def conseil_button(label, category=None, item=None, key=None):
    """Champ texte avec bouton 💡 conseil"""
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

# ---------------- NAVIGATION ----------------
brief_phase = st.radio(
    "Phase du Brief",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief", "📝 Synthèse"],
    horizontal=True,
    key="brief_phase_selector"
)
st.session_state.brief_phase = brief_phase

# ---------------- GESTION ----------------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        st.text_input("Intitulé du poste", key="poste_intitule")
        st.text_input("Nom du manager", key="manager_nom")
        st.text_input("Recruteur", key="recruteur")
        st.selectbox("Affectation", ["Chantier", "Siège"], key="affectation_type")
        st.text_input("Nom de l’affectation", key="affectation_nom")
        st.date_input("Date du Brief", key="date_brief")

        if st.button("💾 Sauvegarder le brief", type="primary", use_container_width=True):
            if not st.session_state.current_brief_name:
                st.session_state.current_brief_name = f"{st.session_state.poste_intitule}_{st.session_state.manager_nom}"
            nom = st.session_state.current_brief_name
            st.session_state.saved_briefs[nom] = {
                "poste_intitule": st.session_state.poste_intitule,
                "manager_nom": st.session_state.manager_nom,
                "recruteur": st.session_state.recruteur,
                "affectation_type": st.session_state.affectation_type,
                "affectation_nom": st.session_state.affectation_nom,
                "date_brief": str(st.session_state.date_brief),
                "ksa_data": st.session_state.ksa_data,
            }
            save_briefs()
            st.success(f"✅ Brief créé avec succès : {nom}")
            st.session_state.brief_phase = "🔄 Avant-brief"
            st.rerun()

    with col2:
        st.subheader("🔍 Recherche & Chargement")
        filter_month = st.selectbox("Mois", [""] + [f"{i:02d}" for i in range(1, 13)], key="filter_month")
        filter_recruteur = st.text_input("Recruteur", key="filter_recruteur")
        filter_poste = st.text_input("Poste", key="filter_poste")
        filter_manager = st.text_input("Manager", key="filter_manager")

        if st.button("Rechercher briefs"):
            st.session_state.filtered_briefs = filter_briefs(
                st.session_state.saved_briefs,
                filter_month or None,
                filter_recruteur or None,
                filter_poste or None,
                filter_manager or None
            )
            st.session_state.show_filtered_results = True

        if st.session_state.show_filtered_results and st.session_state.filtered_briefs:
            selected_brief = st.selectbox("Choisir un brief", [""] + list(st.session_state.filtered_briefs.keys()))
            if selected_brief and st.button("📂 Charger ce brief"):
                loaded_data = st.session_state.filtered_briefs[selected_brief]
                for k, v in loaded_data.items():
                    st.session_state[k] = v
                st.session_state.current_brief_name = selected_brief
                st.success("Brief chargé avec succès!")
                st.rerun()
            if selected_brief and st.button("🗑️ Supprimer ce brief"):
                del st.session_state.saved_briefs[selected_brief]
                save_briefs()
                st.success("Brief supprimé!")
                st.rerun()

# ---------------- AVANT-BRIEF ----------------
elif brief_phase == "🔄 Avant-brief":
    st.header("🔄 Avant-brief (Préparation)")
    st.info("Remplissez les informations préparatoires avant la réunion avec le manager.")

    conseil_button("Raison ouverture", "Contexte", "Pourquoi ce poste est-il ouvert?", key="raison_ouverture")
    conseil_button("Impact stratégique", "Contexte", "Impact stratégique du poste", key="impact_strategique")
    st.text_area("Rattachement hiérarchique", key="rattachement")
    st.text_area("Défis principaux", key="defis_principaux")

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Modifications sauvegardées")
# ---------------- RÉUNION (Wizard interne) ----------------
elif brief_phase == "✅ Réunion de brief":
    st.header("✅ Réunion de brief avec le Manager")

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
        st.text_area("Critères d’exclusion", key="criteres_exclusion")
        st.text_area("Processus d’évaluation (détails)", key="processus_evaluation")

        if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True):
            save_briefs()
            st.success("✅ Données de réunion sauvegardées")

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
elif brief_phase == "📝 Synthèse":
    st.header("📝 Synthèse du Brief")
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
    # Exemple simple basé sur KSA
    score_total = 0
    count = 0
    for cat, comps in st.session_state.ksa_data.items():
        for comp, details in comps.items():
            score_total += int(details.get("score") or 0)
            count += 1
    score_global = (score_total / count) if count else 0
    st.metric("Score Global Cible", f"{score_global:.2f}/5")

    if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Brief final confirmé et sauvegardé")

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
