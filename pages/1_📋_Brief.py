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

# -------------------- Init --------------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Brief Recrutement")

# -------------------- Choix Phase --------------------
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
            st.success(f"✅ Brief créé avec succès sous le nom : {st.session_state.current_brief_name}")

    with col2:
        st.subheader("Chargement & Templates")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_month = st.selectbox("Mois:", [""] + [f"{i:02d}" for i in range(1, 13)], key="filter_month")
            filter_recruteur = st.selectbox("Recruteur:", [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"], key="filter_recruteur")
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
                selected_brief = st.selectbox("Choisir un brief:", [""] + list(st.session_state.filtered_briefs.keys()))
                target_tab = st.radio("Charger dans:", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)
                col_load1, col_load2 = st.columns(2)
                with col_load1:
                    if selected_brief and st.button("📂 Charger ce brief"):
                        loaded_data = st.session_state.filtered_briefs[selected_brief]
                        if isinstance(loaded_data, dict):
                            st.session_state.update(loaded_data)
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
        st.subheader("📑 Templates")
        template_choice = st.selectbox("Choisir un template:", list(BRIEF_TEMPLATES.keys()))
        col_temp1, col_temp2, col_temp3 = st.columns(3)
        with col_temp1:
            if st.button("🔄 Appliquer le template"):
                st.session_state.brief_data = BRIEF_TEMPLATES[template_choice].copy()
                st.success(f"Template {template_choice} appliqué!")
                st.rerun()
        with col_temp2:
            if st.button("💾 Créer un nouveau template"):
                BRIEF_TEMPLATES[st.session_state.current_brief_name] = st.session_state.brief_data.copy()
                st.success(f"Template {st.session_state.current_brief_name} créé!")
        with col_temp3:
            if template_choice != "Template standard" and st.button("🗑️ Supprimer ce template"):
                del BRIEF_TEMPLATES[template_choice]
                st.success(f"Template {template_choice} supprimé!")

# -------------------- Phases Avant & Réunion --------------------
elif brief_phase in ["🔄 Avant-brief", "✅ Réunion de brief"]:
    st.header(f"{brief_phase} - {st.session_state.poste_intitule}")
    st.caption(f"Manager: {st.session_state.manager_nom} | Recruteur: {st.session_state.recruteur}")

    st.subheader("✍️ Remplir le brief")
    for cat, items in SIMPLIFIED_CHECKLIST.items():
        with st.expander(cat, expanded=False):
            for item in items:
                st.session_state.brief_data.setdefault(cat, {})
                st.session_state.brief_data[cat].setdefault(item, {"valeur": "", "importance": 3})
                st.session_state.brief_data[cat][item]["valeur"] = st.text_area(
                    item,
                    value=st.session_state.brief_data[cat][item]["valeur"],
                    key=f"{cat}_{item}_{brief_phase}"
                )

    # --- Volet KSA ---
    st.subheader("📊 Compétences (KSA)")
    for category in ["Knowledge", "Skills", "Abilities"]:
        with st.expander(category, expanded=False):
            new_comp = st.text_input(f"Nouvelle compétence {category}", key=f"new_{category}")
            if st.button(f"➕ Ajouter {category}", key=f"add_{category}"):
                st.session_state.ksa_data.setdefault(category, [])
                st.session_state.ksa_data[category].append({
                    "competence": new_comp,
                    "niveau": "Intermédiaire",
                    "priorite": "Indispensable",
                    "evaluateur": "Manager"
                })
                st.rerun()
            if category in st.session_state.ksa_data:
                for i, comp in enumerate(st.session_state.ksa_data[category]):
                    col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])
                    with col1: st.text_input("Compétence", comp["competence"], key=f"comp_{category}_{i}")
                    with col2: st.selectbox("Niveau", ["Débutant","Intermédiaire","Expert"], index=["Débutant","Intermédiaire","Expert"].index(comp["niveau"]), key=f"niv_{category}_{i}")
                    with col3: st.selectbox("Priorité", ["Indispensable","Souhaitable"], index=["Indispensable","Souhaitable"].index(comp["priorite"]), key=f"prio_{category}_{i}")
                    with col4: st.selectbox("Évaluateur", ["Manager","Recruteur","Les deux"], index=["Manager","Recruteur","Les deux"].index(comp["evaluateur"]), key=f"eval_{category}_{i}")
                    with col5:
                        if st.button("🗑️", key=f"del_{category}_{i}"):
                            st.session_state.ksa_data[category].pop(i)
                            st.rerun()

    # --- Actions ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Enregistrer ce brief"):
            st.session_state.saved_briefs[st.session_state.current_brief_name] = {
                "poste_intitule": st.session_state.poste_intitule,
                "manager_nom": st.session_state.manager_nom,
                "recruteur": st.session_state.recruteur,
                "affectation_type": st.session_state.affectation_type,
                "affectation_nom": st.session_state.affectation_nom,
                "brief_data": st.session_state.brief_data,
                "ksa_data": st.session_state.ksa_data,
                "comment_libre": st.session_state.comment_libre
            }
            save_briefs()
            st.success("✅ Brief enregistré")
    with col2:
        if st.button("👁️ Visualiser le brief"):
            st.subheader("📖 Visualisation du brief")
            st.json(st.session_state.saved_briefs.get(st.session_state.current_brief_name, {}))
    with col3:
        if PDF_AVAILABLE and st.button("📄 Exporter PDF"):
            pdf_buffer = export_brief_pdf()
            if pdf_buffer:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buffer, file_name=f"{st.session_state.current_brief_name}.pdf")
