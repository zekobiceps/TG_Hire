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
        if st.button("🗑️ Supprimer le dernier critère", type="secondary"):
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

# Style CSS pour les onglets personnalisés
st.markdown("""
    <style>
    /* Cache les onglets par défaut de Streamlit */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        border-bottom: 1px solid #424242;
    }
    
    /* Style de base pour tous les onglets */
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
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
        background-color: transparent !important;
        border-bottom: 3px solid #ff4b4b !important;
    }
    
    /* Style général pour l'application */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
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
    </style>
""", unsafe_allow_html=True)

# Vérification si un brief est chargé au début de l'application
if "current_brief_name" not in st.session_state:
    st.session_state.current_brief_name = ""

# Utilisation d'onglets comme dans la page sourcing
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Gestion", 
    "🔄 Avant-brief", 
    "✅ Réunion de brief", 
    "📝 Synthèse"
])

# ---------------- ONGLET GESTION ----------------
with tab1:
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        st.subheader("Informations de base")
        
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Intitulé du poste *", key="poste_intitule")
            st.text_input("Nom du manager *", key="manager_nom")
        with col2:
            st.text_input("Poste à recruter", key="niveau_hierarchique")
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
        with col3:
            st.selectbox("Type de brief", ["Brief", "Template"], key="brief_type")
            st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type")
            st.text_input("Nom de l'affectation", key="affectation_nom")
        
        # Nouvelle disposition pour Date du Brief et message
        col_date, col_msg = st.columns([1, 2])
        with col_date:
            st.date_input("Date du Brief *", key="date_brief", value=datetime.today().date())
        with col_msg:
            # Placeholder pour les messages d'erreur/confirmation
            message_placeholder = st.empty()

        # --- SAUVEGARDE
        if st.button("💾 Sauvegarder le Brief", type="primary", use_container_width=True):
            if not all([st.session_state.poste_intitule, st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                message_placeholder.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                if "saved_briefs" not in st.session_state:
                    st.session_state.saved_briefs = {}
                
                st.session_state.saved_briefs[brief_name] = {
                    "poste_intitule": st.session_state.poste_intitule,
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "date_brief": str(st.session_state.date_brief),
                    "niveau_hierarchique": st.session_state.niveau_hierarchique,
                    "brief_type": st.session_state.brief_type,
                    "affectation_type": st.session_state.affectation_type,
                    "affectation_nom": st.session_state.affectation_nom,
                    "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                    "impact_strategique": st.session_state.get("impact_strategique", ""),
                    "rattachement": st.session_state.get("rattachement", ""),
                    "defis_principaux": st.session_state.get("defis_principaux", ""),
                    "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                    "canaux_profil": st.session_state.get("canaux_profil", ""),
                    "synonymes_poste": st.session_state.get("synonymes_poste", ""),
                    "budget": st.session_state.get("budget", ""),
                    "commentaires": st.session_state.get("commentaires", ""),
                    "ksa_data": st.session_state.get("ksa_data", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict() if hasattr(st.session_state, 'ksa_matrix') else {}
                }
                save_briefs()
                message_placeholder.success(f"✅ Brief '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name

    with col_side:
        st.subheader("Recherche & Chargement")
        
        # --- RECHERCHE & CHARGEMENT (2 colonnes)
        col1, col2 = st.columns(2)
        with col1:
            months = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            month = st.selectbox("Mois", months)
            brief_type_filter = st.selectbox("Type", ["", "Brief", "Template"], key="brief_type_filter")
        with col2:
            recruteur = st.selectbox("Recruteur", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="search_recruteur")
            manager = st.text_input("Manager")
        
        # Nouvelle ligne pour Affectation et Nom de l'affectation
        col_affect, col_nom_affect = st.columns(2)
        with col_affect:
            affectation = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="search_affectation")
        with col_nom_affect:
            nom_affectation = st.text_input("Nom de l'affectation", key="search_nom_affectation")

        if st.button("🔎 Rechercher", type="secondary", use_container_width=True):
            briefs = load_briefs()
            # Modification ici pour gérer les nouveaux paramètres de filtrage
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
                st.info(f"ℹ️ {len(st.session_state.filtered_briefs)} brief(s) trouvé(s).")
            else:
                st.error("❌ Aucun brief trouvé avec ces critères.")

        if st.session_state.filtered_briefs:
            st.subheader("Résultats de recherche")
            
            # Afficher les résultats en deux colonnes
            briefs_list = list(st.session_state.filtered_briefs.items())
            half = len(briefs_list) // 2
            col_left, col_right = st.columns(2)
            
            with col_left:
                for name, data in briefs_list[:half]:
                    with st.expander(f"📌 {name}"):
                        st.write(f"**Type:** {data.get('brief_type', '')}")
                        st.write(f"**Manager:** {data.get('manager_nom', '')}")
                        st.write(f"**Recruteur:** {data.get('recruteur', '')}")
                        st.write(f"**Affectation:** {data.get('affectation_type', '')} - {data.get('affectation_nom', '')}")
                        st.write(f"**Date:** {data.get('date_brief', '')}")
                        
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
                                                      "defis_principaux", "entreprises_profil", "canaux_profil",
                                                      "synonymes_poste", "budget", "commentaires", "brief_type"]
                                    
                                    for key in non_widget_keys:
                                        if key in data:
                                            st.session_state[key] = data[key]
                                    
                                    # Gestion spéciale pour les données KSA
                                    if "ksa_data" in data:
                                        st.session_state.ksa_data = data["ksa_data"]
                                    
                                    # Gestion spéciale pour la matrice KSA
                                    if "ksa_matrix" in data and data["ksa_matrix"]:
                                        st.session_state.ksa_matrix = pd.DataFrame(data["ksa_matrix"])
                                    
                                    st.success(f"✅ Brief '{name}' chargé avec succès!")
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
            
            with col_right:
                for name, data in briefs_list[half:]:
                    with st.expander(f"📌 {name}"):
                        st.write(f"**Type:** {data.get('brief_type', '')}")
                        st.write(f"**Manager:** {data.get('manager_nom', '')}")
                        st.write(f"**Recruteur:** {data.get('recruteur', '')}")
                        st.write(f"**Affectation:** {data.get('affectation_type', '')} - {data.get('affectation_nom', '')}")
                        st.write(f"**Date:** {data.get('date_brief', '')}")
                        
                        colA, colB = st.columns(2)
                        with colA:
                            if st.button(f"📂 Charger", key=f"load2_{name}"):
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
                                                      "defis_principaux", "entreprises_profil", "canaux_profil",
                                                      "synonymes_poste", "budget", "commentaires", "brief_type"]
                                    
                                    for key in non_widget_keys:
                                        if key in data:
                                            st.session_state[key] = data[key]
                                    
                                    # Gestion spéciale pour les données KSA
                                    if "ksa_data" in data:
                                        st.session_state.ksa_data = data["ksa_data"]
                                    
                                    # Gestion spéciale pour la matrice KSA
                                    if "ksa_matrix" in data and data["ksa_matrix"]:
                                        st.session_state.ksa_matrix = pd.DataFrame(data["ksa_matrix"])
                                    
                                    st.success(f"✅ Brief '{name}' chargé avec succès!")
                                    st.rerun()
                                
                                except Exception as e:
                                    st.error(f"❌ Erreur lors du chargement: {str(e)}")
                        with colB:
                            if st.button(f"🗑️ Supprimer", key=f"del2_{name}"):
                                all_briefs = load_briefs()
                                if name in all_briefs:
                                    del all_briefs[name]
                                    st.session_state.saved_briefs = all_briefs
                                    save_briefs()
                                    if name in st.session_state.filtered_briefs:
                                        del st.session_state.filtered_briefs[name]
                                    st.warning(f"❌ Brief '{name}' supprimé.")
                                    st.rerun()

# ---------------- AVANT-BRIEF ----------------
with tab2:
    # Vérification si un brief est chargé
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.info("💡 Utilisez l'onglet Gestion pour créer un nouveau brief ou charger un template existant")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours avec Manager/Recruteur à gauche
    st.markdown(f"<h3>🔄 Avant-brief (Préparation) - Manager: {st.session_state.get('manager_nom', '')} | Recruteur: {st.session_state.get('recruteur', '')}</h3>", 
                unsafe_allow_html=True)

    # Titre pour le tableau
    st.subheader("📋 Portrait robot candidat")

    # Organisation structurée sous forme de tableau minimaliste
    st.markdown("""
    <style>
    .minimal-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    .minimal-table th, .minimal-table td {
        border: 1px solid #424242;
        padding: 6px;
        text-align: left;
    }
    .minimal-table th {
        background-color: #262730;
        font-weight: bold;
    }
    .section-col {
        width: 15%;
        font-weight: bold;
    }
    .details-col {
        width: 25%;
    }
    .info-col {
        width: 60%;
    }
    .info-textarea {
        width: 100%;
        height: 60px;
        background-color: #262730;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px;
        resize: vertical;
    }
    </style>
    
    <table class="minimal-table">
        <tr>
            <th class="section-col">Section</th>
            <th class="details-col">Détails</th>
            <th class="info-col">Informations</th>
        </tr>
        <!-- Contexte du poste -->
        <tr>
            <td rowspan="3" class="section-col">Contexte du poste</td>
            <td class="details-col">Raison de l'ouverture</td>
            <td><textarea class="info-textarea" placeholder="Remplacement / Création / Évolution interne"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Mission globale</td>
            <td><textarea class="info-textarea" placeholder="Résumé du rôle et objectif principal"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Défis principaux</td>
            <td><textarea class="info-textarea" placeholder="Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget"></textarea></td>
        </tr>
        <!-- Profil recherché -->
        <tr>
            <td rowspan="4" class="section-col">Profil recherché</td>
            <td class="details-col">Expérience</td>
            <td><textarea class="info-textarea" placeholder="Nombre d'années minimum, expériences similaires dans le secteur"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Connaissances / Diplômes / Certifications</td>
            <td><textarea class="info-textarea" placeholder="Diplômes exigés, certifications spécifiques"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Compétences / Outils</td>
            <td><textarea class="info-textarea" placeholder="Techniques, logiciels, méthodes à maîtriser"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Soft skills / aptitudes comportementales</td>
            <td><textarea class="info-textarea" placeholder="Leadership, rigueur, communication, autonomie"></textarea></td>
        </tr>
        <!-- Missions / Tâches -->
        <tr>
            <td rowspan="2" class="section-col">Missions / Tâches</td>
            <td class="details-col">Tâches principales</td>
            <td><textarea class="info-textarea" placeholder="4-6 missions détaillées"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Autres responsabilités</td>
            <td><textarea class="info-textarea" placeholder="Points additionnels ou spécifiques à préciser"></textarea></td>
        </tr>
        <!-- Sourcing et marché -->
        <tr>
            <td rowspan="3" class="section-col">Sourcing et marché</td>
            <td class="details-col">Entreprises où trouver ce profil</td>
            <td><textarea class="info-textarea" placeholder="Concurrents, secteurs similaires"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Synonymes / intitulés proches</td>
            <td><textarea class="info-textarea" placeholder="Titres alternatifs pour affiner le sourcing"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Canaux à utiliser</td>
            <td><textarea class="info-textarea" placeholder="LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels"></textarea></td>
        </tr>
        <!-- Conditions et contraintes -->
        <tr>
            <td rowspan="2" class="section-col">Conditions et contraintes</td>
            <td class="details-col">Localisation</td>
            <td><textarea class="info-textarea" placeholder="Site principal, télétravail, déplacements"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Budget recrutement</td>
            <td><textarea class="info-textarea" placeholder="Salaire indicatif, avantages, primes éventuelles"></textarea></td>
        </tr>
        <!-- Notes libres -->
        <tr>
            <td rowspan="2" class="section-col">Notes libres</td>
            <td class="details-col">Points à discuter ou à clarifier avec le manager</td>
            <td><textarea class="info-textarea" placeholder="Points à discuter ou à clarifier"></textarea></td>
        </tr>
        <tr>
            <td class="details-col">Case libre</td>
            <td><textarea class="info-textarea" placeholder="Pour tout point additionnel ou remarque spécifique"></textarea></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    # Section Profils pertinents
    st.subheader("🔗 Profils pertinents")
    
    # Initialiser les liens s'ils n'existent pas
    if "profil_links" not in st.session_state:
        st.session_state.profil_links = ["", "", ""]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.text_input("Lien profil 1", value=st.session_state.profil_links[0], key="profil_link_1")
    
    with col2:
        st.text_input("Lien profil 2", value=st.session_state.profil_links[1], key="profil_link_2")
    
    with col3:
        st.text_input("Lien profil 3", value=st.session_state.profil_links[2], key="profil_link_3")

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_name = st.session_state.current_brief_name
            
            # Sauvegarder les liens de profils
            st.session_state.profil_links = [
                st.session_state.get("profil_link_1", ""),
                st.session_state.get("profil_link_2", ""),
                st.session_state.get("profil_link_3", "")
            ]
            
            # Mettre à jour le brief avec les liens
            st.session_state.saved_briefs[brief_name]["profil_links"] = st.session_state.profil_links
            
            save_briefs()
            st.success("✅ Modifications sauvegardées")
        else:
            st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

# ---------------- RÉUNION (Wizard interne) ----------------
with tab3:
    # Vérification si un brief est chargé
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.info("💡 Utilisez l'onglet Gestion pour créer un nouveau brief ou charger un template existant")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.subheader(f"✅ Réunion de brief avec le Manager - {st.session_state.get('poste_intitule', '')}")
    st.info(f"Manager: {st.session_state.get('manager_nom', '')} | Recruteur: {st.session_state.get('recruteur', '')}")

    total_steps = 4
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation manager")
        
        # Afficher le tableau du portrait robot avec une colonne pour les notes du manager
        st.info("Veuillez valider et compléter le portrait robot candidat")
        
        # Créer un formulaire pour que le manager puisse ajouter ses notes
        st.markdown("""
        <style>
        .manager-notes {
            background-color: #262730;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="manager-notes">', unsafe_allow_html=True)
        st.text_area("Notes du manager", key="manager_notes", height=150, 
                    placeholder="Ajoutez vos commentaires et notes sur le portrait robot candidat...")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Afficher le tableau du portrait robot (similaire à l'onglet Avant-brief)
        st.markdown("""
        <table class="minimal-table">
            <tr>
                <th class="section-col">Section</th>
                <th class="details-col">Détails</th>
                <th class="info-col">Informations</th>
            </tr>
            <tr>
                <td rowspan="3" class="section-col">Contexte du poste</td>
                <td class="details-col">Raison de l'ouverture</td>
                <td>{raison_ouverture}</td>
            </tr>
            <tr>
                <td class="details-col">Mission globale</td>
                <td>{mission_globale}</td>
            </tr>
            <tr>
                <td class="details-col">Défis principaux</td>
                <td>{defis_principaux}</td>
            </tr>
            <tr>
                <td rowspan="4" class="section-col">Profil recherché</td>
                <td class="details-col">Expérience</td>
                <td>{experience}</td>
            </tr>
            <tr>
                <td class="details-col">Connaissances / Diplômes / Certifications</td>
                <td>{diplomes}</td>
            </tr>
            <tr>
                <td class="details-col">Compétences / Outils</td>
                <td>{competences}</td>
            </tr>
            <tr>
                <td class="details-col">Soft skills / aptitudes comportementales</td>
                <td>{soft_skills}</td>
            </tr>
        </table>
        """.format(
            raison_ouverture=st.session_state.get("raison_ouverture", "Non renseigné"),
            mission_globale=st.session_state.get("mission_globale", "Non renseigné"),
            defis_principaux=st.session_state.get("defis_principaux", "Non renseigné"),
            experience=st.session_state.get("experience_requise", "Non renseigné"),
            diplomes=st.session_state.get("diplomes_certifications", "Non renseigné"),
            competences=st.session_state.get("competences_outils", "Non renseigné"),
            soft_skills=st.session_state.get("soft_skills", "Non renseigné")
        ), unsafe_allow_html=True)

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

        if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                brief_name = st.session_state.current_brief_name
                st.session_state.saved_briefs[brief_name].update({
                    "ksa_data": st.session_state.get("ksa_data", {}),
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict(),
                    "manager_notes": st.session_state.get("manager_notes", "")
                })
                save_briefs()
                st.success("✅ Données de réunion sauvegardées")
            else:
                st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

    # ---- Navigation wizard ----
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if step > 1:
            if st.button("⬅️ Précédent"):
                st.session_state.reunion_step -= 1
                st.rerun()
    with col3:
        if step < total_steps:
            if st.button("Suivant ➡️"):
                st.session_state.reunion_step += 1
                st.rerun()

# ---------------- SYNTHÈSE ----------------
with tab4:
    # Vérification si un brief est chargé
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.info("💡 Utilisez l'onglet Gestion pour créer un nouveau brief ou charger un template existant")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.subheader(f"📝 Synthèse du Brief - {st.session_state.get('poste_intitule', '')}")
    st.info(f"Manager: {st.session_state.get('manager_nom', '')} | Recruteur: {st.session_state.get('recruteur', '')}")
    
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
        "Défis principaux": st.session_state.get("defis_principaux", ""),
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

    if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state:
            save_briefs()
            st.success(f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !")
        else:
            st.error("❌ Aucun brief à sauvegarder. Veuillez d'abord créer un brief.")

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