import sys, os 
import streamlit as st
from datetime import datetime
import json
import pandas as pd
import requests

# For PDF file reading
import pdfplumber

# ✅ allows access to utils.py at the root
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

# Fonction pour appeler l'IA et extraire les informations (MISE À JOUR)
def extract_info_with_deepseek(text, job_title):
    """
    Appelle l'API DeepSeek pour extraire les critères d'une fiche de poste.
    
    PARAMÈTRES:
    text (str): Le contenu textuel de la fiche de poste.
    job_title (str): L'intitulé du poste à recruter.
    
    RETOURNE:
    dict: Un dictionnaire contenant les informations extraites, ou un dictionnaire vide en cas d'erreur.
    """
    if "DEEPSEEK_API_KEY" not in st.secrets:
        st.error("Clé API DeepSeek non trouvée dans les secrets de Streamlit. Veuillez la configurer.")
        return {}
        
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    system_prompt = f"""
    Vous êtes un expert en recrutement. Votre tâche est d'analyser une fiche de poste et d'extraire les informations clés pour créer un brief de recrutement. 
    Les informations à extraire sont :
    - raison_ouverture : La raison de la création du poste (remplacement, création, etc.).
    - impact_strategique : La mission principale et l'impact du rôle.
    - taches_principales : Les responsabilités et tâches les plus importantes.
    - must_have_experience : L'expérience minimale requise.
    - must_have_diplomes : Les diplômes ou certifications obligatoires.
    - must_have_competences : Les compétences techniques (hard skills) essentielles.
    - must_have_softskills : Les soft skills ou aptitudes comportementales incontournables.
    - nice_to_have_experience : L'expérience souhaitée mais non obligatoire.
    - nice_to_have_diplomes : Les diplômes ou certifications appréciés mais non essentiels.
    - nice_to_have_competences : Les compétences techniques additionnelles.
    - entreprises_profil : Les types d'entreprises ou les secteurs où trouver ce profil.
    - synonymes_poste : Les titres de poste alternatifs.
    - canaux_profil : Les meilleurs canaux de sourcing.
    - budget : Le budget ou la fourchette salariale.
    - commentaires : Des notes additionnelles ou des points à clarifier.
    
    Répondez uniquement avec un objet JSON contenant ces clés et les valeurs extraites. Ne donnez aucune autre explication ou texte avant ou après le JSON. Si une information n'est pas trouvée, la valeur correspondante doit être une chaîne vide.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-coder",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyse la fiche de poste pour le poste de '{job_title}' :\n\n{text}"}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        raw_content = response_data['choices'][0]['message']['content']
        
        parsed_data = json.loads(raw_content)
        return parsed_data
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de l'appel à l'API DeepSeek : {e}")
        return {}
    except json.JSONDecodeError:
        st.error("Erreur de format de réponse de l'API. La réponse n'est pas un JSON valide.")
        return {}

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
    
if "job_descriptions" not in st.session_state:
    st.session_state.job_descriptions = {}

if "avant_brief_completed" not in st.session_state:
    st.session_state.avant_brief_completed = False

if "reunion_completed" not in st.session_state:
    st.session_state.reunion_completed = False

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

st.markdown("""
    <style>
    /* CSS code from previous response */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stTabs [data-baseweb="tab-list"] { gap: 0px; background-color: #0E1117; padding: 0px; border-radius: 4px; }
    .stTabs [data-baseweb="tab"] { background-color: #0E1117 !important; color: white !important; border: none !important; padding: 10px 16px !important; font-weight: 500 !important; border-radius: 0 !important; margin-right: 0 !important; height: auto !important; }
    .stTabs [aria-selected="true"] { color: #ff4b4b !important; border-bottom: 3px solid #ff4b4b !important; }
    .stButton > button { background-color: #FF4B4B; color: white; border: none; border-radius: 5px; padding: 0.5rem 1rem; font-weight: 500; }
    .stButton > button:hover { background-color: #FF6B6B; color: white; }
    .stButton > button[kind="secondary"] { background-color: #262730; color: #FAFAFA; border: 1px solid #FF4B4B; }
    .stButton > button[kind="secondary"]:hover { background-color: #3D3D4D; color: #FAFAFA; }
    .streamlit-expanderHeader { background-color: #262730; color: #FAFAFA; border-radius: 5px; padding: 0.5rem; }
    div[data-baseweb="select"] > div { border: none !important; background-color: #262730 !important; color: white !important; border-radius: 4px !important; }
    .stTextInput input { background-color: #262730 !important; color: white !important; border-radius: 4px !important; border: none !important; }
    .stTextArea textarea { background-color: #262730 !important; color: white !important; border-radius: 4px !important; border: none !important; }
    .stDateInput input { background-color: #262730 !important; color: white !important; border-radius: 4px !important; border: none !important; }
    .stTextArea textarea { height: 100px !important; }
    .message-container { margin-top: 10px; padding: 10px; border-radius: 5px; }
    .stAlert { padding: 10px; margin-top: 10px; }
    .comparison-table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
    .comparison-table th, .comparison-table td { border: 1px solid #424242; padding: 8px; text-align: left; }
    .comparison-table th { background-color: #262730; font-weight: bold; }
    .dataframe { width: 100%; }
    .disabled-tab { opacity: 0.5; pointer-events: none; cursor: not-allowed; }
    .dark-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #0d1117; font-size: 0.9em; border: 1px solid #ffffff; }
    .dark-table th, .dark-table td { padding: 12px 16px; text-align: left; border: 1px solid #ffffff; color: #e6edf3; }
    .dark-table th { background-color: #FF4B4B !important; color: white !important; font-weight: 600; padding: 14px 16px; font-size: 16px; border: 1px solid #ffffff; }
    .dark-table th:nth-child(1), .dark-table td:nth-child(1) { width: 15%; }
    .dark-table th:nth-child(2), .dark-table td:nth-child(2) { width: 20%; }
    .dark-table th:nth-child(3), .dark-table td:nth-child(3) { width: 65%; }
    .dark-table.four-columns th:nth-child(1), .dark-table.four-columns td:nth-child(1) { width: 15%; }
    .dark-table.four-columns th:nth-child(2), .dark-table.four-columns td:nth-child(2) { width: 20%; }
    .dark-table.four-columns th:nth-child(3), .dark-table.four-columns td:nth-child(3) { width: 40%; }
    .dark-table.four-columns th:nth-child(4), .dark-table.four-columns td:nth-child(4) { width: 25%; }
    .section-title { font-weight: 600; color: #58a6ff; font-size: 0.95em; }
    .table-textarea { width: 100%; min-height: 60px; background-color: #2D2D2D; color: white; border: 1px solid #555; border-radius: 4px; padding: 6px; font-size: 0.9em; resize: vertical; }
    .table-text { padding: 6px; font-size: 0.9em; color: #e6edf3; }
    .empty-row { display: none; }
    .stDataFrame { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #0d1117; font-size: 0.9em; border: 1px solid #ffffff; }
    .stDataFrame th, .stDataFrame td { padding: 12px 16px; text-align: left; border: 1px solid #ffffff; color: #e6edf3; }
    .stDataFrame th { background-color: #FF4B4B !important; color: white !important; font-weight: 600; padding: 14px 16px; font-size: 16px; border: 1px solid #ffffff; }
    .stDataFrame td:first-child { font-weight: 600; color: #58a6ff; }
    .stDataFrame td:nth-child(1) { width: 15%; }
    .stDataFrame td:nth-child(2) { width: 20%; }
    .stDataFrame td:nth-child(3) { width: 65%; }
    .stDataFrame td:nth-child(3) textarea { background-color: #2D2D2D !important; color: white !important; border: 1px solid #555 !important; border-radius: 4px !important; padding: 6px !important; min-height: 60px !important; resize: vertical !important; }
    </style>
""", unsafe_allow_html=True)

# Check if a brief is loaded at the start of the application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

# Creation of tabs with access management
tabs = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse",
    "📚 Bibliothèque"
])

# Determine which tabs are accessible
can_access_avant_brief = st.session_state.current_brief_name != ""
can_access_reunion = can_access_avant_brief and st.session_state.avant_brief_completed
can_access_synthese = can_access_reunion and st.session_state.reunion_completed
can_access_bibliotheque = True # Updated to be always accessible

# ---------------- ONGLET GESTION ----------------
with tabs[0]:
    st.markdown("""
    <style>
    /* ... (CSS for Gestion tab) ... */
    .st-emotion-cache-1r6slb0 { margin-bottom: 0.2rem; }
    .st-emotion-cache-1r6slb0 p { margin-bottom: 0.2rem; }
    h3 { margin-bottom: 0.5rem !important; }
    .stTextInput input, .stSelectbox select, .stDateInput input { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; height: 2rem !important; }
    .st-emotion-cache-ocqkz7 { gap: 0.5rem !important; }
    .custom-radio { display: flex; background-color: #262730; padding: 3px; border-radius: 5px; border: 1px solid #424242; margin-left: 10px; }
    .custom-radio input[type="radio"] { display: none; }
    .custom-radio label { padding: 3px 8px; cursor: pointer; border-radius: 3px; margin: 0 3px; font-size: 0.9em; }
    .custom-radio input[type="radio"]:checked + label { background-color: #FF4B4B; color: white; }
    div[data-testid="stRadio"] > div { display: none; }
    .st-emotion-cache-5rimss p { margin-bottom: 0.3rem; }
    .compact-title { display: flex; align-items: center; margin-bottom: 0.5rem !important; }
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
                                new_brief = {}
                                for key, value in data.items():
                                    new_brief[key] = value
                                st.session_state.loaded_brief = new_brief
                                st.session_state.current_brief_name = name
                                non_widget_keys = ["raison_ouverture", "impact_strategique", "rattachement", 
                                                  "taches_principales", "must_have_experience", "must_have_diplomes",
                                                  "must_have_competences", "must_have_softskills", "nice_to_have_experience",
                                                  "nice_to_have_diplomes", "nice_to_have_competences", "entreprises_profil", 
                                                  "canaux_profil", "synonymes_poste", "budget", "commentaires", 
                                                  "notes_libres", "profil_links"]
                                for key in non_widget_keys:
                                    if key in data:
                                        st.session_state[key] = data[key]
                                if "brief_type" in data:
                                    st.session_state.gestion_brief_type = data["brief_type"]
                                if "ksa_data" in data:
                                    st.session_state.ksa_data = data["ksa_data"]
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

st.markdown("""
<script>
// ... (JavaScript for custom radio buttons) ...
document.querySelectorAll('.custom-radio input[type="radio"]').forEach(radio => { radio.addEventListener('change', function() { const value = this.value; const streamlitRadio = parent.document.querySelector('input[type="radio"][value="' + value + '"]'); if (streamlitRadio) { streamlitRadio.click(); } }); });
document.addEventListener('DOMContentLoaded', function() { const streamlitValue = parent.document.querySelector('input[type="radio"]:checked').value; const customRadio = document.querySelector('.custom-radio input[value="' + streamlitValue + '"]'); if (customRadio) { customRadio.checked = true; } });
</script>
""", unsafe_allow_html=True)

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.stop()
    
    st.markdown(f"<h3>🔄 Avant-brief (Préparation)</h3>", unsafe_allow_html=True)

    st.subheader("📋 Portrait robot candidat")

    sections = [
        { "title": "Contexte du poste", "category": "contexte", "fields": [ ("Raison de l'ouverture", "raison_ouverture", "Remplacement / Création / Évolution interne"), ("Mission globale", "impact_strategique", "Résumé du rôle et objectif principal"), ("Tâches principales", "taches_principales", "Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget"), ] },
        { "title": "Must-have (Indispensables)", "category": "must-have", "fields": [ ("Expérience", "must_have_experience", "Nombre d'années minimum, expériences similaires dans le secteur"), ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Diplômes exigés, certifications spécifiques"), ("Compétences / Outils", "must_have_competences", "Techniques, logiciels, méthodes à maîtriser"), ("Soft skills / aptitudes comportementales", "must_have_softskills", "Leadership, rigueur, communication, autonomie"), ] },
        { "title": "Nice-to-have (Atouts)", "category": "nice-to-have", "fields": [ ("Expérience additionnelle", "nice_to_have_experience", "Ex. projets internationaux, multi-sites"), ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Diplômes ou certifications supplémentaires appréciés"), ("Compétences complémentaires", "nice_to_have_competences", "Compétences supplémentaires non essentielles mais appréciées"), ] },
        { "title": "Sourcing et marché", "category": "sourcing", "fields": [ ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"), ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"), ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels"), ] },
        { "title": "Conditions et contraintes", "category": "conditions", "fields": [ ("Localisation", "rattachement", "Site principal, télétravail, déplacements"), ("Budget recrutement", "budget", "Salaire indicatif, avantages, primes éventuelles"), ] },
        { "title": "Profils pertinents", "category": "profils", "fields": [ ("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"), ("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"), ("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre"), ] },
        { "title": "Notes libres", "category": "notes", "fields": [ ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"), ("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique"), ] },
    ]

    if st.button("💡 Prérédiger avec l'IA", type="secondary", use_container_width=True, key="ai_fill_button"):
        with st.spinner("L'IA génère les suggestions..."):
            for section in sections:
                if section["category"] == "profils":
                    continue
                for field_name, field_key, _ in section["fields"]:
                    advice = generate_checklist_advice(section["category"], field_name)
                    st.session_state[field_key] = advice
            st.success("✅ Suggestions IA ajoutées. Vous pouvez maintenant les modifier.")
            st.rerun()

    data = []
    field_keys = []
    for section in sections:
        first_field = True
        for field_name, field_key, _ in section["fields"]:
            data.append([section["title"] if first_field else "", field_name, st.session_state.get(field_key, "")])
            field_keys.append(field_key)
            first_field = False

    df = pd.DataFrame(data, columns=["Section", "Détails", "Informations"])

    edited_df = st.data_editor(
        df,
        column_config={
            "Section": st.column_config.TextColumn("Section", disabled=True),
            "Détails": st.column_config.TextColumn("Détails", disabled=True),
            "Informations": st.column_config.TextColumn("Informations", width="large")
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed"
    )

    col_save, col_reset = st.columns([1, 1])
    with col_save:
        if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True, key="save_avant_brief"):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                brief_name = st.session_state.current_brief_name
                for i in range(len(edited_df)):
                    field_key = field_keys[i]
                    st.session_state[field_key] = edited_df["Informations"].iloc[i]
                st.session_state.profil_links = [
                    st.session_state.get("profil_link_1", ""),
                    st.session_state.get("profil_link_2", ""),
                    st.session_state.get("profil_link_3", "")
                ]
                brief_data = {
                    "profil_links": st.session_state.profil_links,
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
                    "rattachement": st.session_state.get("rattachement", ""),
                    "budget": st.session_state.get("budget", ""),
                    "commentaires": st.session_state.get("commentaires", ""),
                    "notes_libres": st.session_state.get("notes_libres", "")
                }
                existing_briefs = load_briefs()
                if brief_name in existing_briefs:
                    existing_briefs[brief_name].update(brief_data)
                    st.session_state.saved_briefs = existing_briefs
                else:
                    st.session_state.saved_briefs[brief_name] = brief_data
                save_briefs()
                st.session_state.avant_brief_completed = True
                st.success("✅ Modifications sauvegardées")
                st.rerun()
            else:
                st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
    
    with col_reset:
        if st.button("🗑️ Réinitialiser le Brief", type="secondary", use_container_width=True, key="reset_avant_brief"):
            delete_current_brief()

# ---------------- RÉUNION (Wizard interne) ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter et sauvegarder l'onglet Avant-brief")
        st.stop()
    
    st.subheader(f"✅ Réunion de brief avec le Manager - {st.session_state.get('niveau_hierarchique', '')}")
    total_steps = 5
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")
    
    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation")
        sections = [
            { "title": "Contexte du poste", "fields": [ ("Raison de l'ouverture", "raison_ouverture", "Remplacement / Création / Évolution interne"), ("Mission globale", "impact_strategique", "Résumé du rôle et objectif principal"), ("Tâches principales", "taches_principales", "Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget"), ] },
            { "title": "Must-have (Indispensables)", "fields": [ ("Expérience", "must_have_experience", "Nombre d'années minimum, expériences similaires dans le secteur"), ("Connaissances / Diplômes / Certifications", "must_have_diplomes", "Diplômes exigés, certifications spécifiques"), ("Compétences / Outils", "must_have_competences", "Techniques, logiciels, méthodes à maîtriser"), ("Soft skills / aptitudes comportementales", "must_have_softskills", "Leadership, rigueur, communication, autonomie"), ] },
            { "title": "Nice-to-have (Atouts)", "fields": [ ("Expérience additionnelle", "nice_to_have_experience", "Ex. projets internationaux, multi-sites"), ("Diplômes / Certifications valorisantes", "nice_to_have_diplomes", "Diplômes ou certifications supplémentaires appréciés"), ("Compétences complémentaires", "nice_to_have_competences", "Compétences supplémentaires non essentielles mais appréciées"), ] },
            { "title": "Sourcing et marché", "fields": [ ("Entreprises où trouver ce profil", "entreprises_profil", "Concurrents, secteurs similaires"), ("Synonymes / intitulés proches", "synonymes_poste", "Titres alternatifs pour affiner le sourcing"), ("Canaux à utiliser", "canaux_profil", "LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels"), ] },
            { "title": "Conditions et contraintes", "fields": [ ("Localisation", "rattachement", "Site principal, télétravail, déplacements"), ("Budget recrutement", "budget", "Salaire indicatif, avantages, primes éventuelles"), ] },
            { "title": "Profils pertinents", "fields": [ ("Lien profil 1", "profil_link_1", "URL du profil LinkedIn ou autre"), ("Lien profil 2", "profil_link_2", "URL du profil LinkedIn ou autre"), ("Lien profil 3", "profil_link_3", "URL du profil LinkedIn ou autre"), ] },
            { "title": "Notes libres", "fields": [ ("Points à discuter ou à clarifier avec le manager", "commentaires", "Points à discuter ou à clarifier"), ("Case libre", "notes_libres", "Pour tout point additionnel ou remarque spécifique"), ] },
        ]
        data = []
        field_keys = []
        comment_keys = []
        k = 1
        for section in sections:
            first_field = True
            for field_name, field_key, placeholder in section["fields"]:
                data.append([section["title"] if first_field else "", field_name, st.session_state.get(field_key, placeholder), ""])
                field_keys.append(field_key)
                comment_keys.append(f"manager_comment_{k}")
                k += 1
                first_field = False
        df = pd.DataFrame(data, columns=["Section", "Détails", "Informations", "Commentaires du manager"])
        edited_df = st.data_editor(
            df,
            column_config={
                "Section": st.column_config.TextColumn("Section", disabled=True),
                "Détails": st.column_config.TextColumn("Détails", disabled=True),
                "Informations": st.column_config.TextColumn(
                    "Informations", 
                    width="medium", 
                    disabled=True,
                    default=[f"Entrez {placeholder.lower()}" for placeholder in df["Informations"]]
                ),
                "Commentaires du manager": st.column_config.TextColumn(
                    "Commentaires du manager", 
                    width="medium",
                    default=[f"Ajoutez vos commentaires sur {field_name.lower()}" for field_name in df["Détails"]]
                )
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        if st.button("💾 Sauvegarder commentaires", type="primary", key="save_comments_step1"):
            for i in range(len(edited_df)):
                comment_key = comment_keys[i]
                st.session_state[comment_key] = edited_df["Commentaires du manager"].iloc[i]
            st.success("✅ Commentaires sauvegardés")

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

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True, key="save_reunion"):
                if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                    brief_name = st.session_state.current_brief_name
                    manager_comments = {}
                    for i in range(1, 21):
                        comment_key = f"manager_comment_{i}"
                        if comment_key in st.session_state:
                            manager_comments[comment_key] = st.session_state[comment_key]
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
                    st.success("✅ Données de réunion sauvegardées")
                    st.rerun()
                else:
                    st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        
        with col_cancel:
            if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_reunion"):
                delete_current_brief()

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
    if not can_access_synthese:
        st.warning("⚠️ Veuillez d'abord compléter et sauvegarder l'onglet Réunion de brief")
        st.stop()
    
    st.subheader(f"📝 Synthèse du Brief - {st.session_state.get('niveau_hierarchique', '')}")
    if "current_brief_name" in st.session_state:
        st.success(f"Brief actuel: {st.session_state.current_brief_name}")
    
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("niveau_hierarchique", ""),
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
    
    if hasattr(st.session_state, 'ksa_matrix') and not st.session_state.ksa_matrix.empty:
        if "Échelle d'évaluation (1-5)" in st.session_state.ksa_matrix.columns:
            scores = st.session_state.ksa_matrix["Échelle d'évaluation (1-5)"].astype(int)
            score_global = scores.mean()
            st.metric("Score Global Cible", f"{score_global:.2f}/5")
    elif "ksa_data" in st.session_state:
        for cat, comps in st.session_state.get("ksa_data", {}).items():
            for comp, details in comps.items():
                score_total += int(details.get("score") or 0)
                count += 1
        score_global = (score_total / count) if count else 0
        st.metric("Score Global Cible", f"{score_global:.2f}/5")
    else:
        st.info("ℹ️ Aucune donnée KSA disponible pour calculer le score")

    col_save, col_cancel = st.columns([1, 1])
    with col_save:
        if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True, key="save_synthese"):
            if "current_brief_name" in st.session_state:
                save_briefs()
                st.success(f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !")
            else:
                st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")
    
    with col_cancel:
        if st.button("🗑️ Annuler le Brief", type="secondary", use_container_width=True, key="cancel_synthese"):
            delete_current_brief()

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


# ---------------- NOUVEL ONGLET BIBLIOTHÈQUE ----------------
with tabs[4]:
    # Pas de condition, cet onglet est toujours accessible
    st.header("📚 Bibliothèque de fiches de poste")
    
    lib_tabs = st.tabs(["📥 Télécharger & Analyser", "🔍 Chercher & Modifier"])

    with lib_tabs[0]:
        st.info("Chargez une fiche de poste et l'IA extraira automatiquement les informations.")
        
        col_upload, col_action = st.columns([1, 2])
        
        with col_upload:
            uploaded_file = st.file_uploader(
                "Télécharger une fiche de poste (PDF)",
                type=["pdf"],
                help="L'IA analysera le contenu pour vous."
            )
        
        with col_action:
            if uploaded_file and st.session_state.get("niveau_hierarchique"):
                if st.button("🚀 Analyser & Sauvegarder", type="primary", use_container_width=True):
                    with st.spinner("Analyse et sauvegarde du document..."):
                        try:
                            with pdfplumber.open(uploaded_file) as pdf:
                                full_text = ""
                                for page in pdf.pages:
                                    full_text += page.extract_text() or ""
                                
                                job_title = st.session_state.niveau_hierarchique
                                extracted_data = extract_info_with_deepseek(full_text, job_title)
                                
                                if extracted_data:
                                    doc_name = f"{job_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                    st.session_state.job_descriptions[doc_name] = {
                                        "raw_text": full_text,
                                        "extracted_data": extracted_data,
                                        "date_upload": str(datetime.now().date())
                                    }
                                    st.success(f"✅ Fiche de poste '{job_title}' analysée et sauvegardée.")
                                    
                                    # Mettre à jour les champs du brief
                                    for key, value in extracted_data.items():
                                        if key in st.session_state:
                                            st.session_state[key] = value
                                    
                                    st.info("Les champs du brief ont été mis à jour avec les données extraites.")
                                    st.rerun()
                                else:
                                    st.error("❌ L'extraction a échoué. Veuillez vérifier la réponse de l'API.")
                        except Exception as e:
                            st.error(f"Erreur lors de la lecture du PDF ou de l'analyse : {e}")
            elif not uploaded_file:
                st.warning("⚠️ Veuillez télécharger une fiche de poste pour continuer.")
            elif not st.session_state.get("niveau_hierarchique"):
                st.warning("⚠️ Veuillez d'abord remplir le champ 'Poste à recruter' dans l'onglet 'Gestion'.")

    with lib_tabs[1]:
        st.subheader("🔍 Bibliothèque")
        search_query = st.text_input("Rechercher une fiche de poste par titre...", key="lib_search_query")
        
        filtered_docs = {
            name: data
            for name, data in st.session_state.job_descriptions.items()
            if search_query.lower() in name.lower()
        }
        
        if not filtered_docs:
            st.info("Aucune fiche de poste trouvée ou stockée.")
        else:
            for name, doc_data in filtered_docs.items():
                with st.expander(f"Fiche de poste : {name}", expanded=False):
                    st.write(f"**Date d'upload :** {doc_data['date_upload']}")
                    
                    # Permet de visualiser et éditer le texte brut
                    st.subheader("Contenu original (modificable)")
                    edited_text = st.text_area(
                        "Modifier le texte de la fiche de poste si nécessaire",
                        value=doc_data["raw_text"],
                        height=300,
                        key=f"edit_text_{name}"
                    )
                    
                    st.subheader("Données extraites par l'IA")
                    # Afficher les données extraites sous forme de dictionnaire pour modification
                    edited_extracted_data = st.data_editor(
                        pd.DataFrame(list(doc_data["extracted_data"].items()), columns=["Critère", "Valeur"]),
                        hide_index=True,
                        use_container_width=True,
                        key=f"edit_data_{name}"
                    )
                    
                    col_update, col_load, col_delete = st.columns(3)
                    with col_update:
                        if st.button("💾 Mettre à jour la fiche", key=f"update_doc_{name}", use_container_width=True, type="primary"):
                            st.session_state.job_descriptions[name]["raw_text"] = edited_text
                            
                            updated_dict = edited_extracted_data.set_index("Critère")["Valeur"].to_dict()
                            st.session_state.job_descriptions[name]["extracted_data"] = updated_dict
                            
                            st.success("✅ Fiche de poste mise à jour avec succès !")
                            st.rerun()
                            
                    with col_load:
                        if st.button("📂 Charger dans le brief", key=f"load_doc_{name}", use_container_width=True):
                            # Charger les données extraites dans le brief
                            extracted_data_to_load = st.session_state.job_descriptions[name]["extracted_data"]
                            for key, value in extracted_data_to_load.items():
                                if key in st.session_state:
                                    st.session_state[key] = value
                            st.session_state.brief_phase = "🔄 Avant-brief"
                            st.success("✅ Données chargées. Rendez-vous dans l'onglet 'Avant-brief' !")
                            st.rerun()

                    with col_delete:
                        if st.button("🗑️ Supprimer", key=f"delete_doc_{name}", use_container_width=True, type="secondary"):
                            del st.session_state.job_descriptions[name]
                            st.warning(f"❌ Fiche de poste '{name}' supprimée.")
                            st.rerun()


# JavaScript to disable inaccessible tabs
st.markdown(f"""
<script>
// Disable tabs based on permissions
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
</script>
""", unsafe_allow_html=True)