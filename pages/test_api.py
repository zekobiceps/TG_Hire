import os, sys, json
import pandas as pd
import streamlit as st
from datetime import datetime, date
from io import BytesIO

# Accès utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    load_briefs,
    get_example_for_field,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
    generate_automatic_brief_name,
    save_library,
    generate_ai_question,
    test_deepseek_connection,
    save_brief_to_gsheet,
    export_brief_pdf_pretty,
    refresh_saved_briefs,
    load_all_local_briefs,
    get_brief_value,
    save_ksa_matrix_to_current_brief
)

# --------------------------------------------------------------------------------
# Initialisation session
# --------------------------------------------------------------------------------
init_session_state()

# Sécurité variable sections (doit exister – sinon créer squelette minimal)
if "sections" not in st.session_state:
    # sections attendue pour Avant-brief (titre + fields (label, key, placeholder))
    st.session_state.sections = [
        {
            "title": "Contexte du poste",
            "fields": [
                ("Raison de l'ouverture", "raison_ouverture", "Pourquoi le poste s'ouvre..."),
                ("Impact stratégique", "impact_strategique", "Impact sur l'organisation..."),
                ("Tâches principales", "taches_principales", "3-6 missions clés...")
            ]
        },
        {
            "title": "Must-have (Indispensables)",
            "fields": [
                ("Expérience", "must_have_experience", "Années, type de projets..."),
                ("Diplômes / Certifications", "must_have_diplomes", "Diplômes, habilitations..."),
                ("Compétences / Outils", "must_have_competences", "Outils, méthodes..."),
                ("Soft skills", "must_have_softskills", "Leadership, rigueur...")
            ]
        },
        {
            "title": "Nice-to-have (Atouts)",
            "fields": [
                ("Expérience additionnelle", "nice_to_have_experience", "Atouts expérience..."),
                ("Diplômes valorisants", "nice_to_have_diplomes", "Certifs / plus..."),
                ("Compétences complémentaires", "nice_to_have_competences", "Atouts techniques...")
            ]
        },
        {
            "title": "Sourcing et marché",
            "fields": [
                ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents / secteurs proches..."),
                ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs..."),
                ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards...")
            ]
        },
        {
            "title": "Profils pertinents",
            "fields": [
                ("Lien profil 1", "lien_profil_1", "URL"),
                ("Lien profil 2", "lien_profil_2", "URL"),
                ("Lien profil 3", "lien_profil_3", "URL")
            ]
        },
        {
            "title": "Notes libres",
            "fields": [
                ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à valider..."),
                ("Case libre", "notes_libres", "Notes diverses...")
            ]
        }
    ]
sections = st.session_state.sections

# --------------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------------
tabs = st.tabs(["Gestion", "Avant-brief", "Réunion", "Synthèse"])

# =================================================================================
# ONGLET 1 : GESTION
# =================================================================================
with tabs[0]:
    st.header("📂 Gestion des briefs")

    # Formulaire rapide création
    with st.expander("➕ Créer un nouveau brief", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            poste = st.text_input("Intitulé du poste", key="poste_intitule")
        with c2:
            manager = st.text_input("Manager", key="manager_nom")
        with c3:
            recruteur = st.text_input("Recruteur", key="recruteur")

        col_date, col_aff_type, col_aff_nom = st.columns(3)
        with col_date:
            if "date_brief" not in st.session_state:
                st.session_state.date_brief = date.today()
            st.date_input("Date du brief", key="date_brief")
        with col_aff_type:
            st.selectbox("Affectation (type)", ["", "Chantier", "Siège", "Dépôt"], key="affectation_type")
        with col_aff_nom:
            st.text_input("Nom affectation", key="affectation_nom")

        if st.button("Créer le brief", type="primary"):
            if not poste or not manager:
                st.warning("Intitulé + Manager requis.")
            else:
                brief_name = generate_automatic_brief_name(poste, manager, st.session_state.date_brief)
                if brief_name in st.session_state.saved_briefs:
                    st.error("Ce brief existe déjà.")
                else:
                    st.session_state.saved_briefs[brief_name] = {
                        "BRIEF_NAME": brief_name,
                        "POSTE_INTITULE": poste,
                        "MANAGER_NOM": manager,
                        "RECRUTEUR": recruteur,
                        "AFFECTATION_TYPE": st.session_state.affectation_type,
                        "AFFECTATION_NOM": st.session_state.affectation_nom,
                        "DATE_BRIEF": str(st.session_state.date_brief)
                    }
                    st.session_state.current_brief_name = brief_name
                    save_briefs()
                    save_brief_to_gsheet(brief_name, st.session_state.saved_briefs[brief_name])
                    st.success(f"Brief créé: {brief_name}")
                    st.rerun()

    st.markdown("### 🔎 Filtrer")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.date_input("Date", key="filter_date", value=None)
    with f2:
        st.text_input("Recruteur", key="filter_recruteur")
    with f3:
        st.text_input("Manager", key="filter_manager")
    f4, f5, f6 = st.columns(3)
    with f4:
        st.selectbox("Affectation", ["", "Chantier", "Siège", "Dépôt"], key="filter_affectation")
    with f5:
        st.text_input("Nom affectation", key="filter_nom_affectation")
    with f6:
        st.selectbox("Type de brief", ["", "Standard", "Urgent", "Stratégique"], key="filter_brief_type")

    if st.button("Appliquer le filtre"):
        month = st.session_state.filter_date.strftime("%m") if st.session_state.filter_date else ""
        st.session_state.filtered_briefs = filter_briefs(
            st.session_state.saved_briefs,
            month,
            st.session_state.filter_recruteur,
            st.session_state.filter_brief_type,
            st.session_state.filter_manager,
            st.session_state.filter_affectation,
            st.session_state.filter_nom_affectation
        )
        st.session_state.show_filtered_results = True
        st.rerun()

    if st.session_state.get("show_filtered_results"):
        st.markdown("### 📋 Briefs sauvegardés")
        briefs_to_show = st.session_state.filtered_briefs
        if briefs_to_show:
            for name in sorted(briefs_to_show.keys()):
                bd = briefs_to_show[name]
                cA, cB, cC, cD = st.columns([5, 1, 1, 1])
                with cA:
                    st.write(f"• {name} | Manager: {bd.get('MANAGER_NOM','')} | Affectation: {bd.get('AFFECTATION_NOM','')}")
                with cB:
                    if st.button("✏️", key=f"edit_{name}", help="Éditer"):
                        st.session_state.current_brief_name = name
                        # Charger KSA JSON
                        kjson = bd.get("KSA_MATRIX_JSON", "")
                        if kjson:
                            try:
                                st.session_state.ksa_matrix = pd.DataFrame(json.loads(kjson))
                            except:
                                st.session_state.ksa_matrix = pd.DataFrame()
                        st.rerun()
                with cC:
                    if st.button("🗑️", key=f"del_{name}", help="Supprimer"):
                        st.session_state.saved_briefs.pop(name, None)
                        save_briefs()
                        st.success("Supprimé.")
                        st.rerun()
                with cD:
                    if st.button("📄", key=f"exp_{name}", help="Exporter (PDF/Word)"):
                        st.session_state.current_brief_name = name
                        # Déclencher juste export modal
                        st.info("Allez sur Synthèse pour exporter.")
        else:
            st.info("Aucun résultat.")
    else:
        st.caption("Aucun brief affiché tant que vous n'appliquez pas un filtre.")

# =================================================================================
# ONGLET 2 : AVANT-BRIEF
# =================================================================================
with tabs[1]:
    st.header("📝 Avant-brief")

    if not st.session_state.current_brief_name:
        st.info("Créez ou sélectionnez un brief dans l’onglet Gestion.")
    else:
        brief_name = st.session_state.current_brief_name
        brief_data = st.session_state.saved_briefs.get(brief_name, {})

        st.markdown("### 💡 Assistance IA (suggestion ciblée)")
        ai_c1, ai_c2 = st.columns([3,1])
        with ai_c1:
            ai_field_opts = [
                f"{section['title']} ➜ {label}"
                for section in sections
                for (label, key, placeholder) in section["fields"]
            ]
            selected_ai_field = st.selectbox("Champ à enrichir", ai_field_opts, key="ab_ai_field")
        with ai_c2:
            if st.button("💡 Suggestion IA"):
                sec_title, field_label = selected_ai_field.split(" ➜ ", 1)
                for section in sections:
                    if section["title"] == sec_title:
                        for label, key, placeholder in section["fields"]:
                            if label == field_label:
                                advice = generate_checklist_advice(section["title"], label)
                                ex = get_example_for_field(section["title"], label)
                                st.session_state[f"advice_{key}"] = (advice or "") + (f"\nExemple:\n{ex}" if ex else "")
                                st.success("Suggestion ajoutée au champ.")
                                break

        with st.form("avant_brief_form"):
            for section in sections:
                st.markdown(f"#### {section['title']}")
                for label, key, placeholder in section["fields"]:
                    current_val = brief_data.get(key, "")
                    # injection suggestion si présente
                    if st.session_state.get(f"advice_{key}"):
                        if not current_val or st.session_state[f"advice_{key}"] not in current_val:
                            current_val = st.session_state[f"advice_{key}"]
                    st.text_area(label, key=f"ab_{key}", value=current_val, placeholder=placeholder, height=140)
                    if st.session_state.get(f"advice_{key}"):
                        st.info(st.session_state[f"advice_{key}"])
            submitted = st.form_submit_button("💾 Enregistrer")
            if submitted:
                # Sauvegarde
                for section in sections:
                    for label, key, placeholder in section["fields"]:
                        brief_data[key] = st.session_state.get(f"ab_{key}", "")
                st.session_state.saved_briefs[brief_name] = brief_data
                save_briefs()
                save_brief_to_gsheet(brief_name, brief_data)
                st.success("Avant-brief sauvegardé.")
                st.rerun()

# =================================================================================
# ONGLET 3 : RÉUNION DE BRIEF
# =================================================================================
with tabs[2]:
    st.header("👥 Réunion de brief")

    total_steps = 4
    if "reunion_step" not in st.session_state or not isinstance(st.session_state.reunion_step, int):
        st.session_state.reunion_step = 1
    step = st.session_state.reunion_step
    pct = int(((step - 1) / (total_steps - 1)) * 100)
    st.progress(pct, text=f"Étape {step}/{total_steps}")

    if not st.session_state.current_brief_name:
        st.info("Sélectionnez un brief dans Gestion.")
    else:
        brief_name = st.session_state.current_brief_name
        brief_data = st.session_state.saved_briefs.get(brief_name, {})

        # Charger KSA depuis JSON si vide
        if ("ksa_matrix" not in st.session_state or
            not isinstance(st.session_state.ksa_matrix, pd.DataFrame) or
            st.session_state.ksa_matrix.empty) and brief_data.get("KSA_MATRIX_JSON"):
            try:
                st.session_state.ksa_matrix = pd.DataFrame(json.loads(brief_data["KSA_MATRIX_JSON"]))
            except:
                st.session_state.ksa_matrix = pd.DataFrame()

        # ---- Étape 1 : Synthèse + commentaires manager ----
        if step == 1:
            st.subheader("📝 Étape 1 : Synthèse & commentaires manager")
            rows = []
            for section in sections:
                if section["title"] == "Profils pertinents":
                    continue
                for label, key, _ in section["fields"]:
                    rows.append({
                        "Section": section["title"],
                        "Item": label,
                        "Infos": get_brief_value(brief_data, key, ""),
                        "Commentaire manager": brief_data.get("manager_comments", {}).get(key, ""),
                        "_key": key
                    })
            if not rows:
                st.warning("Avant-brief vide.")
            else:
                base_df = pd.DataFrame(rows)
                display_df = base_df.drop(columns=["_key"])
                edited_df = st.data_editor(
                    display_df,
                    hide_index=True,
                    key="reunion_step1_editor",
                )
                if st.button("Enregistrer commentaires", key="save_mgr_comments"):
                    new_comments = {}
                    for idx, row in edited_df.iterrows():
                        val = row.get("Commentaire manager")
                        if val and idx in base_df.index:
                            orig_key = base_df.loc[idx, "_key"]  # corrigé (df -> base_df)
                            new_comments[orig_key] = val
                    brief_data["manager_comments"] = new_comments
                    brief_data["MANAGER_COMMENTS_JSON"] = json.dumps(new_comments, ensure_ascii=False)
                    st.session_state.saved_briefs[st.session_state.current_brief_name] = brief_data
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data)
                    st.success("Commentaires sauvegardés.")
                    st.rerun()

        # ---- Étape 2 : KSA ----
        elif step == 2:
            st.subheader("📊 Étape 2 : Matrice KSA")
            with st.expander("ℹ️ Méthode KSA (détails & exemples)", expanded=False):
                st.markdown("""
**KSA = Knowledge / Skills / Abilities**  
Objectif : structurer les questions & réduire les biais.

🧠 Knowledge = Connaissances (réglementaire, technique)  
💪 Skills = Compétences pratiquées (exécution, outils)  
✨ Abilities = Aptitudes durables (leadership, décision)  

Types :
- Comportementale (passé réel – STAR)
- Situationnelle (scénario)
- Technique (validation expertise)
- Générale (vision / structuration)

Exemples :
- Skills / Situationnelle → “Si un chantier prend 2 semaines de retard…”
- Knowledge / Technique → “Explique les étapes critiques d’un PPSPS.”
- Abilities / Comportementale → “Raconte un recadrage difficile.”

Bonnes pratiques : 4–7 critères, 1 question = 1 critère.
""")

            # Formulaire ajout
            with st.form("form_add_ksa"):
                c1, c2, c3, c4 = st.columns([1,1,1,1])
                with c1:
                    rubrique = st.selectbox("Rubrique", ["Knowledge","Skills","Abilities"], key="f_rubrique")
                with c2:
                    critere = st.text_input("Critère", key="f_critere")
                with c3:
                    type_q = st.selectbox("Type de question", ["Comportementale","Situationnelle","Technique","Générale"], key="f_typeq")
                with c4:
                    evaluateur = st.selectbox("Évaluateur", ["Recruteur","Manager","Les deux"], key="f_eval")

                qc, ec = st.columns([3,1])
                with qc:
                    question = st.text_input("Question pour l'entretien", key="f_question", placeholder="Ex: Si un retard critique menace la livraison...")
                with ec:
                    eval_note = st.slider("Évaluation (1-5)", 1, 5, 3, key="f_eval_note")

                prompt = st.text_input("Prompt IA (génération question ciblée)", key="f_prompt",
                                       placeholder="Ex: question situationnelle leadership chantier")
                st.checkbox("⚡ Mode rapide (réponse concise)", key="f_concise")

                bgen, badd = st.columns(2)
                with bgen:
                    gen = st.form_submit_button("💡 Générer IA", use_container_width=True)
                with badd:
                    add = st.form_submit_button("➕ Ajouter", use_container_width=True)

                st.markdown("""
<style>
div[data-testid="stForm"] button:has(span:contains('Générer IA')) {
    background:#c40000 !important;
    color:#fff !important;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

                if gen:
                    if not prompt:
                        st.warning("Indique un prompt.")
                    else:
                        try:
                            resp = generate_ai_question(prompt, concise=st.session_state.f_concise)
                            if resp.lower().startswith("question:"):
                                resp = resp.split(":",1)[1].strip()
                            st.session_state.f_question = resp
                            st.success("Question générée.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur IA: {e}")

                if add:
                    if not critere or not question:
                        st.error("Critère + question requis.")
                    else:
                        new_row = {
                            "Rubrique": rubrique,
                            "Critère": critere,
                            "Type de question": type_q,
                            "Question pour l'entretien": question,
                            "Évaluation (1-5)": eval_note,
                            "Évaluateur": evaluateur
                        }
                        if ("ksa_matrix" not in st.session_state or
                            not isinstance(st.session_state.ksa_matrix, pd.DataFrame) or
                            st.session_state.ksa_matrix.empty):
                            st.session_state.ksa_matrix = pd.DataFrame([new_row])
                        else:
                            st.session_state.ksa_matrix = pd.concat(
                                [st.session_state.ksa_matrix, pd.DataFrame([new_row])],
                                ignore_index=True
                            )
                        # Après avoir fait st.session_state.ksa_matrix = pd.concat(...)
                        save_ksa_matrix_to_current_brief()
                        st.success("Critère ajouté.")
                        st.rerun()

            if "ksa_matrix" in st.session_state and isinstance(st.session_state.ksa_matrix, pd.DataFrame) and not st.session_state.ksa_matrix.empty:
                cols_order = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
                for c in cols_order:
                    if c not in st.session_state.ksa_matrix.columns:
                        st.session_state.ksa_matrix[c] = ""
                edited = st.data_editor(
                    st.session_state.ksa_matrix[cols_order],
                    hide_index=True,
                    use_container_width=True,
                    key="ksa_editor_reunion",
                    column_config={
                        "Rubrique": st.column_config.SelectboxColumn("Rubrique", options=["Knowledge","Skills","Abilities"]),
                        "Type de question": st.column_config.SelectboxColumn("Type de question",
                            options=["Comportementale","Situationnelle","Technique","Générale"]),
                        "Évaluation (1-5)": st.column_config.NumberColumn("Évaluation (1-5)", min_value=1, max_value=5),
                        "Évaluateur": st.column_config.SelectboxColumn("Évaluateur", options=["Recruteur","Manager","Les deux"])
                    }
                )
                # Après edited = st.data_editor(...)
                if not edited.equals(st.session_state.ksa_matrix):
                    st.session_state.ksa_matrix = edited
                    save_ksa_matrix_to_current_brief()
                try:
                    avg = round(st.session_state.ksa_matrix["Évaluation (1-5)"].astype(float).mean(), 2)
                    st.markdown(f"<div style='font-size:20px;margin-top:6px;'>🎯 Score cible moyen : {avg} / 5</div>",
                                unsafe_allow_html=True)
                except:
                    pass
            else:
                st.info("Aucun critère KSA.")

        # ---- Étape 3 : Processus & exclusion ----
        elif step == 3:
            st.subheader("🛠️ Étape 3 : Stratégie & Processus")
            if "canaux_prioritaires" not in st.session_state or not isinstance(st.session_state.canaux_prioritaires, list):
                st.session_state.canaux_prioritaires = []
            st.multiselect("Canaux prioritaires", ["LinkedIn","Jobboards","Cooptation","Chasse","Réseaux métiers"],
                           key="canaux_prioritaires", default=st.session_state.canaux_prioritaires)
            cL, cR = st.columns(2)
            with cL:
                st.text_area("🚫 Critères d'exclusion", key="criteres_exclusion", height=180,
                             placeholder="Ex: Moins de 3 ans sur fonction similaire...")
            with cR:
                st.text_area("🧪 Processus d'évaluation", key="processus_evaluation", height=180,
                             placeholder="Ex: 1. Screening 2. Manager 3. Test 4. Décision")

        # ---- Étape 4 : Final ----
        elif step == 4:
            st.subheader("✅ Étape 4 : Validation finale")
            st.text_area("🗒️ Notes finales manager", key="manager_notes", height=200,
                         placeholder="Points d'attention finaux...")
            if st.button("💾 Sauvegarder & Finaliser", key="btn_finalize_reunion"):
                if "ksa_matrix" in st.session_state:
                    save_ksa_matrix_to_current_brief()
                brief_data["MANAGER_NOTES"] = st.session_state.get("manager_notes","")
                st.session_state.saved_briefs[brief_name] = brief_data
                save_briefs()
                save_brief_to_gsheet(brief_name, brief_data)
                st.success("Réunion finalisée.")
                st.session_state.reunion_completed = True
                st.rerun()

        # Navigation
        nav_prev, nav_next = st.columns([1,1])
        with nav_prev:
            if st.session_state.reunion_step > 1 and st.button("⬅️ Précédent"):
                st.session_state.reunion_step -= 1
                st.rerun()
        with nav_next:
            if st.session_state.reunion_step < 4 and st.button("Suivant ➡️"):
                # Auto-save léger
                if st.session_state.reunion_step in (1,2,3) and st.session_state.current_brief_name:
                    bd = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
                    bd["CRITERES_EXCLUSION"] = st.session_state.get("criteres_exclusion","")
                    bd["PROCESSUS_EVALUATION"] = st.session_state.get("processus_evaluation","")
                    bd["MANAGER_NOTES"] = st.session_state.get("manager_notes","")
                    save_ksa_matrix_to_current_brief()
                    st.session_state.saved_briefs[st.session_state.current_brief_name] = bd
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, bd)
                st.session_state.reunion_step += 1
                st.rerun()

# =================================================================================
# ONGLET 4 : SYNTHÈSE
# =================================================================================
with tabs[3]:
    st.header("📑 Synthèse du brief")
    if not st.session_state.current_brief_name:
        st.info("Sélectionnez un brief.")
    else:
        bname = st.session_state.current_brief_name
        bdata = st.session_state.saved_briefs.get(bname, {})
        st.write(f"**Brief :** {bname}")
        st.write(f"**Poste :** {bdata.get('POSTE_INTITULE', bdata.get('poste_intitule',''))}")
        st.write(f"**Manager :** {bdata.get('MANAGER_NOM', bdata.get('manager_nom',''))}")
        st.write("---")
        # Charger KSA si absent
        if ("ksa_matrix" not in st.session_state or
            not isinstance(st.session_state.ksa_matrix, pd.DataFrame) or
            st.session_state.ksa_matrix.empty):
            kjson = bdata.get("KSA_MATRIX_JSON","")
            if kjson:
                try:
                    st.session_state.ksa_matrix = pd.DataFrame(json.loads(kjson))
                except:
                    st.session_state.ksa_matrix = pd.DataFrame()

        if "ksa_matrix" in st.session_state and isinstance(st.session_state.ksa_matrix, pd.DataFrame) and not st.session_state.ksa_matrix.empty:
            df_show = st.session_state.ksa_matrix.copy()
            needed = ["Rubrique","Critère","Type de question","Question pour l'entretien","Évaluation (1-5)","Évaluateur"]
            for c in needed:
                if c not in df_show.columns:
                    df_show[c] = ""
            st.subheader("📊 Matrice KSA")
            st.dataframe(df_show[needed], hide_index=True, use_container_width=True)
            try:
                avg_s = round(df_show["Évaluation (1-5)"].astype(float).mean(), 2)
                st.markdown(f"<div style='font-size:20px;margin-top:4px;'>🎯 Score cible moyen : {avg_s} / 5</div>",
                            unsafe_allow_html=True)
            except:
                pass
        else:
            st.info("Pas de matrice KSA.")

        # Export
        exp_c1, exp_c2 = st.columns(2)
        with exp_c1:
            if PDF_AVAILABLE and st.button("📄 Export PDF simple"):
                pdf_buf = export_brief_pdf()
                if pdf_buf:
                    st.download_button("⬇️ Télécharger PDF", data=pdf_buf, file_name=f"{bname}.pdf",
                                       mime="application/pdf", key="dl_pdf_simple")
        with exp_c2:
            if WORD_AVAILABLE and st.button("📝 Export Word"):
                wbuf = export_brief_word()
                if wbuf:
                    st.download_button("⬇️ Télécharger Word", data=wbuf, file_name=f"{bname}.docx",
                                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                       key="dl_word")

        # PDF pretty (si lib disponible)
        if PDF_AVAILABLE and st.button("📑 Export PDF structuré"):
            ksa_df = None
            if "ksa_matrix" in st.session_state and isinstance(st.session_state.ksa_matrix, pd.DataFrame):
                ksa_df = st.session_state.ksa_matrix
            buf_pretty = export_brief_pdf_pretty(bname, bdata, ksa_df)
            if buf_pretty:
                st.download_button("⬇️ Télécharger PDF structuré", data=buf_pretty.getvalue(),
                                   file_name=f"{bname}_pretty.pdf", mime="application/pdf", key="dl_pdf_pretty")