import streamlit as st
from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    BRIEF_TEMPLATES,
    generate_automatic_brief_name,
    filter_briefs,
    save_briefs,
    export_brief_pdf,
    export_brief_word,
    load_briefs,
)

# -------- INIT --------
init_session_state()
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("📋 Brief Recrutement")

# -------- FUNCTION: RENDER KSA --------
def render_ksa_section():
    st.subheader("📊 Modèle KSA (Knowledge, Skills, Abilities)")
    categories = ["Knowledge", "Skills", "Abilities"]

    for cat in categories:
        with st.expander(cat, expanded=True):
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
                st.session_state[f"new_{cat}"] = ""  # reset
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
                        "Score", min_value=0, max_value=10, value=int(details.get("score") or 0),
                        key=f"score_{cat}_{comp}"
                    )
                with col6:
                    if st.button("🗑️", key=f"del_{cat}_{comp}"):
                        del st.session_state.ksa_data[cat][comp]
                        st.rerun()

# -------- PHASE SELECTOR --------
brief_phase = st.radio(
    "Phase du Brief :",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief", "📝 Synthèse"],
    horizontal=True,
    key="brief_phase_selector"
)
st.session_state.brief_phase = brief_phase

# -------- GESTION --------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        st.text_input("Intitulé du poste", key="poste_intitule")
        st.text_input("Nom du manager", key="manager_nom")
        st.selectbox(
            "Recruteur",
            ["", "Zakaria", "Sara", "Jalal", "Bouchra"],
            key="recruteur"
        )
        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.selectbox("Affectation", ["Chantier", "Siège"], key="affectation_type")
        with col_aff2:
            st.text_input("Nom de l’affectation", key="affectation_nom")

        st.date_input("Date du Brief", key="date_brief")

        if st.button("💾 Sauvegarder le brief", type="primary", use_container_width=True):
            if not st.session_state.current_brief_name:
                st.session_state.current_brief_name = generate_automatic_brief_name()
            nom = st.session_state.current_brief_name
            save_data = {
                "poste_intitule": st.session_state.poste_intitule,
                "manager_nom": st.session_state.manager_nom,
                "recruteur": st.session_state.recruteur,
                "affectation_type": st.session_state.affectation_type,
                "affectation_nom": st.session_state.affectation_nom,
                "date_brief": str(st.session_state.date_brief),
                "brief_data": st.session_state.brief_data,
                "ksa_data": st.session_state.ksa_data,
                "comment_libre": st.session_state.comment_libre,
            }
            st.session_state.saved_briefs[nom] = save_data
            save_briefs()
            st.success(f"✅ Brief créé avec succès sous le nom : {nom}")

    with col2:
        st.subheader("Chargement & Templates")
        st.markdown("**Filtres de recherche**")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_month = st.selectbox("Mois", [""] + [f"{i:02d}" for i in range(1, 13)], key="filter_month")
            filter_recruteur = st.selectbox("Recruteur", [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"], key="filter_recruteur")
        with filter_col2:
            filter_poste = st.text_input("Poste", key="filter_poste")
            filter_manager = st.text_input("Manager", key="filter_manager")

        if st.button("🔍 Rechercher briefs", type="secondary"):
            st.session_state.filtered_briefs = filter_briefs(
                st.session_state.saved_briefs,
                filter_month or None,
                filter_recruteur or None,
                filter_poste or None,
                filter_manager or None
            )
            st.session_state.show_filtered_results = True

        if st.session_state.show_filtered_results:
            if st.session_state.filtered_briefs:
                selected_brief = st.selectbox("Choisir un brief", [""] + list(st.session_state.filtered_briefs.keys()))
                target_tab = st.radio("Charger dans", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)
                col_load1, col_load2 = st.columns(2)
                with col_load1:
                    if selected_brief and st.button("📂 Charger ce brief"):
                        loaded_data = st.session_state.filtered_briefs[selected_brief]
                        for k, v in loaded_data.items():
                            st.session_state[k] = v
                        st.session_state.current_brief_name = selected_brief
                        st.session_state.brief_phase = target_tab
                        st.success("Brief chargé avec succès!")
                        st.rerun()
                with col_load2:
                    if selected_brief and st.button("🗑️ Supprimer ce brief"):
                        del st.session_state.saved_briefs[selected_brief]
                        save_briefs()
                        st.success("Brief supprimé!")
                        st.rerun()

        st.divider()
        template_choice = st.selectbox("Choisir un template", list(BRIEF_TEMPLATES.keys()))
        col_template1, col_template2 = st.columns(2)
        with col_template1:
            if st.button("🔄 Appliquer le template"):
                st.session_state.brief_data = BRIEF_TEMPLATES[template_choice].copy()
                st.success("Template appliqué!")
                st.session_state.brief_phase = "🔄 Avant-brief"
                st.rerun()
        with col_template2:
            if st.button("🗑️ Supprimer ce template"):
                if template_choice in BRIEF_TEMPLATES and template_choice != "Template standard":
                    del BRIEF_TEMPLATES[template_choice]
                    st.success("Template supprimé!")
                    st.rerun()

# -------- AVANT-BRIEF --------
elif brief_phase == "🔄 Avant-brief":
    st.info("Phase de préparation : remplissez les informations collectées avant la réunion.")
    st.text_area("Commentaires libres", key="comment_libre")
    render_ksa_section()
    if st.button("💾 Enregistrer modifications (Avant-brief)", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Modifications sauvegardées")

# -------- REUNION --------
elif brief_phase == "✅ Réunion de brief":
    st.info("Phase de réunion : validez et complétez les informations avec le manager.")
    st.text_area("Notes de réunion", key="notes_reunion")
    render_ksa_section()
    if st.button("💾 Enregistrer modifications (Réunion)", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Modifications sauvegardées")

# -------- SYNTHÈSE --------
elif brief_phase == "📝 Synthèse":
    st.header("📝 Synthèse du Brief")

    st.write("Résumé des informations enregistrées :")
    st.json({
        "Poste": st.session_state.poste_intitule,
        "Manager": st.session_state.manager_nom,
        "Recruteur": st.session_state.recruteur,
        "Affectation": f"{st.session_state.affectation_type} - {st.session_state.affectation_nom}",
        "Date": str(st.session_state.date_brief),
        "KSA": st.session_state.ksa_data
    })

    # -------- EXPORT PDF/WORD --------
    st.subheader("📄 Export du Brief complet")
    col1, col2 = st.columns(2)
    with col1:
        if PDF_AVAILABLE:
            pdf_buf = export_brief_pdf()
            if pdf_buf:
                st.download_button(
                    "⬇️ Télécharger PDF",
                    data=pdf_buf,
                    file_name=f"{st.session_state.current_brief_name}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("⚠️ PDF non dispo (pip install reportlab)")

    with col2:
        if WORD_AVAILABLE:
            word_buf = export_brief_word()
            if word_buf:
                st.download_button(
                    "⬇️ Télécharger Word",
                    data=word_buf,
                    file_name=f"{st.session_state.current_brief_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")
