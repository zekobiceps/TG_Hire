import sys
import os
import importlib.util
import streamlit as st
from datetime import datetime

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# Initialisation des variables manquantes
defaults = {
    "poste_intitule": "",
    "manager_nom": "",
    "recruteur": "Zakaria",
    "affectation_type": "Chantier",
    "affectation_nom": "",
    "current_brief_name": "",
    "saved_briefs": {},
    "filtered_briefs": {},
    "show_filtered_results": False,
    "brief_data": {},
    "ksa_data": {},
    "comment_libre": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Brief Recrutement")

# -------------------- Phase sélection --------------------
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

    # -------- Colonne gauche --------
    with col1:
        st.subheader("Informations de base")

        st.session_state.poste_intitule = st.text_input(
            "Intitulé du poste:",
            value=st.session_state.poste_intitule,
            placeholder="Ex: Chargé de recrutement",
            key="brief_poste_intitule"
        )

        st.session_state.manager_nom = st.text_input(
            "Nom du manager:",
            value=st.session_state.manager_nom,
            placeholder="Ex: Ahmed Alami",
            key="brief_manager_nom"
        )

        st.session_state.recruteur = st.selectbox(
            "Recruteur:",
            ["Zakaria", "Sara", "Jalal", "Bouchra"],
            index=["Zakaria", "Sara", "Jalal", "Bouchra"].index(st.session_state.recruteur),
            key="brief_recruteur"
        )

        col_aff1, col_aff2 = st.columns(2)
        with col_aff1:
            st.session_state.affectation_type = st.selectbox(
                "Affectation:",
                ["Chantier", "Direction"],
                index=0 if st.session_state.affectation_type == "Chantier" else 1,
                key="brief_affectation_type"
            )
        with col_aff2:
            st.session_state.affectation_nom = st.text_input(
                "Nom:",
                value=st.session_state.affectation_nom,
                placeholder=f"Nom du {st.session_state.affectation_type.lower()}",
                key="brief_affectation_nom"
            )

        if (
            st.session_state.manager_nom
            and st.session_state.poste_intitule
            and st.session_state.recruteur
            and st.session_state.affectation_nom
        ):
            suggested_name = utils.generate_automatic_brief_name()
            st.session_state.current_brief_name = st.text_input(
                "Nom du brief:",
                value=suggested_name,
                placeholder="Nom automatique généré",
                key="brief_nom"
            )

    # -------- Colonne droite --------
    with col2:
        st.subheader("Chargement & Templates")

        st.markdown("**Filtres de recherche:**")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_month = st.selectbox("Mois:", [""] + [f"{i:02d}" for i in range(1, 13)], key="filter_month")
            filter_recruteur = st.selectbox("Recruteur:", [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"], key="filter_recruteur")
        with filter_col2:
            filter_poste = st.text_input("Poste:", key="filter_poste")
            filter_manager = st.text_input("Manager:", key="filter_manager")

        if st.button("🔍 Rechercher briefs", type="secondary", key="search_briefs"):
            st.session_state.filtered_briefs = utils.filter_briefs(
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

                selected_brief = st.selectbox("Choisir un brief:", [""] + list(st.session_state.filtered_briefs.keys()), key="select_brief")
                target_tab = st.radio("Charger dans:", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True, key="target_tab")

                col_load1, col_load2 = st.columns(2)
                with col_load1:
                    if selected_brief and st.button("📂 Charger ce brief", key="load_brief"):
                        loaded_data = st.session_state.filtered_briefs[selected_brief]
                        if isinstance(loaded_data, dict):
                            for k in ["poste_intitule", "manager_nom", "recruteur", "affectation_type", "affectation_nom", "brief_data", "ksa_data", "comment_libre"]:
                                st.session_state[k] = loaded_data.get(k, st.session_state[k])
                            st.session_state.current_brief_name = selected_brief
                            st.session_state.brief_phase = target_tab
                            st.success("Brief chargé avec succès!")
                            st.rerun()

                with col_load2:
                    if selected_brief and st.button("🗑️ Supprimer ce brief", key="delete_brief"):
                        del st.session_state.saved_briefs[selected_brief]
                        if selected_brief in st.session_state.filtered_briefs:
                            del st.session_state.filtered_briefs[selected_brief]
                        utils.save_briefs()
                        st.success("Brief supprimé!")
                        st.rerun()
            else:
                st.warning("Aucun brief trouvé avec ces critères.")

        st.divider()
        # Application d’un template existant
        template_choice = st.selectbox("Choisir un template:", list(utils.BRIEF_TEMPLATES.keys()), key="template_choice")
        col_template1, col_template2 = st.columns(2)
        with col_template1:
            if st.button("🔄 Appliquer le template", key="apply_template"):
                st.session_state.brief_data = utils.BRIEF_TEMPLATES[template_choice].copy()
                st.success("Template appliqué!")
                st.rerun()
        with col_template2:
            if st.button("🔄 Réinitialiser tout", key="reset_template"):
                st.session_state.brief_data = {
                    category: {item: {"valeur": "", "importance": 3} for item in items}
                    for category, items in utils.SIMPLIFIED_CHECKLIST.items()
                }
                st.session_state.ksa_data = {}
                st.success("Brief réinitialisé!")
                st.rerun()

    st.divider()
    st.subheader("📄 Export du Brief")
    col_export1, col_export2 = st.columns(2)
    with col_export1:
        if utils.PDF_AVAILABLE:
            if st.button("📄 Exporter en PDF", use_container_width=True, key="export_pdf"):
                pdf_buffer = utils.export_brief_pdf()
                if pdf_buffer:
                    st.download_button(
                        label="⬇️ Télécharger PDF",
                        data=pdf_buffer,
                        file_name=f"brief_{st.session_state.poste_intitule.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf"
                    )
        else:
            st.info("📄 Exporter en PDF: pip install reportlab")

    with col_export2:
        if utils.WORD_AVAILABLE:
            if st.button("📄 Exporter en Word", use_container_width=True, key="export_word"):
                word_buffer = utils.export_brief_word()
                if word_buffer:
                    st.download_button(
                        label="⬇️ Télécharger Word",
                        data=word_buffer,
                        file_name=f"brief_{st.session_state.poste_intitule.replace(' ', '_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="download_word"
                    )
        else:
            st.info("📄 Exporter en Word: pip install python-docx")

    st.divider()
    # -------- Sauvegarde vers bibliothèque --------
    if st.button("💾 Sauvegarder dans la bibliothèque", key="save_brief_lib"):
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": "Brief",
            "poste": st.session_state.poste_intitule,
            "requete": f"Brief {st.session_state.current_brief_name}",
        }
        st.session_state.library_entries.append(entry)
        utils.save_library_entries()
        st.success("✅ Brief ajouté à la bibliothèque")

# -------------------- Phase Avant-brief --------------------
elif brief_phase == "🔄 Avant-brief":
    st.header("🔄 Avant-brief")
    st.write("➡️ Ici tu ajoutes les champs spécifiques à l’avant-brief (questions au manager, contexte, etc.)")
    st.session_state.comment_libre = st.text_area("Commentaires libres", value=st.session_state.comment_libre, key="avant_comment")

# -------------------- Phase Réunion de brief --------------------
elif brief_phase == "✅ Réunion de brief":
    st.header("✅ Réunion de brief")
    st.write("➡️ Ici tu ajoutes les champs spécifiques à la réunion de brief (points validés, validations finales, etc.)")
    st.session_state.comment_libre = st.text_area("Compte rendu réunion", value=st.session_state.comment_libre, key="reunion_comment")
