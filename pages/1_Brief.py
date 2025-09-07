import sys, os
import streamlit as st

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
    
    # Initialisation des données KSA si nécessaire
    if "ksa_data" not in st.session_state:
        st.session_state.ksa_data = {
            "Connaissances": {},
            "Compétences": {},
            "Aptitudes": {}
        }
    
    # Interface pour ajouter de nouvelles compétences
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
    
    # Affichage des compétences existantes
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

# ---------------- ONGLET GESTION ----------------
if st.session_state.brief_phase == "📁 Gestion":
    st.header("📁 Gestion des Briefs")

    # --- INFOS DE BASE (3 colonnes)
    st.subheader("Informations de base")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Intitulé du poste", key="poste_intitule")
        st.text_input("Nom du manager", key="manager_nom")
        st.date_input("Date du Brief", key="date_brief")
    with col2:
        st.text_input("Service", key="service")
        st.text_input("Niveau hiérarchique", key="niveau_hierarchique")
        st.selectbox("Recruteur", ["Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
    with col3:
        st.selectbox("Affectation", ["Chantier", "Siège"], key="affectation_type")
        st.text_input("Nom de l'affectation", key="affectation_nom")
        st.text_input("Budget", key="budget_salaire")

    # --- SAUVEGARDE
    if st.button("💾 Sauvegarder le Brief"):
        brief_name = generate_automatic_brief_name()
        st.session_state.saved_briefs[brief_name] = {
            "poste_intitule": st.session_state.poste_intitule,
            "manager_nom": st.session_state.manager_nom,
            "recruteur": st.session_state.recruteur,
            "date_brief": str(st.session_state.date_brief),
            "service": st.session_state.service,
            "niveau_hierarchique": st.session_state.niveau_hierarchique,
            "affectation_type": st.session_state.affectation_type,
            "affectation_nom": st.session_state.affectation_nom,
            "budget_salaire": st.session_state.budget_salaire,
        }
        save_briefs()
        st.success(f"✅ Brief '{brief_name}' sauvegardé avec succès !")

    st.markdown("---")

    # --- RECHERCHE & CHARGEMENT (2 colonnes)
    st.subheader("Recherche & Chargement")
    col1, col2 = st.columns(2)
    with col1:
        month = st.text_input("Mois (ex: 05)")
        recruteur = st.selectbox("Recruteur", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="search_recruteur")
    with col2:
        poste = st.text_input("Poste")
        manager = st.text_input("Manager")

    if st.button("🔎 Rechercher"):
        briefs = load_briefs()
        st.session_state.filtered_briefs = filter_briefs(briefs, month, recruteur, poste, manager)
        if st.session_state.filtered_briefs:
            st.info(f"ℹ️ {len(st.session_state.filtered_briefs)} brief(s) trouvé(s).")
            st.session_state.show_filtered_results = True
        else:
            st.error("❌ Aucun brief trouvé avec ces critères.")

    if st.session_state.get("show_filtered_results", False):
        for name, data in st.session_state.filtered_briefs.items():
            st.write(f"📌 **{name}** — {data.get('poste_intitule', '')} / {data.get('recruteur', '')}")
            colA, colB = st.columns(2)
            with colA:
                if st.button(f"📂 Charger {name}", key=f"load_{name}"):
                    for k, v in data.items():
                        st.session_state[k] = v
                    st.info(f"ℹ️ Brief '{name}' chargé dans la session.")
            with colB:
                if st.button(f"🗑️ Supprimer {name}", key=f"del_{name}"):
                    all_briefs = load_briefs()
                    if name in all_briefs:
                        del all_briefs[name]
                        st.session_state.saved_briefs = all_briefs
                        save_briefs()
                        st.warning(f"❌ Brief '{name}' supprimé.")

# ---------------- AVANT-BRIEF ----------------
elif st.session_state.brief_phase == "🔄 Avant-brief":
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
elif st.session_state.brief_phase == "✅ Réunion de brief":
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
        st.text_area("Critères d'exclusion", key="criteres_exclusion")
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation")

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
elif st.session_state.brief_phase == "📝 Synthèse":
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
    if "ksa_data" in st.session_state:
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
                                   file_name=f"{st.session_state.get('current_brief_name', 'brief')}.pdf", mime="application/pdf")
        else:
            st.info("⚠️ PDF non dispo (pip install reportlab)")
    with col2:
        if WORD_AVAILABLE:
            word_buf = export_brief_word()
            if word_buf:
                st.download_button("⬇️ Télécharger Word", data=word_buf,
                                   file_name=f"{st.session_state.get('current_brief_name', 'brief')}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")

# ---------------- NAVIGATION PRINCIPALE ----------------
st.sidebar.title("Navigation Brief")
phases = ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief", "📝 Synthèse"]
new_phase = st.sidebar.radio("Phase du brief", phases, index=phases.index(st.session_state.brief_phase))
if new_phase != st.session_state.brief_phase:
    st.session_state.brief_phase = new_phase
    st.rerun()