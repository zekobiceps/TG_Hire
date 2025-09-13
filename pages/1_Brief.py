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
    
    /* Largeur des colonnes */
    .dark-table th:nth-child(1),
    .dark-table td:nth-child(1) {
        width: 15%; /* Réduction de la première colonne */
    }
    
    .dark-table th:nth-child(2),
    .dark-table td:nth-child(2) {
        width: 20%;
    }
    
    .dark-table th:nth-child(3),
    .dark-table td:nth-child(3) {
        width: 65%; /* Colonne Informations plus large */
    }
    
    /* Style pour les tableaux avec 4 colonnes (réunion de brief) */
    .dark-table.four-columns th:nth-child(1),
    .dark-table.four-columns td:nth-child(1) {
        width: 15%;
    }
    
    .dark-table.four-columns th:nth-child(2),
    .dark-table.four-columns td:nth-child(2) {
        width: 20%;
    }
    
    .dark-table.four-columns th:nth-child(3),
    .dark-table.four-columns td:nth-child(3) {
        width: 40%; /* Réduit pour faire de la place à la colonne notes */
    }
    
    .dark-table.four-columns th:nth-child(4),
    .dark-table.four-columns td:nth-child(4) {
        width: 25%; /* Colonne Commentaires du manager élargie */
    }
    
    .section-title {
        font-weight: 600;
        color: #58a6ff; /* Couleur bleue pour les titres de section */
        font-size: 0.95em; /* Augmentation de la taille du texte */
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
        width: 15%;
    }
    
    .stDataFrame td:nth-child(2) {
        width: 20%;
    }
    
    .stDataFrame td:nth-child(3) {
        width: 65%;
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
    </style>
""", unsafe_allow_html=True)

# Vérification si un brief est chargé au début de l'application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

# Création des onglets avec gestion des accès
tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse"
])

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
    /* Style compact pour les radio buttons */
    .custom-radio {
        display: flex;
        background-color: #262730;
        padding: 3px;
        border-radius: 5px;
        border: 1px solid #424242;
        margin-left: 10px;
    }
    .custom-radio input[type="radio"] {
        display: none;
    }
    .custom-radio label {
        padding: 3px 8px;
        cursor: pointer;
        border-radius: 3px;
        margin: 0 3px;
        font-size: 0.9em;
    }
    .custom-radio input[type="radio"]:checked + label {
        background-color: #FF4B4B;
        color: white;
    }
    /* Cacher le radio button Streamlit */
    div[data-testid="stRadio"] > div {
        display: none;
    }
    /* Réduire l'espace entre les colonnes */
    .st-emotion-cache-5rimss p {
        margin-bottom: 0.3rem;
    }
    /* Style pour le titre compact */
    .compact-title {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # En-tête avec les titres alignés - VERSION COMPACTE
    col_title_left, col_title_right = st.columns([2, 1])
    with col_title_left:
        # Titre "Informations de base" avec le type à droite - VERSION COMPACTE
        st.markdown("""
        <div class="compact-title">
            <h3 style="margin: 0; margin-right: 10px;">Informations de base</h3>
            <div style="display: flex; align-items: center;">
                <span style="margin-right: 5px; font-size: 0.9em;">Type:</span>
                <div class="custom-radio">
                    <input type="radio" id="brief" name="brief_type" value="Brief" checked>
                    <label for="brief">Brief</label>
                    <input type="radio" id="template" name="brief_type" value="Canevas">
                    <label for="template">Canevas</label>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_title_right:
        st.markdown("<h3 style='margin-bottom: 0.5rem;'>Recherche & Chargement</h3>", unsafe_allow_html=True)
    
    # Radio button Streamlit caché pour la fonctionnalité
    # Utilisation d'une clé différente pour éviter l'erreur de session state
    if "gestion_brief_type" not in st.session_state:
        st.session_state.gestion_brief_type = "Brief"
    
    brief_type = st.radio("", ["Brief", "Canevas"], key="gestion_brief_type", horizontal=True, label_visibility="collapsed")
    
    # Synchronisation avec la variable principale
    if st.session_state.gestion_brief_type != st.session_state.get("brief_type", "Brief"):
        st.session_state.brief_type = st.session_state.gestion_brief_type
    
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Nom du manager *", key="manager_nom")
        with col2:
            st.text_input("Poste à recruter", key="niveau_hierarchique")
        with col3:
            st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type")
        
        col4, col5, col6 = st.columns(3)
        with col4:
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
        with col5:
            st.text_input("Nom de l'affectation", key="affectation_nom")
        with col6:
            st.date_input("Date du Brief *", key="date_brief", value=datetime.today().date())
        
        # --- SAUVEGARDE - Bouton étendu
        if st.button("💾 Sauvegarder", type="primary", use_container_width=True, key="save_gestion"):
            if not all([st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                
                # Charger les briefs existants depuis le fichier
                existing_briefs = load_briefs()
                if "saved_briefs" not in st.session_state:
                    st.session_state.saved_briefs = existing_briefs
                else:
                    # Mettre à jour avec les briefs existants
                    st.session_state.saved_briefs.update(existing_briefs)
                
                # Créer ou mettre à jour le brief
                st.session_state.saved_briefs[brief_name] = {
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "date_brief": str(st.session_state.date_brief),
                    "niveau_hierarchique": st.session_state.niveau_hierarchique,
                    "brief_type": st.session_state.gestion_brief_type,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                    "impact_strategique": st.session_state.get("impact_strategique", ""),
                    "rattachement": st.session_state.get("rattachement", ""),
                    "taches_principales": st.session_state.get("taches_principales", ""),
                    "must_have_experience": st.session_state.get("must_have_experience", ""),
                    "must_have_diplomes": st.session_state.get("must_have_diplomes", ""),
                    "must_have_competences": st.session_state.get("must_have_competences", ""),
                    "must_have_softskills": st.session_state.get("must_have_softskills", ""),
                    "nice_to_have_experience": st.session_state.get("nice_to_have_experience", ""),
                    "nice_to_have_diplomes": st.session_state.get("nice_to_have_diplomes", ""),
                    "nice_to_have_competences": st.session_state.get("nice_to_have_competences", ""),
                    "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                    "canaux_profil": st.session_state.get("canaux_profil", ""),
                    "synonymes_poste": st.session_state.get("synonymes_poste", ""),
                    "budget": st.session_state.get("budget", ""),
                    "commentaires": st.session_state.get("commentaires", ""),
                    "notes_libres": st.session_state.get("notes_libres", ""),
                    "profil_links": st.session_state.get("profil_links", ["", "", ""]),
                    "ksa_data": st.session_state.get("ksa_data", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict() if hasattr(st.session_state, 'ksa_matrix') else {}
                }
                save_briefs()
                st.success(f"✅ {st.session_state.gestion_brief_type} '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name
                st.session_state.avant_brief_completed = False
                st.session_state.reunion_completed = False

    with col_side:
        # --- RECHERCHE & CHARGEMENT (6 cases organisées en 2 lignes de 3)
        # Première ligne
        col1, col2, col3 = st.columns(3)
        with col1:
            months = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            month = st.selectbox("Mois", months, key="search_month")
        with col2:
            brief_type_filter = st.selectbox("Type", ["", "Brief", "Canevas"], key="brief_type_filter")
        with col3:
            recruteur = st.selectbox("Recruteur", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="search_recruteur")
        
        # Deuxième ligne
        col4, col5, col6 = st.columns(3)
        with col4:
            manager = st.text_input("Manager", key="search_manager")
        with col5:
            affectation = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="search_affectation")
        with col6:
            nom_affectation = st.text_input("Nom de l'affectation", key="search_nom_affectation")

        # Bouton Rechercher en rouge vif
        if st.button("🔎 Rechercher", type="primary", use_container_width=True, key="search_button"):
            briefs = load_briefs()
            st.session_state.filtered_briefs = {}
            
            for name, data in briefs.items():
                # Filtrage par mois
                if month and month != "":
                    brief_date = data.get("date_brief", "")
                    if not (brief_date and brief_date.split("-")[1] == month):
                        continue
                
                # Filtrage par type
                if brief_type_filter and brief_type_filter != "" and data.get("brief_type") != brief_type_filter:
                    continue
                
                # Filtrage par recruteur
                if recruteur and recruteur != "" and data.get("recruteur") != recruteur:
                    continue
                
                # Filtrage par manager
                if manager and manager != "" and manager.lower() not in data.get("manager_nom", "").lower():
                    continue
                
                # Filtrage par affectation
                if affectation and affectation != "" and data.get("affectation_type") != affectation:
                    continue
                
                # Filtrage par nom d'affectation
                if nom_affectation and nom_affectation != "" and nom_affectation.lower() not in data.get("affectation_nom", "").lower():
                    continue
                
                st.session_state.filtered_briefs[name] = data
            
            if st.session_state.filtered_briefs:
                st.info(f"ℹ️ {len(st.session_state.filtered_briefs)} résultats trouvés.")
            else:
                st.error("❌ Aucun brief trouvé avec ces critères.")

        if st.session_state.filtered_briefs:
            st.markdown("<h4 style='margin-bottom: 0.5rem;'>Résultats de recherche</h4>", unsafe_allow_html=True)
            
            # Afficher les résultats avec des expanders
            for name, data in st.session_state.filtered_briefs.items():
                with st.expander(f"📌 {name}", expanded=False):
                    # Utiliser deux colonnes pour afficher les informations
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.markdown(f"""
                        **Type:** {data.get('brief_type', 'N/A')}  
                        **Manager:** {data.get('manager_nom', 'N/A')}  
                        **Recruteur:** {data.get('recruteur', 'N/A')}
                        """)
                    
                    with col_right:
                        st.markdown(f"""
                        **Affectation:** {data.get('affectation_type', 'N/A')}  
                        **Date:** {data.get('date_brief', 'N/A')}  
                        **Nom de l'affectation:** {data.get('affectation_nom', 'N/A')}
                        """)
                    
                    colA, colB = st.columns(2)
                    with colA:
                        if st.button(f"📂 Charger", key=f"load_{name}"):
                            try:
                                # Créer un nouveau brief sans écraser les widgets
                                new_brief = {}
                                
                                # Copier toutes les données du brief
                                for key, value in data.items():
                                    new_brief[key] = value
                                
                                # Stocker le brief chargé dans une clé spéciale
                                st.session_state.loaded_brief = new_brief
                                st.session_state.current_brief_name = name
                                
                                # Mettre à jour uniquement les champs non-widgets
                                non_widget_keys = ["raison_ouverture", "impact_strategique", "rattachement", 
                                                    "taches_principales", "must_have_experience", "must_have_diplomes",
                                                    "must_have_competences", "must_have_softskills", "nice_to_have_experience",
                                                    "nice_to_have_diplomes", "nice_to_have_competences", "entreprises_profil", 
                                                    "canaux_profil", "synonymes_poste", "budget", "commentaires", 
                                                    "notes_libres", "profil_links"]
                                
                                for key in non_widget_keys:
                                    if key in data:
                                        st.session_state[key] = data[key]
                                
                                # Mettre à jour le type de brief avec la clé de gestion
                                if "brief_type" in data:
                                    st.session_state.gestion_brief_type = data["brief_type"]
                                
                                # Gestion spéciale pour les données KSA
                                if "ksa_data" in data:
                                    st.session_state.ksa_data = data["ksa_data"]
                                
                                # Gestion spéciale pour la matrice KSA
                                if "ksa_matrix" in data and data["ksa_matrix"]:
                                    st.session_state.ksa_matrix = pd.DataFrame(data["ksa_matrix"])
                                
                                st.success(f"✅ Brief '{name}' chargé avec succès!")
                                st.session_state.avant_brief_completed = True
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ Erreur lors du chargement: {str(e)}")
                    with colB:
                        if st.button(f"🗑️ Supprimer", key=f"del_{name}"):
                            all_briefs = load_briefs()
                            if name in all_briefs:
                                del all_briefs[name]
                                st.session_state.saved_briefs = existing_briefs
                                save_briefs()
                                if name in st.session_state.filtered_briefs:
                                    del st.session_state.filtered_briefs[name]
                                st.warning(f"❌ Brief '{name}' supprimé.")
                                st.rerun()

# JavaScript pour synchroniser les radio buttons personnalisés avec Streamlit
st.markdown("""
<script>
// Synchroniser les radio buttons personnalisés avec Streamlit
document.querySelectorAll('.custom-radio input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', function() {
        // Mettre à jour la valeur dans Streamlit
        const value = this.value;
        const streamlitRadio = parent.document.querySelector('input[type="radio"][value="' + value + '"]');
        if (streamlitRadio) {
            streamlitRadio.click();
        }
    });
});

// Synchroniser l'état initial
document.addEventListener('DOMContentLoaded', function() {
    const briefType = window.parent.document.querySelector('[data-testid="stRadio"] input[name="brief_type_hidden_radio"]:checked');
    if (briefType) {
        const customRadio = document.querySelector('.custom-radio input[value="' + briefType.value + '"]');
        if (customRadio) {
            customRadio.checked = true;
        }
    }
});
</script>
""", unsafe_allow_html=True)

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    # Vérifier l'accès
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet 'Gestion'.")
    else:
        st.header("🔄 Avant-brief")
        st.info("💡 Utilisez cet espace pour préparer la réunion de brief. L'IA peut vous aider à générer des questions.")
        
        # Bouton pour générer des conseils IA
        if st.button("🤖 Générer des conseils IA", key="generate_avant_brief_advice"):
            st.session_state.raison_ouverture = generate_checklist_advice("avant_brief", "raison_ouverture")
            st.session_state.impact_strategique = generate_checklist_advice("avant_brief", "impact_strategique")
            st.session_state.rattachement = generate_checklist_advice("avant_brief", "rattachement")
            st.session_state.taches_principales = generate_checklist_advice("avant_brief", "taches_principales")
            st.rerun()
            
        st.subheader("❓ Ce qu'il faut préparer avant le brief")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Raison de l'ouverture du poste", key="raison_ouverture", height=150)
        with col2:
            st.text_area("Impact stratégique de l'embauche", key="impact_strategique", height=150)
            
        st.text_area("Rattachement hiérarchique et fonctionnel", key="rattachement", height=150)
        st.text_area("Tâches et missions principales", key="taches_principales", height=150)
        
        st.markdown("---")
        
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            # Bouton pour passer à l'étape suivante
            if st.button("Continuer vers la Réunion de brief", type="primary", use_container_width=True, key="go_to_reunion"):
                st.session_state.avant_brief_completed = True
                st.session_state.brief_phase = "✅ Réunion de brief"
                st.rerun()
        with col_end2:
            # Bouton pour sauvegarder l'avant-brief
            if st.button("💾 Sauvegarder l'avant-brief", type="secondary", use_container_width=True, key="save_avant_brief"):
                if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
                    brief_name = st.session_state.current_brief_name
                    st.session_state.saved_briefs[brief_name]["raison_ouverture"] = st.session_state.get("raison_ouverture", "")
                    st.session_state.saved_briefs[brief_name]["impact_strategique"] = st.session_state.get("impact_strategique", "")
                    st.session_state.saved_briefs[brief_name]["rattachement"] = st.session_state.get("rattachement", "")
                    st.session_state.saved_briefs[brief_name]["taches_principales"] = st.session_state.get("taches_principales", "")
                    save_briefs()
                    st.success("✅ Avant-brief sauvegardé avec succès.")
                else:
                    st.error("❌ Aucun brief n'est actuellement chargé.")

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter l'onglet 'Avant-brief'.")
    else:
        st.header("✅ Réunion de brief")
        st.info(f"Brief en cours: **{st.session_state.current_brief_name}**")
        st.info(f"Étape en cours: **{st.session_state.reunion_step}/3**")
        
        if st.session_state.reunion_step == 1:
            st.subheader("1. Connaissances et savoir-faire (MUST-HAVE)")
            st.text_area("Expérience requise", key="must_have_experience")
            st.text_area("Diplômes et certifications", key="must_have_diplomes")
            st.text_area("Compétences techniques (Hard Skills)", key="must_have_competences")
            st.text_area("Compétences comportementales (Soft Skills)", key="must_have_softskills")
            
            if st.button("Continuer", key="step1_continue"):
                st.session_state.reunion_step = 2
                st.rerun()
        
        elif st.session_state.reunion_step == 2:
            st.subheader("2. Savoir-être et autres critères (NICE-TO-HAVE)")
            st.text_area("Expérience appréciée", key="nice_to_have_experience")
            st.text_area("Diplômes et certifications appréciées", key="nice_to_have_diplomes")
            st.text_area("Compétences supplémentaires", key="nice_to_have_competences")
            
            st.subheader("3. Budget et Sourcing")
            st.text_input("Budget (fourchette salariale)", key="budget")
            st.text_area("Synonymes de poste", key="synonymes_poste")
            st.text_area("Entreprises cibles ou type de profil", key="entreprises_profil")
            st.text_area("Canaux de sourcing", key="canaux_profil")
            
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                if st.button("Précédent", key="step2_previous"):
                    st.session_state.reunion_step = 1
                    st.rerun()
            with col_nav2:
                if st.button("Continuer", key="step2_continue"):
                    st.session_state.reunion_step = 3
                    st.rerun()

        elif st.session_state.reunion_step == 3:
            st.subheader("4. Matrice KSA (Knowledge, Skills, Abilities)")
            render_ksa_matrix()
            
            st.subheader("5. Notes libres et liens")
            st.text_area("Notes libres", key="notes_libres")
            st.text_input("Lien 1 (LinkedIn, etc.)", key="link1")
            st.text_input("Lien 2", key="link2")
            st.text_input("Lien 3", key="link3")
            
            col_end1, col_end2 = st.columns(2)
            with col_end1:
                if st.button("Précédent", key="step3_previous"):
                    st.session_state.reunion_step = 2
                    st.rerun()
            with col_end2:
                if st.button("Finaliser le brief", type="primary", use_container_width=True, key="finalize_brief"):
                    st.session_state.reunion_completed = True
                    
                    # Sauvegarder les données du brief
                    brief_name = st.session_state.current_brief_name
                    if brief_name:
                        brief_data = st.session_state.saved_briefs.get(brief_name, {})
                        brief_data.update({
                            "must_have_experience": st.session_state.get("must_have_experience", ""),
                            "must_have_diplomes": st.session_state.get("must_have_diplomes", ""),
                            "must_have_competences": st.session_state.get("must_have_competences", ""),
                            "must_have_softskills": st.session_state.get("must_have_softskills", ""),
                            "nice_to_have_experience": st.session_state.get("nice_to_have_experience", ""),
                            "nice_to_have_diplomes": st.session_state.get("nice_to_have_diplomes", ""),
                            "nice_to_have_competences": st.session_state.get("nice_to_have_competences", ""),
                            "budget": st.session_state.get("budget", ""),
                            "synonymes_poste": st.session_state.get("synonymes_poste", ""),
                            "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                            "canaux_profil": st.session_state.get("canaux_profil", ""),
                            "notes_libres": st.session_state.get("notes_libres", ""),
                            "profil_links": [st.session_state.get("link1", ""), st.session_state.get("link2", ""), st.session_state.get("link3", "")],
                            "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict('list') if hasattr(st.session_state, 'ksa_matrix') else {}
                        })
                        st.session_state.saved_briefs[brief_name] = brief_data
                        save_briefs()
                    
                    st.success("✅ Brief finalisé et sauvegardé avec succès ! Vous pouvez consulter la synthèse.")
                    st.session_state.brief_phase = "📝 Synthèse"
                    st.rerun()
                    
# ---------------- ONGLET SYNTHÈSE ----------------
with tabs[3]:
    if not can_access_synthese:
        st.warning("⚠️ Veuillez d'abord finaliser le brief dans l'onglet 'Réunion de brief'.")
    else:
        st.header("📝 Synthèse du brief")
        st.info(f"Brief en cours: **{st.session_state.current_brief_name}**")
        
        current_brief = st.session_state.get("saved_briefs", {}).get(st.session_state.current_brief_name, {})
        
        if not current_brief:
            st.error("❌ Erreur : Le brief en cours n'a pas pu être chargé.")
        else:
            # Afficher la synthèse
            st.subheader("Informations principales")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Manager:** {current_brief.get('manager_nom', 'N/A')}")
                st.markdown(f"**Recruteur:** {current_brief.get('recruteur', 'N/A')}")
            with col2:
                st.markdown(f"**Poste:** {current_brief.get('niveau_hierarchique', 'N/A')}")
                st.markdown(f"**Affectation:** {current_brief.get('affectation_nom', 'N/A')}")
            with col3:
                st.markdown(f"**Date:** {current_brief.get('date_brief', 'N/A')}")
                st.markdown(f"**Type:** {current_brief.get('brief_type', 'N/A')}")

            st.markdown("---")
            
            st.subheader("Détails")
            st.markdown(f"**Raison de l'ouverture:** {current_brief.get('raison_ouverture', 'N/A')}")
            st.markdown(f"**Impact stratégique:** {current_brief.get('impact_strategique', 'N/A')}")
            st.markdown(f"**Rattachement:** {current_brief.get('rattachement', 'N/A')}")
            st.markdown(f"**Tâches principales:** {current_brief.get('taches_principales', 'N/A')}")
            st.markdown(f"**Budget:** {current_brief.get('budget', 'N/A')}")
            
            st.markdown("---")
            
            st.subheader("Profil recherché")
            st.markdown(f"**Expérience (MUST-HAVE):** {current_brief.get('must_have_experience', 'N/A')}")
            st.markdown(f"**Diplômes (MUST-HAVE):** {current_brief.get('must_have_diplomes', 'N/A')}")
            st.markdown(f"**Compétences (MUST-HAVE):** {current_brief.get('must_have_competences', 'N/A')}")
            st.markdown(f"**Soft Skills (MUST-HAVE):** {current_brief.get('must_have_softskills', 'N/A')}")
            st.markdown(f"**Expérience (NICE-TO-HAVE):** {current_brief.get('nice_to_have_experience', 'N/A')}")
            st.markdown(f"**Diplômes (NICE-TO-HAVE):** {current_brief.get('nice_to_have_diplomes', 'N/A')}")
            st.markdown(f"**Compétences (NICE-TO-HAVE):** {current_brief.get('nice_to_have_competences', 'N/A')}")
            
            st.markdown("---")
            
            st.subheader("Matrice KSA")
            if current_brief.get("ksa_matrix"):
                df_ksa = pd.DataFrame(current_brief["ksa_matrix"])
                st.dataframe(df_ksa, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune matrice KSA n'a été complétée.")
                
            st.markdown("---")
            
            st.subheader("Export")
            col_export_pdf, col_export_word, col_delete = st.columns(3)
            with col_export_pdf:
                if st.button("Exporter en PDF", disabled=not PDF_AVAILABLE, use_container_width=True, key="export_pdf"):
                    st.info("Création du PDF...")
                    try:
                        pdf_path = export_brief_pdf(current_brief)
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="Télécharger le PDF",
                                data=f,
                                file_name=f"{st.session_state.current_brief_name}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        st.success("✅ PDF créé avec succès.")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la création du PDF: {str(e)}")
            with col_export_word:
                if st.button("Exporter en Word", disabled=not WORD_AVAILABLE, use_container_width=True, key="export_word"):
                    st.info("Création du document Word...")
                    try:
                        word_path = export_brief_word(current_brief)
                        with open(word_path, "rb") as f:
                            st.download_button(
                                label="Télécharger le document Word",
                                data=f,
                                file_name=f"{st.session_state.current_brief_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )
                        st.success("✅ Document Word créé avec succès.")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la création du document Word: {str(e)}")
            
            with col_delete:
                if st.button("🗑️ Supprimer le brief", type="secondary", use_container_width=True, key="delete_brief_final"):
                    delete_current_brief()