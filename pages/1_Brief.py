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
def render_interactive_brief_table(brief_data, tab_key, is_editable=True):
    """
    Affiche un tableau interactif pour les données du brief.
    Permet l'édition si is_editable est True.
    """
    # Créer un DataFrame à partir des données structurées pour un affichage en tableau
    df_data = [
        {"Catégorie": "Informations de poste", "Critère": "Raison de l'ouverture", "Description": brief_data.get("raison_ouverture", "")},
        {"Catégorie": "Informations de poste", "Critère": "Impact stratégique", "Description": brief_data.get("impact_strategique", "")},
        {"Catégorie": "Informations de poste", "Critère": "Rattachement", "Description": brief_data.get("rattachement", "")},
        {"Catégorie": "Informations de poste", "Critère": "Tâches principales", "Description": brief_data.get("taches_principales", "")},
        {"Catégorie": "Profil Must-Have", "Critère": "Expérience", "Description": brief_data.get("must_have_experience", "")},
        {"Catégorie": "Profil Must-Have", "Critère": "Diplômes & Certifications", "Description": brief_data.get("must_have_diplomes", "")},
        {"Catégorie": "Profil Must-Have", "Critère": "Compétences techniques", "Description": brief_data.get("must_have_competences", "")},
        {"Catégorie": "Profil Must-Have", "Critère": "Soft Skills", "Description": brief_data.get("must_have_softskills", "")},
        {"Catégorie": "Profil Nice-to-Have", "Critère": "Expérience", "Description": brief_data.get("nice_to_have_experience", "")},
        {"Catégorie": "Profil Nice-to-Have", "Critère": "Diplômes & Certifications", "Description": brief_data.get("nice_to_have_diplomes", "")},
        {"Catégorie": "Profil Nice-to-Have", "Critère": "Compétences techniques", "Description": brief_data.get("nice_to_have_competences", "")},
        {"Catégorie": "Sources & Marché", "Critère": "Entreprises et profils cibles", "Description": brief_data.get("entreprises_profil", "")},
        {"Catégorie": "Sources & Marché", "Critère": "Synonymes de poste", "Description": brief_data.get("synonymes_poste", "")},
        {"Catégorie": "Sources & Marché", "Critère": "Canaux de sourcing", "Description": brief_data.get("canaux_profil", "")},
        {"Catégorie": "Informations complémentaires", "Critère": "Budget", "Description": brief_data.get("budget", "")},
        {"Catégorie": "Informations complémentaires", "Critère": "Notes libres", "Description": brief_data.get("notes_libres", "")},
        {"Catégorie": "Informations complémentaires", "Critère": "Commentaires du manager", "Description": brief_data.get("commentaires", "")},
    ]

    df = pd.DataFrame(df_data)

    if is_editable:
        edited_df = st.data_editor(
            df,
            column_config={
                "Catégorie": st.column_config.TextColumn(
                    "Catégorie", disabled=True
                ),
                "Critère": st.column_config.TextColumn(
                    "Critère", disabled=True
                ),
                "Description": st.column_config.TextColumn(
                    "Description", help="Ajoutez vos informations ici"
                )
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key=f"brief_data_editor_{tab_key}"
        )
        return edited_df
    else:
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Catégorie": st.column_config.TextColumn("Catégorie"),
                "Critère": st.column_config.TextColumn("Critère"),
                "Description": st.column_config.TextColumn("Description")
            }
        )
        return df

def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau interactif et stylisé"""
    st.subheader("📊 Matrice KSA (Knowledge, Skills, Abilities)")
    
    # Initialiser les données KSA si elles n'existent pas
    if "ksa_matrix" not in st.session_state or st.session_state.ksa_matrix.empty:
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
            new_score = st.slider("Importance", 1, 5, 3, key="new_score")
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
                st.session_state.ksa_matrix = pd.concat([st.session_state.ksa_matrix, pd.DataFrame([new_row])], ignore_index=True)
                st.success("✅ Critère ajouté avec succès")
                st.rerun()

    if not st.session_state.ksa_matrix.empty:
        edited_df = st.data_editor(
            st.session_state.ksa_matrix,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rubrique": st.column_config.TextColumn("Rubrique", disabled=True),
                "Critère": st.column_config.TextColumn("Critère"),
                "Cible / Standard attendu": st.column_config.TextColumn("Cible / Standard attendu"),
                "Échelle d'évaluation (1-5)": st.column_config.NumberColumn(
                    "Importance (1-5)", format="%d", min_value=1, max_value=5
                ),
                "Évaluateur": st.column_config.TextColumn("Évaluateur"),
            }
        )
        st.session_state.ksa_matrix = edited_df

        if "Échelle d'évaluation (1-5)" in st.session_state.ksa_matrix.columns and not st.session_state.ksa_matrix.empty:
            scores = pd.to_numeric(st.session_state.ksa_matrix["Échelle d'évaluation (1-5)"], errors='coerce').dropna()
            if not scores.empty:
                moyenne = scores.mean()
                st.metric("Note globale", f"{moyenne:.1f}/5")
            else:
                st.info("Aucune note pour le moment.")
        
        if st.button("🗑️ Supprimer le dernier critère", type="secondary", key="delete_last_criteria"):
            if not st.session_state.ksa_matrix.empty:
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
            
            keys_to_reset = [
                "manager_nom", "niveau_hierarchique", "affectation_type", 
                "recruteur", "affectation_nom", "date_brief", "raison_ouverture",
                "impact_strategique", "rattachement", "taches_principales",
                "must_have_experience", "must_have_diplomes", "must_have_competences",
                "must_have_softskills", "nice_to_have_experience", "nice_to_have_diplomes",
                "nice_to_have_competences", "entreprises_profil", "synonymes_poste",
                "canaux_profil", "budget", "commentaires", "notes_libres",
                "ksa_matrix", "avant_brief_data", "reunion_data"
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
    st.session_state.avant_brief_completed = False

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = False

if "avant_brief_data" not in st.session_state:
    st.session_state.avant_brief_data = {}

if "reunion_data" not in st.session_state:
    st.session_state.reunion_data = {}

# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques Brief")
    
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
    .stDataFrame {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #0d1117; /* Fond noir pour le tableau */
        font-size: 0.9em; /* Augmentation de la taille du texte */
        border: 1px solid #ffffff; /* Bordure blanche */
    }
    
    .stDataFrame th, .stDataFrame td {
        padding: 12px 16px;
        text-align: left;
        border: 1px solid #ffffff; /* Bordures blanches */
        color: #e6edf3; /* Texte clair sur fond sombre */
    }
    
    .stDataFrame th {
        background-color: #FF4B4B !important; /* Rouge vif pour les en-têtes */
        color: white !important;
        font-weight: 600;
        padding: 14px 16px;
        font-size: 16px;
        border: 1px solid #ffffff; /* Bordure blanche */
    }
    
    /* Largeur des colonnes pour le tableau data_editor */
    .stDataFrame th:nth-child(1),
    .stDataFrame td:nth-child(1) {
        width: 15%; /* Réduction de la première colonne (Catégorie) */
    }
    
    .stDataFrame th:nth-child(2),
    .stDataFrame td:nth-child(2) {
        width: 20%; /* Réduction de la deuxième colonne (Critère) */
    }
    
    .stDataFrame th:nth-child(3),
    .stDataFrame td:nth-child(3) {
        width: 65%; /* Colonne Description plus large */
    }
    
    .section-title {
        font-weight: 600;
        color: #58a6ff; /* Couleur bleue pour les titres de section */
        font-size: 0.95em; /* Augmentation de la taille du texte */
    }
    
    /* Style pour les cellules éditables (Description) */
    .stDataFrame textarea {
        background-color: #2D2D2D !important;
        color: white !important;
        border: 1px solid #555 !important;
        border-radius: 4px !important;
        padding: 6px !important;
        min-height: 60px !important;
        resize: vertical !important;
        white-space: pre-wrap !important; /* Permet les retours à la ligne */
    }
    </style>
""", unsafe_allow_html=True)

# Vérification si un brief est chargé au début de l'application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse"
])

can_access_avant_brief = st.session_state.current_brief_name != ""
can_access_reunion = can_access_avant_brief and st.session_state.avant_brief_completed
can_access_synthese = can_access_reunion and st.session_state.reunion_completed

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
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
    
    col_title_left, col_title_right = st.columns([2, 1])
    with col_title_left:
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
    
    if "gestion_brief_type" not in st.session_state:
        st.session_state.gestion_brief_type = "Brief"
    
    brief_type = st.radio("", ["Brief", "Canevas"], key="gestion_brief_type", horizontal=True, label_visibility="collapsed")
    
    if st.session_state.gestion_brief_type != st.session_state.get("brief_type", "Brief"):
        st.session_state.brief_type = st.session_state.gestion_brief_type
    
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
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
        
        if st.button("💾 Sauvegarder", type="primary", use_container_width=True, key="save_gestion"):
            if not all([st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                
                existing_briefs = load_briefs()
                if "saved_briefs" not in st.session_state:
                    st.session_state.saved_briefs = existing_briefs
                else:
                    st.session_state.saved_briefs.update(existing_briefs)
                
                st.session_state.saved_briefs[brief_name] = {
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "date_brief": str(st.session_state.date_brief),
                    "niveau_hierarchique": st.session_state.niveau_hierarchique,
                    "brief_type": st.session_state.gestion_brief_type,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "avant_brief_data": st.session_state.get("avant_brief_data", {}),
                    "reunion_data": st.session_state.get("reunion_data", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict('records')
                }
                save_briefs()
                st.success(f"✅ {st.session_state.gestion_brief_type} '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name
                st.session_state.avant_brief_completed = False
                st.session_state.reunion_completed = False

    with col_side:
        col1, col2, col3 = st.columns(3)
        with col1:
            months = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            month = st.selectbox("Mois", months, key="search_month")
        with col2:
            brief_type_filter = st.selectbox("Type", ["", "Brief", "Canevas"], key="brief_type_filter")
        with col3:
            recruteur = st.selectbox("Recruteur", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="search_recruteur")
        
        col4, col5, col6 = st.columns(3)
        with col4:
            manager = st.text_input("Manager", key="search_manager")
        with col5:
            affectation = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="search_affectation")
        with col6:
            nom_affectation = st.text_input("Nom de l'affectation", key="search_nom_affectation")

        if st.button("🔎 Rechercher", type="primary", use_container_width=True, key="search_button"):
            briefs = load_briefs()
            st.session_state.filtered_briefs = {}
            
            for name, data in briefs.items():
                if month and month != "":
                    brief_date = data.get("date_brief", "")
                    if not (brief_date and brief_date.split("-")[1] == month):
                        continue
                if brief_type_filter and brief_type_filter != "" and data.get("brief_type") != brief_type_filter:
                    continue
                if recruteur and recruteur != "" and data.get("recruteur") != recruteur:
                    continue
                if manager and manager != "" and manager.lower() not in data.get("manager_nom", "").lower():
                    continue
                if affectation and affectation != "" and data.get("affectation_type") != affectation:
                    continue
                if nom_affectation and nom_affectation != "" and nom_affectation.lower() not in data.get("affectation_nom", "").lower():
                    continue
                
                st.session_state.filtered_briefs[name] = data
            
            if st.session_state.filtered_briefs:
                st.info(f"ℹ️ {len(st.session_state.filtered_briefs)} résultats trouvés.")
            else:
                st.error("❌ Aucun brief trouvé avec ces critères.")

        if st.session_state.filtered_briefs:
            st.markdown("<h4 style='margin-bottom: 0.5rem;'>Résultats de recherche</h4>", unsafe_allow_html=True)
            
            for name, data in st.session_state.filtered_briefs.items():
                with st.expander(f"📌 {name}", expanded=False):
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
                                loaded_brief = load_briefs().get(name, {})
                                if loaded_brief:
                                    # Mettre à jour les champs de l'onglet Gestion
                                    for key in ["manager_nom", "niveau_hierarchique", "affectation_type", "recruteur", "affectation_nom", "date_brief"]:
                                        if key in loaded_brief:
                                            st.session_state[key] = loaded_brief[key]

                                    # Mettre à jour les données des tableaux
                                    st.session_state.avant_brief_data = loaded_brief.get("avant_brief_data", {})
                                    st.session_state.reunion_data = loaded_brief.get("reunion_data", {})
                                    
                                    # Mettre à jour la matrice KSA
                                    if "ksa_matrix" in loaded_brief and loaded_brief["ksa_matrix"]:
                                        st.session_state.ksa_matrix = pd.DataFrame(loaded_brief["ksa_matrix"])
                                    else:
                                        st.session_state.ksa_matrix = pd.DataFrame() # Réinitialiser si vide

                                    st.session_state.current_brief_name = name
                                    st.session_state.avant_brief_completed = True
                                    st.session_state.reunion_completed = loaded_brief.get("reunion_data", {}) != {}
                                    
                                    st.success(f"✅ Brief '{name}' chargé avec succès!")
                                    st.rerun()
                                else:
                                    st.error("❌ Brief non trouvé.")
                            except Exception as e:
                                st.error(f"❌ Erreur lors du chargement: {str(e)}")
                    with colB:
                        if st.button(f"🗑️ Supprimer", key=f"del_{name}"):
                            all_briefs = load_briefs()
                            if name in all_briefs:
                                del all_briefs[name]
                                with open("briefs.json", "w") as f:
                                    json.dump(all_briefs, f)
                                if name in st.session_state.filtered_briefs:
                                    del st.session_state.filtered_briefs[name]
                                st.warning(f"❌ Brief '{name}' supprimé.")
                                st.rerun()

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet 'Gestion'.")
    else:
        st.header("🔄 Avant-brief")
        st.markdown("Complétez ce tableau avant la réunion de brief pour optimiser l'échange.")
        
        # Affiche le tableau interactif
        edited_df = render_interactive_brief_table(st.session_state.avant_brief_data, "avant_brief")
        
        # Capture les modifications du tableau et les stocke
        if not edited_df.empty:
            for index, row in edited_df.iterrows():
                critere = row["Critère"]
                description = row["Description"]
                
                # Mapping des critères aux clés de session state
                if critere == "Raison de l'ouverture":
                    st.session_state.avant_brief_data["raison_ouverture"] = description
                elif critere == "Impact stratégique":
                    st.session_state.avant_brief_data["impact_strategique"] = description
                elif critere == "Rattachement":
                    st.session_state.avant_brief_data["rattachement"] = description
                elif critere == "Tâches principales":
                    st.session_state.avant_brief_data["taches_principales"] = description
                elif critere == "Expérience":
                    st.session_state.avant_brief_data["must_have_experience"] = description
                elif critere == "Diplômes & Certifications":
                    st.session_state.avant_brief_data["must_have_diplomes"] = description
                elif critere == "Compétences techniques":
                    st.session_state.avant_brief_data["must_have_competences"] = description
                elif critere == "Soft Skills":
                    st.session_state.avant_brief_data["must_have_softskills"] = description
                elif critere == "Expérience" and row["Catégorie"] == "Profil Nice-to-Have":
                    st.session_state.avant_brief_data["nice_to_have_experience"] = description
                elif critere == "Diplômes & Certifications" and row["Catégorie"] == "Profil Nice-to-Have":
                    st.session_state.avant_brief_data["nice_to_have_diplomes"] = description
                elif critere == "Compétences techniques" and row["Catégorie"] == "Profil Nice-to-Have":
                    st.session_state.avant_brief_data["nice_to_have_competences"] = description
                elif critere == "Entreprises et profils cibles":
                    st.session_state.avant_brief_data["entreprises_profil"] = description
                elif critere == "Synonymes de poste":
                    st.session_state.avant_brief_data["synonymes_poste"] = description
                elif critere == "Canaux de sourcing":
                    st.session_state.avant_brief_data["canaux_profil"] = description
                elif critere == "Budget":
                    st.session_state.avant_brief_data["budget"] = description
                elif critere == "Notes libres":
                    st.session_state.avant_brief_data["notes_libres"] = description
                elif critere == "Commentaires du manager":
                    st.session_state.avant_brief_data["commentaires"] = description

        st.markdown("---")
        col_buttons = st.columns([1, 1, 1, 1])
        with col_buttons[0]:
            if st.button("Sauvegarder", type="primary"):
                st.session_state.avant_brief_completed = True
                st.success("✅ Données Avant-brief sauvegardées ! Vous pouvez passer à l'étape suivante.")
                st.rerun()
        with col_buttons[3]:
            if st.button("Générer conseil IA", type="secondary"):
                st.info("Fonctionnalité non implémentée.")

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter l'onglet 'Avant-brief' et le sauvegarder.")
    else:
        st.header("✅ Réunion de brief")
        st.markdown("Saisissez les informations obtenues directement avec le manager.")
        
        # Initialise le dictionnaire de réunion avec les données de l'avant-brief
        if st.session_state.reunion_data == {}:
            st.session_state.reunion_data = st.session_state.avant_brief_data
        
        # Affiche le tableau de l'onglet Réunion
        edited_df = render_interactive_brief_table(st.session_state.reunion_data, "reunion_brief")
        
        # Met à jour les données de la session avec les modifications du tableau
        if not edited_df.empty:
            for index, row in edited_df.iterrows():
                critere = row["Critère"]
                description = row["Description"]

                # Mapping des critères aux clés de session state pour les données de réunion
                if critere == "Raison de l'ouverture":
                    st.session_state.reunion_data["raison_ouverture"] = description
                # ... et ainsi de suite pour tous les critères

        st.markdown("---")
        st.subheader("💡 Critères KSA (Knowledge, Skills, Abilities)")
        render_ksa_matrix()
        
        st.markdown("---")
        col_buttons = st.columns([1, 1, 1, 1])
        with col_buttons[0]:
            if st.button("Sauvegarder", type="primary", key="save_reunion_button"):
                st.session_state.reunion_completed = True
                st.success("✅ Brief de réunion sauvegardé ! Vous pouvez passer à l'étape suivante.")
                st.rerun()
        with col_buttons[3]:
            if st.button("Générer synthèse", type="secondary", key="generer_synthese_button"):
                st.info("Fonctionnalité non implémentée.")
        
# ---------------- ONGLET SYNTHÈSE ----------------
with tabs[3]:
    if not can_access_synthese:
        st.warning("⚠️ Veuillez d'abord compléter l'onglet 'Réunion de brief' et le sauvegarder.")
    else:
        st.header("📝 Synthèse du brief")
        
        if st.button("🗑️ Supprimer le brief actuel", type="secondary"):
            delete_current_brief()
        
        if st.session_state.get("current_brief_name"):
            st.markdown(f"**Brief actuel :** {st.session_state.current_brief_name}")
            
            # Afficher les informations de base
            st.subheader("Informations de base")
            st.write(f"**Manager :** {st.session_state.get('manager_nom', 'N/A')}")
            st.write(f"**Recruteur :** {st.session_state.get('recruteur', 'N/A')}")
            st.write(f"**Poste :** {st.session_state.get('niveau_hierarchique', 'N/A')}")
            st.write(f"**Date :** {st.session_state.get('date_brief', 'N/A')}")
            
            # Afficher le tableau de la réunion de brief
            st.subheader("Détails de la réunion de brief")
            render_interactive_brief_table(st.session_state.reunion_data, "synthese", is_editable=False)
            
            # Afficher la matrice KSA
            st.subheader("Matrice KSA")
            if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
                st.dataframe(st.session_state.ksa_matrix, hide_index=True, use_container_width=True)
            else:
                st.info("Aucune matrice KSA disponible.")
                
            # Boutons d'exportation
            st.markdown("---")
            st.subheader("Exportations")
            col_export = st.columns(2)
            
            if WORD_AVAILABLE:
                with col_export[0]:
                    if st.button("Exporter au format Word", use_container_width=True):
                        st.info("Fonctionnalité d'exportation Word non implémentée.")
                        # export_brief_word(st.session_state.brief_data, st.session_state.ksa_data)
            
            if PDF_AVAILABLE:
                with col_export[1]:
                    if st.button("Exporter au format PDF", use_container_width=True):
                        st.info("Fonctionnalité d'exportation PDF non implémentée.")
                        # export_brief_pdf(st.session_state.brief_data, st.session_state.ksa_data)