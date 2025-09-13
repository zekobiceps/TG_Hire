import sys, os
import streamlit as st
from datetime import datetime
import json
import pandas as pd
import base64

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
def get_table_download_link_html(df, filename, text):
    """Génère un lien HTML pour télécharger un DataFrame en tant que fichier CSV."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def render_styled_brief_table(brief_data, tab_key, is_editable=True):
    """
    Affiche un tableau stylisé pour les données du brief, avec une ligne d'en-tête rouge vif.
    """
    # Données du tableau structurées par catégorie
    table_structure = {
        "Informations de poste": [
            "Raison de l'ouverture", "Impact stratégique", "Rattachement", "Tâches principales"
        ],
        "Profil Must-Have": [
            "Expérience", "Diplômes & Certifications", "Compétences techniques", "Soft Skills"
        ],
        "Profil Nice-to-Have": [
            "Expérience", "Diplômes & Certifications", "Compétences techniques"
        ],
        "Sources & Marché": [
            "Entreprises et profils cibles", "Synonymes de poste", "Canaux de sourcing"
        ],
        "Informations complémentaires": [
            "Budget", "Notes libres", "Commentaires du manager"
        ]
    }

    st.markdown("""
        <style>
        .red-header {
            background-color: #FF4B4B;
            color: white;
            padding: 12px;
            font-weight: bold;
            font-size: 1.1em;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            text-align: center;
        }
        .table-row {
            display: flex;
            border-bottom: 1px solid #424242;
            padding: 8px 0;
        }
        .table-row:last-child {
            border-bottom: none;
        }
        .table-cell {
            padding: 8px;
            overflow-wrap: break-word;
            word-wrap: break-word;
            hyphens: auto;
        }
        .table-category {
            font-weight: bold;
            color: #ff4b4b;
        }
        .category-header {
            background-color: #262730;
            padding: 8px;
            font-weight: bold;
            margin-top: 10px;
            border-radius: 4px;
        }
        .stTextArea textarea {
            background-color: #2D2D2D !important;
            color: white !important;
            border: 1px solid #555 !important;
            border-radius: 4px !important;
            padding: 6px !important;
            min-height: 100px !important;
            resize: vertical !important;
        }
        .stMarkdown p {
            margin: 0;
            padding: 0;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1: st.markdown("<div class='red-header' style='border-top-right-radius: 0;'>Catégorie</div>", unsafe_allow_html=True)
    with col2: st.markdown("<div class='red-header' style='border-radius: 0;'>Critère</div>", unsafe_allow_html=True)
    with col3: st.markdown("<div class='red-header' style='border-top-left-radius: 0;'>Description</div>", unsafe_allow_html=True)
    
    for category, criteria in table_structure.items():
        st.markdown(f"<div class='category-header'>{category}</div>", unsafe_allow_html=True)
        for i, criterion in enumerate(criteria):
            mapping_key = f"{category}_{criterion}"
            current_value = brief_data.get(mapping_key, "")

            col_cat, col_crit, col_desc = st.columns([1, 1, 3])
            
            with col_cat:
                if i == 0:
                    st.markdown(f"<p class='table-category'>{category}</p>", unsafe_allow_html=True)
            with col_crit:
                st.markdown(f"<p>{criterion}</p>", unsafe_allow_html=True)
            with col_desc:
                if is_editable:
                    new_value = st.text_area(label="", value=current_value, key=f"{tab_key}_{mapping_key}", label_visibility="collapsed")
                    brief_data[mapping_key] = new_value
                else:
                    st.markdown(f"<p>{current_value}</p>", unsafe_allow_html=True)
    return brief_data

def render_ksa_matrix():
    """Affiche la matrice KSA sous forme de tableau interactif et stylisé"""
    st.subheader("📊 Matrice KSA (Knowledge, Skills, Abilities)")
    
    if "ksa_matrix" not in st.session_state or st.session_state.ksa_matrix.empty:
        st.session_state.ksa_matrix = pd.DataFrame(columns=[
            "Rubrique", "Critère", "Cible / Standard attendu", 
            "Échelle d'évaluation (1-5)", "Évaluateur"
        ])

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
                "recruteur", "affectation_nom", "date_brief", 
                "avant_brief_data", "reunion_data", "ksa_matrix"
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

if "avant_brief_step" not in st.session_state:
    st.session_state.avant_brief_step = 1

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
                           if b.get("ksa_matrix") and len(b.get("ksa_matrix")) > 0)
    
    st.metric("📋 Briefs créés", total_briefs)
    st.metric("✅ Briefs complétés", completed_briefs)
    
    st.divider()
    st.info("💡 Assistant IA pour la création et gestion de briefs de recrutement")

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("🤖 TG-Hire IA - Brief")

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
    
    /* Style pour les messages d'alerte */
    .stAlert {
        padding: 10px;
        margin-top: 10px;
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
    .compact-title {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col_title_left, col_title_right = st.columns([2, 1])
    with col_title_left:
        st.markdown("<h3 style='margin: 0; margin-right: 10px;'>Informations de base</h3>", unsafe_allow_html=True)
    with col_title_right:
        st.markdown("<h3 style='margin-bottom: 0.5rem;'>Recherche & Chargement</h3>", unsafe_allow_html=True)
    
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
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "avant_brief_data": st.session_state.get("avant_brief_data", {}),
                    "reunion_data": st.session_state.get("reunion_data", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict('records')
                }
                save_briefs()
                st.success(f"✅ Brief '{brief_name}' sauvegardé avec succès !")
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
            st.session_state.filtered_briefs = filter_briefs(briefs, month, brief_type_filter, recruteur, manager, affectation, nom_affectation)
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
                                    st.session_state.avant_brief_completed = loaded_brief.get("avant_brief_data", {}) != {}
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
        
        # Affiche le wizard
        if "avant_brief_step" not in st.session_state:
            st.session_state.avant_brief_step = 1

        if st.session_state.avant_brief_step == 1:
            st.subheader("Informations de poste")
            st.text_area("Raison de l'ouverture", key="raison_ouverture")
            st.text_area("Impact stratégique", key="impact_strategique")
            st.text_area("Rattachement", key="rattachement")
            st.text_area("Tâches principales", key="taches_principales")
            
            st.markdown("---")
            if st.button("Étape suivante", use_container_width=True, type="primary", key="next_step_avant_brief"):
                st.session_state.avant_brief_step = 2
                st.rerun()

        elif st.session_state.avant_brief_step == 2:
            st.subheader("Profil Must-Have")
            st.text_area("Expérience", key="must_have_experience")
            st.text_area("Diplômes & Certifications", key="must_have_diplomes")
            st.text_area("Compétences techniques", key="must_have_competences")
            st.text_area("Soft Skills", key="must_have_softskills")

            st.markdown("---")
            cols = st.columns([1, 1, 1])
            with cols[0]:
                if st.button("Étape précédente", use_container_width=True, key="prev_step_avant_brief"):
                    st.session_state.avant_brief_step = 1
                    st.rerun()
            with cols[2]:
                if st.button("Sauvegarder", type="primary", use_container_width=True, key="save_avant_brief"):
                    st.session_state.avant_brief_completed = True
                    # Transférer les données du wizard vers le dictionnaire de données
                    st.session_state.avant_brief_data["Informations de poste_Raison de l'ouverture"] = st.session_state.get("raison_ouverture", "")
                    st.session_state.avant_brief_data["Informations de poste_Impact stratégique"] = st.session_state.get("impact_strategique", "")
                    st.session_state.avant_brief_data["Informations de poste_Rattachement"] = st.session_state.get("rattachement", "")
                    st.session_state.avant_brief_data["Informations de poste_Tâches principales"] = st.session_state.get("taches_principales", "")
                    st.session_state.avant_brief_data["Profil Must-Have_Expérience"] = st.session_state.get("must_have_experience", "")
                    st.session_state.avant_brief_data["Profil Must-Have_Diplômes & Certifications"] = st.session_state.get("must_have_diplomes", "")
                    st.session_state.avant_brief_data["Profil Must-Have_Compétences techniques"] = st.session_state.get("must_have_competences", "")
                    st.session_state.avant_brief_data["Profil Must-Have_Soft Skills"] = st.session_state.get("must_have_softskills", "")
                    st.success("✅ Données Avant-brief sauvegardées ! Vous pouvez passer à l'étape suivante.")
                    st.rerun()
        
# ---------------- ONGLET RÉUNION DE BRIEF ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter l'onglet 'Avant-brief' et le sauvegarder.")
    else:
        st.header("✅ Réunion de brief")
        st.markdown("Saisissez les informations obtenues directement avec le manager.")
        
        # Initialise le dictionnaire de réunion avec les données de l'avant-brief
        if st.session_state.reunion_data == {}:
            st.session_state.reunion_data = st.session_state.avant_brief_data.copy()
        
        st.session_state.reunion_data = render_styled_brief_table(st.session_state.reunion_data, "reunion", is_editable=True)

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
            
            st.subheader("Informations de base")
            st.write(f"**Manager :** {st.session_state.get('manager_nom', 'N/A')}")
            st.write(f"**Recruteur :** {st.session_state.get('recruteur', 'N/A')}")
            st.write(f"**Poste :** {st.session_state.get('niveau_hierarchique', 'N/A')}")
            st.write(f"**Date :** {st.session_state.get('date_brief', 'N/A')}")
            
            st.subheader("Détails de la réunion de brief")
            render_styled_brief_table(st.session_state.reunion_data, "synthese", is_editable=False)
            
            st.subheader("Matrice KSA")
            if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
                st.dataframe(st.session_state.ksa_matrix, hide_index=True, use_container_width=True)
            else:
                st.info("Aucune matrice KSA disponible.")
                
            st.markdown("---")
            st.subheader("Exportations")
            col_export = st.columns(2)
            
            if WORD_AVAILABLE:
                with col_export[0]:
                    if st.button("Exporter au format Word", use_container_width=True):
                        st.info("Fonctionnalité d'exportation Word non implémentée.")
            
            if PDF_AVAILABLE:
                with col_export[1]:
                    if st.button("Exporter au format PDF", use_container_width=True):
                        st.info("Fonctionnalité d'exportation PDF non implémentée.")