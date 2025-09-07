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
)

# Init
init_session_state()
st.set_page_config(page_title="TG-Hire IA - Brief", page_icon="🤖", layout="wide")
st.title("📋 Brief Recrutement")

# Reset messages quand on change d’onglet
if "notif_message" not in st.session_state:
    st.session_state.notif_message = ""

brief_phase = st.radio(
    "Phase du Brief:",
    ["📁 Gestion", "🔄 Avant-brief", "✅ Réunion de brief"],
    horizontal=True,
    key="brief_phase_selector",
)
st.session_state.brief_phase = brief_phase
st.session_state.notif_message = ""

# ---------------- Phase Gestion ----------------
if brief_phase == "📁 Gestion":
    st.header("📁 Gestion du Brief")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations de base")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.session_state.poste_intitule = st.text_input(
                "Intitulé du poste", value=st.session_state.poste_intitule
            )
            st.session_state.recruteur = st.selectbox(
                "Recruteur",
                ["", "Zakaria", "Sara", "Jalal", "Bouchra"],
                index=(
                    ["", "Zakaria", "Sara", "Jalal", "Bouchra"].index(st.session_state.recruteur)
                    if st.session_state.recruteur in ["Zakaria", "Sara", "Jalal", "Bouchra"]
                    else 0
                ),
            )
        with col_g2:
            st.session_state.manager_nom = st.text_input(
                "Nom du manager", value=st.session_state.manager_nom
            )
            st.session_state.affectation_type = st.selectbox(
                "Affectation",
                ["Chantier", "Direction"],
                index=0 if st.session_state.affectation_type == "Chantier" else 1,
            )

        st.session_state.affectation_nom = st.text_input(
            "Nom", value=st.session_state.affectation_nom
        )

        if (
            st.session_state.manager_nom
            and st.session_state.poste_intitule
            and st.session_state.recruteur
            and st.session_state.affectation_nom
        ):
            suggested_name = generate_automatic_brief_name()
            st.session_state.current_brief_name = st.text_input(
                "Nom du brief", value=suggested_name
            )
            st.session_state.notif_message = f"✅ Brief créé avec succès sous le nom : {suggested_name}"

        if st.session_state.notif_message:
            st.success(st.session_state.notif_message)

    with col2:
        st.subheader("Chargement & Templates")

        st.markdown("**Filtres de recherche :**")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_month = st.selectbox("Mois", [""] + [f"{i:02d}" for i in range(1, 13)])
            filter_recruteur = st.selectbox("Recruteur", [""] + ["Zakaria", "Sara", "Jalal", "Bouchra"])
        with filter_col2:
            filter_poste = st.text_input("Poste")
            filter_manager = st.text_input("Manager")

        if st.button("🔍 Rechercher briefs", type="secondary"):
            st.session_state.filtered_briefs = filter_briefs(
                st.session_state.saved_briefs,
                filter_month or None,
                filter_recruteur or None,
                filter_poste or None,
                filter_manager or None,
            )
            st.session_state.show_filtered_results = True

        if st.session_state.show_filtered_results:
            if st.session_state.filtered_briefs:
                st.markdown(f"**{len(st.session_state.filtered_briefs)} brief(s) trouvé(s):**")
                selected_brief = st.selectbox("Choisir un brief", [""] + list(st.session_state.filtered_briefs.keys()))
                target_tab = st.radio("Charger dans", ["🔄 Avant-brief", "✅ Réunion de brief"], horizontal=True)

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
        template_choice = st.selectbox("Choisir un template", list(BRIEF_TEMPLATES.keys()))
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
        if PDF_AVAILABLE and st.button("📄 Exporter en PDF", use_container_width=True):
            pdf_buffer = export_brief_pdf()
            if pdf_buffer:
                st.download_button("⬇️ Télécharger PDF", data=pdf_buffer, file_name="brief.pdf", mime="application/pdf")
    with col_export2:
        if WORD_AVAILABLE and st.button("📄 Exporter en Word", use_container_width=True):
            word_buffer = export_brief_word()
            if word_buffer:
                st.download_button("⬇️ Télécharger Word", data=word_buffer, file_name="brief.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ---------------- Phase Avant-brief & Réunion ----------------
elif brief_phase in ["🔄 Avant-brief", "✅ Réunion de brief"]:
    st.caption(
        f"Poste: {st.session_state.poste_intitule or '-'} | "
        f"Manager: {st.session_state.manager_nom or '-'} | "
        f"Recruteur: {st.session_state.recruteur or '-'} | "
        f"Affectation: {st.session_state.affectation_type} {st.session_state.affectation_nom or '-'}"
    )

    # Sections principales
    for category, items in SIMPLIFIED_CHECKLIST.items():
        with st.expander(f"📌 {category}", expanded=False):
            for item in items:
                current_val = st.session_state.brief_data.get(category, {}).get(item, {"valeur": "", "importance": 3})
                st.session_state.brief_data.setdefault(category, {})
                st.session_state.brief_data[category][item] = {
                    "valeur": st.text_area(item, value=current_val["valeur"], height=80, key=f"{brief_phase}_{category}_{item}"),
                    "importance": current_val.get("importance", 3),
                }

    # Volet KSA
    st.subheader("📊 Matrice KSA")
    total_score = 0
    for cat in ["Knowledge (Connaissances)", "Skills (Savoir-faire)", "Abilities (Aptitudes)"]:
        with st.expander(cat, expanded=False):
            st.session_state.ksa_data.setdefault(cat, {})
            to_delete = []
            for comp, details in st.session_state.ksa_data[cat].items():
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                with col1:
                    new_name = st.text_input("Compétence", value=comp, key=f"{cat}_{comp}_name")
                with col2:
                    details["niveau"] = st.selectbox("Niveau", ["Débutant", "Intermédiaire", "Expert"],
                                                    index=["Débutant", "Intermédiaire", "Expert"].index(details.get("niveau", "Intermédiaire")),
                                                    key=f"{cat}_{comp}_niveau")
                with col3:
                    details["priorite"] = st.selectbox("Priorité", ["Indispensable", "Souhaitable"],
                                                       index=["Indispensable", "Souhaitable"].index(details.get("priorite", "Indispensable")),
                                                       key=f"{cat}_{comp}_priorite")
                with col4:
                    details["evaluateur"] = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"],
                                                         index=["Manager", "Recruteur", "Les deux"].index(details.get("evaluateur", "Manager")),
                                                         key=f"{cat}_{comp}_eval")
                with col5:
                    details["eval_score"] = st.checkbox("Évaluer ?", value=details.get("eval_score", False), key=f"{cat}_{comp}_evalscore")
                with col6:
                    if details.get("eval_score", False):
                        details["note"] = st.slider("Note", 1, 5, details.get("note", 3), key=f"{cat}_{comp}_note")
                        total_score += details["note"] * st.session_state.brief_data.get("Missions et Responsabilités", {}).get("Objectifs à atteindre (3-5 maximum)", {}).get("importance", 3)
                    if st.button("🗑️", key=f"delete_{cat}_{comp}"):
                        to_delete.append(comp)
            for comp in to_delete:
                del st.session_state.ksa_data[cat][comp]

            new_comp = st.text_input("➕ Ajouter compétence", key=f"new_{cat}")
            if new_comp:
                if st.button(f"Ajouter {cat}", key=f"add_{cat}"):
                    st.session_state.ksa_data[cat][new_comp] = {"niveau": "Intermédiaire", "priorite": "Indispensable", "evaluateur": "Manager"}
                    st.rerun()

    st.markdown(f"### 🔢 Score global du brief : **{total_score} points**")

    # Commentaires
    st.subheader("💬 Commentaires libres")
    st.session_state.comment_libre = st.text_area("Ajoutez vos notes ici", value=st.session_state.comment_libre, height=120, key=f"{brief_phase}_commentaires")

    # Boutons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder", type="primary", key=f"save_{brief_phase}"):
            st.session_state.saved_briefs[st.session_state.current_brief_name] = {
                "poste_intitule": st.session_state.poste_intitule,
                "manager_nom": st.session_state.manager_nom,
                "recruteur": st.session_state.recruteur,
                "affectation_type": st.session_state.affectation_type,
                "affectation_nom": st.session_state.affectation_nom,
                "brief_data": st.session_state.brief_data,
                "ksa_data": st.session_state.ksa_data,
                "comment_libre": st.session_state.comment_libre,
            }
            save_briefs()
            st.success("✅ Brief sauvegardé avec succès")
    with col2:
        if st.button("🔄 Réinitialiser", key=f"reset_{brief_phase}"):
            st.session_state.brief_data = {cat: {i: {"valeur": "", "importance": 3} for i in items} for cat, items in SIMPLIFIED_CHECKLIST.items()}
            st.session_state.ksa_data = {}
            st.session_state.comment_libre = ""
            st.success("Formulaire réinitialisé")
            st.rerun()
