# 1_Brief.py
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
    export_brief_pdf,
    export_brief_word,
    generate_checklist_advice,
    filter_briefs,
    generate_automatic_brief_name,
    save_library,
    get_ai_pre_redaction
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
    
    /* Bouton Pré-rédiger jaune avec lampe */
    .stButton > button[key="pre_rediger"], .stButton > button[key="pre_rediger_ia"] {
        background-color: #FFD700 !important;
        color: black !important;
        border: none;
    }
    
    .stButton > button[key="pre_rediger"]:hover, .stButton > button[key="pre_rediger_ia"]:hover {
        background-color: #FFEA00 !important;
        color: black !important;
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
    /* Permettre le retour à la ligne avec Alt+Enter */
.stTextArea textarea {
    white-space: pre-wrap !important;
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
    
    /* Style pour les onglets désactivés */
    .disabled-tab {
        opacity: 0.5;
        pointer-events: none;
        cursor: not-allowed;
    }
    
    /* Nouveau style pour le tableau amélioré - TABLEAU SOMBRE */
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
    
    /* Largeur des colonnes réduites */
    .dark-table th:nth-child(1),
    .dark-table td:nth-child(1) {
        width: 10%; /* Réduite */
    }
    
    .dark-table th:nth-child(2),
    .dark-table td:nth-child(2) {
        width: 15%; /* Réduite */
    }
    
    .dark-table th:nth-child(3),
    .dark-table td:nth-child(3) {
        width: 65%; /* Colonne Informations plus large */
    }
    
    /* Style pour les tableaux avec 4 colonnes (réunion de brief) */
    .dark-table.four-columns th:nth-child(1),
    .dark-table.four-columns td:nth-child(1) {
        width: 10%; /* Réduite */
    }
    
    .dark-table.four-columns th:nth-child(2),
    .dark-table.four-columns td:nth-child(2) {
        width: 15%; /* Réduite */
    }
    
    .dark-table.four-columns th:nth-child(3),
    .dark-table.four-columns td:nth-child(3) {
        width: 50%; /* Réduit pour faire de la place à la colonne notes */
    }
    
    .dark-table.four-columns th:nth-child(4),
    .dark-table.four-columns td:nth-child(4) {
        width: 25%; /* Colonne Commentaires du manager élargie */
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
    
    .stDataFrame td:nth-child(1) {
        width: 10%; /* Réduite */
    }
    
    .stDataFrame td:nth-child(2) {
        width: 15%; /* Réduite */
    }
    
    .stDataFrame td:nth-child(3) {
        width: 50%;
    }
    
    .stDataFrame td:nth-child(4) {
        width: 25%;
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

# Création des onglets dans l'ordre demandé : Gestion, Avant-brief, Réunion, Synthèse, Bibliothèque
tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse",
    "📚 Bibliothèque"
])

# Détection changement d'onglet pour reset message
selected_tab = st.session_state.current_tab
if selected_tab != st.session_state.current_tab:
    st.session_state.save_message = None
    st.session_state.current_tab = selected_tab

# Affichage message persistant si présent
if st.session_state.save_message:
    st.success(st.session_state.save_message)

# Déterminer quels onglets sont accessibles
can_access_avant_brief = st.session_state.current_brief_name != ""
can_access_reunion = can_access_avant_brief and st.session_state.avant_brief_completed
can_access_synthese = can_access_reunion and st.session_state.reunion_completed

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    # Style CSS personnalisé pour réduire les espaces
    st.markdown("""
    <style>
    /* Réduire l'espace entre les éléments */
    .st-emotion-cache-1r6slb0 {
        margin-bottom: 0.2rem;
    }
    .st-emotion-cache-1r6slb0 p {
        margin-bottom: 0.2rem;
    }
    /* Réduire l'espace entre les titres et les champs */
    h3 {
        margin-bottom: 0.5rem !important;
    }
    /* Réduire la hauteur des champs */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
        height: 2rem !important;
    }
    /* Réduire l'espace entre les lignes de formulaire */
    .st-emotion-cache-ocqkz7 {
        gap: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Trois colonnes: Informations de base, Filtrage et Actions
    col_info, col_filter, col_actions = st.columns([2, 1, 1])
    
    with col_info:
        # En-tête avec les titres alignés - VERSION COMPACTE
        st.markdown('<div class="compact-title"><h3>Informations de base</h3></div>', unsafe_allow_html=True)
        
        # Ligne 1: Poste à recruter | Manager
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Poste à recruter", key="poste_intitule")
        with col2:
            st.text_input("Manager", key="manager_nom")
        
        # Ligne 2: Recruteur | Type d'affectation
        col3, col4 = st.columns(2)
        with col3:
            st.selectbox("Recruteur", ["Zakaria", "Jalal", "Sara", "Ghita", "Bouchra"], key="recruteur")
        with col4:
            st.selectbox("Type d'affectation", ["Chantier", "Siège", "Dépôt"], key="affectation_type")
        
        # Ligne 3: Nom affectation | Date du brief
        col5, col6 = st.columns(2)
        with col5:
            st.text_input("Nom affectation", key="affectation_nom")
        with col6:
            st.date_input("Date du brief", key="date_brief", value=datetime.today())
    
    with col_filter:
        # Section Filtrage - VERSION COMPACTE
        st.markdown('<h3 style="margin-bottom: 0.3rem;">🔍 Filtrer les briefs</h3>', unsafe_allow_html=True)
        
        month = st.selectbox("Mois", ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"], key="filter_month")
        brief_type_filter = st.selectbox("Type de brief", ["", "Standard", "Méthode complète"], key="filter_brief_type")
        recruteur_filter = st.text_input("Recruteur", key="filter_recruteur")
        manager_filter = st.text_input("Manager", key="filter_manager")
        affectation_filter = st.selectbox("Affectation", ["", "Chantier", "Siège", "Dépôt"], key="filter_affectation")
        nom_affectation_filter = st.text_input("Nom affectation", key="filter_nom_affectation")
        
        if st.button("🔎 Filtrer", use_container_width=True, key="apply_filter"):
            st.session_state.filtered_briefs = filter_briefs(st.session_state.saved_briefs, month, recruteur_filter, brief_type_filter, manager_filter, affectation_filter, nom_affectation_filter)
            st.session_state.show_filtered_results = True
    
    with col_actions:
        # Section Type de brief et boutons
        st.markdown('<h3 style="margin-bottom: 0.3rem;">⚙️ Actions</h3>', unsafe_allow_html=True)
        
        brief_type = st.radio("Type de brief", ["Standard", "Méthode complète"], horizontal=False, key="brief_type")
        
        # Boutons Créer et Annuler - VERSION COMPACTE
        if st.button("💾 Créer brief", type="primary", use_container_width=True, key="create_brief"):
            # Générer un nom unique avec timestamp
            now = datetime.now()
            job_title = st.session_state.get("poste_intitule", "Nouveau")
            brief_name = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{job_title.replace(' ', '_')}"
            
            if brief_name not in st.session_state.saved_briefs:
                st.session_state.saved_briefs[brief_name] = {
                    "poste_intitule": st.session_state.poste_intitule,
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "date_brief": str(st.session_state.date_brief),
                    "brief_type": st.session_state.brief_type
                }
                save_briefs()
                st.session_state.current_brief_name = brief_name
                st.session_state.save_message = f"✅ Brief '{brief_name}' créé avec succès"
                st.rerun()
            else:
                st.warning("⚠️ Un brief avec ce nom existe déjà")
        
        if st.button("🗑️ Annuler", type="secondary", use_container_width=True, key="cancel_brief"):
            # Reset fields
            st.session_state.poste_intitule = ""
            st.session_state.manager_nom = ""
            st.session_state.recruteur = ""
            st.session_state.affectation_type = ""
            st.session_state.affectation_nom = ""
            st.session_state.date_brief = datetime.today()
            st.session_state.brief_type = "Standard"
            st.rerun()
    
    st.divider()
    
    # Affichage des résultats - UNIQUEMENT si recherche effectuée
    if st.session_state.show_filtered_results:
        st.markdown('<h3 style="margin-bottom: 0.3rem;">📋 Briefs sauvegardés</h3>', unsafe_allow_html=True)
        briefs_to_show = st.session_state.filtered_briefs
        
        if briefs_to_show:
            for name, data in briefs_to_show.items():
                col_brief1, col_brief2, col_brief3, col_brief4 = st.columns([3, 1, 1, 1])
                with col_brief1:
                    st.write(f"**{name}** - {data.get('brief_type', '')}")
                with col_brief2:
                    if st.button("📝 Éditer", key=f"edit_{name}"):
                        st.session_state.current_brief_name = name
                        st.session_state.avant_brief_completed = True  # Permet l'accès aux onglets suivants
                        st.rerun()
                with col_brief3:
                    if st.button("🗑️ Supprimer", key=f"delete_{name}"):
                        del st.session_state.saved_briefs[name]
                        save_briefs()
                        st.rerun()
                with col_brief4:
                    if st.button("📄 Exporter", key=f"export_{name}"):
                        # Logique d'export à implémenter si nécessaire
                        pass
        else:
            st.info("Aucun brief sauvegardé ou correspondant aux filtres.")

# ---------------- AVANT-BRIEF ----------------
with tabs[1]:
    # Afficher les informations du brief en cours
    st.subheader(f"🔄 Avant-brief - {st.session_state.get('poste_intitule', '')}")
    
    if "current_brief_name" in st.session_state:
        st.success(f"Brief actuel: {st.session_state.current_brief_name}")
    
    # Ajouter ce style CSS pour réduire la largeur des colonnes
    st.markdown("""
    <style>
    /* Réduire la largeur des colonnes Section et Détails */
    .stDataFrame th:nth-child(1), .stDataFrame td:nth-child(1) {
        width: 15% !important;
        max-width: 15% !important;
    }
    .stDataFrame th:nth-child(2), .stDataFrame td:nth-child(2) {
        width: 20% !important;
        max-width: 20% !important;
    }
    .stDataFrame th:nth-child(3), .stDataFrame td:nth-child(3) {
        width: 65% !important;
        max-width: 65% !important;
    }
    /* Supprimer complètement les lignes vides */
    .empty-row {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Liste des sections et champs pour le tableau
    sections = [
        # ... (le reste de la définition des sections reste inchangé)
    ]

    # Construire le DataFrame sans lignes vides
    data = []
    for section in sections:
        # Ajouter la section seulement (pas de ligne vide après)
        data.append([section["title"], "", ""])
        for field_name, field_key, placeholder in section["fields"]:
            value = st.session_state.get(field_key, "")
            data.append(["", field_name, value])

    df = pd.DataFrame(data, columns=["Section", "Détails", "Informations"])

    # Afficher le data_editor stylé avec des colonnes réduites
    edited_df = st.data_editor(
        df,
        column_config={
            "Section": st.column_config.TextColumn("Section", disabled=True, width="small"),
            "Détails": st.column_config.TextColumn("Détails", disabled=True, width="small"),
            "Informations": st.column_config.TextColumn("Informations", width="large")
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed"
    )
    
    # ... (le reste du code reste inchangé)

    # Boutons Enregistrer et Pré-rédiger par IA
    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("💾 Enregistrer modifications", type="primary", use_container_width=True, key="save_avant_brief"):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                brief_name = st.session_state.current_brief_name
                brief_data = {
                    "raison_ouverture": edited_df["Informations"].iloc[1],
                    "impact_strategique": edited_df["Informations"].iloc[2],
                    "taches_principales": edited_df["Informations"].iloc[3],
                    "must_have_experience": edited_df["Informations"].iloc[5],
                    "must_have_diplomes": edited_df["Informations"].iloc[6],
                    "must_have_competences": edited_df["Informations"].iloc[7],
                    "must_have_softskills": edited_df["Informations"].iloc[8],
                    "nice_to_have_experience": edited_df["Informations"].iloc[10],
                    "nice_to_have_diplomes": edited_df["Informations"].iloc[11],
                    "nice_to_have_competences": edited_df["Informations"].iloc[12],
                    "entreprises_profil": edited_df["Informations"].iloc[14],
                    "synonymes_poste": edited_df["Informations"].iloc[15],
                    "canaux_profil": edited_df["Informations"].iloc[16],
                    "rattachement": edited_df["Informations"].iloc[18],
                    "budget": edited_df["Informations"].iloc[19],
                    "profil_link_1": edited_df["Informations"].iloc[21],
                    "profil_link_2": edited_df["Informations"].iloc[22],
                    "profil_link_3": edited_df["Informations"].iloc[23],
                    "commentaires": edited_df["Informations"].iloc[25],
                    "notes_libres": edited_df["Informations"].iloc[26]
                }
                st.session_state.saved_briefs[brief_name].update(brief_data)
                save_briefs()
                st.session_state.avant_brief_completed = True
                st.session_state.save_message = "✅ Modifications sauvegardées"
                st.rerun()
            else:
                st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
    
    with col_reset:
        if st.button("💡 Pré-rédiger par IA", type="secondary", use_container_width=True, key="pre_rediger_ia"):
            poste = st.session_state.get("poste_intitule", "")
            if poste:
                library = st.session_state.job_library
                matching_job = next((job for job in library if job['title'].lower() == poste.lower()), None)
                if matching_job:
                    fiche_data = (
                        f"Title: {matching_job['title']}\n"
                        f"Finalite: {matching_job.get('finalite', '')}\n"
                        f"Activites: {matching_job.get('activites', '')}\n"
                        f"Experience: {matching_job.get('experience_globale', '')}\n"
                        f"Niveau diplome: {matching_job.get('niveau_diplome', '')}\n"
                        f"Competences: {matching_job.get('competences', '')}"
                    )
                    try:
                        ai_output = get_ai_pre_redaction(fiche_data)
                        
                        # Parse
                        lines = ai_output.split("\n")
                        mission_globale_ai = ""
                        taches_ai = ""
                        must_have_ai = ""
                        nice_to_have_ai = ""
                        
                        current_section = None
                        for line in lines:
                            if "- Mission globale:" in line:
                                current_section = "mission"
                                mission_globale_ai = line.split(":", 1)[1].strip()
                            elif "- Tâches principales:" in line:
                                current_section = "taches"
                            elif "- Must have:" in line:
                                current_section = "must"
                            elif "- Nice to have:" in line:
                                current_section = "nice"
                            elif line.startswith("- ") and current_section:
                                if current_section == "taches":
                                    taches_ai += line + "\n"
                                elif current_section == "must":
                                    must_have_ai += line + "\n"
                                elif current_section == "nice":
                                    nice_to_have_ai += line + "\n"
                        
                        st.session_state.impact_strategique = mission_globale_ai
                        st.session_state.taches_principales = taches_ai.strip()
                        st.session_state.must_have_experience = must_have_ai.strip()
                        st.session_state.must_have_diplomes = must_have_ai.strip()
                        st.session_state.must_have_competences = must_have_ai.strip()
                        st.session_state.nice_to_have_experience = nice_to_have_ai.strip()
                        st.session_state.nice_to_have_diplomes = nice_to_have_ai.strip()
                        st.session_state.nice_to_have_competences = nice_to_have_ai.strip()
                        
                        st.session_state.save_message = "✅ Pré-rédaction AI appliquée (synthèse courte)"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur AI: {e}")
                else:
                    st.warning("⚠️ Aucune fiche de poste trouvée pour ce titre")
            else:
                st.warning("⚠️ Veuillez d'abord entrer le poste à recruter")

# ---------------- RÉUNION ----------------
with tabs[2]:
    # Afficher les informations du brief en cours
    st.subheader(f"✅ Réunion de brief avec le Manager - {st.session_state.get('poste_intitule', '')}")

    total_steps = 5
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation")

        # Construire le DataFrame avec les données du brief actuel
        data = []
        field_keys = []
        comment_keys = []
        k = 1
        
        # Récupérer les données du brief actuel
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_data = st.session_state.saved_briefs[st.session_state.current_brief_name]
            
            for section in sections:
                data.append([section["title"], "", "", ""])
                for field_name, field_key, placeholder in section["fields"]:
                    value = brief_data.get(field_key, "")
                    data.append(["", field_name, value, ""])
                    field_keys.append(field_key)
                    comment_keys.append(f"manager_comment_{k}")
                    k += 1

        df = pd.DataFrame(data, columns=["Section", "Détails", "Informations", "Commentaires du manager"])

        # Afficher le data_editor stylé
        edited_df = st.data_editor(
            df,
            column_config={
                "Section": st.column_config.TextColumn("Section", disabled=True),
                "Détails": st.column_config.TextColumn("Détails", disabled=True),
                "Informations": st.column_config.TextColumn("Informations", width="medium", disabled=True),
                "Commentaires du manager": st.column_config.TextColumn("Commentaires du manager", width="medium")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        # Sauvegarde des commentaires
        if st.button("💾 Sauvegarder commentaires", type="primary", key="save_comments_step1"):
            section_index = 0
            for i in range(len(edited_df)):
                if edited_df["Section"].iloc[i] != "":
                    section_index += 1
                else:
                    comment_key = comment_keys[i - section_index]
                    st.session_state[comment_key] = edited_df["Commentaires du manager"].iloc[i]
            st.session_state.save_message = "✅ Commentaires sauvegardés"
            st.rerun()

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
                if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                    brief_name = st.session_state.current_brief_name
                    
                    # Récupérer tous les commentaires du manager
                    manager_comments = {}
                    for i in range(1, 21):
                        comment_key = f"manager_comment_{i}"
                        if comment_key in st.session_state:
                            manager_comments[comment_key] = st.session_state[comment_key]
                    
                    # Charger les briefs existants depuis le fichier
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
    # Vérification si l'onglet est accessible
    if not can_access_synthese:
        st.warning("⚠️ Veuillez d'abord compléter et sauvegarder l'onglet Réunion de brief")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.subheader(f"📝 Synthèse du Brief - {st.session_state.get('poste_intitule', '')}")
    
    if "current_brief_name" in st.session_state:
        st.success(f"Brief actuel: {st.session_state.current_brief_name}")
    
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("poste_intitule", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Type": st.session_state.get("brief_type", ""),
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
            if "current_brief_name" in st.session_state:
                save_briefs()
                st.session_state.save_message = f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !"
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
            if "current_brief_name" in st.session_state:
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
            if "current_brief_name" in st.session_state:
                word_buf = export_brief_word()
                if word_buf:
                    st.download_button("⬇️ Télécharger Word", data=word_buf,
                                     file_name=f"{st.session_state.current_brief_name}.docx",
                                     mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            else:
                st.info("ℹ️ Créez d'abord un brief pour l'exporter")
        else:
            st.info("⚠️ Word non dispo (pip install python-docx)")

# ---------------- ONGLET BIBLIOTHÈQUE (toujours accessible, recherche, buttons modifier/supprimer, modification dans mêmes cases) ----------------
with tabs[4]:
    st.header("📚 Bibliothèque des fiches de poste")
    
    library = st.session_state.job_library
    
    # Recherche (par nom, date) - Liste n'apparaît que si recherche effectuée
    col_search1, col_search2 = st.columns(2)
    with col_search1:
        search_name = st.text_input("Rechercher par nom du poste")
    with col_search2:
        search_date = st.date_input("Date de création", value=None)
    
    filtered_library = []
    if search_name or search_date:
        filtered_library = library
        if search_name:
            filtered_library = [j for j in filtered_library if search_name.lower() in j.get("title", "").lower()]
        if search_date:
            filtered_library = [j for j in filtered_library if j.get("date_creation") and datetime.strptime(j["date_creation"], "%Y-%m-%d %H:%M:%S").date() == search_date]
    
    # Affichage seulement si recherche faite
    if filtered_library:
        # Afficher les résultats de recherche
        for i, job in enumerate(filtered_library):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{job['title']}** - {job.get('date_creation', '')}")
            with col2:
                if st.button("Modifier", key=f"modify_job_{i}"):
                    st.session_state.editing_job = job['title']
                    st.rerun()
            with col3:
                if st.button("Supprimer", key=f"delete_job_{i}"):
                    # Trouver l'index du job à supprimer
                    index_to_delete = next((idx for idx, j in enumerate(library) if j['title'] == job['title']), None)
                    if index_to_delete is not None:
                        del library[index_to_delete]
                        save_library(library)
                        st.session_state.job_library = library
                        st.session_state.save_message = f"✅ Fiche de poste '{job['title']}' supprimée"
                        st.rerun()
    else:
        if not search_name and not search_date:
            st.info("Effectuez une recherche pour voir les fiches.")
        else:
            st.info("Aucune fiche trouvée.")
    
    # Formulaire pour ajouter ou modifier (mêmes cases, avec vérif unique)
    editing = 'editing_job' in st.session_state
    job_data = next((j for j in library if j['title'] == st.session_state.editing_job), {}) if editing else {}
    
    with st.form("job_form"):
        title = st.text_input("Intitulé du poste", value=job_data.get('title', ''))
        finalite = st.text_area("Finalité du poste", value=job_data.get('finalite', ''))
        activites = st.text_area("Activités principales", value=job_data.get('activites', ''))
        n1_hierarchique = st.text_input("N+1 hiérarchique", value=job_data.get('n1_hierarchique', ''))
        n1_fonctionnel = st.text_input("N+1 fonctionnel", value=job_data.get('n1_fonctionnel', ''))
        entite_rattachement = st.text_input("Entité de rattachement", value=job_data.get('entite_rattachement', ''))
        indicateurs = st.text_area("Indicateurs clés de performance", value=job_data.get('indicateurs', ''))
        interne = st.text_area("Interlocuteurs internes", value=job_data.get('interne', ''))
        supervision_directe = st.text_input("Supervision directe", value=job_data.get('supervision_directe', ''))
        externe = st.text_area("Interlocuteurs externes", value=job_data.get('externe', ''))
        supervision_indirecte = st.text_input("Supervision indirecte", value=job_data.get('supervision_indirecte', ''))
        niveau_diplome = st.text_input("Niveau de diplôme", value=job_data.get('niveau_diplome', ''))
        experience_globale = st.text_input("Expérience globale", value=job_data.get('experience_globale', ''))
        competences = st.text_area("Compétences requises", value=job_data.get('competences', ''))
        
        if st.form_submit_button("💾 Sauvegarder"):
            # Vérif intitulé unique
            if any(j["title"].lower() == title.lower() for j in library if not (editing and j["title"] == job_data.get("title", ""))):
                st.error("Une fiche avec cet intitulé existe déjà.")
            else:
                new_job = {
                    'title': title,
                    'finalite': finalite,
                    'activites': activites,
                    'n1_hierarchique': n1_hierarchique,
                    'n1_fonctionnel': n1_fonctionnel,
                    'entite_rattachement': entite_rattachement,
                    'indicateurs': indicateurs,
                    'interne': interne,
                    'supervision_directe': supervision_directe,
                    'externe': externe,
                    'supervision_indirecte': supervision_indirecte,
                    'niveau_diplome': niveau_diplome,
                    'experience_globale': experience_globale,
                    'competences': competences,
                    "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if editing:
                    # Mettre à jour la fiche existante
                    index_to_update = next((idx for idx, j in enumerate(library) if j['title'] == st.session_state.editing_job), None)
                    if index_to_update is not None:
                        library[index_to_update] = new_job
                    del st.session_state.editing_job
                    st.session_state.save_message = f"✅ Fiche de poste '{title}' modifiée avec succès"
                else:
                    library.append(new_job)
                    st.session_state.save_message = f"✅ Fiche de poste '{title}' créée avec succès"
                save_library(library)
                st.session_state.job_library = library
                st.rerun()

# JavaScript pour désactiver les onglets non accessibles (Bibliothèque exclue)
st.markdown(f"""
<script>
// Désactiver les onglets selon les permissions
const tabs = parent.document.querySelectorAll('[data-baseweb="tab"]');
if (!{str(can_access_avant_brief).lower()}) {{
    tabs[1].classList.add('disabled-tab');
}}
if (!{str(can_access_reunion).lower()}) {{
    tabs[2].classList.add('disabled-tab');
}}
if (!{str(can_access_synthese).lower()}) {{
    tabs[3].classList.add('disabled-tab');
}}
// Bibliothèque (tabs[4]) toujours accessible
</script>
""", unsafe_allow_html=True)