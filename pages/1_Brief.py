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
        # CSS pour améliorer l'apparence
        st.markdown("""
        <style>
            .stTextInput, .stSelectbox, .stSlider, .stTextArea {
                margin-bottom: 15px;
                padding: 10px;
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
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                margin-top: 10px;
            }
            .stButton > button:hover {
                background-color: #45a049;
            }
            .st-expander {
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #1e1e1e;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Sélecteur de type de question pour prévisualiser le placeholder
        st.markdown("**Prévisualiser le type de question**")
        preview_type = st.selectbox("Type de question (aperçu)", 
                                    ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                    key="preview_type_question")
        st.text_area("Aperçu Cible / Standard attendu", 
                     placeholder_dict.get(preview_type, "Définissez la cible ou le standard attendu pour ce critère."), 
                     disabled=True, height=100)
        
        # Formulaire pour ajouter un critère
        with st.form(key="add_ksa_criterion_form"):
            col1, col2 = st.columns([1, 1.5])  # Ratio pour un meilleur alignement
            with col1:
                st.markdown("<div style='padding: 10px;'>", unsafe_allow_html=True)
                rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
                critere = st.text_input("Critère", placeholder="Ex: Leadership", key="new_critere")
                type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                             key="new_type_question")
                st.markdown("</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div style='padding: 10px;'>", unsafe_allow_html=True)
                placeholder = placeholder_dict.get(type_question, "Définissez la cible ou le standard attendu pour ce critère.")
                cible = st.text_area("Cible / Standard attendu", 
                                     value=st.session_state.get("ai_generated_cible", ""), 
                                     placeholder=placeholder, key="new_cible", height=100)
                evaluation = st.slider("Échelle d'évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                evaluateur = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"], key="new_evaluateur")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Section pour demander une question à l'IA
            st.markdown("**Demander une question à l'IA**")
            ai_prompt = st.text_input("Prompt pour l'IA", placeholder="Ex: Donne-moi une question pour évaluer la gestion de projets", 
                                      key="ai_prompt")
            if st.form_submit_button("Générer question IA"):
                if ai_prompt:
                    with st.spinner("Génération de la question par l'IA en cours..."):
                        try:
                            ai_response = generate_ai_question(ai_prompt)
                            st.session_state.ai_generated_cible = ai_response  # Stocker dans une variable temporaire
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
                    "Cible / Standard attendu": cible,
                    "Échelle d'évaluation (1-5)": evaluation,
                    "Évaluateur": evaluateur
                }])
                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, new_row], ignore_index=True)
                st.success("✅ Critère ajouté à la matrice KSA")
                # Réinitialiser les champs
                st.session_state.new_rubrique = "Knowledge"
                st.session_state.new_critere = ""
                st.session_state.new_type_question = "Comportementale"
                st.session_state.ai_generated_cible = ""  # Réinitialiser la variable temporaire
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

if "filtered_briefs" in st.session_state:
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
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Style pour les onglets de navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #0E1117;
        padding: 0px;
        border-radius: 4px;
    }
    
    /* Style de base pour tous les onglets */
    .stTabs [data-baseweb="tab"] {
        background-color: #0E1117 !important;
        color: white !important;
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
        background-color: #0E1117 !important;
        border-bottom: 3px solid #ff4b4b !important;
    }
    
    /* Boutons principaux */
    .stButton > button {
        background-color: #FF4B4B;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #FF6B6B;
        color: white;
    }
    
    /* Boutons secondaires */
    .stButton > button[kind="secondary"] {
        background-color: #262730;
        color: #FAFAFA;
        border: 1px solid #FF4B4B;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #3D3D4D;
        color: #FAFAFA;
    }
    
    /* Bouton Filtrer en rouge vif */
    .stButton > button[key="apply_filter"] {
        background-color: #FF0000 !important;
        color: white !important;
        border: none;
    }
    
    .stButton > button[key="apply_filter"]:hover {
        background-color: #FF3333 !important;
        color: white !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #262730;
        color: #FAFAFA;
        border-radius: 5px;
        padding: 0.5rem;
    }
    
    /* Correction pour les selectbox */
    div[data-baseweb="select"] > div {
        border: none !important;
        background-color: #262730 !important;
        color: white !important;
        border-radius: 4px !important;
    }
    
    /* Style pour la matrice KSA */
    .stDataFrame {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #0d1117;
        font-size: 0.9em;
        border: 1px solid #ffffff;
    }
    
    .stDataFrame th, .stDataFrame td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #ffffff;
        color: #e6edf3;
    }
    
    .stDataFrame th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ffffff;
    }
    
    /* Auto-size pour les colonnes de la matrice */
    .stDataFrame td:nth-child(1), .stDataFrame th:nth-child(1) { width: 10%; }
    .stDataFrame td:nth-child(2), .stDataFrame th:nth-child(2) { width: 25%; }
    .stDataFrame td:nth-child(3), .stDataFrame th:nth-child(3) { width: 15%; }
    .stDataFrame td:nth-child(4), .stDataFrame th:nth-child(4) { width: 40%; }
    .stDataFrame td:nth-child(5), .stDataFrame th:nth-child(5) { width: 10%; }
    
    /* Correction pour les inputs */
    .stTextInput input {
        background-color: #262730 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    /* Correction pour les textareas */
    .stTextArea textarea {
        background-color: #262730 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    /* Correction pour les date inputs */
    .stDateInput input {
        background-color: #262730 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    /* Réduire la hauteur de la section avant-brief */
    .stTextArea textarea {
        height: 100px !important;
    }
    
    /* Ajustement pour le message de confirmation */
    .message-container {
        margin-top: 10px;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* Style pour les messages d'alerte */
    .stAlert {
        padding: 10px;
        margin-top: 10px;
    }
    
    /* Style pour le tableau de méthode complète */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
    }
    
    .comparison-table th, .comparison-table td {
        border: 1px solid #424242;
        padding: 8px;
        text-align: left;
    }
    
    .comparison-table th {
        background-color: #262730;
        font-weight: bold;
    }
    
    /* Style pour la matrice KSA */
    .dataframe {
        width: 100%;
    }
    
    /* Style pour le tableau amélioré - TABLEAU SOMBRE */
    .dark-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #0d1117;
        font-size: 0.9em;
        border: 1px solid #ffffff;
    }
    
    .dark-table th, .dark-table td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #ffffff;
        color: #e6edf3;
    }
    
    .dark-table th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ffffff;
    }
    
    /* Auto-size pour les deux premières colonnes */
    .dark-table th:nth-child(1), .dark-table td:nth-child(1) { width: auto !important; min-width: 100px; }
    .dark-table th:nth-child(2), .dark-table td:nth-child(2) { width: auto !important; min-width: 150px; }
    .dark-table th:nth-child(3), .dark-table td:nth-child(3) { width: 65% !important; }
    
    /* Style pour les tableaux avec 4 colonnes (réunion de brief) */
    .dark-table.four-columns th:nth-child(1), .dark-table.four-columns td:nth-child(1) { width: auto !important; min-width: 100px; }
    .dark-table.four-columns th:nth-child(2), .dark-table.four-columns td:nth-child(2) { width: auto !important; min-width: 150px; }
    .dark-table.four-columns th:nth-child(3), .dark-table.four-columns td:nth-child(3) { width: 50% !important; }
    .dark-table.four-columns th:nth-child(4), .dark-table.four-columns td:nth-child(4) { width: 25% !important; }
    
    .section-title {
        font-weight: 600;
        color: #58a6ff;
        font-size: 0.95em;
        margin-bottom: 0 !important;
    }
    
    /* Style pour les textareas dans les tableaux */
    .table-textarea {
        width: 100%;
        min-height: 60px;
        background-color: #2D2D2D;
        color: white;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 6px;
        font-size: 0.9em;
        resize: vertical;
    }
    
    /* Style pour les cellules de texte */
    .table-text {
        padding: 6px;
        font-size: 0.9em;
        color: #e6edf3;
    }
    
    /* Supprimer complètement les lignes vides */
    .empty-row {
        display: none;
    }
    
    /* Style pour le data_editor afin de le faire ressembler au dark-table */
    .stDataFrame {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #0d1117;
        font-size: 0.9em;
        border: 1px solid #ffffff;
    }
    
    .stDataFrame th, .stDataFrame td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #ffffff;
        color: #e6edf3;
    }
    
    .stDataFrame th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ffffff;
    }
    
    .stDataFrame td:first-child {
        font-weight: 600;
        color: #58a6ff;
    }
    
    /* Auto-size pour les deux premières colonnes */
    .stDataFrame td:nth-child(1) { width: auto !important; min-width: 100px; }
    .stDataFrame td:nth-child(2) { width: auto !important; min-width: 150px; }
    .stDataFrame td:nth-child(3) { width: 50% !important; }
    .stDataFrame td:nth-child(4) { width: 25% !important; }
    
    /* Style pour les cellules éditable (Informations) */
    .stDataFrame td:nth-child(3) textarea {
        background-color: #2D2D2D !important;
        color: white !important;
        border: 1px solid #555 !important;
        border-radius: 4px !important;
        padding: 6px !important;
        min-height: 60px !important;
        resize: vertical !important;
    }
    
    /* Permettre le retour à la ligne avec Alt+Enter */
    .stTextArea textarea {
        white-space: pre-wrap !important;
    }
    
    /* Élargir manuellement les lignes */
    .stDataFrame tr {
        height: auto !important;
    }
    
    .stDataFrame td {
        height: auto !important;
        min-height: 60px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Sections pour le formulaire Avant Brief
sections = [
    {
        "title": "Identité du poste",
        "fields": [
            ("Intitulé du poste", "poste_intitule", "Ex: Ingénieur travaux"),
            ("Service", "service", "Ex: Travaux publics"),
            ("Niveau hiérarchique", "niveau_hierarchique", "Ex: Cadre"),
            ("Type de contrat", "type_contrat", "Ex: CDI"),
            ("Localisation", "localisation", "Ex: Paris"),
            ("Budget salaire", "budget_salaire", "Ex: 40-50k€ annuel"),
            ("Date de prise de poste souhaitée", "date_prise_poste", "Ex: 01/01/2024")
        ]
    },
    {
        "title": "Contexte du poste",
        "fields": [
            ("Raison de l'ouverture", "raison_ouverture", "Ex: Remplacement, création de poste"),
            ("Mission globale et impact stratégique", "impact_strategique", "Ex: Supervision des chantiers pour garantir les délais"),
            ("Tâches principales", "taches_principales", "Ex: Gestion des équipes, suivi des budgets")
        ]
    },
    {
        "title": "Must-have (Indispensables)",
        "fields": [
            ("Expérience", "must_have_experience", "Ex: 5 ans en gestion de projets BTP"),
            ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Ex: Diplôme d’ingénieur BTP"),
            ("Compétences / Outils", "must_have_competences", "Ex: Maîtrise d’AutoCAD, Excel"),
            ("Soft skills / aptitudes comportementales", "must_have_softskills", "Ex: Leadership, gestion du stress")
        ]
    },
    {
        "title": "Nice-to-have (Atouts)",
        "fields": [
            ("Expérience additionnelle", "nice_to_have_experience", "Ex: Expérience à l’international"),
            ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Ex: Certification PMP"),
            ("Compétences complémentaires", "nice_to_have_competences", "Ex: Connaissance en BIM")
        ]
    },
    {
        "title": "Sourcing et marché",
        "fields": [
            ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"),
            ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"),
            ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels")
        ]
    },
    {
        "title": "Profils pertinents",
        "fields": [
            ("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"),
            ("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"),
            ("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre")
        ]
    },
    {
        "title": "Notes libres",
        "fields": [
            ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"),
            ("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique")
        ]
    },
]

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
    
    # Contrôles pour générer les conseils IA avec sélection de champ
    col1, col2 = st.columns([1, 1])  # Equal width columns
    with col1:
        field_options = [f"{section['title']} - {title}" for section in sections for title, key, _ in section["fields"]]
        selected_field = st.selectbox("Choisir un champ", field_options, index=0)
    with col2:
        if st.button("💡 Générer par l'IA", key="generate_advice_btn", type="primary", help="Génère un conseil IA pour le champ sélectionné"):
            section_title, field_title = selected_field.split(" - ", 1)
            # Clear all advice before generating new one
            for section in sections:
                for title, key, _ in section["fields"]:
                    st.session_state[f"advice_{key}"] = ""
            # Generate advice for the selected field
            for section in sections:
                if section["title"] == section_title:
                    for title, key, _ in section["fields"]:
                        if title == field_title:
                            advice = generate_checklist_advice(section["title"], title)
                            if advice != "Pas de conseil disponible.":
                                example = get_example_for_field(section["title"], title)
                                st.session_state[f"advice_{key}"] = f"{advice}\n**Exemple :**\n{example}"

    brief_data = {}
    if st.session_state.current_brief_name in st.session_state.saved_briefs:
        brief_data = st.session_state.saved_briefs[st.session_state.current_brief_name]

    # Initialiser les conseils dans session_state si non existants
    for section in sections:
        for title, key, _ in section["fields"]:
            if f"advice_{key}" not in st.session_state:
                st.session_state[f"advice_{key}"] = ""

    # Formulaire avec expanders et champs éditable
    with st.form(key="avant_brief_form"):
        for section in sections:
            with st.expander(f"📋 {section['title']}", expanded=True):
                for title, key, placeholder in section["fields"]:
                    # Larger height for all fields
                    height = 150  # Increased from 100 for all fields
                    current_value = brief_data.get(key, st.session_state.get(key, ""))
                    st.text_area(title, value=current_value, key=key, placeholder=placeholder, height=height)
                    # Afficher le conseil généré juste en dessous du champ avec meilleur formatage
                    if f"advice_{key}" in st.session_state and st.session_state[f"advice_{key}"]:
                        advice_and_example = st.session_state[f'advice_{key}'].split('\n**Exemple :**\n')
                        advice_text = advice_and_example[0].strip()
                        example_text = advice_and_example[1].strip() if len(advice_and_example) > 1 else ""
                        
                        st.markdown(f"""
<div class="ai-advice-box">
    <strong>Conseil :</strong> {advice_text}<br>
    <strong>Exemple :</strong> {example_text}
</div>
""", unsafe_allow_html=True)

        # Boutons Enregistrer et Annuler dans le formulaire
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.form_submit_button("💾 Enregistrer modifications", type="primary", use_container_width=True):
                if st.session_state.current_brief_name in st.session_state.saved_briefs:
                    brief_name = st.session_state.current_brief_name
                    update_data = {key: st.session_state[key] for _, key, _ in [item for sublist in [s["fields"] for s in sections] for item in sublist]}
                    st.session_state.saved_briefs[brief_name].update(update_data)
                    save_briefs()
                    st.session_state.avant_brief_completed = True
                    st.session_state.save_message = "✅ Modifications sauvegardées"
                    st.session_state.save_message_tab = "Avant-brief"
                    st.rerun()
                else:
                    st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        
        with col_cancel:
            if st.form_submit_button("🗑️ Annuler", type="secondary", use_container_width=True):
                st.session_state.current_brief_name = ""
                st.session_state.avant_brief_completed = False
                st.rerun()

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
def reunion_brief_tab():
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Réunion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Afficher les informations du brief en cours
    brief_display_name = f"Réunion de brief - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.subheader(f"✅ {brief_display_name}")

    total_steps = 4
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation")

        # Construire le DataFrame sans répétition de "Contexte du poste"
        data = []
        field_keys = []
        comment_keys = []
        k = 1
        
        if st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_data = st.session_state.saved_briefs[st.session_state.current_brief_name]
            
            for section in sections:
                for i, (field_name, field_key, placeholder) in enumerate(section["fields"]):
                    value = brief_data.get(field_key, "")
                    section_title = section["title"] if i == 0 else ""
                    data.append([section_title, field_name, value, ""])
                    field_keys.append(field_key)
                    comment_keys.append(f"manager_comment_{k}")
                    k += 1

        df = pd.DataFrame(data, columns=["Section", "Détails", "Informations", "Commentaires du manager"])

        # Afficher le data_editor avec auto-size pour les deux premières colonnes
        edited_df = st.data_editor(
            df,
            column_config={
                "Section": st.column_config.TextColumn("Section", disabled=True, width="small"),
                "Détails": st.column_config.TextColumn("Détails", disabled=True, width="medium"),
                "Informations": st.column_config.TextColumn("Informations", width="medium", disabled=True),
                "Commentaires du manager": st.column_config.TextColumn("Commentaires du manager", width="medium")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        # Sauvegarde des commentaires
        if st.button("💾 Sauvegarder commentaires", type="primary", key="save_comments_step1"):
            for i in range(len(edited_df)):
                if edited_df["Détails"].iloc[i] != "":
                    comment_key = comment_keys[i]
                    st.session_state[comment_key] = edited_df["Commentaires du manager"].iloc[i]
            st.session_state.save_message = "✅ Commentaires sauvegardés"
            st.session_state.save_message_tab = "Réunion"
            st.rerun()

    elif step == 2:
        st.subheader("📊 Matrice KSA - Validation manager")
        render_ksa_matrix()

    elif step == 3:
        st.subheader("4️⃣ Stratégie Recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion", height=100)
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation", height=100)
        
    elif step == 4:
        st.subheader("📝 Notes générales du manager")
        st.text_area("Notes et commentaires généraux du manager", key="manager_notes", height=200, 
                    placeholder="Ajoutez vos commentaires et notes généraux...")

        # Boutons Enregistrer et Annuler
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True, key="save_reunion"):
                if st.session_state.current_brief_name in st.session_state.saved_briefs:
                    brief_name = st.session_state.current_brief_name
                    
                    # Récupérer tous les commentaires du manager
                    manager_comments = {}
                    for i in range(1, 21):
                        comment_key = f"manager_comment_{i}"
                        if comment_key in st.session_state:
                            manager_comments[comment_key] = st.session_state[comment_key]
                    
                    # Mettre à jour les briefs
                    existing_briefs = load_briefs()
                    if brief_name in existing_briefs:
                        existing_briefs[brief_name].update({
                            "ksa_data": st.session_state.get("ksa_data", {}),
                            "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict(),
                            "manager_notes": st.session_state.get("manager_notes", ""),
                            "manager_comments": manager_comments,
                            "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                            "criteres_exclusion": st.session_state.get("criteres_exclusion", ""),
                            "processus_evaluation": st.session_state.get("processus_evaluation", "")
                        })
                        st.session_state.saved_briefs = existing_briefs
                    else:
                        st.session_state.saved_briefs[brief_name].update({
                            "ksa_data": st.session_state.get("ksa_data", {}),
                            "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict(),
                            "manager_notes": st.session_state.get("manager_notes", ""),
                            "manager_comments": manager_comments,
                            "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                            "criteres_exclusion": st.session_state.get("criteres_exclusion", ""),
                            "processus_evaluation": st.session_state.get("processus_evaluation", "")
                        })
                    
                    save_briefs()
                    st.session_state.reunion_completed = True
                    st.session_state.save_message = "✅ Données de réunion sauvegardées"
                    st.session_state.save_message_tab = "Réunion"
                    st.rerun()
                else:
                    st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_reunion"):
                delete_current_brief()

    # ---- Navigation wizard ----
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

# ---------------- ONGLET MÉTHODE COMPLÈTE ----------------
def methode_complete_tab():
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Synthèse"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Vérifier si un brief est chargé et si la réunion est terminée
    if not st.session_state.current_brief_name:
        st.warning("⚠️ Veuillez créer ou sélectionner un brief dans l'onglet Gestion avant d'accéder à cette section.")
    elif not st.session_state.reunion_completed:
        st.warning("⚠️ Veuillez compléter la réunion de brief avant d'accéder à cette section.")
    else:
        st.subheader(f"📝 Synthèse - {st.session_state.current_brief_name}")
        
        # Afficher les données du brief
        brief_data = st.session_state.saved_briefs.get(st.session_state.current_brief_name, {})
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
        
        # Afficher la matrice KSA si disponible
        if "ksa_matrix" in st.session_state and not st.session_state.ksa_matrix.empty:
            st.subheader("📊 Matrice KSA")
            st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
        
        # Sauvegarde de la synthèse
        st.write("### Actions")
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True, key="save_synthese"):
                if st.session_state.current_brief_name:
                    save_briefs()
                    st.session_state.save_message = f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !"
                    st.session_state.save_message_tab = "Synthèse"
                    st.rerun()
                else:
                    st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")
        
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_synthese"):
                delete_current_brief()

        # -------- EXPORT PDF/WORD --------
        st.subheader("📄 Export du Brief complet")
        col1, col2 = st.columns(2)
        with col1:
            if PDF_AVAILABLE:
                if st.session_state.current_brief_name:
                    pdf_buf = export_brief_pdf()
                    if pdf_buf:
                        st.download_button("⬇️ Télécharger PDF", data=pdf_buf,
                                         file_name=f"{st.session_state.current_brief_name}.pdf", mime="application/pdf")
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ PDF non dispo (pip install reportlab)")
        with col2:
            if WORD_AVAILABLE:
                if st.session_state.current_brief_name:
                    word_buf = export_brief_word()
                    if word_buf:
                        st.download_button("⬇️ Télécharger Word", data=word_buf,
                                         file_name=f"{st.session_state.current_brief_name}.docx",
                                         mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                else:
                    st.info("ℹ️ Créez d'abord un brief pour l'exporter")
            else:
                st.info("⚠️ Word non dispo (pip install python-docx)")

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
    st.session_state.current_tab = "Réunion"

with tabs[3]:
    methode_complete_tab()
    st.session_state.current_tab = "Synthèse"