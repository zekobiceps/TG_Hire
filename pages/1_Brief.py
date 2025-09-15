import sys, os 
import streamlit as st
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
)

# ---------------- NOUVELLES FONCTIONS ----------------
def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau et permet l'ajout de critères."""
    
    # Ajout des explications dans un expander
    with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
        st.markdown("""
### Méthode KSA (Knowledge, Skills, Abilities)
- **Knowledge (Connaissances)** : Savoirs théoriques nécessaires. Ex: Connaissances en normes de sécurité BTP (ISO 45001).
- **Skills (Compétences)** : Aptitudes pratiques acquises. Ex: Maîtrise d'AutoCAD pour dessiner des plans de chantier.
- **Abilities (Aptitudes)** : Capacités innées ou développées. Ex: Capacité à gérer des crises sur chantier.

### Types de questions :
- **Comportementale** : Basée sur des expériences passées (méthode STAR: Situation, Tâche, Action, Résultat). Ex: "Décrivez une situation où vous avez résolu un conflit d'équipe."
- **Situationnelle** : Hypothétique, pour évaluer la réaction future. Ex: "Que feriez-vous si un délai de chantier était menacé ?"
- **Technique** : Évalue les connaissances spécifiques. Ex: "Expliquez comment vous utilisez AutoCAD pour la modélisation BTP."
- **Générale** : Questions ouvertes sur l'expérience globale. Ex: "Parlez-moi de votre parcours en BTP."
        """)
    
    # Initialiser les données KSA si elles n'existent pas
    if "ksa_matrix" not in st.session_state:
        st.session_state.ksa_matrix = pd.DataFrame(columns=[
            "Rubrique", 
            "Critère", 
            "Type de question", 
            "Cible / Standard attendu", 
            "Échelle d'évaluation (1-5)", 
            "Évaluateur"
        ])
    
    # Dictionnaire des placeholders pour "Cible / Standard attendu"
    placeholder_dict = {
        "Comportementale": "Ex: Décrivez une situation où vous avez géré une équipe sous pression (méthode STAR: Situation, Tâche, Action, Résultat).",
        "Situationnelle": "Ex: Que feriez-vous si un délai de chantier était menacé par un retard de livraison ?",
        "Technique": "Ex: Expliquez comment vous utilisez AutoCAD pour la modélisation de structures BTP.",
        "Générale": "Ex: Parlez-moi de votre expérience globale dans le secteur BTP."
    }
    
    # Expander pour ajouter un nouveau critère
    with st.expander("➕ Ajouter un critère", expanded=True):
        # CSS pour un design moderne et épuré
        st.markdown("""
        <style>
            /* Fond global de l'application */
            .stApp {
                background: linear-gradient(to bottom, #1a1b26, #24283b);
                color: #c0caf5;
            }
            
            /* Style des inputs */
            .stTextInput input, .stTextArea textarea {
                background-color: #32333d !important;
                color: #c0caf5 !important;
                border: 1px solid #41466b !important;
                border-radius: 6px !important;
                padding: 8px !important;
            }
            .stTextInput input:focus, .stTextArea textarea:focus {
                border-color: #7aa2f7 !important;
                box-shadow: 0 0 0 2px rgba(122, 162, 247, 0.3) !important;
            }
            
            /* Style des selectboxes */
            div[data-baseweb="select"] > div {
                background-color: #32333d !important;
                color: #c0caf5 !important;
                border: 1px solid #41466b !important;
                border-radius: 6px !important;
            }
            
            /* Style des sliders */
            .stSlider [data-baseweb="slider"] {
                background-color: transparent !important;
            }
            .stSlider [data-baseweb="slider"] > div > div {
                background-color: #7aa2f7 !important;
            }
            
            /* Boutons principaux */
            .stButton > button {
                background-color: #ff4b4b !important;
                color: #ffffff !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-weight: 500 !important;
                border: none !important;
            }
            .stButton > button:hover {
                background-color: #ff6b6b !important;
            }
            
            /* Bouton Générer question IA */
            .stButton > button[key="generate_ai_question"] {
                background-color: #7aa2f7 !important;
            }
            .stButton > button[key="generate_ai_question"]:hover {
                background-color: #89b4fa !important;
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background-color: #32333d !important;
                color: #c0caf5 !important;
                border-radius: 6px !important;
                padding: 8px !important;
            }
            
            /* Style du tableau KSA */
            .stDataFrame {
                width: 100%;
                border-collapse: collapse;
                background-color: #1a1b26;
                border: 1px solid #41466b;
                font-size: 0.9em;
            }
            .stDataFrame th, .stDataFrame td {
                padding: 12px 16px;
                text-align: left;
                border: 1px solid #41466b;
                color: #c0caf5;
            }
            .stDataFrame th {
                background-color: #7aa2f7 !important;
                color: #ffffff !important;
                font-weight: 600;
                font-size: 1em;
            }
            .stDataFrame td:nth-child(1), .stDataFrame th:nth-child(1) { width: 15%; }
            .stDataFrame td:nth-child(2), .stDataFrame th:nth-child(2) { width: 20%; }
            .stDataFrame td:nth-child(3), .stDataFrame th:nth-child(3) { width: 15%; }
            .stDataFrame td:nth-child(4), .stDataFrame th:nth-child(4) { width: 35%; }
            .stDataFrame td:nth-child(5), .stDataFrame th:nth-child(5) { width: 15%; }
        </style>
        """, unsafe_allow_html=True)
        
        # Formulaire pour ajouter un critère
        with st.form(key="add_ksa_criterion_form"):
            col1, col2, col3 = st.columns([1, 1, 1])  # Trois colonnes équilibrées
            with col1:
                st.markdown("<div style='padding: 10px;'>", unsafe_allow_html=True)
                rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
                critere = st.text_input("Critère", placeholder="Ex: Leadership", key="new_critere")
                st.markdown("</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div style='padding: 10px;'>", unsafe_allow_html=True)
                type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                             key="new_type_question")
                # Utiliser une variable temporaire pour stocker la question générée par l'IA
                cible = st.text_area("Cible / Standard attendu", 
                                     value=st.session_state.get("temp_cible", ""), 
                                     placeholder=placeholder_dict.get(type_question, "Définissez la cible ou le standard attendu pour ce critère."), 
                                     key="new_cible", 
                                     height=100)
                st.markdown("</div>", unsafe_allow_html=True)
            with col3:
                st.markdown("<div style='padding: 10px;'>", unsafe_allow_html=True)
                evaluation = st.slider("Échelle d'évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                evaluateur = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"], key="new_evaluateur")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Section pour demander une question à l'IA
            st.markdown("**Demander une question à l'IA**")
            ai_prompt = st.text_input("Prompt pour l'IA", placeholder="Ex: Donne-moi une question pour évaluer la gestion de projets", 
                                      key="ai_prompt")
            if st.form_submit_button("Générer question IA", key="generate_ai_question"):
                if ai_prompt:
                    with st.spinner("Génération de la question par l'IA en cours..."):
                        try:
                            ai_response = generate_ai_question(ai_prompt)
                            st.session_state.temp_cible = ai_response  # Stocker dans une variable temporaire
                            st.success(f"Question générée : {ai_response}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la génération de la question : {e}")
                else:
                    st.error("Veuillez entrer un prompt pour l'IA.")
            
            # Bouton pour ajouter le critère
            if st.form_submit_button("Ajouter"):
                new_row = pd.DataFrame([{
                    "Rubrique": rubrique,
                    "Critère": critere,
                    "Type de question": type_question,
                    "Cible / Standard attendu": cible,  # Utiliser la valeur du widget directement
                    "Échelle d'évaluation (1-5)": evaluation,
                    "Évaluateur": evaluateur
                }])
                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, new_row], ignore_index=True)
                st.success("✅ Critère ajouté à la matrice KSA")
                # Réinitialiser les champs
                st.session_state.new_rubrique = "Knowledge"
                st.session_state.new_critere = ""
                st.session_state.new_type_question = "Comportementale"
                st.session_state.temp_cible = ""  # Réinitialiser la variable temporaire
                st.session_state.new_evaluation = 3
                st.session_state.new_evaluateur = "Manager"
                st.session_state.ai_prompt = ""
                st.rerun()
    
    # Afficher la matrice KSA sous forme de data_editor
    if not st.session_state.ksa_matrix.empty:
        st.session_state.ksa_matrix = st.data_editor(
            st.session_state.ksa_matrix,
            hide_index=True,
            column_config={
                "Rubrique": st.column_config.SelectboxColumn(
                    "Rubrique",
                    options=["Knowledge", "Skills", "Abilities"],
                    required=True,
                ),
                "Critère": st.column_config.TextColumn(
                    "Critère",
                    help="Critère spécifique à évaluer.",
                    required=True,
                ),
                "Type de question": st.column_config.SelectboxColumn(
                    "Type de question",
                    options=["Comportementale", "Situationnelle", "Technique", "Générale"],
                    help="Type de question pour l'entretien.",
                    required=True,
                ),
                "Cible / Standard attendu": st.column_config.TextColumn(
                    "Cible / Standard attendu",
                    help="Objectif ou standard à évaluer pour ce critère.",
                    required=True,
                ),
                "Échelle d'évaluation (1-5)": st.column_config.NumberColumn(
                    "Échelle d'évaluation (1-5)",
                    help="Notez la réponse du candidat de 1 à 5.",
                    min_value=1,
                    max_value=5,
                    step=1,
                    format="%d"
                ),
                "Évaluateur": st.column_config.SelectboxColumn(
                    "Évaluateur",
                    options=["Manager", "Recruteur", "Les deux"],
                    help="Qui évalue ce critère.",
                    required=True,
                ),
            },
            num_rows="dynamic",
            use_container_width=True,
        )

def delete_current_brief():
    """Supprime le brief actuel et retourne à l'onglet Gestion"""
    if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
        brief_name = st.session_state.current_brief_name
        if brief_name in st.session_state.saved_briefs:
            del st.session_state.saved_briefs[brief_name]
            save_briefs()
            
            # Réinitialiser l'état de la session
            st.session_state.current_brief_name = ""
            st.session_state.avant_brief_completed = True
            st.session_state.reunion_completed = True
            st.session_state.reunion_step = 1
            
            # Réinitialiser les champs du formulaire
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
            # Rediriger vers l'onglet Gestion
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

# Variables pour gérer l'accès aux onglets (tous débloqués)
if "avant_brief_completed" not in st.session_state:
    st.session_state.avant_brief_completed = True

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = True

# Message persistant jusqu'à changement d'onglet
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Gestion"
if "save_message" not in st.session_state:
    st.session_state.save_message = None
if "save_message_tab" not in st.session_state:
    st.session_state.save_message_tab = None

# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques Brief")
    
    # Calculer quelques statistiques
    total_briefs = len(st.session_state.get("saved_briefs", {}))
    completed_briefs = sum(1 for b in st.session_state.get("saved_briefs", {}).values() 
                          if b.get("ksa_data") and any(b["ksa_data"].values()))
    
    st.metric("📋 Briefs créés", total_briefs)
    st.metric("✅ Briefs complétés", completed_briefs)
    
    st.divider()
    st.info("💡 Assistant IA pour la création et gestion de briefs de recrutement")
    if st.button("Tester DeepSeek", key="test_deepseek"):
        test_deepseek_connection()

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

# Style CSS pour les onglets personnalisés et les tableaux améliorés
st.markdown("""
    <style>
    /* Style général pour l'application */
    .stApp {
        background: linear-gradient(to bottom, #1a1b26, #24283b);
        color: #c0caf5;
    }
    
    /* Style pour les onglets de navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #1a1b26;
        padding: 0px;
        border-radius: 6px;
    }
    
    /* Style de base pour tous les onglets */
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1b26 !important;
        color: #c0caf5 !important;
        border: none !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        border-radius: 0 !important;
        margin-right: 0 !important;
        height: auto !important;
    }
    
    /* Style pour l'onglet actif */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #ff4b4b !important;
        background-color: #1a1b26 !important;
        border-bottom: 3px solid #ff4b4b !important;
    }
    
    /* Boutons principaux */
    .stButton > button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #ff6b6b;
        color: white;
    }
    
    /* Boutons secondaires */
    .stButton > button[kind="secondary"] {
        background-color: #32333d;
        color: #c0caf5;
        border: 1px solid #ff4b4b;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #41466b;
        color: #c0caf5;
    }
    
    /* Bouton Filtrer en rouge vif */
    .stButton > button[key="apply_filter"] {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none;
    }
    
    .stButton > button[key="apply_filter"]:hover {
        background-color: #ff6b6b !important;
        color: white !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #32333d;
        color: #c0caf5;
        border-radius: 6px;
        padding: 0.5rem;
    }
    
    /* Correction pour les selectbox */
    div[data-baseweb="select"] > div {
        border: none !important;
        background-color: #32333d !important;
        color: #c0caf5 !important;
        border-radius: 6px !important;
    }
    
    /* Style pour les inputs */
    .stTextInput input {
        background-color: #32333d !important;
        color: #c0caf5 !important;
        border-radius: 6px !important;
        border: 1px solid #41466b !important;
    }
    
    /* Correction pour les textareas */
    .stTextArea textarea {
        background-color: #32333d !important;
        color: #c0caf5 !important;
        border-radius: 6px !important;
        border: 1px solid #41466b !important;
    }
    
    /* Correction pour les date inputs */
    .stDateInput input {
        background-color: #32333d !important;
        color: #c0caf5 !important;
        border-radius: 6px !important;
        border: 1px solid #41466b !important;
    }
    
    /* Réduire la hauteur de la section avant-brief */
    .stTextArea textarea {
        height: 100px !important;
    }
    
    /* Ajustement pour le message de confirmation */
    .message-container {
        margin-top: 10px;
        padding: 10px;
        border-radius: 6px;
    }
    
    /* Style pour les messages d'alerte */
    .stAlert {
        padding: 10px;
        margin-top: 10px;
        background-color: #32333d;
        color: #c0caf5;
        border-radius: 6px;
    }
    
    /* Style pour le tableau de méthode complète */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
        background-color: #1a1b26;
    }
    
    .comparison-table th, .comparison-table td {
        border: 1px solid #41466b;
        padding: 8px;
        text-align: left;
        color: #c0caf5;
    }
    
    .comparison-table th {
        background-color: #7aa2f7;
        font-weight: bold;
        color: #ffffff;
    }

    /* Style pour la matrice KSA */
    .dataframe {
        width: 100%;
        background-color: #1a1b26;
    }
    
    /* Style pour le tableau amélioré - TABLEAU SOMBRE */
    .dark-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #1a1b26;
        font-size: 0.9em;
        border: 1px solid #41466b;
    }
    
    .dark-table th, .dark-table td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #41466b;
        color: #c0caf5;
    }
    
    .dark-table th {
        background-color: #7aa2f7 !important;
        color: #ffffff !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 1em;
        border: 1px solid #41466b;
    }
    
    /* Auto-size pour les colonnes */
    .dark-table th:nth-child(1), .dark-table td:nth-child(1) { width: auto !important; min-width: 100px; }
    .dark-table th:nth-child(2), .dark-table td:nth-child(2) { width: auto !important; min-width: 150px; }
    .dark-table th:nth-child(3), .dark-table td:nth-child(3) { width: 65% !important; }
    
    /* Style pour les tableaux avec 4 colonnes (réunion de brief) */
    .dark-table.four-columns th:nth-child(1), .dark-table.four-columns td:nth-child(1) { width: auto !important; min-width: 100px; }
    .dark-table.four-columns th:nth-child(2), .dark-table.four-columns td:nth-child(2) { width: auto !important; min-width: 150px; }
    .dark-table.four-columns th:nth-child(3), .dark-table.four-columns td:nth-child(3) { width: auto !important; min-width: 150px; }
    .dark-table.four-columns th:nth-child(4), .dark-table.four-columns td:nth-child(4) { width: 45% !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------- ONGLET GESTION ----------------
def gestion_tab():
    st.header("📁 Gestion des Briefs")
    
    # Créer un nouveau brief
    with st.expander("Créer un nouveau brief", expanded=True):
        if st.button("Créer brief"):
            brief_name = generate_automatic_brief_name()
            st.session_state.current_brief_name = brief_name
            st.session_state.saved_briefs[brief_name] = {
                "poste_intitule": st.session_state.get("poste_intitule", ""),
                "manager_nom": st.session_state.get("manager_nom", ""),
                "date_brief": st.session_state.get("date_brief", datetime.today().strftime("%Y-%m-%d")),
                "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame())
            }
            save_briefs()
            st.success(f"Brief '{brief_name}' créé avec succès !")
            st.session_state.brief_phase = "📝 Avant Brief"
            st.rerun()
    
    # Filtrer les briefs existants
    with st.expander("Filtrer les briefs", expanded=False):
        with st.form(key="filter_form"):
            month = st.selectbox("Mois", [""] + [f"{i:02d}" for i in range(1, 13)], index=0)
            recruteur = st.text_input("Recruteur")
            brief_type = st.selectbox("Type de brief", ["", "CDI", "CDD", "Stage", "Alternance"])
            manager = st.text_input("Manager")
            affectation = st.selectbox("Type d'affectation", ["", "Projet", "Service", "Chantier"])
            nom_affectation = st.text_input("Nom affectation")
            if st.form_submit_button("Filtrer", key="apply_filter"):
                st.session_state.filtered_briefs = filter_briefs(
                    st.session_state.saved_briefs, month, recruteur, brief_type, manager, affectation, nom_affectation
                )
                st.session_state.show_filtered_results = True
    
    # Afficher les briefs filtrés
    if st.session_state.show_filtered_results and st.session_state.filtered_briefs:
        st.subheader("Résultats filtrés")
        for name, data in st.session_state.filtered_briefs.items():
            with st.expander(f"Brief: {name}"):
                st.write(f"Poste: {data.get('poste_intitule', '')}")
                st.write(f"Manager: {data.get('manager_nom', '')}")
                st.write(f"Date: {data.get('date_brief', '')}")
                if st.button("Charger", key=f"load_{name}"):
                    st.session_state.current_brief_name = name
                    for key, value in data.items():
                        st.session_state[key] = value
                    st.session_state.brief_phase = "📝 Avant Brief"
                    st.rerun()
                if st.button("Supprimer", key=f"delete_{name}"):
                    del st.session_state.saved_briefs[name]
                    save_briefs()
                    st.session_state.filtered_briefs = filter_briefs(
                        st.session_state.saved_briefs, month, recruteur, brief_type, manager, affectation, nom_affectation
                    )
                    st.success(f"Brief '{name}' supprimé")
                    st.rerun()

# ---------------- ONGLET AVANT BRIEF ----------------
def avant_brief_tab():
    st.header("📝 Avant Brief")
    
    with st.form(key="avant_brief_form"):
        st.subheader("Identité du poste")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Intitulé du poste", key="poste_intitule")
            st.text_input("Service", key="service")
            st.selectbox("Niveau hiérarchique", ["", "Cadre", "Non-cadre", "Manager"], key="niveau_hierarchique")
        with col2:
            st.selectbox("Type de contrat", ["", "CDI", "CDD", "Stage", "Alternance"], key="type_contrat")
            st.text_input("Localisation", key="localisation")
            st.text_input("Budget salaire", key="budget_salaire")
        
        st.subheader("Contexte & Enjeux")
        st.text_area("Raison de l'ouverture", key="raison_ouverture", placeholder=get_example_for_field("Contexte du poste", "Raison de l'ouverture"))
        st.text_area("Mission globale", key="impact_strategique", placeholder=get_example_for_field("Contexte du poste", "Mission globale"))
        st.text_area("Tâches principales", key="taches_principales", placeholder=get_example_for_field("Contexte du poste", "Tâches principales"))
        
        st.subheader("Exigences")
        st.text_area("Expérience indispensable", key="must_have_experience", placeholder=get_example_for_field("Must-have (Indispensables)", "Expérience"))
        st.text_area("Connaissances/Diplômes", key="must_have_diplomes", placeholder=get_example_for_field("Must-have (Indispensables)", "Connaissances / Diplômes / Certifications"))
        st.text_area("Compétences/Outils", key="must_have_competences", placeholder=get_example_for_field("Must-have (Indispensables)", "Compétences / Outils"))
        st.text_area("Soft skills", key="must_have_softskills", placeholder=get_example_for_field("Must-have (Indispensables)", "Soft skills / aptitudes comportementales"))
        
        st.subheader("Atouts")
        st.text_area("Expérience additionnelle", key="nice_to_have_experience", placeholder=get_example_for_field("Nice-to-have (Atouts)", "Expérience additionnelle"))
        st.text_area("Diplômes/Certifications valorisantes", key="nice_to_have_diplomes", placeholder=get_example_for_field("Nice-to-have (Atouts)", "Diplômes / Certifications valorisantes"))
        st.text_area("Compétences complémentaires", key="nice_to_have_competences", placeholder=get_example_for_field("Nice-to-have (Atouts)", "Compétences complémentaires"))
        
        st.subheader("Sourcing et marché")
        st.text_area("Entreprises où trouver ce profil", key="entreprises_profil", placeholder=get_example_for_field("Sourcing et marché", "Entreprises où trouver ce profil"))
        st.text_area("Synonymes/Intitulés proches", key="synonymes_poste", placeholder=get_example_for_field("Sourcing et marché", "Synonymes / intitulés proches"))
        st.text_area("Canaux à utiliser", key="canaux_profil", placeholder=get_example_for_field("Sourcing et marché", "Canaux à utiliser"))
        
        if st.form_submit_button("Enregistrer et passer à Réunion"):
            brief_name = st.session_state.current_brief_name
            st.session_state.saved_briefs[brief_name] = {
                "poste_intitule": st.session_state.get("poste_intitule", ""),
                "service": st.session_state.get("service", ""),
                "niveau_hierarchique": st.session_state.get("niveau_hierarchique", ""),
                "type_contrat": st.session_state.get("type_contrat", ""),
                "localisation": st.session_state.get("localisation", ""),
                "budget_salaire": st.session_state.get("budget_salaire", ""),
                "date_prise_poste": st.session_state.get("date_prise_poste", ""),
                "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                "impact_strategique": st.session_state.get("impact_strategique", ""),
                "taches_principales": st.session_state.get("taches_principales", ""),
                "must_have_experience": st.session_state.get("must_have_experience", ""),
                "must_have_diplomes": st.session_state.get("must_have_diplomes", ""),
                "must_have_competences": st.session_state.get("must_have_competences", ""),
                "must_have_softskills": st.session_state.get("must_have_softskills", ""),
                "nice_to_have_experience": st.session_state.get("nice_to_have_experience", ""),
                "nice_to_have_diplomes": st.session_state.get("nice_to_have_diplomes", ""),
                "nice_to_have_competences": st.session_state.get("nice_to_have_competences", ""),
                "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                "synonymes_poste": st.session_state.get("synonymes_poste", ""),
                "canaux_profil": st.session_state.get("canaux_profil", ""),
                "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame())
            }
            save_briefs()
            st.session_state.avant_brief_completed = True
            st.session_state.brief_phase = "🤝 Réunion de brief"
            st.session_state.save_message = f"✅ Brief '{brief_name}' enregistré avec succès"
            st.session_state.save_message_tab = "Réunion de brief"
            st.rerun()

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
def reunion_brief_tab():
    st.header("🤝 Réunion de Brief")
    
    if "manager_comments" not in st.session_state:
        st.session_state.manager_comments = {}
    
    with st.form(key="reunion_form"):
        st.subheader("Informations générales")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Manager", key="manager_nom")
            st.selectbox("Type d'affectation", ["", "Projet", "Service", "Chantier"], key="affectation_type")
            st.text_input("Recruteur", key="recruteur")
        with col2:
            st.text_input("Nom affectation", key="affectation_nom")
            st.date_input("Date du brief", key="date_brief")
        
        st.subheader("Stratégie de recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion", placeholder="Ex: Moins de 3 ans d'expérience")
        st.text_area("Processus d'évaluation", key="processus_evaluation", placeholder="Ex: Entretien manager, test technique")
        
        st.subheader("Notes du manager")
        st.text_area("Notes générales", key="manager_notes")
        
        for i in range(1, 21):
            st.text_area(f"Commentaire {i}", key=f"manager_comment_{i}", placeholder=f"Commentaire spécifique {i}")
        
        st.subheader("Matrice KSA")
        render_ksa_matrix()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Enregistrer et passer à Méthode complète"):
                brief_name = st.session_state.current_brief_name
                st.session_state.saved_briefs[brief_name].update({
                    "manager_nom": st.session_state.get("manager_nom", ""),
                    "affectation_type": st.session_state.get("affectation_type", ""),
                    "recruteur": st.session_state.get("recruteur", ""),
                    "affectation_nom": st.session_state.get("affectation_nom", ""),
                    "date_brief": st.session_state.get("date_brief", datetime.today().strftime("%Y-%m-%d")),
                    "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                    "criteres_exclusion": st.session_state.get("criteres_exclusion", ""),
                    "processus_evaluation": st.session_state.get("processus_evaluation", ""),
                    "manager_notes": st.session_state.get("manager_notes", ""),
                    "manager_comments": st.session_state.get("manager_comments", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame())
                })
                save_briefs()
                st.session_state.reunion_completed = True
                st.session_state.brief_phase = "📊 Méthode complète"
                st.session_state.save_message = f"✅ Brief '{brief_name}' enregistré avec succès"
                st.session_state.save_message_tab = "Méthode complète"
                st.rerun()
        with col2:
            if st.form_submit_button("Supprimer le brief", type="secondary"):
                delete_current_brief()

# ---------------- ONGLET MÉTHODE COMPLÈTE ----------------
def methode_complete_tab():
    st.header("📊 Méthode Complète")
    
    # Afficher le message de confirmation si pertinent
    if st.session_state.save_message and st.session_state.save_message_tab == "Méthode complète":
        st.markdown(f'<div class="message-container">{st.session_state.save_message}</div>', unsafe_allow_html=True)
    
    # Téléchargement PDF
    if PDF_AVAILABLE:
        if st.button("📥 Télécharger PDF"):
            pdf_buffer = export_brief_pdf()
            if pdf_buffer:
                st.download_button(
                    label="Télécharger le brief en PDF",
                    data=pdf_buffer,
                    file_name=f"Brief_{st.session_state.current_brief_name}.pdf",
                    mime="application/pdf"
                )
    
    # Téléchargement Word
    if WORD_AVAILABLE:
        if st.button("📥 Télécharger Word"):
            word_buffer = export_brief_word()
            if word_buffer:
                st.download_button(
                    label="Télécharger le brief en Word",
                    data=word_buffer,
                    file_name=f"Brief_{st.session_state.current_brief_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    
    # Afficher les données du brief
    brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
    
    st.subheader("1. Identité du poste")
    data = [
        ["Intitulé", brief_data.get("poste_intitule", "")],
        ["Service", brief_data.get("service", "")],
        ["Niveau Hiérarchique", brief_data.get("niveau_hierarchique", "")],
        ["Type de Contrat", brief_data.get("type_contrat", "")],
        ["Localisation", brief_data.get("localisation", "")],
        ["Budget Salaire", brief_data.get("budget_salaire", "")],
        ["Date Prise de Poste", brief_data.get("date_prise_poste", "")]
    ]
    st.markdown('<table class="dark-table"><tr><th>Champ</th><th>Valeur</th></tr>' + 
                ''.join([f'<tr><td>{row[0]}</td><td>{row[1]}</td></tr>' for row in data]) + 
                '</table>', unsafe_allow_html=True)
    
    st.subheader("2. Contexte & Enjeux")
    for field in ["raison_ouverture", "impact_strategique", "taches_principales"]:
        if field in brief_data and brief_data[field]:
            st.markdown(f"**{field.replace('_', ' ').title()}**: {brief_data[field]}")
    
    st.subheader("3. Exigences")
    for field in [
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences"
    ]:
        if field in brief_data and brief_data[field]:
            st.markdown(f"**{field.replace('_', ' ').title()}**: {brief_data[field]}")
    
    st.subheader("4. Matrice KSA")
    if not brief_data.get("ksa_matrix", pd.DataFrame()).empty:
        st.dataframe(brief_data["ksa_matrix"], use_container_width=True)
    else:
        st.write("Aucune donnée KSA disponible.")
    
    st.subheader("5. Stratégie de recrutement")
    for field in ["canaux_prioritaires", "criteres_exclusion", "processus_evaluation"]:
        if field in brief_data and brief_data[field]:
            value = ", ".join(brief_data[field]) if field == "canaux_prioritaires" else brief_data[field]
            st.markdown(f"**{field.replace('_', ' ').title()}**: {value}")
    
    st.subheader("6. Notes du manager")
    if brief_data.get("manager_notes"):
        st.markdown(f"**Notes Générales**: {brief_data['manager_notes']}")
    for i in range(1, 21):
        comment_key = f"manager_comment_{i}"
        if comment_key in brief_data.get("manager_comments", {}) and brief_data["manager_comments"][comment_key]:
            st.markdown(f"**Commentaire {i}**: {brief_data['manager_comments'][comment_key]}")
    
    if st.button("Supprimer le brief", type="secondary"):
        delete_current_brief()

# ---------------- NAVIGATION ----------------
tabs = st.tabs(["📁 Gestion", "📝 Avant Brief", "🤝 Réunion de brief", "📊 Méthode complète"])

with tabs[0]:
    gestion_tab()
    st.session_state.current_tab = "Gestion"

with tabs[1]:
    avant_brief_tab()
    st.session_state.current_tab = "Avant Brief"

with tabs[2]:
    reunion_brief_tab()
    st.session_state.current_tab = "Réunion de brief"

with tabs[3]:
    methode_complete_tab()
    st.session_state.current_tab = "Méthode complète"