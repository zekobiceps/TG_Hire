import streamlit as st
import sys, os 
from datetime import datetime
import json
import pandas as pd

# ✅ permet d'accéder à utils.py à la racine
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
)

# --- CSS pour augmenter la taille du texte des onglets ---
st.markdown("""
    <style>
    /* Style minimal pour les onglets */
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 10px 16px !important;
    }
    
    /* Style pour les boutons principaux */
    .stButton > button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    /* Style pour les expanders */
    .streamlit-expanderHeader {
        font-weight: 600;
    }
    
    /* Style pour les dataframes */
    .stDataFrame {
        width: 100%;
    }
    
    /* Style pour les textareas */
    .stTextArea textarea {
        min-height: 100px;
        resize: vertical;
    }
    
    /* Permettre le retour à la ligne avec Alt+Enter */
    .stTextArea textarea {
        white-space: pre-wrap !important;
    }
    </style>
""", unsafe_allow_html=True)

def delete_current_brief():
    """Supprime le brief actuel et retourne à l'onglet Gestion"""
    if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
        brief_name = st.session_state.current_brief_name
        file_path = os.path.join("briefs", f"{brief_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            st.session_state.saved_briefs.pop(brief_name, None)
            save_briefs()
            
            st.session_state.current_brief_name = ""
            st.session_state.avant_brief_completed = True
            st.session_state.reunion_completed = True
            st.session_state.reunion_step = 1
            
            keys_to_reset = [
                "manager_nom", "niveau_hierarchique", "affectation_type", 
                "recruteur", "affectation_nom", "date_brief", "raison_ouverture",
                "impact_strategique", "rattachement", "taches_principales",
                "must_have_experience", "must_have_diplomes", "must_have_competences",
                "must_have_softskills", "nice_to_have_experience", "nice_to_have_diplomes",
                "nice_to_have_competences", "entreprises_profil", "synonymes_poste",
                "canaux_profil", "budget", "commentaires", "notes_libres"
            ]
            
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success(f"✅ Brief '{brief_name}' supprimé avec succès")
            st.session_state.brief_phase = "📁 Gestion"
            st.rerun()

# ---------------- INIT ----------------
init_session_state() 
st.set_page_config(
    page_title="TG-Hire IA - Brief",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "brief_phase" not in st.session_state:
    st.session_state.brief_phase = "📁 Gestion"

if "reunion_step" not in st.session_state:
    st.session_state.reunion_step = 1

if "filtered_briefs" not in st.session_state:
    st.session_state.filtered_briefs = {}

if "avant_brief_completed" not in st.session_state:
    st.session_state.avant_brief_completed = True

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = True

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Gestion"
if "save_message" not in st.session_state:
    st.session_state.save_message = None
if "save_message_tab" not in st.session_state:
    st.session_state.save_message_tab = None

# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques Brief")
    
    total_briefs = len(load_briefs())
    completed_briefs = sum(1 for b in load_briefs().values() 
                          if b.get("ksa_matrix") and not b["ksa_matrix"].empty)
    
    st.metric("📋 Briefs créés", total_briefs)
    st.metric("✅ Briefs complétés", completed_briefs)
    
    st.divider()
    if st.button("Tester DeepSeek", key="test_deepseek"):
        test_deepseek_connection()

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px; 
}
.stTextArea textarea {
    white-space: pre-wrap !important;
}
</style>
""", unsafe_allow_html=True)

if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse"
])

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Gestion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    st.session_state.saved_briefs = load_briefs()

    col_info, col_filter = st.columns(2)
    
    with col_info:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Informations de base</h3>', unsafe_allow_html=True)
        
        with st.form(key="create_brief_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text_input("Poste à recruter", key="poste_intitule")
            with col2:
                st.text_input("Manager", key="manager_nom")
            with col3:
                st.selectbox("Recruteur", ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"], key="recruteur")
            
            col4, col5, col6 = st.columns(3)
            with col4:
                st.selectbox("Type d'affectation", ["Chantier", "Siège", "Dépôt"], key="affectation_type")
            with col5:
                st.text_input("Nom affectation", key="affectation_nom")
            with col6:
                st.date_input("Date du brief", key="date_brief", value=datetime.today())
            
            col_create, col_cancel = st.columns(2)
            with col_create:
                if st.form_submit_button("💾 Créer brief", type="primary", use_container_width=True):
                    if not st.session_state.poste_intitule or not st.session_state.manager_nom:
                        st.warning("Veuillez remplir au moins le poste et le nom du manager.")
                    else:
                        brief_name = generate_automatic_brief_name()
                        st.session_state.current_brief_name = brief_name
                        
                        brief_data = {
                            "poste_intitule": st.session_state.poste_intitule,
                            "manager_nom": st.session_state.manager_nom,
                            "recruteur": st.session_state.recruteur,
                            "affectation_type": st.session_state.affectation_type,
                            "affectation_nom": st.session_state.affectation_nom,
                            "date_brief": st.session_state.date_brief,
                            "ksa_matrix": pd.DataFrame(),
                            "manager_comments": {},
                        }
                        
                        st.session_state.saved_briefs[brief_name] = brief_data
                        save_briefs()  
                        save_brief_to_gsheet(brief_name, brief_data)
                        
                        st.success(f"✅ Brief '{brief_name}' créé avec succès")
                        st.rerun()
            with col_cancel:
                if st.form_submit_button("🗑️ Annuler", use_container_width=True):
                    st.session_state.poste_intitule = ""
                    st.session_state.manager_nom = ""
                    st.rerun()

    with col_filter:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">🔍 Filtrer les briefs</h3>', unsafe_allow_html=True)
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.date_input("Date", key="filter_date", value=None)
        with col_filter2:
            st.text_input("Recruteur", key="filter_recruteur")
        with col_filter3:
            st.text_input("Manager", key="filter_manager")
        
        col_filter4, col_filter5, col_filter6 = st.columns(3)
        with col_filter4:
            st.selectbox("Affectation", ["", "Chantier", "Siège", "Dépôt"], key="filter_affectation")
        with col_filter5:
            st.text_input("Nom affectation", key="filter_nom_affectation")
        with col_filter6:
            st.selectbox("Type de brief", ["", "Standard", "Urgent", "Stratégique"], key="filter_brief_type")
        
        if st.button("🔎 Filtrer", use_container_width=True, key="apply_filter"):
            filter_month = st.session_state.filter_date.strftime("%m") if st.session_state.filter_date else ""
            st.session_state.filtered_briefs = filter_briefs(
                st.session_state.saved_briefs,
                filter_month,
                st.session_state.filter_recruteur,
                st.session_state.filter_brief_type,
                st.session_state.filter_manager,
                st.session_state.filter_affectation,
                st.session_state.filter_nom_affectation
            )
            st.session_state.show_filtered_results = True
            st.rerun()
        
        if st.session_state.get("show_filtered_results", False):
            st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
            briefs_to_show = st.session_state.get("filtered_briefs", load_briefs())
            
            if briefs_to_show:
                for name, data in briefs_to_show.items():
                    col_brief1, col_brief2, col_brief3 = st.columns([4, 1, 1])
                    with col_brief1:
                        st.write(f"**{name}** - Manager: {data.get('manager_nom', 'N/A')} - Affectation: {data.get('affectation_nom', 'N/A')}")
                    with col_brief2:
                        if st.button("📝 Éditer", key=f"edit_{name}", use_container_width=True):
                            st.session_state.current_brief_name = name
                            st.rerun()
                    with col_brief3:
                        if st.button("🗑️ Supprimer", key=f"delete_{name}", use_container_width=True):
                            st.session_state.current_brief_name = name
                            delete_current_brief()
            else:
                st.info("Aucun brief sauvegardé ou correspondant aux filtres.")


# ---------------- AVANT-BRIEF ----------------
with tabs[1]:
    if not st.session_state.current_brief_name:
        st.info("Veuillez créer ou sélectionner un brief dans l'onglet 'Gestion' pour commencer.")
    else:
        if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Avant-brief"):
            st.success(st.session_state.save_message)
            st.session_state.save_message = None
            st.session_state.save_message_tab = None

        brief_display_name = f"Avant-brief - {st.session_state.current_brief_name}"
        st.subheader(f"🔄 {brief_display_name}")
        
        sections = [
            {"title": "Contexte du poste", "fields": [("Raison de l'ouverture", "raison_ouverture", "Remplacement, création de poste, nouveau projet..."),("Impact stratégique", "impact_strategique", "En quoi ce poste est-il clé pour les objectifs de l'entreprise ?"),("Tâches principales", "taches_principales", "Lister les missions et responsabilités clés du poste."),]},
            {"title": "Must-have (Indispensables)", "fields": [("Expérience", "must_have_experience", "Nombre d'années minimum, expériences similaires dans le secteur"),("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Diplômes exigés, certifications spécifiques"),("Compétences / Outils", "must_have_competences", "Techniques, logiciels, méthodes à maîtriser"),("Soft skills / aptitudes comportementales", "must_have_softskills", "Leadership, rigueur, communication, autonomie"),]},
            {"title": "Nice-to-have (Atouts)", "fields": [("Expérience additionnelle", "nice_to_have_experience", "Ex. projets internationaux, multi-sites"),("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Diplômes ou certifications supplémentaires appréciés"),("Compétences complémentaires", "nice_to_have_competences", "Compétences supplémentaires non essentielles mais appréciées"),]},
            {"title": "Conditions et contraintes", "fields": [("Localisation", "rattachement", "Site principal, télétravail, déplacements"),("Budget recrutement", "budget", "Salaire indicatif, avantages, primes éventuelles"),]},
            {"title": "Sourcing et marché", "fields": [("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"),("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"),("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels"),]},
            {"title": "Profils pertinents", "fields": [("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"),("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"),("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre"),]},
            {"title": "Notes libres", "fields": [("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"),("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique"),]},
        ]

        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})

        with st.form(key="avant_brief_form"):
            for section in sections:
                with st.expander(f"📋 {section['title']}", expanded=False):
                    for title, key, placeholder in section["fields"]:
                        current_value = brief_data.get(key, st.session_state.get(key, ""))
                        st.text_area(title, value=current_value, key=key, placeholder=placeholder, height=150)

            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Enregistrer modifications", type="primary", use_container_width=True):
                    brief_to_update = st.session_state.saved_briefs[st.session_state.current_brief_name]
                    
                    all_field_keys = [field[1] for section in sections for field in section['fields']]
                    for key in all_field_keys:
                        brief_to_update[key] = st.session_state.get(key)
                    
                    save_briefs()
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_to_update)
                    
                    st.success("✅ Modifications sauvegardées avec succès.")
                    st.rerun()

            with col_cancel:
                if st.form_submit_button("Annuler", use_container_width=True):
                    st.rerun()


# ---------------- REUNION BRIEF ----------------           
with tabs[2]:
    if not st.session_state.current_brief_name:
        st.info("Veuillez créer ou sélectionner un brief dans l'onglet 'Gestion' pour commencer.")
    else:
        brief_display_name = f"Réunion de brief - {st.session_state.current_brief_name}"
        st.markdown(f"<h3>📝 {brief_display_name}</h3>", unsafe_allow_html=True)

        total_steps = 4
        step = st.session_state.reunion_step
        
        st.progress(int((step / total_steps) * 100), text=f"**Étape {step} sur {total_steps}**")

        if step == 1:
            st.subheader("Étape 1 : Validation du brief et commentaires du manager")
            with st.expander("📝 Portrait robot du candidat - Validation", expanded=True):
                brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
                manager_comments = brief_data.get("manager_comments", {})
                
                table_data = []
                # On réutilise la variable 'sections' de l'onglet précédent
                for section in sections:
                    if section["title"] == "Profils pertinents":
                        continue
                    for title, key, _ in section["fields"]:
                        table_data.append({
                            "Section": section["title"], "Détails": title, "Informations": brief_data.get(key, ""),
                            "Commentaires du manager": manager_comments.get(key, ""), "_key": key
                        })
                
                if not table_data:
                    st.warning("Veuillez d'abord remplir l'onglet 'Avant-brief'.")
                else:
                    df = pd.DataFrame(table_data)
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Section": st.column_config.TextColumn(disabled=True),
                            "Détails": st.column_config.TextColumn(disabled=True),
                            "Informations": st.column_config.TextColumn(disabled=True, width="large"),
                            "Commentaires du manager": st.column_config.TextColumn(width="large"),
                            "_key": None,
                        },
                        use_container_width=True, hide_index=True, key="manager_comments_editor"
                    )

                    if st.button("💾 Enregistrer les commentaires", type="primary"):
                        comments_to_save = {row["_key"]: row["Commentaires du manager"] for _, row in edited_df.iterrows() if row["Commentaires du manager"]}
                        st.session_state.saved_briefs[st.session_state.current_brief_name]["manager_comments"] = comments_to_save
                        save_briefs()
                        st.success("✅ Commentaires sauvegardés !")
                        st.rerun()

        elif step == 2:
            st.subheader("Étape 2 : Matrice KSA")
            # Ici, on peut appeler la fonction render_ksa_matrix si vous l'avez définie, 
            # ou intégrer le code KSA directement.
            # Pour l'instant, on laisse la version simple de votre dernier fichier.
            with st.expander("📊 Matrice KSA - Validation manager", expanded=True):
                with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
                    st.markdown("""
                        ### Méthode KSA (Knowledge, Skills, Abilities)
                        ... (Votre texte complet d'explication ici) ...
                        """)
                st.write("Fonctionnalité KSA à développer ici.")


        elif step == 3:
            st.subheader("Étape 3 : Stratégie et Processus")
            with st.expander("💡 Stratégie et Processus", expanded=True):
                st.multiselect("🎯 Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], key="canaux_prioritaires")
                st.text_area("🚫 Critères d'exclusion", key="criteres_exclusion", height=150)
                st.text_area("✅ Processus d'évaluation (détails)", key="processus_evaluation", height=150)
        
        elif step == 4:
            st.subheader("Étape 4 : Finalisation")
            with st.expander("📝 Notes générales du manager", expanded=True):
                st.text_area("Notes et commentaires généraux du manager", key="manager_notes", height=250)

            st.markdown("---")
            
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 Enregistrer la réunion", type="primary", use_container_width=True, key="save_reunion_final"):
                    current_brief_name = st.session_state.current_brief_name
                    
                    brief_data_to_save = st.session_state.saved_briefs.get(current_brief_name, {}).copy()
                    
                    brief_data_to_save.update({
                        "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                        "criteres_exclusion": st.session_state.get("criteres_exclusion", ""),
                        "processus_evaluation": st.session_state.get("processus_evaluation", ""),
                        "manager_notes": st.session_state.get("manager_notes", "")
                    })
                    
                    ksa_matrix_df = st.session_state.get("ksa_matrix", pd.DataFrame())
                    brief_data_to_save["ksa_matrix"] = ksa_matrix_df
                    
                    save_briefs()
                    save_brief_to_gsheet(current_brief_name, brief_data_to_save)
                    
                    st.session_state.reunion_completed = True
                    st.success("✅ Données de réunion sauvegardées et synchronisées avec succès !")
                    st.rerun()
            
            with col_cancel:
                if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_reunion_final"):
                    delete_current_brief()

        # ---- Navigation wizard ----
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 8, 1])
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
with tabs[3]:
    if not st.session_state.current_brief_name:
        st.info("Veuillez sélectionner un brief pour voir la synthèse.")
    else:
        st.subheader(f"📝 Synthèse - {st.session_state.current_brief_name}")
        
        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
        if not brief_data:
            st.warning("Aucune donnée trouvée pour ce brief.")
        else:
            st.write("### Informations générales")
            st.write(f"- **Poste :** {brief_data.get('poste_intitule', 'N/A')}")
            st.write(f"- **Manager :** {brief_data.get('manager_nom', 'N/A')}")
            st.write(f"- **Affectation :** {brief_data.get('affectation_nom', 'N/A')} ({brief_data.get('affectation_type', 'N/A')})")
            
            st.write("### Détails du brief")
            for section in sections:
                with st.expander(f"📋 {section['title']}"):
                    has_content = False
                    for title, key, _ in section["fields"]:
                        value = brief_data.get(key)
                        if value:
                            st.write(f"- **{title} :** {value}")
                            has_content = True
                    if not has_content:
                        st.write("_Aucune information pour cette section._")
            
            ksa_df = brief_data.get("ksa_matrix")
            if ksa_df is not None and not ksa_df.empty:
                st.subheader("📊 Matrice KSA")
                st.dataframe(ksa_df, use_container_width=True, hide_index=True)

            st.subheader("📄 Export du Brief complet")
            col1, col2 = st.columns(2)
            with col1:
                if PDF_AVAILABLE:
                    pdf_buf = export_brief_pdf()
                    if pdf_buf:
                        st.download_button("⬇️ Télécharger PDF", data=pdf_buf, file_name=f"{st.session_state.current_brief_name}.pdf", mime="application/pdf", use_container_width=True)
                else:
                    st.info("⚠️ PDF non disponible (reportlab manquant)")
            with col2:
                if WORD_AVAILABLE:
                    word_buf = export_brief_word()
                    if word_buf:
                        st.download_button("⬇️ Télécharger Word", data=word_buf, file_name=f"{st.session_state.current_brief_name}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                else:
                    st.info("⚠️ Word non disponible (python-docx manquant)")