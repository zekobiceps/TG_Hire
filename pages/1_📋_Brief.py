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
    export_brief_word
)

# ---------------- Init ----------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Brief Recrutement")

# ---------------- Choix de la phase ----------------
brief_phase = st.radio(
    "Phase du Brief:",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"],
    horizontal=True,
    key="brief_phase_selector"
)
st.session_state.brief_phase = brief_phase

# ---------------- Fonction Section KSA ----------------
def render_ksa_section():
    st.subheader("📊 Modèle KSA (Knowledge, Skills, Abilities)")

    categories = ["Knowledge (Connaissances)", "Skills (Savoir-faire)", "Abilities (Aptitudes)"]

    for cat in categories:
        if cat not in st.session_state.ksa_data:
            st.session_state.ksa_data[cat] = {}

        with st.expander(cat, expanded=True):
            new_comp = st.text_input(f"Ajouter {cat}", key=f"new_{cat}")
            if st.button(f"➕ Ajouter {cat}", key=f"btn_add_{cat}") and new_comp:
                st.session_state.ksa_data[cat][new_comp] = {
                    "niveau": "Intermédiaire",
                    "priorite": "Indispensable",
                    "evaluateur": "Recruteur",
                    "score": "",
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
                        "Score", min_value=0, max_value=10, value=int(details.get("score") or 0),
                        key=f"score_{cat}_{comp}"
                    )
                with col6:
                    if st.button("🗑️", key=f"del_{cat}_{comp}"):
                        del st.session_state.ksa_data[cat][comp]
                        st.rerun()

# ---------------- Fonction Section Texte ----------------
def render_text_sections():
    st.subheader("📝 Sections descriptives")
    st.session_state.brief_data["contexte"] = st.text_area(
        "Contexte du poste",
        value=st.session_state.brief_data.get("contexte", ""),
        height=100
    )
    st.session_state.brief_data["missions"] = st.text_area(
        "Missions principales",
        value=st.session_state.brief_data.get("missions", ""),
        height=120
    )
    st.session_state.brief_data["profil"] = st.text_area(
        "Profil recherché",
        value=st.session_state.brief_data.get("profil", ""),
        height=120
    )
    st.session_state.comment_libre = st.text_area(
        "Commentaire libre",
        value=st.session_state.comment_libre,
        height=80
    )

# ---------------- Phase Gestion ----------------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        st.session_state.poste_intitule = st.text_input("Intitulé du poste", value=st.session_state.poste_intitule)
        st.session_state.manager_nom = st.text_input("Nom du manager", value=st.session_state.manager_nom)
        st.session_state.recruteur = st.selectbox(
            "Recruteur",
            ["", "Zakaria", "Sara", "Jalal", "Bouchra"],
            index=(["", "Zakaria", "Sara", "Jalal", "Bouchra"].index(st.session_state.recruteur)
                   if st.session_state.recruteur in ["Zakaria", "Sara", "Jalal", "Bouchra"] else 0),
            key="recruteur_gestion"
        )
        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.session_state.affectation_type = st.selectbox(
                "Affectation",
                ["Chantier", "Direction"],
                index=0 if st.session_state.affectation_type == "Chantier" else 1
            )
        with col_aff2:
            st.session_state.affectation_nom = st.text_input("Nom", value=st.session_state.affectation_nom)

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
                "brief_data": st.session_state.brief_data,
                "ksa_data": st.session_state.ksa_data,
                "comment_libre": st.session_state.comment_libre,
            }
            st.session_state.saved_briefs[nom] = save_data
            save_briefs()
            st.success(f"✅ Brief créé avec succès sous le nom : {nom}")
            st.session_state.brief_phase = "🔄 Avant-brief"
            st.rerun()

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

# ---------------- Phase Avant-brief ----------------
elif brief_phase == "🔄 Avant-brief":
    st.info("Phase de préparation : remplissez les informations collectées avant la réunion.")
    render_ksa_section()
    render_text_sections()
    if st.button("💾 Enregistrer modifications (Avant-brief)", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Modifications sauvegardées")

# ---------------- Phase Réunion ----------------
elif brief_phase == "✅ Réunion de brief":
    st.info("Phase de réunion : corrigez et validez les informations avec le manager.")
    render_ksa_section()
    render_text_sections()
    if st.button("💾 Enregistrer modifications (Réunion)", type="primary", use_container_width=True):
        save_briefs()
        st.success("✅ Modifications sauvegardées")

# ---------------- Export ----------------
st.divider()
st.subheader("📄 Export du Brief")
col1, col2 = st.columns(2)
with col1:
    if PDF_AVAILABLE:
        if st.button("📄 Exporter en PDF", use_container_width=True):
            pdf_buffer = export_brief_pdf()
            if pdf_buffer:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buffer,
                                   file_name=f"brief_{st.session_state.poste_intitule}.pdf", mime="application/pdf")
    else:
        st.info("PDF non dispo (pip install reportlab)")
with col2:
    if WORD_AVAILABLE:
        if st.button("📄 Exporter en Word", use_container_width=True):
            word_buffer = export_brief_word()
            if word_buffer:
                st.download_button("⬇️ Télécharger Word", data=word_buffer,
                                   file_name=f"brief_{st.session_state.poste_intitule}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        st.info("Word non dispo (pip install python-docx)")
