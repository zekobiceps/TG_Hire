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

# --- CSS pour augmenter la taille du texte des onglets ---
st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px; 
}
</style>
""", unsafe_allow_html=True)

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
        # CSS pour améliorer l'apparence avec 3 colonnes et styliser la réponse
        st.markdown("""
        <style>
            .stTextInput, .stSelectbox, .stSlider, .stTextArea {
                margin-bottom: 5px;
                padding: 5px;
                border-radius: 8px;
                background-color: #F0F2F6;
                color: #333333;
            }
            .stTextInput > div > input, .stTextArea > div > textarea {
                background-color: #F0F2F6;
                color: #333333;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            .stSelectbox > div > select {
                background-color: #F0F2F6;
                color: #333333;
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
                background-color: #FFFFFF;
                padding: 5px;
            }
            .ai-response {
                margin-top: 10px;
                padding: 5px;
                background-color: #28a745;
                border-radius: 8px;
                color: #FFFFFF;
            }
            .success-icon {
                display: inline-block;
                margin-right: 5px;
                color: #28a745;
            }
            .stSuccess {
                background-color: #28a745 !important;
                color: #FFFFFF !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Formulaire pour ajouter un critère avec 3 colonnes
        with st.form(key="add_ksa_criterion_form"):
            # "Cible / Standard attendu" en haut, sur toute la largeur
            st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
            cible = st.text_area("Cible / Standard attendu", 
                                 placeholder="Définissez la cible ou le standard attendu pour ce critère.", 
                                 key="new_cible", height=100)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Champs en 3 colonnes
            col1, col2, col3 = st.columns([1, 1, 1.5])
            with col1:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
                st.markdown("</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                critere = st.text_input("Critère", placeholder="", key="new_critere")
                type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], 
                                            key="new_type_question")
                st.markdown("</div>", unsafe_allow_html=True)
            with col3:
                st.markdown("<div style='padding: 5px;'>", unsafe_allow_html=True)
                evaluation = st.slider("Échelle d'évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                evaluateur = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"], key="new_evaluateur")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # --- Section pour demander une question à l'IA ---
            st.markdown("---")
            st.markdown("**Demander une question à l'IA**")
            
            # Champ de saisie et checkbox sur des lignes séparées
            ai_prompt = st.text_input("Décrivez ce que l'IA doit générer :", 
                                     placeholder="Ex: une question générale pour évaluer la maîtrise des techniques de sourcing par un chargé de recrutement", 
                                     key="ai_prompt")
            st.checkbox("⚡ Mode rapide (réponse concise)", key="concise_checkbox")
            
            # Boutons sur une ligne distincte
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
            
            # Bouton pour ajouter le critère
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

        # Afficher la réponse générée uniquement en bas
        if "ai_response" in st.session_state and st.session_state.ai_response:
            st.markdown(f"<div class='ai-response'>{st.session_state.ai_response}</div>", unsafe_allow_html=True)

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
        file_path = os.path.join("briefs", f"{brief_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            st.session_state.saved_briefs.pop(brief_name, None)
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
    total_briefs = len(load_briefs())
    completed_briefs = sum(1 for b in load_briefs().values() 
                          if b.get("ksa_data") and any(b["ksa_data"].values()))
    
    st.metric("📋 Briefs créés", total_briefs)
    st.metric("✅ Briefs complétés", completed_briefs)
    
    st.divider()
    if st.button("Tester DeepSeek", key="test_deepseek"):
        test_deepseek_connection()

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

# Style CSS pour les onglets personnalisés et les tableaux améliorés
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        padding: 0px;
        border-radius: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF !important;
        color: #333333 !important;
        border: none !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        border-radius: 0 !important;
        margin-right: 0 !important;
        height: auto !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #ff4b4b !important;
        background-color: #FFFFFF !important;
        border-bottom: 3px solid #ff4b4b !important;
    }
    
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
    
    .stButton > button[kind="secondary"] {
        background-color: #E0E0E0;
        color: #333333;
        border: 1px solid #FF4B4B;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #D0D0D0;
        color: #333333;
    }
    
    .stButton > button[key="apply_filter"] {
        background-color: #FF0000 !important;
        color: white !important;
        border: none;
    }
    
    .stButton > button[key="apply_filter"]:hover {
        background-color: #FF3333 !important;
        color: white !important;
    }
    
    .streamlit-expanderHeader {
        background-color: #E0E0E0;
        color: #333333;
        border-radius: 5px;
        padding: 0.5rem;
    }
    
    div[data-baseweb="select"] > div {
        border: none !important;
        background-color: #F0F2F6 !important;
        color: #333333 !important;
        border-radius: 4px !important;
    }
    
    .stDataFrame {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #FFFFFF;
        font-size: 0.9em;
        border: 1px solid #CCCCCC;
    }
    
    .stDataFrame th, .stDataFrame td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #CCCCCC;
        color: #333333;
    }
    
    .stDataFrame th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #CCCCCC;
    }
    
    .stDataFrame td:nth-child(1), .stDataFrame th:nth-child(1) { width: 10%; }
    .stDataFrame td:nth-child(2), .stDataFrame th:nth-child(2) { width: 25%; }
    .stDataFrame td:nth-child(3), .stDataFrame th:nth-child(3) { width: 15%; }
    .stDataFrame td:nth-child(4), .stDataFrame th:nth-child(4) { width: 40%; }
    .stDataFrame td:nth-child(5), .stDataFrame th:nth-child(5) { width: 10%; }
    
    .stTextInput input {
        background-color: #F0F2F6 !important;
        color: #333333 !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    .stTextArea textarea {
        background-color: #F0F2F6 !important;
        color: #333333 !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    .stDateInput input {
        background-color: #F0F2F6 !important;
        color: #333333 !important;
        border-radius: 4px !important;
        border: none !important;
    }
    
    .stTextArea textarea {
        height: 100px !important;
    }
    
    .message-container {
        margin-top: 10px;
        padding: 10px;
        border-radius: 5px;
    }
    
    .stAlert {
        padding: 10px;
        margin-top: 10px;
    }
    
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
    }
    
    .comparison-table th, .comparison-table td {
        border: 1px solid #CCCCCC;
        padding: 8px;
        text-align: left;
    }
    
    .comparison-table th {
        background-color: #E0E0E0;
        font-weight: bold;
    }

    .dataframe {
        width: 100%;
    }
    
    .dark-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #FFFFFF;
        font-size: 0.9em;
        border: 1px solid #CCCCCC;
    }
    
    .dark-table th, .dark-table td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #CCCCCC;
        color: #333333;
    }
    
    .dark-table th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #CCCCCC;
    }
    
    .dark-table th:nth-child(1), .dark-table td:nth-child(1) { width: auto; min-width: 100px; }
    .dark-table th:nth-child(2), .dark-table td:nth-child(2) { width: auto; min-width: 150px; }
    .dark-table th:nth-child(3), .dark-table td:nth-child(3) { width: 65%; }
    
    .dark-table.four-columns th:nth-child(1), .dark-table.four-columns td:nth-child(1) { width: auto; min-width: 100px; }
    .dark-table.four-columns th:nth-child(2), .dark-table.four-columns td:nth-child(2) { width: auto; min-width: 150px; }
    .dark-table.four-columns th:nth-child(3), .dark-table.four-columns td:nth-child(3) { width: 50%; }
    .dark-table.four-columns th:nth-child(4), .dark-table.four-columns td:nth-child(4) { width: 25%; }
    
    .section-title {
        font-weight: 600;
        color: #1f77b4;
        font-size: 0.95em;
        margin-bottom: 0 !important;
    }
    
    .table-textarea {
        width: 100%;
        min-height: 60px;
        background-color: #F0F2F6;
        color: #333333;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 6px;
        font-size: 0.9em;
        resize: vertical;
    }
    
    .table-text {
        padding: 6px;
        font-size: 0.9em;
        color: #333333;
    }
    
    .empty-row {
        display: none;
    }
    
    .stDataFrame {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #FFFFFF;
        font-size: 0.9em;
        border: 1px solid #CCCCCC;
    }
    
    .stDataFrame th, .stDataFrame td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #CCCCCC;
        color: #333333;
    }
    
    .stDataFrame th {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #CCCCCC;
    }
    
    .stDataFrame td:first-child {
        font-weight: 600;
        color: #1f77b4;
    }
    
    .stDataFrame td:nth-child(1) { width: auto; min-width: 100px; }
    .stDataFrame td:nth-child(2) { width: auto; min-width: 150px; }
    .stDataFrame td:nth-child(3) { width: 50%; }
    .stDataFrame td:nth-child(4) { width: 25%; }
    
    .stDataFrame td:nth-child(3) textarea {
        background-color: #F0F2F6 !important;
        color: #333333 !important;
        border: 1px solid #555 !important;
        border-radius: 4px !important;
        padding: 6px !important;
        min-height: 60px !important;
        resize: vertical !important;
    }
    
    .stTextArea textarea {
        white-space: pre-wrap !important;
    }
    
    .stDataFrame tr {
        height: auto !important;
    }
    
    .stDataFrame td {
        height: auto !important;
        min-height: 60px !important;
    }
    
    .ai-advice-box {
        background-color: #F0F2F6;
        border-left: 4px solid #FF4B4B;
        padding: 1rem;
        border-radius: 4px;
        margin-top: 1rem;
        color: #333333;
    }
    .ai-advice-box strong {
        color: #000000;
    }
    </style>
""", unsafe_allow_html=True)

# Vérification si un brief est chargé au début de l'application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

# Création des onglets dans l'ordre demandé : Gestion, Avant-brief, Réunion de brief, Synthèse
tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse"
])

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Gestion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Charger les briefs depuis les fichiers JSON
    st.session_state.saved_briefs = load_briefs()

    # Organiser les sections Informations de base et Filtrer les briefs en 2 colonnes
    col_info, col_filter = st.columns(2)
    
    # Section Informations de base
    with col_info:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Informations de base</h3>', unsafe_allow_html=True)
        
        # Organiser en 3 colonnes
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
        
        # Boutons Créer et Annuler
        col_create, col_cancel = st.columns(2)
        with col_create:
            if st.button("💾 Créer brief", type="primary", use_container_width=True, key="create_brief"):
                brief_name = generate_automatic_brief_name()
                st.session_state.saved_briefs[brief_name] = {
                    "poste_intitule": st.session_state.poste_intitule,
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "date_brief": str(st.session_state.date_brief),
                    "brief_type": "Standard"
                }
                save_briefs()
                st.session_state.current_brief_name = brief_name
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
    
    # Section Filtrage
    with col_filter:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">🔍 Filtrer les briefs</h3>', unsafe_allow_html=True)
        
        # Organiser en 3 colonnes
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
        
        # Bouton Filtrer
        if st.button("🔎 Filtrer", use_container_width=True, key="apply_filter"):
            filter_month = st.session_state.filter_date.strftime("%m") if st.session_state.filter_date else ""
            st.session_state.filtered_briefs = filter_briefs(
                load_briefs(), 
                filter_month, 
                st.session_state.filter_recruteur, 
                st.session_state.filter_brief_type, 
                st.session_state.filter_manager, 
                st.session_state.filter_affectation, 
                st.session_state.filter_nom_affectation
            )
            st.session_state.show_filtered_results = True
            st.rerun()
        
        # Affichage des résultats en dessous du bouton Filtrer
        if st.session_state.show_filtered_results:
            st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
            briefs_to_show = st.session_state.filtered_briefs
            
            if briefs_to_show:
                for name, data in briefs_to_show.items():
                    col_brief1, col_brief2, col_brief3, col_brief4 = st.columns([3, 1, 1, 1])
                    with col_brief1:
                        st.write(f"**{name}** - Manager: {data.get('manager_nom', 'N/A')} - Affectation: {data.get('affectation_nom', 'N/A')}")
                    with col_brief2:
                        if st.button("📝 Éditer", key=f"edit_{name}"):
                            st.session_state.current_brief_name = name
                            st.session_state.avant_brief_completed = True
                            st.rerun()
                    with col_brief3:
                        if st.button("🗑️ Supprimer", key=f"delete_{name}"):
                            file_path = os.path.join("briefs", f"{name}.json")
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            st.session_state.saved_briefs.pop(name, None)
                            save_briefs()
                            st.rerun()
                    with col_brief4:
                        if st.button("📄 Exporter", key=f"export_{name}"):
                            pass  # Logique d'export à implémenter si nécessaire
            else:
                st.info("Aucun brief sauvegardé ou correspondant aux filtres.")

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Avant-brief"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Vérifier si un brief est chargé
    if not st.session_state.current_brief_name:
        st.warning("⚠️ Veuillez créer ou sélectionner un brief dans l'onglet Gestion avant d'accéder à cette section.")
    else:
        brief_display_name = st.session_state.current_brief_name
        st.subheader(f"📝 Avant-brief - {brief_display_name}")

        # Afficher un expander pour la méthode complète
        with st.expander("ℹ️ Méthode complète", expanded=False):
            st.markdown("""
### Méthode complète
Le brief recrutement est un document structuré qui définit les besoins d'un poste ouvert. Il sert de référence pour le recruteur et le manager pour aligner les attentes et optimiser le processus de recrutement.

#### Éléments clés du brief :
- **Contexte du poste** : Raison de l'ouverture, mission globale, tâches principales.
- **Must-have (Indispensables)** : Expérience, diplômes, compétences techniques, soft skills.
- **Nice-to-have (Atouts)** : Éléments valorisants non essentiels.
- **Sourcing et marché** : Entreprises cibles, synonymes du poste, canaux de recrutement.

#### Avantages du brief :
- Alignement entre recruteur et manager.
- Définition claire des critères d'évaluation.
- Optimisation du temps de recrutement.

#### Conseils pour un bon brief :
- Soyez précis sur les must-have pour éviter les candidats non qualifiés.
- Utilisez la matrice KSA (Knowledge, Skills, Abilities) pour structurer les exigences.
- Impliquez le manager pour valider les critères.

#### Matrice KSA exemple :
| Rubrique | Critère | Type de question | Cible / Standard attendu | Échelle (1-5) | Évaluateur |
|----------|---------|------------------|--------------------------|---------------|------------|
| Knowledge | Normes BTP | Technique | Expliquer ISO 45001 | 4 | Recruteur |
| Skills | AutoCAD | Technique | Démontrer utilisation | 5 | Manager |
| Abilities | Leadership | Comportementale | Exemple STAR | 3 | Les deux |

Cette matrice aide à évaluer objectivement les candidats pendant les entretiens.
""")

        # Sections du brief
        sections = [
            {
                "title": "Contexte du poste",
                "fields": [
                    ("Raison de l'ouverture", "raison_ouverture", "Ex: remplacement, création de poste..."),
                    ("Impact stratégique", "impact_strategique", "Ex: contribution à un projet majeur..."),
                    ("Rattachement hiérarchique", "rattachement", "Ex: rattaché au Directeur des Opérations"),
                    ("Tâches principales", "taches_principales", "Ex: gestion de chantier, coordination d'équipes..."),
                ]
            },
            {
                "title": "Must-have (Indispensables)",
                "fields": [
                    ("Expérience", "must_have_experience", "Ex: 5 ans en BTP"),
                    ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Ex: Diplôme en génie civil"),
                    ("Compétences / Outils", "must_have_competences", "Ex: Maîtrise d'AutoCAD"),
                    ("Soft skills / aptitudes comportementales", "must_have_softskills", "Ex: Leadership"),
                ]
            },
            {
                "title": "Nice-to-have (Atouts)",
                "fields": [
                    ("Expérience additionnelle", "nice_to_have_experience", "Ex: Projets internationaux"),
                    ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Ex: Certification LEED"),
                    ("Compétences complémentaires", "nice_to_have_competences", "Ex: Connaissance en BIM"),
                ]
            },
            {
                "title": "Sourcing et marché",
                "fields": [
                    ("Entreprises où trouver ce profil", "entreprises_profil", "Ex: Vinci, Bouygues"),
                    ("Synonymes / intitulés proches", "synonymes_poste", "Ex: Conducteur de travaux"),
                    ("Canaux à utiliser", "canaux_profil", "Ex: LinkedIn, jobboards BTP"),
                ]
            },
            {
                "title": "Autres",
                "fields": [
                    ("Budget", "budget", "Ex: 50k-60k € brut annuel"),
                    ("Commentaires", "commentaires", "Ex: Profil urgent"),
                    ("Notes libres", "notes_libres", "Ex: Préférences supplémentaires"),
                ]
            }
        ]

        # Affichage des sections du brief
        for section in sections:
            with st.expander(f"📋 {section['title']}", expanded=True):
                for field_name, field_key, placeholder in section["fields"]:
                    st.text_area(field_name, key=field_key, placeholder=placeholder, height=100)
                    # Affichage de l'exemple contextuel
                    example = get_example_for_field(section['title'], field_name)
                    st.markdown(f"<div class='ai-advice-box'><strong>Exemple :</strong> {example}</div>", unsafe_allow_html=True)

        # Matrice KSA
        st.markdown("### 📊 Matrice KSA")
        render_ksa_matrix()

        # Boutons Sauvegarder et Annuler
        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Sauvegarder avant-brief", type="primary", use_container_width=True, key="save_avant_brief"):
                if st.session_state.current_brief_name:
                    brief_data = {
                        "raison_ouverture": st.session_state.raison_ouverture,
                        "impact_strategique": st.session_state.impact_strategique,
                        "rattachement": st.session_state.rattachement,
                        "taches_principales": st.session_state.taches_principales,
                        "must_have_experience": st.session_state.must_have_experience,
                        "must_have_diplomes": st.session_state.must_have_diplomes,
                        "must_have_competences": st.session_state.must_have_competences,
                        "must_have_softskills": st.session_state.must_have_softskills,
                        "nice_to_have_experience": st.session_state.nice_to_have_experience,
                        "nice_to_have_diplomes": st.session_state.nice_to_have_diplomes,
                        "nice_to_have_competences": st.session_state.nice_to_have_competences,
                        "entreprises_profil": st.session_state.entreprises_profil,
                        "synonymes_poste": st.session_state.synonymes_poste,
                        "canaux_profil": st.session_state.canaux_profil,
                        "budget": st.session_state.budget,
                        "commentaires": st.session_state.commentaires,
                        "notes_libres": st.session_state.notes_libres,
                        "ksa_matrix": st.session_state.ksa_matrix.to_dict(),
                    }
                    st.session_state.saved_briefs[st.session_state.current_brief_name].update(brief_data)
                    save_briefs()
                    st.session_state.avant_brief_completed = True
                    st.session_state.save_message = "✅ Données avant-brief sauvegardées"
                    st.session_state.save_message_tab = "Avant-brief"
                    st.rerun()
                else:
                    st.error("❌ Veuillez d'abord créer un brief dans l'onglet Gestion")
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_avant_brief"):
                delete_current_brief()

# ---------------- RÉUNION DE BRIEF ----------------
with tabs[2]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Réunion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Vérifier si un brief est chargé et si l'avant-brief est terminée
    if not st.session_state.current_brief_name:
        st.warning("⚠️ Veuillez créer ou sélectionner un brief dans l'onglet Gestion avant d'accéder à cette section.")
    elif not st.session_state.avant_brief_completed:
        st.warning("⚠️ Veuillez compléter l'avant-brief avant d'accéder à cette section.")
    else:
        brief_display_name = st.session_state.current_brief_name
        st.subheader(f"✅ Réunion de brief - {brief_display_name}")

        total_steps = 4
        step = st.session_state.reunion_step
        
        st.progress(int((step / total_steps) * 100), text=f"**Étape {step} sur {total_steps}**")

        if step == 1:
            with st.expander("📋 Portrait robot candidat - Validation", expanded=True):
                data = []
                field_keys = []
                comment_keys = []
                k = 1
                brief_data = load_briefs().get(st.session_state.current_brief_name, {})
                for section in sections:
                    for i, (field_name, field_key, placeholder) in enumerate(section["fields"]):
                        value = brief_data.get(field_key, "")
                        section_title = section["title"] if i == 0 else ""
                        data.append([section_title, field_name, value, ""])
                        field_keys.append(field_key)
                        comment_keys.append(f"manager_comment_{k}")
                        k += 1
                df = pd.DataFrame(data, columns=["Section", "Détails", "Informations", "Commentaires du manager"])

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

                if st.button("💾 Sauvegarder commentaires", type="primary", key="save_comments_step1"):
                    for i in range(len(edited_df)):
                        if edited_df["Détails"].iloc[i] != "":
                            comment_key = comment_keys[i]
                            st.session_state[comment_key] = edited_df["Commentaires du manager"].iloc[i]
                    st.session_state.save_message = "✅ Commentaires sauvegardés"
                    st.session_state.save_message_tab = "Réunion"
                    st.rerun()

        elif step == 2:
            with st.expander("📊 Matrice KSA - Validation manager", expanded=True):
                with st.expander("ℹ️ Explications de la méthode KSA", expanded=False):
                    st.markdown("""
                        ### Méthode KSA (Knowledge, Skills, Abilities)
                        La méthode KSA permet de décomposer un poste en trois catégories de compétences pour une évaluation plus précise.
                        
                        #### 🧠 Knowledge (Connaissances)
                        Ce sont les connaissances théoriques ou factuelles qu'un candidat doit posséder.
                        - **Exemple 1 :** Connaissances des protocoles de sécurité IT (ISO 27001).
                        - **Exemple 2 :** Maîtrise des concepts de la comptabilité analytique.
                        - **Exemple 3 :** Connaissance approfondie des langages de programmation Python et R.
                        
                        #### 💪 Skills (Compétences)
                        Ce sont les compétences pratiques et techniques que l'on acquiert par la pratique.
                        - **Exemple 1 :** Capacité à utiliser le logiciel Adobe Photoshop pour le design graphique.
                        - **Exemple 2 :** Expertise en négociation commerciale pour la conclusion de contrats.
                        - **Exemple 3 :** Maîtrise de la gestion de projet Agile ou Scrum.
                        
                        #### ✨ Abilities (Aptitudes)
                        Ce sont les aptitudes plus générales ou innées, souvent liées au comportement.
                        - **Exemple 1 :** Capacité à gérer le stress et la pression.
                        - **Exemple 2 :** Aptitude à communiquer clairement des idées complexes.
                        - **Exemple 3 :** Capacité à travailler en équipe et à collaborer efficacement.
                        """, unsafe_allow_html=True)

                with st.form(key="add_criteria_form"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
                    with col2:
                        critere = st.text_input("Critère", placeholder="Ex: Leadership", key="new_critere")
                    with col3:
                        type_question = st.selectbox("Type de question", ["Comportementale", "Situationnelle", "Technique", "Générale"], key="new_type_question")
                    with col4:
                        evaluateur = st.selectbox("Qui évalue ce critère ?", ["Recruteur", "Manager", "Les deux"], key="new_evaluateur")

                    col_q_text, col_slider = st.columns([2, 1])
                    with col_q_text:
                        question = st.text_input("Question pour l'entretien", placeholder="Ex: Parlez-moi d'une situation où vous avez dû faire preuve de leadership.", key="new_question")
                    with col_slider:
                        evaluation = st.slider("Évaluation (1-5)", min_value=1, max_value=5, value=3, step=1, key="new_evaluation")
                    
                    ai_prompt = st.text_input("Décrivez ce que l'IA doit générer comme Question", placeholder="Ex: Donne-moi une question pour évaluer la gestion de projets", key="ai_prompt_input")
                    concise_mode = st.checkbox("⚡ Mode rapide (réponse concise)", key="concise_mode")
                    
                    st.markdown("---")
                    
                    col_ai, col_add = st.columns(2)
                    with col_ai:
                        if st.form_submit_button("💡 Générer question IA", type="primary", use_container_width=True):
                            if ai_prompt:
                                with st.spinner("Génération en cours..."):
                                    try:
                                        ai_response = generate_ai_question(ai_prompt, concise_mode)
                                        if ai_response.strip().startswith("Question:"):
                                            ai_response = ai_response.strip().replace("Question:", "", 1).strip()
                                        st.session_state.ai_generated_question = ai_response
                                    except Exception as e:
                                        st.error(f"Erreur lors de la génération : {e}")
                            else:
                                st.error("Veuillez entrer un prompt pour l'IA.")
                    
                    with col_add:
                        if st.form_submit_button("➕ Ajouter le critère", type="secondary", use_container_width=True):
                            if not critere or not question:
                                st.error("Veuillez remplir au moins le critère et la question.")
                            else:
                                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, pd.DataFrame([{
                                    "Rubrique": rubrique,
                                    "Critère": critere,
                                    "Type de question": type_question,
                                    "Question pour l'entretien": question,
                                    "Évaluation (1-5)": evaluation,
                                    "Évaluateur": evaluateur
                                }])], ignore_index=True)
                                st.success("✅ Critère ajouté avec succès !")
                                st.rerun()

                if "ai_generated_question" in st.session_state and st.session_state.ai_generated_question:
                    st.success(f"**Question :** `{st.session_state.ai_generated_question}`")
                    st.session_state.ai_generated_question = ""
                
                st.dataframe(st.session_state.ksa_matrix, use_container_width=True, hide_index=True)
                
                if not st.session_state.ksa_matrix.empty:
                    avg_rating = st.session_state.ksa_matrix["Évaluation (1-5)"].mean()
                    st.markdown(f"**<div style='font-size: 24px;'>Note cible de l'ensemble des critères : 🎯 {avg_rating:.2f} / 5</div>**", unsafe_allow_html=True)

        elif step == 3:
            with st.expander("💡 Stratégie et Processus", expanded=True):
                st.info("Définissez les canaux de sourcing et les critères d'évaluation.")
                st.multiselect("🎯 Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], key="canaux_prioritaires")
                
                st.markdown("---")
                st.subheader("Critères d'exclusion et Processus d'évaluation")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_area("🚫 Critères d'exclusion", key="criteres_exclusion", height=150, 
                                 placeholder="Ex: ne pas avoir d'expérience dans le secteur public...")
                with col2:
                    st.text_area("✅ Processus d'évaluation (détails)", key="processus_evaluation", height=150, 
                                 placeholder="Ex: Entretien RH (30min), Test technique, Entretien manager (60min)...")
            
        elif step == 4:
            with st.expander("📝 Notes générales du manager", expanded=True):
                st.info("Ajoutez des notes ou des commentaires finaux pour le brief.")
                st.text_area("Notes et commentaires généraux du manager", key="manager_notes", height=250, 
                             placeholder="Ajoutez vos commentaires et notes généraux...")

            st.markdown("---")
            col_save, col_cancel = st.columns([1, 1])
            with col_save:
                if st.button("💾 Enregistrer la réunion", type="primary", use_container_width=True, key="save_reunion"):
                    if st.session_state.current_brief_name:
                        manager_comments = {}
                        for i in range(1, 21):
                            comment_key = f"manager_comment_{i}"
                            if comment_key in st.session_state:
                                manager_comments[comment_key] = st.session_state[comment_key]
                        existing_briefs = load_briefs()
                        if st.session_state.current_brief_name in existing_briefs:
                            existing_briefs[st.session_state.current_brief_name].update({
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
                            st.session_state.saved_briefs[st.session_state.current_brief_name].update({
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

# ---------------- SYNTHÈSE ----------------
with tabs[3]:
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