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
  
# Style CSS moderne pour les onglets personnalisés et les tableaux améliorés
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
    
    /* NOUVEAU STYLE POUR LE TABLEAU MODERNE */
    .modern-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-bottom: 20px;
        background-color: #0d1117;
        font-size: 0.95em;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(255, 75, 75, 0.1);
        border: 2px solid rgba(255, 75, 75, 0.2);
    }

    .modern-table th, .modern-table td {
        padding: 16px 20px;
        text-align: left;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: #e6edf3;
        position: relative;
    }

    .modern-table th {
        background: linear-gradient(135deg, #FF4B4B 0%, #FF6B6B 100%);
        color: white !important;
        font-weight: 700;
        font-size: 17px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        border-bottom: 3px solid rgba(255, 255, 255, 0.2);
    }

    /* Effet de dégradé subtil sur les lignes */
    .modern-table tbody tr:nth-child(odd) {
        background: linear-gradient(90deg, #0d1117 0%, #161b22 100%);
    }

    .modern-table tbody tr:nth-child(even) {
        background: linear-gradient(90deg, #161b22 0%, #21262d 100%);
    }

    /* Effet de survol moderne */
    .modern-table tbody tr:hover {
        background: linear-gradient(90deg, #1c2128 0%, #2d333b 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255, 75, 75, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Largeur des colonnes avec nouvelle répartition */
    .modern-table th:nth-child(1),
    .modern-table td:nth-child(1) {
        width: 18%;
        font-weight: 600;
        color: #58a6ff;
    }

    .modern-table th:nth-child(2),
    .modern-table td:nth-child(2) {
        width: 22%;
        font-weight: 500;
    }

    .modern-table th:nth-child(3),
    .modern-table td:nth-child(3) {
        width: 60%;
        line-height: 1.6;
    }

    /* Style pour les tableaux avec 4 colonnes */
    .modern-table.four-columns th:nth-child(1),
    .modern-table.four-columns td:nth-child(1) {
        width: 16%;
    }

    .modern-table.four-columns th:nth-child(2),
    .modern-table.four-columns td:nth-child(2) {
        width: 20%;
    }

    .modern-table.four-columns th:nth-child(3),
    .modern-table.four-columns td:nth-child(3) {
        width: 36%;
    }

    .modern-table.four-columns th:nth-child(4),
    .modern-table.four-columns td:nth-child(4) {
        width: 28%;
    }

    /* Style pour les titres de section */
    .modern-section-title {
        font-weight: 700;
        color: #58a6ff;
        font-size: 1em;
        text-shadow: 0 1px 2px rgba(88, 166, 255, 0.3);
    }

    /* Style moderne pour les textareas dans les tableaux */
    .modern-table-textarea {
        width: 100%;
        min-height: 70px;
        background: linear-gradient(135deg, #1c2128 0%, #2d333b 100%);
        color: white;
        border: 2px solid rgba(88, 166, 255, 0.3);
        border-radius: 8px;
        padding: 12px;
        font-size: 0.95em;
        resize: vertical;
        white-space: pre-wrap;
        transition: all 0.3s ease;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }

    .modern-table-textarea:focus {
        border-color: #FF4B4B;
        box-shadow: 0 0 0 3px rgba(255, 75, 75, 0.1);
        background: linear-gradient(135deg, #2d333b 0%, #3e4451 100%);
        outline: none;
    }

    /* Style pour les cellules de texte avec meilleure lisibilité */
    .modern-table-text {
        padding: 12px;
        font-size: 0.95em;
        color: #e6edf3;
        white-space: pre-wrap;
        line-height: 1.7;
        font-weight: 400;
    }

    /* Indicateurs visuels pour les cellules importantes */
    .modern-table td:first-child::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #FF4B4B 0%, #58a6ff 100%);
        border-radius: 0 2px 2px 0;
    }

    /* Animation douce pour les changements */
    .modern-table td {
        transition: all 0.2s ease;
    }

    /* Style pour les en-têtes avec icônes */
    .modern-table th::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 20px;
        right: 20px;
        height: 2px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 1px;
    }

    /* Style responsive pour les petits écrans */
    @media (max-width: 768px) {
        .modern-table {
            font-size: 0.85em;
        }
        
        .modern-table th,
        .modern-table td {
            padding: 12px 16px;
        }
        
        .modern-table th {
            font-size: 15px;
        }
    }

    /* Style pour le data_editor Streamlit avec le nouveau design */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(255, 75, 75, 0.1);
        border: 2px solid rgba(255, 75, 75, 0.2);
    }

    .stDataFrame th {
        background: linear-gradient(135deg, #FF4B4B 0%, #FF6B6B 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 17px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
        padding: 16px 20px !important;
        border-bottom: 3px solid rgba(255, 255, 255, 0.2) !important;
    }

    .stDataFrame td {
        padding: 16px 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: linear-gradient(90deg, #0d1117 0%, #161b22 100%);
        transition: all 0.2s ease;
    }

    .stDataFrame tr:hover td {
        background: linear-gradient(90deg, #1c2128 0%, #2d333b 100%);
    }

    /* Style pour les cellules éditables amélioré */
    .stDataFrame td textarea {
        background: linear-gradient(135deg, #1c2128 0%, #2d333b 100%) !important;
        color: white !important;
        border: 2px solid rgba(88, 166, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 12px !important;
        min-height: 70px !important;
        resize: vertical !important;
        white-space: pre-wrap !important;
        transition: all 0.3s ease !important;
        font-family: 'Segoe UI', system-ui, sans-serif !important;
    }

    .stDataFrame td textarea:focus {
        border-color: #FF4B4B !important;
        box-shadow: 0 0 0 3px rgba(255, 75, 75, 0.1) !important;
        background: linear-gradient(135deg, #2d333b 0%, #3e4451 100%) !important;
        outline: none !important;
    }
    
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
                                st.session_state.saved_briefs = all_briefs
                                save_briefs()
                                if name in st.session_state.filtered_briefs:
                                    del st.session_state.filtered_briefs[name]
                                st.warning(f"❌ Brief '{name}' supprimé.")
                                st.rerun()
  
# JavaScript pour synchroniser les radio buttons avec le formulaire
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const radios = document.querySelectorAll('input[name="brief_type"]');
    radios.forEach(radio => {
        radio.addEventListener('change', function() {
            // Synchroniser avec Streamlit si nécessaire
        });
    });
});
</script>
""", unsafe_allow_html=True)

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord sauvegarder un brief dans l'onglet 'Gestion' pour accéder à cette section.")
        st.stop()
    
    st.header("🔄 Avant-brief - Préparation")
    
    # Affichage du tableau moderne avec les données du brief
    if st.session_state.current_brief_name:
        loaded_brief = st.session_state.get("loaded_brief", {})
        
        # Génération du tableau HTML moderne
        table_html = f"""
        <table class="modern-table">
            <thead>
                <tr>
                    <th>Section</th>
                    <th>Critère</th>
                    <th>Informations</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="modern-section-title">Informations générales</td>
                    <td>Manager</td>
                    <td class="modern-table-text">{loaded_brief.get('manager_nom', st.session_state.get('manager_nom', 'N/A'))}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Informations générales</td>
                    <td>Poste</td>
                    <td class="modern-table-text">{loaded_brief.get('niveau_hierarchique', st.session_state.get('niveau_hierarchique', 'N/A'))}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Informations générales</td>
                    <td>Affectation</td>
                    <td class="modern-table-text">{loaded_brief.get('affectation_type', st.session_state.get('affectation_type', 'N/A'))} - {loaded_brief.get('affectation_nom', st.session_state.get('affectation_nom', 'N/A'))}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Informations générales</td>
                    <td>Recruteur</td>
                    <td class="modern-table-text">{loaded_brief.get('recruteur', st.session_state.get('recruteur', 'N/A'))}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Informations générales</td>
                    <td>Date</td>
                    <td class="modern-table-text">{loaded_brief.get('date_brief', st.session_state.get('date_brief', 'N/A'))}</td>
                </tr>
            </tbody>
        </table>
        """
        
        st.markdown(table_html, unsafe_allow_html=True)
    
    # Formulaires pour saisie avec conseils IA
    conseil_button("Raison d'ouverture du poste", "contexte", "Décrivez pourquoi ce poste est ouvert", "raison_ouverture")
    conseil_button("Impact stratégique", "strategie", "Expliquez l'impact stratégique de ce recrutement", "impact_strategique")
    conseil_button("Rattachement hiérarchique", "organisation", "Précisez le rattachement hiérarchique", "rattachement")
    conseil_button("Tâches principales", "missions", "Listez les principales missions et responsabilités", "taches_principales")
    
    # Bouton pour valider l'avant-brief
    if st.button("✅ Valider l'avant-brief", type="primary", use_container_width=True):
        st.session_state.avant_brief_completed = True
        st.success("✅ Avant-brief validé ! Vous pouvez maintenant accéder à la réunion de brief.")
        st.rerun()

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter l'avant-brief pour accéder à cette section.")
        st.stop()
    
    st.header("✅ Réunion de brief")
    
    # Formulaires avec conseils IA organisés en étapes
    if st.session_state.reunion_step == 1:
        st.subheader("Étape 1/3 : Profil Must-Have")
        conseil_button("Expérience Must-Have", "experience", "Expérience obligatoire requise", "must_have_experience")
        conseil_button("Diplômes Must-Have", "formation", "Formation obligatoire requise", "must_have_diplomes")
        conseil_button("Compétences Must-Have", "competences", "Compétences techniques obligatoires", "must_have_competences")
        conseil_button("Soft Skills Must-Have", "softskills", "Qualités humaines obligatoires", "must_have_softskills")
        
        if st.button("➡️ Étape suivante", type="primary"):
            st.session_state.reunion_step = 2
            st.rerun()
            
    elif st.session_state.reunion_step == 2:
        st.subheader("Étape 2/3 : Profil Nice-to-Have")
        conseil_button("Expérience Nice-to-Have", "experience", "Expérience souhaitable", "nice_to_have_experience")
        conseil_button("Diplômes Nice-to-Have", "formation", "Formation souhaitable", "nice_to_have_diplomes")
        conseil_button("Compétences Nice-to-Have", "competences", "Compétences techniques souhaitables", "nice_to_have_competences")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Étape précédente", type="secondary"):
                st.session_state.reunion_step = 1
                st.rerun()
        with col2:
            if st.button("➡️ Étape suivante", type="primary"):
                st.session_state.reunion_step = 3
                st.rerun()
                
    elif st.session_state.reunion_step == 3:
        st.subheader("Étape 3/3 : Sourcing et Finalisation")
        conseil_button("Entreprises cibles", "sourcing", "Types d'entreprises à cibler", "entreprises_profil")
        conseil_button("Canaux de diffusion", "canaux", "Où publier l'offre", "canaux_profil")
        conseil_button("Synonymes du poste", "mots_cles", "Mots-clés alternatifs", "synonymes_poste")
        
        st.text_area("Budget/Rémunération", key="budget")
        st.text_area("Commentaires du manager", key="commentaires")
        st.text_area("Notes libres", key="notes_libres")
        
        # Matrice KSA
        render_ksa_matrix()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Étape précédente", type="secondary"):
                st.session_state.reunion_step = 2
                st.rerun()
        with col2:
            if st.button("✅ Finaliser la réunion", type="primary"):
                st.session_state.reunion_completed = True
                st.success("✅ Réunion de brief finalisée ! Vous pouvez maintenant accéder à la synthèse.")
                st.rerun()

# ---------------- ONGLET SYNTHÈSE ----------------
with tabs[3]:
    if not can_access_synthese:
        st.warning("⚠️ Veuillez d'abord finaliser la réunion de brief pour accéder à cette section.")
        st.stop()
    
    st.header("📝 Synthèse du brief")
    
    # Affichage de la synthèse complète avec le nouveau tableau moderne
    if st.session_state.current_brief_name:
        
        # Tableau moderne pour la synthèse complète
        synthese_html = f"""
        <table class="modern-table four-columns">
            <thead>
                <tr>
                    <th>Section</th>
                    <th>Critère</th>
                    <th>Informations</th>
                    <th>Commentaires Manager</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="modern-section-title">Contexte</td>
                    <td>Raison d'ouverture</td>
                    <td class="modern-table-text">{st.session_state.get('raison_ouverture', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Contexte</td>
                    <td>Impact stratégique</td>
                    <td class="modern-table-text">{st.session_state.get('impact_strategique', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Organisation</td>
                    <td>Rattachement</td>
                    <td class="modern-table-text">{st.session_state.get('rattachement', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Missions</td>
                    <td>Tâches principales</td>
                    <td class="modern-table-text">{st.session_state.get('taches_principales', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Must-Have</td>
                    <td>Expérience</td>
                    <td class="modern-table-text">{st.session_state.get('must_have_experience', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Must-Have</td>
                    <td>Formation</td>
                    <td class="modern-table-text">{st.session_state.get('must_have_diplomes', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Must-Have</td>
                    <td>Compétences</td>
                    <td class="modern-table-text">{st.session_state.get('must_have_competences', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Must-Have</td>
                    <td>Soft Skills</td>
                    <td class="modern-table-text">{st.session_state.get('must_have_softskills', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Nice-to-Have</td>
                    <td>Expérience</td>
                    <td class="modern-table-text">{st.session_state.get('nice_to_have_experience', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Nice-to-Have</td>
                    <td>Formation</td>
                    <td class="modern-table-text">{st.session_state.get('nice_to_have_diplomes', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Nice-to-Have</td>
                    <td>Compétences</td>
                    <td class="modern-table-text">{st.session_state.get('nice_to_have_competences', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Sourcing</td>
                    <td>Entreprises cibles</td>
                    <td class="modern-table-text">{st.session_state.get('entreprises_profil', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Sourcing</td>
                    <td>Canaux</td>
                    <td class="modern-table-text">{st.session_state.get('canaux_profil', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="modern-section-title">Rémunération</td>
                    <td>Budget</td>
                    <td class="modern-table-text">{st.session_state.get('budget', 'N/A')}</td>
                    <td class="modern-table-text">{st.session_state.get('commentaires', 'N/A')}</td>
                </tr>
            </tbody>
        </table>
        """
        
        st.markdown(synthese_html, unsafe_allow_html=True)
    
    # Boutons d'export et actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if PDF_AVAILABLE and st.button("📄 Exporter en PDF", type="primary"):
            try:
                export_brief_pdf(st.session_state.current_brief_name)
                st.success("✅ Brief exporté en PDF avec succès !")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'export PDF: {str(e)}")
    
    with col2:
        if WORD_AVAILABLE and st.button("📝 Exporter en Word", type="primary"):
            try:
                export_brief_word(st.session_state.current_brief_name)
                st.success("✅ Brief exporté en Word avec succès !")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'export Word: {str(e)}")
    
    with col3:
        if st.button("🗑️ Supprimer ce brief", type="secondary"):
            delete_current_brief()