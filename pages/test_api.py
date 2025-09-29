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
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 10px 16px !important;
    }
    .stButton > button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
    }
    .stDataFrame {
        width: 100%;
    }
    .stTextArea textarea {
        min-height: 100px;
        resize: vertical;
        white-space: pre-wrap !important;
    }
    </style>
""", unsafe_allow_html=True)

def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau et permet l'ajout de critères."""
    with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
        st.markdown("""
### Méthode KSA (Knowledge, Skills, Abilities)
- **Knowledge (Connaissances)** : Savoirs théoriques nécessaires. Ex: Connaissances en normes de sécurité BTP (ISO 45001).
- **Skills (Compétences)** : Aptitudes pratiques acquises. Ex: Maîtrise d'AutoCAD pour dessiner des plans de chantier.
- **Abilities (Aptitudes)** : Capacités innées ou développées. Ex: Capacité à gérer des crises sur chantier.

### Types de questions :
- **Comportementale** : Basée sur des expériences passées (méthode STAR). Ex: "Décrivez une situation où vous avez résolu un conflit d'équipe."
- **Situationnelle** : Hypothétique, pour évaluer la réaction future. Ex: "Que feriez-vous si un délai de chantier était menacé ?"
- **Technique** : Évalue les connaissances spécifiques. Ex: "Expliquez comment vous utilisez AutoCAD pour la modélisation BTP."
- **Générale** : Questions ouvertes sur l'expérience globale. Ex: "Parlez-moi de votre parcours en BTP."
        """)
    
    if "ksa_matrix" not in st.session_state:
        st.session_state.ksa_matrix = pd.DataFrame(columns=[
            "Rubrique", "Critère", "Type de question", "Cible / Standard attendu", 
            "Échelle d'évaluation (1-5)", "Évaluateur"
        ])
    
    placeholder_dict = {
        "Comportementale": "Ex: Décrivez une situation où vous avez géré une équipe sous pression (méthode STAR).",
        "Situationnelle": "Ex: Que feriez-vous si un délai de chantier était menacé par un retard de livraison ?",
        "Technique": "Ex: Expliquez comment vous utilisez AutoCAD pour la modélisation de structures BTP.",
        "Générale": "Ex: Parlez-moi de votre expérience globale dans le secteur BTP."
    }
    
    with st.expander("➕ Ajouter un critère", expanded=True):
        st.markdown("""
        <style>
            .stTextInput, .stSelectbox, .stSlider, .stTextArea {
                margin-bottom: 5px;
                padding: 5px;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            .stTextInput > div > input, .stTextArea > div > textarea {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            .stSelectbox > div > select {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            .stButton > button {
                background-color: #FF0000;
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
                margin-top: 5px;
            }
            .stButton > button:hover {
                background-color: #FF3333;
            }
            .st-expander {
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #1e1e1e;
                padding: 5px;
            }
        </style>
        """, unsafe_allow_html=True)
        
        with st.form(key="add_ksa_criterion_form"):
            st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
            cible = st.text_area("Cible / Standard attendu", 
                               placeholder="Définissez la cible ou le standard attendu pour ce critère.", 
                               key="new_cible", height=100, value=st.session_state.get("new_cible", ""))
            st.markdown("</div>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1.5])
            with col1:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique",
                                      index=["Knowledge", "Skills", "Abilities"].index(st.session_state.get("new_rubrique", "Knowledge"))
                                      if st.session_state.get("new_rubrique") in ["Knowledge", "Skills", "Abilities"] else 0)
                st.markdown("</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                critere = st.text_input("Critère", placeholder="", key="new_critere", value=st.session_state.get("new_critere", ""))
                type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                           key="new_type_question",
                                           index=["Comportementale", "Situationnelle", "Technique", "Générale"].index(st.session_state.get("new_type_question", "Comportementale"))
                                           if st.session_state.get("new_type_question") in ["Comportementale", "Situationnelle", "Technique", "Générale"] else 0)
                st.markdown("</div>", unsafe_allow_html=True)
            with col3:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                evaluation = st.slider("Échelle d'évaluation (1-5)", min_value=1, max_value=5, value=st.session_state.get("new_evaluation", 3), step=1, key="new_evaluation")
                evaluateur = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"], key="new_evaluateur",
                                        index=["Manager", "Recruteur", "Les deux"].index(st.session_state.get("new_evaluateur", "Manager"))
                                        if st.session_state.get("new_evaluateur") in ["Manager", "Recruteur", "Les deux"] else 0)
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**Demander une question à l'IA**")
            ai_prompt = st.text_input("Décrivez ce que l'IA doit générer :", 
                                    placeholder="Ex: une question générale pour évaluer la maîtrise des techniques de sourcing par un chargé de recrutement", 
                                    key="ai_prompt", value=st.session_state.get("ai_prompt", ""))
            st.checkbox("⚡ Mode rapide (réponse concise)", key="concise_checkbox")
            
            col_buttons = st.columns([1, 1])
            with col_buttons[0]:
                if st.form_submit_button("💡 Générer question IA", use_container_width=True):
                    if ai_prompt:
                        try:
                            ai_response = generate_ai_question(ai_prompt, concise=st.session_state.concise_checkbox)
                            st.session_state.ai_response = ai_response
                        except Exception as e:
                            st.error(f"Erreur lors de la génération de la question : {e}")
                    else:
                        st.error("Veuillez entrer un prompt pour l'IA")
            
            with col_buttons[1]:
                if st.form_submit_button("➕ Ajouter le critère", use_container_width=True):
                    if not critere or not cible:
                        st.error("Veuillez remplir au moins le critère et la cible.")
                    else:
                        new_row = pd.DataFrame([{
                            "Rubrique": rubrique,
                            "Critère": critere,
                            "Type de question": type_question,
                            "Cible / Standard attendu": cible,
                            "Échelle d'évaluation (1-5)": evaluation,
                            "Évaluateur": evaluateur
                        }])
                        st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, new_row], ignore_index=True)
                        st.success("✅ Critère ajouté avec succès !")
                        st.rerun()

        if "ai_response" in st.session_state and st.session_state.ai_response:
            st.success(f"**Question :** {st.session_state.ai_response}")
            st.session_state.ai_response = ""

    if not st.session_state.ksa_matrix.empty:
        st.session_state.ksa_matrix = st.data_editor(
            st.session_state.ksa_matrix,
            hide_index=True,
            column_config={
                "Rubrique": st.column_config.SelectboxColumn(
                    "Rubrique", options=["Knowledge", "Skills", "Abilities"], required=True),
                "Critère": st.column_config.TextColumn("Critère", help="Critère spécifique à évaluer.", required=True),
                "Type de question": st.column_config.SelectboxColumn(
                    "Type de question", options=["Comportementale", "Situationnelle", "Technique", "Générale"], 
                    help="Type de question pour l'entretien.", required=True),
                "Cible / Standard attendu": st.column_config.TextColumn(
                    "Cible / Standard attendu", help="Objectif ou standard à évaluer pour ce critère.", required=True),
                "Échelle d'évaluation (1-5)": st.column_config.NumberColumn(
                    "Échelle d'évaluation (1-5)", help="Notez la réponse du candidat de 1 à 5.", min_value=1, max_value=5, step=1, format="%d"),
                "Évaluateur": st.column_config.SelectboxColumn(
                    "Évaluateur", options=["Manager", "Recruteur", "Les deux"], help="Qui évalue ce critère.", required=True),
            },
            num_rows="dynamic",
            use_container_width=True,
        )

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
    
    # Cette ligne appelle la fonction pour charger toutes les données de la feuille, 
    # puis len() compte le nombre total de briefs.
    total_briefs = len(load_briefs())
    
    # Cette ligne affiche le total que vous avez calculé.
    st.metric("📋 Briefs créés", total_briefs)

    st.divider()
    if st.button("Tester Connexion IA", key="test_deepseek"):
        test_deepseek_connection()

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

# Define tabs before using them
tabs = st.tabs([
    "📁 Gestion",
    "🔄 Avant-brief",
    "✅ Réunion de brief",
    "📝 Synthèse"
])

st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px;
}
.stTextArea textarea {
    white-space: pre-wrap !important;
}
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
    background-color: var(--background-color) !important;
    border-color: var(--border-color) !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select,
.stDateInput > div > div > input {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
}
:root {
    --background-color: #f0f2f6;
    --text-color: #31333F;
    --border-color: #d0d0d0;
}
@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #0e1117;
        --text-color: #fafafa;
        --border-color: #555555;
    }
}
</style>
""", unsafe_allow_html=True)

if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

all_field_keys = [
    "raison_ouverture", "impact_strategique", "taches_principales",
    "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
    "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences",
    "rattachement", "budget",
    "entreprises_profil", "synonymes_poste", "canaux_profil",
    "profil_link_1", "profil_link_2", "profil_link_3",
    "commentaires", "notes_libres",
    "canaux_prioritaires", "criteres_exclusion", "processus_evaluation", "manager_notes"
]

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
        
        # Load brief data if editing
        brief_data = {}
        if st.session_state.current_brief_name:
            brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Poste à recruter", key="poste_intitule", value=brief_data.get("poste_intitule", st.session_state.get("poste_intitule", "")))
        with col2:
            st.text_input("Manager", key="manager_nom", value=brief_data.get("manager_nom", st.session_state.get("manager_nom", "")))
        with col3:
            st.selectbox("Recruteur", ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"], key="recruteur",
                        index=["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"].index(
                            brief_data.get("recruteur", st.session_state.get("recruteur", "Zakaria"))
                        ) if brief_data.get("recruteur", st.session_state.get("recruteur", "Zakaria")) in ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"] else 0)
        
        col4, col5, col6 = st.columns(3)
        with col4:
            st.selectbox("Type d'affectation", ["Chantier", "Siège", "Dépôt"], key="affectation_type",
                        index=["Chantier", "Siège", "Dépôt"].index(
                            brief_data.get("affectation_type", st.session_state.get("affectation_type", "Chantier"))
                        ) if brief_data.get("affectation_type", st.session_state.get("affectation_type", "Chantier")) in ["Chantier", "Siège", "Dépôt"] else 0)
        with col5:
            st.text_input("Nom affectation", key="affectation_nom", value=brief_data.get("affectation_nom", st.session_state.get("affectation_nom", "")))
        with col6:
            st.date_input("Date du brief", key="date_brief", value=brief_data.get("date_brief", st.session_state.get("date_brief", datetime.today())))
        
        col_create, col_cancel = st.columns(2)
        with col_create:
            if st.button("💾 Créer brief", type="primary", use_container_width=True, key="create_brief"):
                brief_name = generate_automatic_brief_name()
                st.session_state.current_brief_name = brief_name
                
                brief_data = {
                    "BRIEF_NAME": brief_name,
                    "poste_intitule": st.session_state.poste_intitule,
                    "manager_nom": st.session_state.manager_nom,
                    "POSTE_INTITULE": st.session_state.poste_intitule,
                    "MANAGER_NOM": st.session_state.manager_nom,
                    "RECRUTEUR": st.session_state.recruteur,
                    "AFFECTATION_TYPE": st.session_state.affectation_type,
                    "AFFECTATION_NOM": st.session_state.affectation_nom,
                    "DATE_BRIEF": str(st.session_state.date_brief),
                    "RAISON_OUVERTURE": st.session_state.get("raison_ouverture", ""),
                    "IMPACT_STRATEGIQUE": st.session_state.get("impact_strategique", ""),
                    "RATTACHEMENT": st.session_state.get("rattachement", ""),
                    "TACHES_PRINCIPALES": st.session_state.get("taches_principales", ""),
                    "MUST_HAVE_EXP": st.session_state.get("must_have_experience", ""),
                    "MUST_HAVE_DIP": st.session_state.get("must_have_diplomes", ""),
                    "MUST_HAVE_COMPETENCES": st.session_state.get("must_have_competences", ""),
                    "MUST_HAVE_SOFTSKILLS": st.session_state.get("must_have_softskills", ""),
                    "NICE_TO_HAVE_EXP": st.session_state.get("nice_to_have_experience", ""),
                    "NICE_TO_HAVE_DIP": st.session_state.get("nice_to_have_diplomes", ""),
                    "NICE_TO_HAVE_COMPETENCES": st.session_state.get("nice_to_have_competences", ""),
                    "ENTREPRISES_PROFIL": st.session_state.get("entreprises_profil", ""),
                    "SYNONYMES_POSTE": st.session_state.get("synonymes_poste", ""),
                    "CANAUX_PROFIL": st.session_state.get("canaux_profil", ""),
                    "BUDGET": st.session_state.get("budget", ""),
                    "COMMENTAIRES": st.session_state.get("commentaires", ""),
                    "NOTES_LIBRES": st.session_state.get("notes_libres", ""),
                    "CRITERES_EXCLUSION": st.session_state.get("criteres_exclusion", ""),
                    "PROCESSUS_EVALUATION": st.session_state.get("processus_evaluation", ""),
                    "MANAGER_NOTES": st.session_state.get("manager_notes", ""),
                    "KSA_MATRIX_JSON": st.session_state.get("KSA_MATRIX_JSON", ""),
                    "brief_type": "Standard",
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()),
                    "manager_comments": st.session_state.get("manager_comments", {}),
                }
                
                st.session_state.saved_briefs[brief_name] = brief_data
                save_briefs()
                save_brief_to_gsheet(brief_name, brief_data)
                
                st.session_state.saved_briefs = load_briefs()
                st.session_state.save_message = f"✅ Brief '{brief_name}' créé avec succès"
                st.session_state.save_message_tab = "Gestion"
                st.rerun()
        with col_cancel:
            if st.button("🗑️ Annuler", type="secondary", use_container_width=True, key="cancel_brief"):
                st.session_state.poste_intitule = ""
                st.session_state.manager_nom = ""
                st.session_state.recruteur = ""
                st.session_state.affectation_type = ""
                st.session_state.affectation_nom = ""
                st.session_state.date_brief = datetime.today()
                st.rerun()
    
    with col_filter:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">🔍 Filtrer les briefs</h3>', unsafe_allow_html=True)
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.date_input("Date", key="filter_date", value=None)
        with col_filter2:
            st.text_input("Recruteur", key="filter_recruteur", value=st.session_state.get("filter_recruteur", ""))
        with col_filter3:
            st.text_input("Manager", key="filter_manager", value=st.session_state.get("filter_manager", ""))
        
        col_filter4, col_filter5, col_filter6 = st.columns(3)
        with col_filter4:
            st.selectbox("Affectation", ["", "Chantier", "Siège", "Dépôt"], key="filter_affectation",
                        index=["", "Chantier", "Siège", "Dépôt"].index(st.session_state.get("filter_affectation", ""))
                        if st.session_state.get("filter_affectation") in ["", "Chantier", "Siège", "Dépôt"] else 0)
        with col_filter5:
            st.text_input("Nom affectation", key="filter_nom_affectation", value=st.session_state.get("filter_nom_affectation", ""))
        with col_filter6:
            st.selectbox("Type de brief", ["", "Standard", "Urgent", "Stratégique"], key="filter_brief_type",
                        index=["", "Standard", "Urgent", "Stratégique"].index(st.session_state.get("filter_brief_type", ""))
                        if st.session_state.get("filter_brief_type") in ["", "Standard", "Urgent", "Stratégique"] else 0)
        
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
        
        if st.session_state.show_filtered_results:
            st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
            briefs_to_show = st.session_state.saved_briefs  # Pour tester sans filtre

st.write("DEBUG - Briefs à afficher :", briefs_to_show)

if briefs_to_show and len(briefs_to_show) > 0:
    for name, brief in briefs_to_show.items():
        col_brief1, col_brief2 = st.columns([6, 1])
        with col_brief1:
            st.markdown(f"**{name}**")
        with col_brief2:
            if st.button("📝 Éditer", key=f"edit_{name}"):
                brief_data_gsheet = st.session_state.saved_briefs.get(name, {})
                for key, value in brief_data_gsheet.items():
                    st.session_state[key] = value
                st.session_state.current_brief_name = name
                st.session_state.avant_brief_completed = True
                st.session_state.reunion_completed = True
                st.session_state.reunion_step = 1
                st.rerun()
else:
    st.info("Aucun brief sauvegardé ou correspondant aux filtres.")

# ---------------- AVANT-BRIEF ----------------
with tabs[1]:
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Avant-brief"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    brief_display_name = f"Avant-brief - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.subheader(f"🔄 {brief_display_name}")
    
    sections = [
        {"title": "Contexte du poste", "fields": [
            ("Raison de l'ouverture", "raison_ouverture", "Remplacement, création de poste, nouveau projet..."),
            ("Impact stratégique", "impact_strategique", "En quoi ce poste est-il clé pour les objectifs de l'entreprise ?"),
            ("Tâches principales", "taches_principales", "Lister les missions et responsabilités clés du poste.")]},
        {"title": "Must-have (Indispensables)", "fields": [
            ("Expérience", "must_have_experience", "Nombre d'années minimum, expériences similaires dans le secteur"),
            ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Diplômes exigés, certifications spécifiques"),
            ("Compétences / Outils", "must_have_competences", "Techniques, logiciels, méthodes à maîtriser"),
            ("Soft skills / aptitudes comportementales", "must_have_softskills", "Leadership, rigueur, communication, autonomie")]},
        {"title": "Nice-to-have (Atouts)", "fields": [
            ("Expérience additionnelle", "nice_to_have_experience", "Ex. projets internationaux, multi-sites"),
            ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Diplômes ou certifications supplémentaires appréciés"),
            ("Compétences complémentaires", "nice_to_have_competences", "Compétences supplémentaires non essentielles mais appréciées")]},
        {"title": "Conditions et contraintes", "fields": [
            ("Localisation", "rattachement", "Site principal, télétravail, déplacements"),
            ("Budget recrutement", "budget", "Salaire indicatif, avantages, primes éventuelles")]},
        {"title": "Sourcing et marché", "fields": [
            ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"),
            ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"),
            ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels")]},
        {"title": "Profils pertinents", "fields": [
            ("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"),
            ("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"),
            ("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre")]},
        {"title": "Notes libres", "fields": [
            ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"),
            ("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique")]},
    ]

    col1, col2 = st.columns([1, 1])
    with col1:
        field_options = [f"{section['title']} - {title}" for section in sections for title, key, _ in section["fields"]]
        selected_field = st.selectbox("Choisir un champ", field_options, index=0)
    with col2:
        if st.button("💡 Générer par l'IA", key="generate_advice_btn", type="primary"):
            section_title, field_title = selected_field.split(" - ", 1)
            for section in sections:
                for title, key, _ in section["fields"]:
                    st.session_state[f"advice_{key}"] = ""
            for section in sections:
                if section["title"] == section_title:
                    for title, key, _ in section["fields"]:
                        if title == field_title:
                            advice = generate_checklist_advice(section["title"], title)
                            if advice:
                                example = get_example_for_field(section["title"], title)
                                st.session_state[f"advice_{key}"] = f"{advice}\n**Exemple :**\n{example}"
                            else:
                                st.session_state[f"advice_{key}"] = "Aucun conseil disponible pour ce champ."

    brief_data = load_briefs().get(st.session_state.current_brief_name, {})

    with st.form(key="avant_brief_form"):
        for section in sections:
            with st.expander(f"📋 {section['title']}", expanded=False):
                for title, key, placeholder in section["fields"]:
                    unique_key = f"{section['title'].replace(' ', '_')}_{key}"
                    current_value = st.session_state.get(key, brief_data.get(key, ""))
                    st.text_area(title, value=current_value, key=unique_key, placeholder=placeholder, height=150)
                    if st.session_state.get(f"advice_{key}", ""):
                        st.info(f"**Conseil IA :**\n{st.session_state[f'advice_{key}']}")

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 Enregistrer modifications", type="primary", use_container_width=True):
                if st.session_state.current_brief_name:
                    current_brief_name = st.session_state.current_brief_name
                    brief_to_update = st.session_state.saved_briefs[current_brief_name]
                    
                    all_field_keys = [field[1] for section in sections for field in section['fields']]
                    for key in all_field_keys:
                        unique_key = f"{next(s['title'].replace(' ', '_') for s in sections if key in [f[1] for f in s['fields']])}_{key}"
                        brief_to_update[key] = st.session_state.get(unique_key, "")
                    
                    save_briefs()
                    
                    payload_for_gsheet = brief_to_update.copy()
                    mapping = {
                        "poste_intitule": "POSTE_INTITULE", "manager_nom": "MANAGER_NOM", "recruteur": "RECRUTEUR",
                        "affectation_type": "AFFECTATION_TYPE", "affectation_nom": "AFFECTATION_NOM", "date_brief": "DATE_BRIEF",
                        "raison_ouverture": "RAISON_OUVERTURE", "impact_strategique": "IMPACT_STRATEGIQUE",
                        "rattachement": "RATTACHEMENT", "taches_principales": "TACHES_PRINCIPALES",
                        "must_have_experience": "MUST_HAVE_EXP", "must_have_diplomes": "MUST_HAVE_DIP",
                        "must_have_competences": "MUST_HAVE_COMPETENCES", "must_have_softskills": "MUST_HAVE_SOFTSKILLS",
                        "nice_to_have_experience": "NICE_TO_HAVE_EXP", "nice_to_have_diplomes": "NICE_TO_HAVE_DIP",
                        "nice_to_have_competences": "NICE_TO_HAVE_COMPETENCES",
                        "entreprises_profil": "ENTREPRISES_PROFIL", "synonymes_poste": "SYNONYMES_POSTE",
                        "canaux_profil": "CANAUX_PROFIL", "budget": "BUDGET", "commentaires": "COMMENTAIRES",
                        "notes_libres": "NOTES_LIBRES",
                        "profil_link_1": "LIEN_PROFIL_1", "profil_link_2": "LIEN_PROFIL_2", "profil_link_3": "LIEN_PROFIL_3"
                    }
                    for session_key, gsheet_key in mapping.items():
                        if session_key in payload_for_gsheet:
                            payload_for_gsheet[gsheet_key] = payload_for_gsheet[session_key]
                    
                    save_brief_to_gsheet(current_brief_name, payload_for_gsheet)
                    st.success("✅ Modifications sauvegardées avec succès sur Google Sheets.")
                    st.rerun()

        with col_cancel:
            if st.form_submit_button("Annuler", use_container_width=True):
                st.rerun()

# ---------------- REUNION BRIEF ----------------
with tabs[2]:
    st.markdown("""
        <style>
            .stTextArea > div > label > div {
                color: #A9A9A9;
            }
            .stTextArea > div > div > textarea {
                background-color: #2F333B;
                color: white;
                border-color: #555555;
            }
            .stTextInput > div > div > input {
                background-color: #2F333B;
                color: white;
                border-color: #555555;
            }
            div[data-testid="stForm"] {
                padding: 1rem;
                border: 1px solid #555555;
                border-radius: 0.5rem;
            }
        </style>
        """, unsafe_allow_html=True)
    
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Réunion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    brief_display_name = f"Réunion de brief - {st.session_state.get('current_brief_name', 'Nom du Brief')}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.markdown(f"<h3 style='color: #FFFFFF;'>📝 {brief_display_name}</h3>", unsafe_allow_html=True)

    total_steps = 4
    step = st.session_state.reunion_step
    
    st.progress(int((step / total_steps) * 100), text=f"**Étape {step} sur {total_steps}**")

    if step == 1:
        st.subheader("Étape 1 : Validation du brief et commentaires du manager")
        with st.expander("📝 Portrait robot du candidat - Validation", expanded=True):
            brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
            manager_comments = brief_data.get("manager_comments", {})

            table_data = []
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

                    payload_for_gsheet = st.session_state.saved_briefs[st.session_state.current_brief_name].copy()
                    payload_for_gsheet['MANAGER_COMMENTS_JSON'] = json.dumps(comments_to_save, indent=4, ensure_ascii=False)
                    
                    mapping = {
                        "poste_intitule": "POSTE_INTITULE", "manager_nom": "MANAGER_NOM", "recruteur": "RECRUTEUR",
                        "affectation_type": "AFFECTATION_TYPE", "affectation_nom": "AFFECTATION_NOM", "date_brief": "DATE_BRIEF",
                        "raison_ouverture": "RAISON_OUVERTURE", "impact_strategique": "IMPACT_STRATEGIQUE",
                        "rattachement": "RATTACHEMENT", "taches_principales": "TACHES_PRINCIPALES",
                        "must_have_experience": "MUST_HAVE_EXP", "must_have_diplomes": "MUST_HAVE_DIP",
                        "must_have_competences": "MUST_HAVE_COMPETENCES", "must_have_softskills": "MUST_HAVE_SOFTSKILLS",
                        "nice_to_have_experience": "NICE_TO_HAVE_EXP", "nice_to_have_diplomes": "NICE_TO_HAVE_DIP",
                        "nice_to_have_competences": "NICE_TO_HAVE_COMPETENCES",
                        "entreprises_profil": "ENTREPRISES_PROFIL", "synonymes_poste": "SYNONYMES_POSTE",
                        "canaux_profil": "CANAUX_PROFIL", "budget": "BUDGET", "commentaires": "COMMENTAIRES",
                        "notes_libres": "NOTES_LIBRES",
                        "profil_link_1": "LIEN_PROFIL_1", "profil_link_2": "LIEN_PROFIL_2", "profil_link_3": "LIEN_PROFIL_3"
                    }
                    for session_key, gsheet_key in mapping.items():
                        if session_key in payload_for_gsheet:
                            payload_for_gsheet[gsheet_key] = payload_for_gsheet[session_key]

                    if "ksa_matrix" in payload_for_gsheet and isinstance(payload_for_gsheet["ksa_matrix"], pd.DataFrame) and not payload_for_gsheet["ksa_matrix"].empty:
                        payload_for_gsheet['KSA_MATRIX_JSON'] = payload_for_gsheet["ksa_matrix"].to_csv(index=False, sep=";", encoding="utf-8")
                    
                    save_brief_to_gsheet(st.session_state.current_brief_name, payload_for_gsheet)
                    st.success("✅ Commentaires sauvegardés et synchronisés avec Google Sheets !")
                    st.rerun()

    elif step == 2:
        with st.expander("📊 Matrice KSA - Validation manager", expanded=True):
            with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
                st.markdown("""
                    ### Méthode KSA (Knowledge, Skills, Abilities)
                    La méthode KSA permet de décomposer un poste en trois catégories de compétences pour une évaluation plus précise.
                    #### 🧠 Knowledge (Connaissances)
                    - **Exemple 1 :** Connaissances des protocoles de sécurité IT (ISO 27001).
                    - **Exemple 2 :** Maîtrise des concepts de la comptabilité analytique.
                    - **Exemple 3 :** Connaissance approfondie des langages de programmation Python et R.
                    #### 💪 Skills (Compétences)
                    - **Exemple 1 :** Capacité à utiliser le logiciel Adobe Photoshop pour le design graphique.
                    - **Exemple 2 :** Expertise en négociation commerciale pour la conclusion de contrats.
                    - **Exemple 3 :** Maîtrise de la gestion de projet Agile ou Scrum.
                    #### ✨ Abilities (Aptitudes)
                    - **Exemple 1 :** Capacité à gérer le stress et la pression.
                    - **Exemple 2 :** Aptitude à communiquer clairement des idées complexes.
                    - **Exemple 3 :** Capacité à travailler en équipe et à collaborer efficacement.
                    """, unsafe_allow_html=True)

            with st.expander("➕ Ajouter un critère", expanded=True):
                with st.form(key="add_criteria_form"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique",
                                              index=["Knowledge", "Skills", "Abilities"].index(st.session_state.get("new_rubrique", "Knowledge"))
                                              if st.session_state.get("new_rubrique") in ["Knowledge", "Skills", "Abilities"] else 0)
                    with col2:
                        st.text_input("Critère", placeholder="Ex: Leadership", key="new_critere")
                    with col3:
                        type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                                   key="new_type_question",
                                                   index=["Comportementale", "Situationnelle", "Technique", "Générale"].index(st.session_state.get("new_type_question", "Comportementale"))
                                                   if st.session_state.get("new_type_question") in ["Comportementale", "Situationnelle", "Technique", "Générale"] else 0)
                    with col4:
                        evaluateur = st.selectbox("Qui évalue ce critère ?", ["Recruteur", "Manager", "Les deux"], key="new_evaluateur",
                                                index=["Recruteur", "Manager", "Les deux"].index(st.session_state.get("new_evaluateur", "Recruteur"))
                                                if st.session_state.get("new_evaluateur") in ["Recruteur", "Manager", "Les deux"] else 0)

                    col_q_text, col_slider = st.columns([2, 1])
                    
                    with col_q_text:
                        question = st.text_input("Question pour l'entretien", 
                                               placeholder="Ex: Parlez-moi d'une situation où vous avez dû faire preuve de leadership.", 
                                               key="new_question")
                    with col_slider:
                        evaluation = st.slider("Évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                    
                    ai_prompt = st.text_input("Décrivez ce que l'IA doit générer comme Question", 
                                            placeholder="Ex: Donne-moi une question pour évaluer la gestion de projets", 
                                            key="ai_prompt_input")
                    concise_mode = st.checkbox("⚡ Mode rapide (réponse concise)", key="concise_mode")
                    
                    st.markdown("---")
                    
                    col_ai, col_add = st.columns(2)
                    with col_ai:
                        if st.form_submit_button("💡 Générer question IA", type="primary", use_container_width=True):
                            if ai_prompt:
                                with st.spinner("Génération en cours..."):
                                    try:
                                        ai_response = generate_ai_question(ai_prompt, concise=concise_mode)
                                        if ai_response.strip().startswith("Question:"):
                                            ai_response = ai_response.strip().replace("Question:", "", 1).strip()
                                        st.session_state.ai_generated_question = ai_response
                                    except Exception as e:
                                        st.error(f"Erreur lors de la génération : {e}")
                            else:
                                st.error("Veuillez entrer un prompt pour l'IA.")
                    
                    with col_add:
                        if st.form_submit_button("➕ Ajouter le critère", type="secondary", use_container_width=True):
                            if not st.session_state.new_critere or not question:
                                st.error("Veuillez remplir au moins le critère et la question.")
                            else:
                                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, pd.DataFrame([{
                                    "Rubrique": rubrique,
                                    "Critère": st.session_state.new_critere,
                                    "Type de question": type_question,
                                    "Question pour l'entretien": question,
                                    "Évaluation (1-5)": evaluation,
                                    "Évaluateur": evaluateur
                                }])], ignore_index=True)
                                st.success("✅ Critère ajouté avec succès !")
                                st.rerun()

                if "ai_generated_question" in st.session_state and st.session_state.ai_generated_question:
                    st.success(f"**Question :** {st.session_state.ai_generated_question}")
                    st.session_state.ai_generated_question = ""
            
            st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
            
            if not st.session_state.ksa_matrix.empty:
                avg_rating = st.session_state.ksa_matrix["Évaluation (1-5)"].mean()
                st.markdown(f"**<div style='font-size: 24px;'>Note cible de l'ensemble des critères : 🎯 {avg_rating:.2f} / 5</div>**", unsafe_allow_html=True)

    elif step == 3:
        with st.expander("💡 Stratégie et Processus", expanded=True):
            st.info("Définissez les canaux de sourcing et les critères d'évaluation.")
            st.multiselect("🎯 Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], 
                          key="canaux_prioritaires", default=st.session_state.get("canaux_prioritaires", []))
            
            st.markdown("---")
            st.subheader("Critères d'exclusion et Processus d'évaluation")
            col1, col2 = st.columns(2)
            with col1:
                st.text_area("🚫 Critères d'exclusion", key="criteres_exclusion", height=150, 
                            placeholder="Ex: ne pas avoir d'expérience dans le secteur public...",
                            value=st.session_state.get("criteres_exclusion", ""))
            with col2:
                st.text_area("✅ Processus d'évaluation (détails)", key="processus_evaluation", height=150, 
                            placeholder="Ex: Entretien RH (30min), Test technique, Entretien manager (60min)...",
                            value=st.session_state.get("processus_evaluation", ""))
        
        _, col_cancel = st.columns([3, 1])
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_reunion"):
                delete_current_brief()

    elif step == 4:
        st.subheader("Étape 4 : Finalisation")
        
        with st.form(key="reunion_final_form"):
            with st.expander("📝 Notes générales du manager", expanded=True):
                st.text_area("Notes et commentaires généraux du manager", key="manager_notes", height=250,
                            value=st.session_state.get("manager_notes", ""))
                st.text_area("🚫 Critères d'exclusion", key="criteres_exclusion", height=150, 
                            placeholder="Ex: ne pas avoir d'expérience dans le secteur public...",
                            value=st.session_state.get("criteres_exclusion", ""))
                st.text_area("✅ Processus d'évaluation (détails)", key="processus_evaluation", height=150, 
                            placeholder="Ex: Entretien RH (30min), Test technique, Entretien manager (60min)...",
                            value=st.session_state.get("processus_evaluation", ""))

            st.markdown("---")
            
            if st.form_submit_button("💾 Enregistrer la réunion", type="primary", use_container_width=True):
                if st.session_state.current_brief_name:
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
                    manager_comments_dict = brief_data_to_save.get("manager_comments", {})
                    
                    st.session_state.saved_briefs[current_brief_name] = brief_data_to_save
                    save_briefs()
                    
                    payload_for_gsheet = brief_data_to_save.copy()
                    if not ksa_matrix_df.empty:
                        payload_for_gsheet['KSA_MATRIX_JSON'] = ksa_matrix_df.to_csv(index=False, sep=";", encoding="utf-8")
                    if manager_comments_dict:
                        payload_for_gsheet['MANAGER_COMMENTS_JSON'] = json.dumps(manager_comments_dict, indent=4, ensure_ascii=False)
                    
                    mapping = {
                        "poste_intitule": "POSTE_INTITULE", "manager_nom": "MANAGER_NOM", "recruteur": "RECRUTEUR",
                        "affectation_type": "AFFECTATION_TYPE", "affectation_nom": "AFFECTATION_NOM", "date_brief": "DATE_BRIEF",
                        "raison_ouverture": "RAISON_OUVERTURE", "impact_strategique": "IMPACT_STRATEGIQUE",
                        "rattachement": "RATTACHEMENT", "taches_principales": "TACHES_PRINCIPALES",
                        "must_have_experience": "MUST_HAVE_EXP", "must_have_diplomes": "MUST_HAVE_DIP",
                        "must_have_competences": "MUST_HAVE_COMPETENCES", "must_have_softskills": "MUST_HAVE_SOFTSKILLS",
                        "nice_to_have_experience": "NICE_TO_HAVE_EXP", "nice_to_have_diplomes": "NICE_TO_HAVE_DIP",
                        "nice_to_have_competences": "NICE_TO_HAVE_COMPETENCES",
                        "entreprises_profil": "ENTREPRISES_PROFIL", "synonymes_poste": "SYNONYMES_POSTE",
                        "canaux_profil": "CANAUX_PROFIL", "budget": "BUDGET", "commentaires": "COMMENTAIRES",
                        "notes_libres": "NOTES_LIBRES",
                        "profil_link_1": "LIEN_PROFIL_1", "profil_link_2": "LIEN_PROFIL_2", "profil_link_3": "LIEN_PROFIL_3",
                        "canaux_prioritaires": "CANAUX_PRIORITAIRES",
                        "criteres_exclusion": "CRITERES_EXCLUSION",
                        "processus_evaluation": "PROCESSUS_EVALUATION",
                        "manager_notes": "MANAGER_NOTES"
                    }
                    for session_key, gsheet_key in mapping.items():
                        if session_key in payload_for_gsheet:
                            value = payload_for_gsheet[session_key]
                            if isinstance(value, list) or isinstance(value, dict):
                                payload_for_gsheet[gsheet_key] = json.dumps(value, indent=4, ensure_ascii=False)
                            else:
                                payload_for_gsheet[gsheet_key] = value
                    
                    save_brief_to_gsheet(current_brief_name, payload_for_gsheet)
                    
                    st.session_state.reunion_completed = True
                    st.success("✅ Données de réunion sauvegardées et synchronisées avec succès !")
                    st.rerun()
                else:
                    st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if step > 1:
            if st.button("⬅️ Précédent", key="prev_step"):
                st.session_state.reunion_step -= 1
                st.rerun()
    with col3:
        if step < total_steps:
            if st.button("Suivant ➡️", key="next_step"):
                st.session_state.reunion_step += 1
                st.rerun()

# ---------------- SYNTHÈSE ----------------
with tabs[3]:
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Synthèse"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    if not st.session_state.current_brief_name:
        st.warning("⚠️ Veuillez créer ou sélectionner un brief dans l'onglet Gestion avant d'accéder à cette section.")
    elif not st.session_state.reunion_completed:
        st.warning("⚠️ Veuillez compléter la réunion de brief avant d'accéder à cette section.")
    else:
        st.subheader(f"📝 Synthèse - {st.session_state.current_brief_name}")
        
        brief_data = load_briefs().get(st.session_state.current_brief_name, {})
        st.write("### Informations générales")
        st.write(f"- **Poste :** {brief_data.get('poste_intitule', 'N/A')}")
        st.write(f"- **Manager :** {brief_data.get('manager_nom', 'N/A')}")
        st.write(f"- **Affectation :** {brief_data.get('affectation_nom', 'N/A')} ({brief_data.get('affectation_type', 'N/A')})")
        st.write(f"- **Date :** {brief_data.get('date_brief', 'N/A')}")
        
        st.write("### Détails du brief")
        for section in sections:
            with st.expander(f"📋 {section['title']}"):
                for title, key, _ in section["fields"]:
                    value = brief_data.get(key, st.session_state.get(key, ""))
                    if value:
                        st.write(f"- **{title} :** {value}")
        
        if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
            st.subheader("📊 Matrice KSA")
            st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
        
        st.write("### Actions")
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True, key="save_synthese"):
                if st.session_state.current_brief_name:
                    save_briefs()
                    brief_data_to_save = load_briefs().get(st.session_state.current_brief_name, {})
                    save_brief_to_gsheet(st.session_state.current_brief_name, brief_data_to_save)
                    st.session_state.save_message = f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !"
                    st.session_state.save_message_tab = "Synthèse"
                    st.rerun()
                else:
                    st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")
        
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_synthese"):
                delete_current_brief()

        st.subheader("📄 Export du Brief complet")
        col1, col2 = st.columns(2)
        with col1:
            if PDF_AVAILABLE:
                if st.session_state.current_brief_name:
                    pdf_buf = export_brief_pdf()
                    if pdf_buf:
                        st.download_button(
                            "⬇️ Télécharger PDF",
                            data=pdf_buf,
                            file_name=f"{st.session_state.current_brief_name}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ PDF non dispo (pip install reportlab)")
        with col2:
            if WORD_AVAILABLE:
                if st.session_state.current_brief_name:
                    word_buf = export_brief_word()
                    if word_buf:
                        st.download_button(
                            "⬇️ Télécharger Word",
                            data=word_buf,
                            file_name=f"{st.session_state.current_brief_name}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ Word non dispo (pip install python-docx)")