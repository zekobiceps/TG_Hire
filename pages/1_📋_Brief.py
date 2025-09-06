import streamlit as st
from utils import (
    init_session_state,
    generate_automatic_brief_name,
    filter_briefs,
    save_briefs,
    BRIEF_TEMPLATES,
    SIMPLIFIED_CHECKLIST,
    export_brief_pdf,
    export_brief_word,
    PDF_AVAILABLE,
    WORD_AVAILABLE
)

# Initialisation de la session
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Brief Recrutement")

# Choix de la phase du brief
brief_phase = st.radio(
    "Phase du Brief:",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"],
    horizontal=True,
    key="brief_phase_selector"
)

st.session_state.brief_phase = brief_phase

# ---------------- Phase Gestion ----------------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        st.session_state.poste_intitule = st.text_input(
            "Intitulé du poste:",
            value=st.session_state.poste_intitule,
            placeholder="Ex: Chargé de recrutement"
        )

        st.session_state.manager_nom = st.text_input(
            "Nom du manager:",
            value=st.session_state.manager_nom,
            placeholder="Ex: Ahmed Alami"
        )

        st.session_state.recruteur = st.selectbox(
            "Recruteur:",
            ["Zakaria", "Sara", "Jalal", "Bouchra"],
            index=["Zakaria", "Sara", "Jalal", "Bouchra"].index(st.session_state.recruteur)
        )

        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.session_state.affectation_type = st.selectbox(
                "Affectation:",
                ["Chantier", "Direction"],
                index=0 if st.session_state.affectation_type == "Chantier" else 1
            )
        with col_aff2:
            st.session_state.affectation_nom = st.text_input(
                "Nom:",
                value=st.session_state.affectation_nom,
                placeholder=f"Nom du {st.session_state.affectation_type.lower()}"
            )

        if (
            st.session_state.manager_nom
            and st.session_state.poste_intitule
            and st.session_state.recruteur
            and st.session_state.affectation_nom
        ):
            suggested_name = generate_automatic_brief_name()
            st.session_state.current_brief_name = st.text_input(
                "Nom du brief:",
                value=suggested_name,
                placeholder="Nom automatique généré"
            )

    with col2:
        st.subheader("Chargement & Templates")

        st.markdown("**Filtres de recherche:**")
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            filter_month = st.selectbox("Mois:", [""] + [f"{i:02d}" for i in range(1, 13)], key="filter_month")
            filter_recruteur = st.selectbox(
                "Recruteur:",
                [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"],
                key="filter_recruteur"
            )

        with filter_col2:
            filter_poste = st.text_input("Poste:", key="filter_poste")
            filter_manager = st.text_input("Manager:", key="filter_manager")

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
                st.markdown(f"**{len(st.session_state.filtered_briefs)} brief(s) trouvé(s):**")

                selected_brief = st.selectbox(
                    "Choisir un brief:", [""] + list(st.session_state.filtered_briefs.keys())
                )
                target_tab = st.radio("Charger dans:", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)

                col_load1, col_load2 = st.columns(2)
                with col_load1:
                    if selected_brief and st.button("📂 Charger ce brief"):
                        loaded_data = st.session_state.filtered_briefs[selected_brief]
                        if isinstance(loaded_data, dict):
                            st.session_state.poste_intitule = loaded_data.get("poste_intitule", "")
                            st.session_state.manager_nom = loaded_data.get("manager_nom", "")
                            st.session_state.recruteur = loaded_data.get("recruteur", "Zakaria")
                            st.session_state.affectation_type = loaded_data.get("affectation_type", "Chantier")
                            st.session_state.affectation_nom = loaded_data.get("affectation_nom", "")
                            st.session_state.brief_data = loaded_data.get("brief_data", {})
                            st.session_state.ksa_data = loaded_data.get("ksa_data", {})
                            st.session_state.comment_libre = loaded_data.get("comment_libre", "")
                            st.session_state.current_brief_name = selected_brief

                            st.session_state.brief_phase = target_tab
                            st.success("Brief chargé avec succès!")
                            st.rerun()

                with col_load2:
                    if selected_brief and st.button("🗑️ Supprimer ce brief"):
                        del st.session_state.saved_briefs[selected_brief]
                        if selected_brief in st.session_state.filtered_briefs:
                            del st.session_state.filtered_briefs[selected_brief]
                        save_briefs()
                        st.success("Brief supprimé!")
                        st.rerun()
            else:
                st.warning("Aucun brief trouvé avec ces critères.")

        st.divider()
        template_choice = st.selectbox("Choisir un template:", list(BRIEF_TEMPLATES.keys()))

        col_template1, col_template2 = st.columns(2)
        with col_template1:
            if st.button("🔄 Appliquer le template"):
                st.session_state.brief_data = BRIEF_TEMPLATES[template_choice].copy()
                st.success("Template appliqué!")
                st.rerun()

        with col_template2:
            if st.button("🔄 Réinitialiser tout"):
                st.session_state.brief_data = {
                    category: {item: {"valeur": "", "importance": 3} for item in items}
                    for category, items in SIMPLIFIED_CHECKLIST.items()
                }
                st.session_state.ksa_data = {}
                st.success("Brief réinitialisé!")
                st.rerun()

    st.divider()
    st.subheader("📄 Export du Brief")
    col_export1, col_export2 = st.columns(2)

    with col_export1:
        if PDF_AVAILABLE:
            if st.button("📄 Exporter en PDF", use_container_width=True):
                pdf_buffer = export_brief_pdf()
                if pdf_buffer:
                    st.download_button(
                        label="⬇️ Télécharger PDF",
                        data=pdf_buffer,
                        file_name=f"brief_{st.session_state.poste_intitule.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.info("📄 Exporter en PDF: pip install reportlab")

    with col_export2:
        if WORD_AVAILABLE:
            if st.button("📄 Exporter en Word", use_container_width=True):
                word_buffer = export_brief_word()
                if word_buffer:
                    st.download_button(
                        label="⬇️ Télécharger Word",
                        data=word_buffer,
                        file_name=f"brief_{st.session_state.poste_intitule.replace(' ', '_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
        else:
            st.info("📄 Exporter en Word: pip install python-docx")
