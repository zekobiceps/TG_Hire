import sys, os 
import streamlit as st
from datetime import datetime
import json
from utils import get_example_for_field
import pandas as pd

# ✅ permet d'accéder à utils.py à la racine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import (
    init_session_state,
    PDF_AVAILABLE,
    WORD_AVAILABLE,
    save_briefs,
    load_briefs,
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
    generate_automatic_brief_name,
    save_library,
    test_deepseek_connection,
)

# ---------------- NOUVELLES FONCTIONS ----------------
def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau"""
    st.subheader("📊 Matrice KSA (Knowledge, Skills, Abilities)")
    
    # Initialiser les données KSA si elles n'existent pas
    if "ksa_matrix" not in st.session_state:
        st.session_state.ksa_matrix = pd.DataFrame(columns=[
            "Rubrique", "Critère", "Cible / Standard attendu", 
            "Échelle d'évaluation (1-5)", "Évaluateur"
        ])
    
    # Formulaire pour ajouter une nouvelle ligne
    with st.expander("➕ Ajouter un critère"):
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            new_rubrique = st.selectbox("Rubrique", ["Knowledge", "Skills", "Abilities"], key="new_rubrique")
        with col2:
            new_critere = st.text_input("Critère", key="new_critere")
        with col3:
            new_cible = st.text_input("Cible / Standard attendu", key="new_cible")
        with col4:
            new_score = st.selectbox("Importance", [1, 2, 3, 4, 5], key="new_score")
        with col5:
            new_evaluateur = st.selectbox("Évaluateur", ["Manager", "Recruteur", "Les deux"], key="new_evaluateur")
        
        if st.button("Ajouter", key="add_ksa"):
            if new_critere and new_cible:
                new_row = {
                    "Rubrique": new_rubrique,
                    "Critère": new_critere,
                    "Cible / Standard attendu": new_cible,
                    "Échelle d'évaluation (1-5)": new_score,
                    "Évaluateur": new_evaluateur
                }
                
                # Ajouter la nouvelle ligne au DataFrame
                st.session_state.ksa_matrix = pd.concat([
                    st.session_state.ksa_matrix, 
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                
                st.success("✅ Critère ajouté avec succès")
                st.rerun()
    
    # Afficher le tableau KSA
    if not st.session_state.ksa_matrix.empty:
        st.dataframe(
            st.session_state.ksa_matrix,
            use_container_width=True,
            hide_index=True
        )
        
        # Calculer et afficher la note globale
        if "Échelle d'évaluation (1-5)" in st.session_state.ksa_matrix.columns:
            scores = st.session_state.ksa_matrix["Échelle d'évaluation (1-5)"].astype(int)
            moyenne = scores.mean()
            st.metric("Note globale", f"{moyenne:.1f}/5")
        
        # Bouton pour supprimer la dernière entrée
        if st.button("🗑️ Supprimer le dernier critère", type="secondary", key="delete_last_criteria"):
            if len(st.session_state.ksa_matrix) > 0:
                st.session_state.ksa_matrix = st.session_state.ksa_matrix.iloc[:-1]
                st.rerun()
    else:
        st.info("Aucun critère défini. Ajoutez des critères pour commencer.")

def conseil_button(titre, categorie, conseil, key):
    """Crée un bouton avec conseil pour un champ"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_area(titre, key=key)
    with col2:
        if st.button("💡", key=f"btn_{key}"):
            st.session_state[key] = generate_checklist_advice(categorie, titre)
            st.rerun()

def delete_current_brief():
    """Supprime le brief actuel et retourne à l'onglet Gestion"""
    if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
        brief_name = st.session_state.current_brief_name
        if brief_name in st.session_state.saved_briefs:
            del st.session_state.saved_briefs[brief_name]
            save_briefs()
            
            # Réinitialiser l'état de la session
            st.session_state.current_brief_name = ""
            st.session_state.avant_brief_completed = False
            st.session_state.reunion_completed = False
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

# Variables pour gérer l'accès aux onglets
if "avant_brief_completed" not in st.session_state:
    st.session_state.avant_brief_completed = False

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = False

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
        background-color: #0d1117; /* Fond noir pour le tableau */
        font-size: 0.9em; /* Augmentation de la taille du texte */
        border: 1px solid #ffffff; /* Bordure blanche */
    }
    
    .dark-table th, .dark-table td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #ffffff; /* Bordures blanches */
        color: #e6edf3; /* Texte clair sur fond sombre */
    }
    
    .dark-table th {
        background-color: #FF4B4B !important;  /* Rouge vif identique aux boutons */
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ffffff; /* Bordure blanche */
    }
    
    /* Auto-size pour les deux premières colonnes */
    .dark-table th:nth-child(1),
    .dark-table td:nth-child(1) {
        width: auto !important;
        min-width: 100px;
    }
    
    .dark-table th:nth-child(2),
    .dark-table td:nth-child(2) {
        width: auto !important;
        min-width: 150px;
    }
    
    .dark-table th:nth-child(3),
    .dark-table td:nth-child(3) {
        width: 65% !important;
    }
    
    /* Style pour les tableaux avec 4 colonnes (réunion de brief) */
    .dark-table.four-columns th:nth-child(1),
    .dark-table.four-columns td:nth-child(1) {
        width: auto !important;
        min-width: 100px;
    }
    
    .dark-table.four-columns th:nth-child(2),
    .dark-table.four-columns td:nth-child(2) {
        width: auto !important;
        min-width: 150px;
    }
    
    .dark-table.four-columns th:nth-child(3),
    .dark-table.four-columns td:nth-child(3) {
        width: 50% !important;
    }
    
    .dark-table.four-columns th:nth-child(4),
    .dark-table.four-columns td:nth-child(4) {
        width: 25% !important;
    }
    
    .section-title {
        font-weight: 600;
        color: #58a6ff; /* Couleur bleue pour les titres de section */
        font-size: 0.95em; /* Augmentation de la taille du texte */
        margin-bottom: 0 !important; /* Pas de marge pour alignement */
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
        font-size: 0.9em; /* Augmentation de la taille du texte */
        resize: vertical;
    }
    
    /* Style pour les cellules de texte */
    .table-text {
        padding: 6px;
        font-size: 0.9em; /* Augmentation de la taille du texte */
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
        color: #58a6ff; /* Couleur bleue pour les titres de section */
    }
    
    /* Auto-size pour les deux premières colonnes */
    .stDataFrame td:nth-child(1) {
        width: auto !important;
        min-width: 100px;
    }
    
    .stDataFrame td:nth-child(2) {
        width: auto !important;
        min-width: 150px;
    }
    
    .stDataFrame td:nth-child(3) {
        width: 50% !important;
    }
    
    .stDataFrame td:nth-child(4) {
        width: 25% !important;
    }
    
    /* Style pour les cellules éditables (Informations) */
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

# Vérification si un brief est chargé au début de l'application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

# Création des onglets dans l'ordre demandé : Gestion, Avant-brief, Réunion, Synthèse, Catalogue des Postes
tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse",
    "📚 Catalogue des Postes"
])

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Gestion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

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
                    "brief_type": "Standard"  # Default to Standard
                }
                save_briefs()
                st.session_state.current_brief_name = brief_name
                st.session_state.save_message = f"✅ Brief '{brief_name}' créé avec succès"
                st.session_state.save_message_tab = "Gestion"
                st.rerun()
        with col_cancel:
            if st.button("🗑️ Annuler", type="secondary", use_container_width=True, key="cancel_brief"):
                # Reset fields
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
                            del st.session_state.saved_briefs[name]
                            save_briefs()
                            st.rerun()
                    with col_brief4:
                        if st.button("📄 Exporter", key=f"export_{name}"):
                            pass  # Logique d'export à implémenter si nécessaire
            else:
                st.info("Aucun brief sauvegardé ou correspondant aux filtres.")

# ---------------- AVANT-BRIEF ----------------
with tabs[1]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Avant-brief"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Afficher les informations du brief en cours
    brief_display_name = f"Avant-brief - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.subheader(f"🔄 {brief_display_name}")
    
    # Liste des sections et champs pour les text_area
    sections = [
        {
            "title": "Contexte du poste",
            "fields": [
                ("Raison de l'ouverture", "raison_ouverture", "Remplacement / Création / Évolution interne"),
                ("Mission globale", "impact_strategique", "Résumé du rôle et objectif principal"),
                ("Tâches principales", "taches_principales", "Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget"),
            ]
        },
        {
            "title": "Must-have (Indispensables)",
            "fields": [
                ("Expérience", "must_have_experience", "Nombre d'années minimum, expériences similaires dans le secteur"),
                ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Diplômes exigés, certifications spécifiques"),
                ("Compétences / Outils", "must_have_competences", "Techniques, logiciels, méthodes à maîtriser"),
                ("Soft skills / aptitudes comportementales", "must_have_softskills", "Leadership, rigueur, communication, autonomie"),
            ]
        },
        {
            "title": "Nice-to-have (Atouts)",
            "fields": [
                ("Expérience additionnelle", "nice_to_have_experience", "Ex. projets internationaux, multi-sites"),
                ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Diplômes ou certifications supplémentaires appréciés"),
                ("Compétences complémentaires", "nice_to_have_competences", "Compétences supplémentaires non essentielles mais appréciées"),
            ]
        },
        {
            "title": "Sourcing et marché",
            "fields": [
                ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"),
                ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"),
                ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels"),
            ]
        },
        {
            "title": "Conditions et contraintes",
            "fields": [
                ("Localisation", "rattachement", "Site principal, télétravail, déplacements"),
                ("Budget recrutement", "budget", "Salaire indicatif, avantages, primes éventuelles"),
            ]
        },
        {
            "title": "Profils pertinents",
            "fields": [
                ("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"),
                ("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"),
                ("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre"),
            ]
        },
        {
            "title": "Notes libres",
            "fields": [
                ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"),
                ("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique"),
            ]
        },
    ]

    brief_data = {}
    if st.session_state.current_brief_name in st.session_state.saved_briefs:
        brief_data = st.session_state.saved_briefs[st.session_state.current_brief_name]

    # Fonction pour générer le conseil IA
    def generate_and_apply_advice(section_title, title, key):
        if st.session_state.get(f"trigger_advice_{key}", False):
            advice = generate_checklist_advice(section_title, title)
            example = get_example_for_field(section_title, title)
            st.session_state[key] = f"{advice}\nExemple : {example}"
            st.session_state[f"trigger_advice_{key}"] = False
            st.rerun()

    # Appliquer les conseils avant le rendu
    for section in sections:
        for title, key, _ in section["fields"]:
            if section["title"] not in ["Conditions et contraintes", "Profils pertinents", "Notes libres"]:
                generate_and_apply_advice(section["title"], title, key)

    # Formulaire pour les widgets
    with st.form(key="avant_brief_form"):
        for section in sections:
            with st.expander(f"📋 {section['title']}"):
                for title, key, placeholder in section["fields"]:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text_area(title, value=brief_data.get(key, st.session_state.get(key, "")), key=key, placeholder=placeholder)
                    with col2:
                        if section["title"] not in ["Conditions et contraintes", "Profils pertinents", "Notes libres"]:
                            if st.button("💡 Conseil IA", key=f"trigger_advice_{key}"):
                                pass  # La logique est gérée dans generate_and_apply_advice

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

# ---------------- RÉUNION ----------------
with tabs[2]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Réunion"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Afficher les informations du brief en cours
    brief_display_name = f"Réunion de brief - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.subheader(f"✅ {brief_display_name}")

    total_steps = 5
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation")

        # Récupérer les données de l'Avant-brief
        if st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_data = st.session_state.saved_briefs[st.session_state.current_brief_name]
            
            # Définir les sections et champs (même structure que dans Avant-brief)
            sections = [
                {"title": "Contexte du poste", "fields": [
                    ("Raison de l'ouverture", "raison_ouverture"),
                    ("Mission globale", "impact_strategique"),
                    ("Tâches principales", "taches_principales"),
                ]},
                {"title": "Must-have (Indispensables)", "fields": [
                    ("Expérience", "must_have_experience"),
                    ("Connaissances / Diplômes / Certifications", "must_have_diplomes"),
                    ("Compétences / Outils", "must_have_competences"),
                    ("Soft skills / aptitudes comportementales", "must_have_softskills"),
                ]},
                {"title": "Nice-to-have (Atouts)", "fields": [
                    ("Expérience additionnelle", "nice_to_have_experience"),
                    ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes"),
                    ("Compétences complémentaires", "nice_to_have_competences"),
                ]},
                {"title": "Sourcing et marché", "fields": [
                    ("Entreprises où trouver ce profil", "entreprises_profil"),
                    ("Synonymes / intitulés proches", "synonymes_poste"),
                    ("Canaux à utiliser", "canaux_profil"),
                ]},
                {"title": "Conditions et contraintes", "fields": [
                    ("Localisation", "rattachement"),
                    ("Budget recrutement", "budget"),
                ]},
                {"title": "Profils pertinents", "fields": [
                    ("Lien profil 1", "profil_link_1"),
                    ("Lien profil 2", "profil_link_2"),
                    ("Lien profil 3", "profil_link_3"),
                ]},
                {"title": "Notes libres", "fields": [
                    ("Points à discuter ou à clarifier avec le manager", "commentaires"),
                    ("Case libre", "notes_libres"),
                ]},
            ]

            # Construire les données pour le tableau
            data = []
            for section in sections:
                for title, key in section["fields"]:
                    value = brief_data.get(key, "")
                    comment_key = f"manager_comment_{key}"
                    comment = st.session_state.get(comment_key, "")
                    data.append([section["title"] if title == section["fields"][0][0] else "", title, value, comment])

            df = pd.DataFrame(data, columns=["Section", "Détails", "Informations", "Commentaires du manager"])

            # Afficher le tableau éditable
            edited_df = st.data_editor(
                df,
                column_config={
                    "Section": st.column_config.TextColumn("Section", disabled=True, width="small"),
                    "Détails": st.column_config.TextColumn("Détails", disabled=True, width="medium"),
                    "Informations": st.column_config.TextColumn("Informations", disabled=True, width="medium"),
                    "Commentaires du manager": st.column_config.TextColumn("Commentaires du manager", width="medium")
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed"
            )

            # Sauvegarder les commentaires
            if st.button("💾 Sauvegarder commentaires", type="primary", key="save_comments_step1"):
                for i, row in edited_df.iterrows():
                    if row["Détails"] != "":
                        comment_key = f"manager_comment_{sections[i // len(sections[0]['fields'])]['fields'][i % len(sections[0]['fields'])][1]}"
                        st.session_state[comment_key] = row["Commentaires du manager"]
                st.session_state.save_message = "✅ Commentaires sauvegardés"
                st.session_state.save_message_tab = "Réunion"
                st.rerun()

        else:
            st.warning("Aucun brief sélectionné. Veuillez créer et sauvegarder un brief dans l'onglet Avant-brief.")

    elif step == 2:
        st.subheader("2️⃣ Questions Comportementales")
        st.text_area("Comment le candidat devrait-il gérer [situation difficile] ?", key="comp_q1", height=100)
        st.text_area("Réponse attendue", key="comp_rep1", height=100)
        st.text_area("Compétences évaluées", key="comp_eval1", height=100)

    elif step == 3:
        st.subheader("📊 Matrice KSA - Validation manager")
        render_ksa_matrix()

    elif step == 4:
        st.subheader("4️⃣ Stratégie Recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion", height=100)
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation", height=100)
        
    elif step == 5:
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
                    manager_comments = {k: v for k, v in st.session_state.items() if k.startswith("manager_comment_")}
                    
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

# ---------------- SYNTHÈSE ----------------
with tabs[3]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Synthèse"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Afficher les informations du brief en cours
    brief_display_name = f"Synthèse - {st.session_state.current_brief_name}_{st.session_state.get('manager_nom', 'N/A')}_{st.session_state.get('affectation_nom', 'N/A')}"
    st.subheader(f"📝 {brief_display_name}")
    
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("poste_intitule", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Affectation": f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}",
        "Date": str(st.session_state.get("date_brief", "")),
        "Raison ouverture": st.session_state.get("raison_ouverture", ""),
        "Tâches principales": st.session_state.get("taches_principales", ""),
        "Entreprises profil": st.session_state.get("entreprises_profil", ""),
        "Canaux": st.session_state.get("canaux_profil", ""),
        "Budget": st.session_state.get("budget", ""),
    })

    st.subheader("📊 Calcul automatique du Score Global")
    score_total = 0
    count = 0
    
    # Calcul basé sur la matrice KSA
    if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
        if "Échelle d'évaluation (1-5)" in st.session_state.ksa_matrix.columns:
            scores = st.session_state.ksa_matrix["Échelle d'évaluation (1-5)"].astype(int)
            score_global = scores.mean()
            st.metric("Score Global Cible", f"{score_global:.2f}/5")
    
    # Calcul de secours basé sur l'ancien système KSA
    elif "ksa_data" in st.session_state:
        for cat, comps in st.session_state.ksa_data.items():
            for comp, details in comps.items():
                score_total += int(details.get("score") or 0)
                count += 1
        score_global = (score_total / count) if count else 0
        st.metric("Score Global Cible", f"{score_global:.2f}/5")
    else:
        st.info("ℹ️ Aucune donnée KSA disponible pour calculer le score")

    # Boutons Confirmer et Annuler
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

# ---------------- ONGLET CATALOGUE DES POSTES ----------------
with tabs[4]:
    # Afficher le message de sauvegarde seulement pour cet onglet
    if ("save_message" in st.session_state and st.session_state.save_message) and ("save_message_tab" in st.session_state and st.session_state.save_message_tab == "Catalogue des Postes"):
        st.success(st.session_state.save_message)
        st.session_state.save_message = None
        st.session_state.save_message_tab = None

    # Afficher les informations du catalogue
    st.subheader("📚 Catalogue des Postes")
    
    # Charger et afficher les briefs sauvegardés
    if st.session_state.saved_briefs:
        st.write("Liste des briefs enregistrés :")
        for name, data in st.session_state.saved_briefs.items():
            st.write(f"- **{name}**: {data.get('poste_intitule', 'Sans titre')} - Manager: {data.get('manager_nom', 'N/A')}")
        
        # Option pour sauvegarder le catalogue
        if st.button("💾 Sauvegarder catalogue", type="primary", key="save_catalogue"):
            save_library(st.session_state.saved_briefs)
            st.session_state.save_message = "✅ Catalogue sauvegardé avec succès"
            st.session_state.save_message_tab = "Catalogue des Postes"
            st.rerun()
    else:
        st.info("Aucun brief enregistré pour le moment.")