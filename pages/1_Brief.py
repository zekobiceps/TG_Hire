apporte cette solution au code en bas et donne moi le code complet à jour : 
1. JavaScript non fonctionnel avec Streamlit
Le code JavaScript avec onchange="updateSessionState()" dans le tableau HTML ne fonctionne pas avec Streamlit. Streamlit ne permet pas d'exécuter du JavaScript personnalisé pour modifier directement session_state.
2. Synchronisation des données manquante
La fonction sync_brief_data() n'est appelée qu'au début de l'onglet réunion, mais pas après la sauvegarde de l'avant-brief.Code corrigé - Onglet Avant-brief fonctionnelCode # Remplacez la section "ONGLET AVANT-BRIEF".

Code :import sys, os 
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

def sync_brief_data():
    """Synchronise les données du brief entre les onglets (version sécurisée)"""
    if "current_brief_name" not in st.session_state or not st.session_state.current_brief_name:
        return
        
    brief_name = st.session_state.current_brief_name
    all_briefs = load_briefs()
    
    if brief_name not in all_briefs:
        return
        
    brief_data = all_briefs[brief_name]
    
    # Liste des clés à synchroniser (uniquement les données, pas les widgets)
    data_keys_to_sync = [
        "raison_ouverture", "impact_strategique", "taches_principales",
        "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
        "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences",
        "entreprises_profil", "synonymes_poste", "canaux_profil", "rattachement", 
        "budget", "commentaires", "notes_libres"
    ]
    
    for key in data_keys_to_sync:
        if key in brief_data:
            # Vérifier si la valeur est différente avant de mettre à jour
            if key not in st.session_state or st.session_state[key] != brief_data[key]:
                st.session_state[key] = brief_data[key]
    
    # Synchroniser les liens de profils
    if "profil_links" in brief_data and brief_data["profil_links"]:
        links = brief_data["profil_links"]
        if len(links) >= 1:
            st.session_state.profil_link_1 = links[0]
        if len(links) >= 2:
            st.session_state.profil_link_2 = links[1]
        if len(links) >= 3:
            st.session_state.profil_link_3 = links[2]

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

# Style CSS pour les onglets personnalisés
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
    
    /* Style pour les sections de formulaire */
    .form-section {
        background-color: #1a1d29;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 4px solid #FF4B4B;
    }
    
    .form-section h4 {
        margin-top: 0;
        color: #FF4B4B;
        display: flex;
        align-items: center;
    }
    
    .form-section h4 .icon {
        margin-right: 10px;
        font-size: 1.2em;
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
    # ... (le code de l'onglet Gestion reste inchangé) ...

# ---------------- ONGLET AVANT-BRIEF CORRIGÉ ----------------
with tabs[1]:
    # Vérification si un brief est chargé
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.markdown(f"<h3>🔄 Avant-brief (Préparation)</h3>", unsafe_allow_html=True)
    st.subheader("📋 Portrait robot candidat")
    
    # Section Contexte du poste
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">📋</span>Contexte du poste</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Raison de l'ouverture**")
        with col2:
            st.text_area("", placeholder="Remplacement / Création / Évolution interne", 
                        key="raison_ouverture_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Mission globale**")
        with col2:
            st.text_area("", placeholder="Résumé du rôle et objectif principal", 
                        key="impact_strategique_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Tâches principales**")
        with col2:
            st.text_area("", placeholder="Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget", 
                        key="taches_principales_input", label_visibility="collapsed", height=100)
    
    # Section Must-have (Indispensables)
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">✅</span>Must-have (Indispensables)</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Expérience**")
        with col2:
            st.text_area("", placeholder="Nombre d'années minimum, expériences similaires dans le secteur", 
                        key="must_have_experience_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Connaissances / Diplômes / Certifications**")
        with col2:
            st.text_area("", placeholder="Diplômes exigés, certifications spécifiques", 
                        key="must_have_diplomes_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Compétences / Outils**")
        with col2:
            st.text_area("", placeholder="Techniques, logiciels, méthodes à maîtriser", 
                        key="must_have_competences_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Soft skills / aptitudes comportementales**")
        with col2:
            st.text_area("", placeholder="Leadership, rigueur, communication, autonomie", 
                        key="must_have_softskills_input", label_visibility="collapsed", height=100)
    
    # Section Nice-to-have (Atouts)
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">🌟</span>Nice-to-have (Atouts)</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Expérience additionnelle**")
        with col2:
            st.text_area("", placeholder="Ex. projets internationaux, multi-sites", 
                        key="nice_to_have_experience_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Diplômes / Certifications valorisantes**")
        with col2:
            st.text_area("", placeholder="Diplômes ou certifications supplémentaires appréciés", 
                        key="nice_to_have_diplomes_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Compétences complémentaires**")
        with col2:
            st.text_area("", placeholder="Compétences supplémentaires non essentielles mais appréciées", 
                        key="nice_to_have_competences_input", label_visibility="collapsed", height=100)
    
    # Section Sourcing et marché
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">🔍</span>Sourcing et marché</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Entreprises où trouver ce profil**")
        with col2:
            st.text_area("", placeholder="Concurrents, secteurs similaires", 
                        key="entreprises_profil_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Synonymes / intitulés proches**")
        with col2:
            st.text_area("", placeholder="Titres alternatifs pour affiner le sourcing", 
                        key="synonymes_poste_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Canaux à utiliser**")
        with col2:
            st.text_area("", placeholder="LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels", 
                        key="canaux_profil_input", label_visibility="collapsed", height=100)
    
    # Section Conditions et contraintes
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">📍</span>Conditions et contraintes</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Localisation**")
        with col2:
            st.text_area("", placeholder="Site principal, télétravail, déplacements", 
                        key="rattachement_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Budget recrutement**")
        with col2:
            st.text_area("", placeholder="Salaire indicatif, avantages, primes éventuelles", 
                        key="budget_input", label_visibility="collapsed", height=100)
    
    # Section Profils pertinents
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">👥</span>Profils pertinents</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Lien profil 1**")
        with col2:
            st.text_input("", placeholder="URL du profil LinkedIn ou autre", 
                         key="profil_link_1_input", label_visibility="collapsed")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Lien profil 2**")
        with col2:
            st.text_input("", placeholder="URL du profil LinkedIn ou autre", 
                         key="profil_link_2_input", label_visibility="collapsed")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Lien profil 3**")
        with col2:
            st.text_input("", placeholder="URL du profil LinkedIn ou autre", 
                         key="profil_link_3_input", label_visibility="collapsed")
    
    # Section Notes libres
    with st.container():
        st.markdown('<div class="form-section"><h4><span class="icon">📝</span>Notes libres</h4></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Points à discuter ou à clarifier avec le manager**")
        with col2:
            st.text_area("", placeholder="Points à discuter ou à clarifier", 
                        key="commentaires_input", label_visibility="collapsed", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**Case libre**")
        with col2:
            st.text_area("", placeholder="Pour tout point additionnel ou remarque spécifique", 
                        key="notes_libres_input", label_visibility="collapsed", height=100)
    
    # --- Boutons Sauvegarder et Réinitialiser ---
    col_save, col_reset = st.columns([1, 1])
    with col_save:
        if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True, key="save_avant_brief"):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
                brief_name = st.session_state.current_brief_name
                
                # Copier les valeurs des champs d'entrée vers les variables session_state
                input_fields = [
                    "raison_ouverture", "impact_strategique", "taches_principales",
                    "must_have_experience", "must_have_diplomes", "must_have_competences", "must_have_softskills",
                    "nice_to_have_experience", "nice_to_have_diplomes", "nice_to_have_competences",
                    "entreprises_profil", "synonymes_poste", "canaux_profil", "rattachement", 
                    "budget", "commentaires", "notes_libres"
                ]
                
                for field in input_fields:
                    input_key = f"{field}_input"
                    if input_key in st.session_state:
                        st.session_state[field] = st.session_state[input_key]
                
                # Sauvegarder les liens de profils
                st.session_state.profil_links = [
                    st.session_state.get("profil_link_1_input", ""),
                    st.session_state.get("profil_link_2_input", ""),
                    st.session_state.get("profil_link_3_input", "")
                ]
                
                # Mettre à jour le brief avec les données
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
                
                # Charger les briefs existants depuis le fichier
                existing_briefs = load_briefs()
                
                # Créer ou mettre à jour le brief
                if brief_name in existing_briefs:
                    existing_briefs[brief_name].update(brief_data)
                else:
                    # Ajouter les informations de base si le brief n'existe pas encore
                    existing_briefs[brief_name] = {
                        "manager_nom": st.session_state.get("manager_nom", ""),
                        "recruteur": st.session_state.get("recruteur", ""),
                        "date_brief": str(st.session_state.get("date_brief", "")),
                        "niveau_hierarchique": st.session_state.get("niveau_hierarchique", ""),
                        "brief_type": st.session_state.get("gestion_brief_type", "Brief"),
                        "affectation_type": st.session_state.get("affectation_type", ""),
                        "affectation_nom": st.session_state.get("affectation_nom", ""),
                        **brief_data
                    }
                
                # Sauvegarder les briefs
                st.session_state.saved_briefs = existing_briefs
                save_briefs()
                st.session_state.avant_brief_completed = True
                st.success("✅ Modifications sauvegardées avec succès!")
                st.rerun()
            else:
                st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
    
    with col_reset:
        if st.button("🗑️ Réinitialiser le Brief", type="secondary", use_container_width=True, key="reset_avant_brief"):
            delete_current_brief()

# ---------------- RÉUNION DE BRIEF CORRIGÉ ----------------
with tabs[2]:
    # Synchroniser les données d'abord
    sync_brief_data()
    
    # Vérification si l'onglet est accessible
    if not can_access_reunion:
        st.warning("⚠️ Veuillez d'abord compléter et sauvegarder l'onglet Avant-brief")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.subheader(f"✅ Réunion de brief avec le Manager - {st.session_state.get('niveau_hierarchique', '')}")

    total_steps = 5  # Augmenté à 5 étapes pour inclure les notes du manager
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("📋 Portrait robot candidat - Validation")
        
        # Afficher le tableau complet du portrait robot avec colonne pour commentaires
        st.markdown("""
        <table class="dark-table four-columns">
            <tr>
                <th>Section</th>
                <th>Détails</th>
                <th>Informations</th>
                <th>Commentaires du manager</th>
            </tr>
            <tr>
                <td rowspan="3" class="section-title">Contexte du poste</td>
                <td>Raison de l'ouverture</td>
                <td class="table-text">""" + (st.session_state.get("raison_ouverture") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_1"></textarea></td>
            </tr>
            <tr>
                <td>Mission globale</td>
                <td class="table-text">""" + (st.session_state.get("impact_strategique") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_2"></textarea></td>
            </tr>
            <tr>
                <td>Tâches principales</td>
                <td class="table-text">""" + (st.session_state.get("taches_principales") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_3"></textarea></td>
            </tr>
            <tr>
                <td rowspan="4" class="section-title">Must-have (Indispensables)</td>
                <td>Expérience</td>
                <td class="table-text">""" + (st.session_state.get("must_have_experience") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_4"></textarea></td>
            </tr>
            <tr>
                <td>Connaissances / Diplômes / Certifications</td>
                <td class="table-text">""" + (st.session_state.get("must_have_diplomes") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_5"></textarea></td>
            </tr>
            <tr>
                <td>Compétences / Outils</td>
                <td class="table-text">""" + (st.session_state.get("must_have_competences") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_6"></textarea></td>
            </tr>
            <tr>
                <td>Soft skills / aptitudes comportementales</td>
                <td class="table-text">""" + (st.session_state.get("must_have_softskills") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_7"></textarea></td>
            </tr>
            <tr>
                <td rowspan="3" class="section-title">Nice-to-have (Atouts)</td>
                <td>Expérience additionnelle</td>
                <td class="table-text">""" + (st.session_state.get("nice_to_have_experience") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_8"></textarea></td>
            </tr>
            <tr>
                <td>Diplômes / Certifications valorisantes</td>
                <td class="table-text">""" + (st.session_state.get("nice_to_have_diplomes") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_9"></textarea></td>
            </tr>
            <tr>
                <td>Compétences complémentaires</td>
                <td class="table-text">""" + (st.session_state.get("nice_to_have_competences") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_10"></textarea></td>
            </tr>
            <tr>
                <td rowspan="3" class="section-title">Sourcing et marché</td>
                <td>Entreprises où trouver ce profil</td>
                <td class="table-text">""" + (st.session_state.get("entreprises_profil") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_11"></textarea></td>
            </tr>
            <tr>
                <td>Synonymes / intitulés proches</td>
                <td class="table-text">""" + (st.session_state.get("synonymes_poste") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_12"></textarea></td>
            </tr>
            <tr>
                <td>Canaux à utiliser</td>
                <td class="table-text">""" + (st.session_state.get("canaux_profil") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_13"></textarea></td>
            </tr>
            <tr>
                <td rowspan="2" class="section-title">Conditions et contraintes</td>
                <td>Localisation</td>
                <td class="table-text">""" + (st.session_state.get("rattachement") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_14"></textarea></td>
            </tr>
            <tr>
                <td>Budget recrutement</td>
                <td class="table-text">""" + (st.session_state.get("budget") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_15"></textarea></td>
            </tr>
            <tr>
                <td rowspan="3" class="section-title">Profils pertinents</td>
                <td>Lien profil 1</td>
                <td class="table-text">""" + (st.session_state.get("profil_link_1") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_16"></textarea></td>
            </tr>
            <tr>
                <td>Lien profil 2</td>
                <td class="table-text">""" + (st.session_state.get("profil_link_2") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_17"></textarea></td>
            </tr>
            <tr>
                <td>Lien profil 3</td>
                <td class="table-text">""" + (st.session_state.get("profil_link_3") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_18"></textarea></td>
            </tr>
            <!-- Notes libres - seulement 2 lignes -->
            <tr>
                <td rowspan="2" class="section-title">Notes libres</td>
                <td>Points à discuter ou à clarifier avec le manager</td>
                <td class="table-text">""" + (st.session_state.get("commentaires") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_19"></textarea></td>
            </tr>
            <tr>
                <td>Case libre</td>
                <td class="table-text">""" + (st.session_state.get("notes_libres") or "Non renseigné") + """</td>
                <td><textarea class="table-textarea" placeholder="Commentaires..." key="manager_comment_20"></textarea></td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

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
                if "current_brief_name" in st.session_state and st.session_state.current_brief_name:
                    brief_name = st.session_state.current_brief_name
                    
                    # Récupérer tous les commentaires du manager
                    manager_comments = {}
                    for i in range(1, 21):  # 20 commentaires maintenant
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
                        # Créer le brief s'il n'existe pas
                        st.session_state.saved_briefs[brief_name] = {
                            "manager_nom": st.session_state.get("manager_nom", ""),
                            "recruteur": st.session_state.get("recruteur", ""),
                            "date_brief": str(st.session_state.get("date_brief", "")),
                            "niveau_hierarchique": st.session_state.get("niveau_hierarchique", ""),
                            "brief_type": st.session_state.get("gestion_brief_type", "Brief"),
                            "affectation_type": st.session_state.get("affectation_type", ""),
                            "affectation_nom": st.session_state.get("affectation_nom", ""),
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
                            "notes_libres": st.session_state.get("notes_libres", ""),
                            "profil_links": st.session_state.get("profil_links", ["", "", ""]),
                            "ksa_data": st.session_state.get("ksa_data", {}),
                            "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict(),
                            "manager_notes": st.session_state.get("manager_notes", ""),
                            "manager_comments": manager_comments,
                            "canaux_prioritaires": st.session_state.get("canaux_prioritaires", []),
                            "criteres_exclusion": st.session_state.get("criteres_exclusion", ""),
                            "processus_evaluation": st.session_state.get("processus_evaluation", "")
                        }
                    
                    save_briefs()
                    st.session_state.reunion_completed = True
                    st.success("✅ Données de réunion sauvegardées avec succès!")
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
                st.success(f"✅ Brief '{st.session_state.current_brief_name}' sauvegardé avec succès !")
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

# JavaScript pour désactiver les onglets non accessibles
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
</script>
""", unsafe_allow_html=True)