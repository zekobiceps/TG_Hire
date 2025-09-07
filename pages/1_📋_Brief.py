import streamlit as st
from utils import (
    init_session_state,
    SIMPLIFIED_CHECKLIST,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    BRIEF_TEMPLATES,
    generate_automatic_brief_name,
    filter_briefs,
    save_briefs,
    export_brief_pdf,
    export_brief_word,
    render_ksa_section
)

# -------------------- Initialisation --------------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Brief Recrutement")

# -------------------- Phase --------------------
brief_phase = st.radio(
    "Phase du Brief:",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"],
    horizontal=True,
    key="brief_phase_selector"
)
st.session_state.brief_phase = brief_phase

# -------------------- Phase Gestion --------------------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        st.session_state.poste_intitule = st.text_input("Intitulé du poste:", value=st.session_state.poste_intitule)
        st.session_state.manager_nom = st.text_input("Nom du manager:", value=st.session_state.manager_nom)
        st.session_state.recruteur = st.selectbox("Recruteur:", ["Zakaria", "Sara", "Jalal", "Bouchra"],
                                                  index=["Zakaria", "Sara", "Jalal", "Bouchra"].index(st.session_state.recruteur))
        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.session_state.affectation_type = st.selectbox("Affectation:", ["Chantier", "Direction"],
                                                             index=0 if st.session_state.affectation_type == "Chantier" else 1)
        with col_aff2:
            st.session_state.affectation_nom = st.text_input("Nom:", value=st.session_state.affectation_nom)

        if st.session_state.manager_nom and st.session_state.poste_intitule and st.session_state.recruteur and st.session_state.affectation_nom:
            suggested_name = generate_automatic_brief_name()
            st.session_state.current_brief_name = st.text_input("Nom du brief:", value=suggested_name)

    with col2:
        st.subheader("Chargement & Templates")
        st.markdown("**Filtres de recherche:**")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_month = st.selectbox("Mois:", [""] + [f"{i:02d}" for i in range(1, 13)])
            filter_recruteur = st.selectbox("Recruteur:", [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"])
        with filter_col2:
            filter_poste = st.text_input("Poste:")
            filter_manager = st.text_input("Manager:")

        if st.button("🔍 Rechercher briefs", type="secondary"):
            st.session_state.filtered_briefs = filter_briefs(st.session_state.saved_briefs,
                                                            filter_month or None, filter_recruteur or None,
                                                            filter_poste or None, filter_manager or None)
            st.session_state.show_filtered_results = True

        if st.session_state.show_filtered_results:
            if st.session_state.filtered_briefs:
                selected_brief = st.selectbox("Choisir un brief:", [""] + list(st.session_state.filtered_briefs.keys()))
                target_tab = st.radio("Charger dans:", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)

                col_load1, col_load2 = st.columns(2)
                with col_load1:
                    if selected_brief and st.button("📂 Charger ce brief"):
                        loaded_data = st.session_state.filtered_briefs[selected_brief]
                        if isinstance(loaded_data, dict):
                            for k in ["poste_intitule", "manager_nom", "recruteur", "affectation_type", "affectation_nom", "brief_data", "ksa_data", "comment_libre"]:
                                st.session_state[k] = loaded_data.get(k, st.session_state[k])
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
                st.warning("Aucun brief trouvé.")

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
                st.session_state.brief_data = {cat: {item: {"valeur": "", "importance": 3} for item in items} for cat, items in SIMPLIFIED_CHECKLIST.items()}
                st.session_state.ksa_data = {}
                st.success("Réinitialisé!")
                st.rerun()

    st.divider()
    st.subheader("📄 Export du Brief")
    col_export1, col_export2 = st.columns(2)
    with col_export1:
        if PDF_AVAILABLE and st.button("📄 Exporter en PDF"):
            pdf_buffer = export_brief_pdf()
            if pdf_buffer:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buffer, file_name=f"brief_{st.session_state.poste_intitule}.pdf", mime="application/pdf")
    with col_export2:
        if WORD_AVAILABLE and st.button("📄 Exporter en Word"):
            word_buffer = export_brief_word()
            if word_buffer:
                st.download_button("⬇️ Télécharger Word", data=word_buffer, file_name=f"brief_{st.session_state.poste_intitule}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# -------------------- Phases Avant & Réunion --------------------
elif brief_phase in ["🔄 Avant-brief", "✅ Réunion de brief"]:
    st.header(f"{brief_phase} - {st.session_state.poste_intitule}")
    if st.session_state.manager_nom:
        st.caption(f"Manager: {st.session_state.manager_nom}")
    if st.session_state.recruteur:
        st.caption(f"Recruteur: {st.session_state.recruteur}")
    if st.session_state.affectation_nom:
        st.caption(f"Affectation: {st.session_state.affectation_type} {st.session_state.affectation_nom}")

    categories = list(SIMPLIFIED_CHECKLIST.keys()) + ["Compétences - Modèle KSA"]
    selected_category = st.selectbox("Section à remplir:", categories)

    if selected_category == "Compétences - Modèle KSA":
        render_ksa_section()
    else:
        st.subheader(selected_category)
        for item in SIMPLIFIED_CHECKLIST[selected_category]:
            current_val = st.session_state.brief_data.get(selected_category, {}).get(item, {"valeur": "", "importance": 3})
            st.session_state.brief_data.setdefault(selected_category, {})[item] = {
                "valeur": st.text_area(item, value=current_val["valeur"], height=80),
                "importance": current_val["importance"]
            }

    st.subheader("💬 Commentaires libres")
    st.session_state.comment_libre = st.text_area("Notes:", value=st.session_state.comment_libre, height=120)
