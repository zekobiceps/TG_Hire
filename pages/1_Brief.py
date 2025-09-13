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
    """Affiche la matrice KSA sous forme de tableau éditable"""
    st.subheader("📊 Matrice KSA (Knowledge, Skills, Abilities)")

    # Initialiser les données KSA si elles n'existent pas
    if "ksa_matrix" not in st.session_state:
        st.session_state.ksa_matrix = pd.DataFrame(columns=[
            "Rubrique", "Critère", "Cible / Standard attendu",
            "Échelle d'évaluation (1-5)", "Évaluateur"
        ])

    # Utiliser st.data_editor pour une édition directe et plus propre
    edited_df = st.data_editor(
        st.session_state.ksa_matrix,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rubrique": st.column_config.SelectboxColumn(
                "Rubrique",
                options=["Knowledge", "Skills", "Abilities"],
                required=True,
            ),
            "Échelle d'évaluation (1-5)": st.column_config.SelectboxColumn(
                "Importance",
                options=[1, 2, 3, 4, 5],
                required=True,
            ),
            "Évaluateur": st.column_config.SelectboxColumn(
                "Évaluateur",
                options=["Manager", "Recruteur", "Les deux"],
                required=True,
            ),
        }
    )

    # Mettre à jour le DataFrame dans la session_state
    st.session_state.ksa_matrix = edited_df

    # Calculer et afficher la note globale si le tableau n'est pas vide
    if not edited_df.empty and "Échelle d'évaluation (1-5)" in edited_df.columns:
        # Assurer que les valeurs sont numériques pour le calcul
        scores = pd.to_numeric(edited_df["Échelle d'évaluation (1-5)"], errors='coerce')
        scores = scores.dropna() # Supprimer les valeurs non-numériques
        if not scores.empty:
            moyenne = scores.mean()
            st.metric("Note globale", f"{moyenne:.1f}/5")

def render_styled_brief_table(data_dict, title, class_name="dark-table"):
    """
    Rend un tableau HTML stylisé à partir d'un dictionnaire de données.
    
    Args:
        data_dict (dict): Dictionnaire contenant les données à afficher.
        title (str): Titre du tableau.
        class_name (str): Classe CSS à appliquer au tableau.
    """
    html_content = f"<h3>{title}</h3>"
    html_content += f'<table class="{class_name}">'

    # Générer les lignes du tableau
    for section, fields in data_dict.items():
        html_content += f'<tr><td rowspan="{len(fields)}" class="section-title">{section}</td>'
        
        first_field = True
        for field, details in fields.items():
            if not first_field:
                html_content += "<tr>"
            
            # Utiliser st.session_state pour récupérer les valeurs
            value = st.session_state.get(field, details.get("default", ""))

            if details.get("type") == "textarea":
                input_field = f'<textarea class="table-textarea" placeholder="{details["placeholder"]}" id="{field}">{value}</textarea>'
            elif details.get("type") == "text":
                input_field = f'<div class="table-text">{value}</div>'
            else:
                input_field = f'<input type="text" class="table-input" placeholder="{details["placeholder"]}" value="{value}">'

            html_content += f'<td>{details["label"]}</td>'
            html_content += f'<td>{input_field}</td>'

            # Ajouter une colonne pour les commentaires si 'notes_libres' existe
            if "comment_field" in details and st.session_state.get(details["comment_field"]):
                comment_value = st.session_state.get(details["comment_field"], "")
                comment_input = f'<textarea class="table-textarea" placeholder="Commentaires du manager" id="{details["comment_field"]}">{comment_value}</textarea>'
                html_content += f'<td>{comment_input}</td>'

            # Ajouter une colonne pour le bouton d'aide si 'aid_key' existe
            if "aid_key" in details:
                 html_content += f'''
                    <td>
                        <button onclick="
                            const parent = document.getElementById('{field}').closest('.st-emotion-cache-1r6slb0');
                            const button = parent.querySelector('.stButton button[data-testid=\'{details["aid_key"]}\']');
                            if (button) button.click();
                        ">💡</button>
                    </td>
                '''

            html_content += "</tr>"
            first_field = False
    
    html_content += "</table>"
    st.markdown(html_content, unsafe_allow_html=True)
    
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
            "canaux_profil", "budget", "commentaires", "notes_libres",
            "profil_links", "ksa_matrix"
        ]

        for key in keys_to_reset:
            if key in st.session_state:
                if key == "ksa_matrix":
                    st.session_state[key] = pd.DataFrame(columns=[
                        "Rubrique", "Critère", "Cible / Standard attendu",
                        "Échelle d'évaluation (1-5)", "Évaluateur"
                    ])
                else:
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
                           if b.get("ksa_data") or (isinstance(b.get("ksa_matrix"), dict) and any(b["ksa_matrix"])))

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
    
    /* Style pour les lignes vides - correction */
    .empty-row {
        display: none;
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
        st.markdown("""
        <div class="compact-title">
            <h3 style="margin: 0; margin-right: 10px;">Informations de base</h3>
            <div style="display: flex; align-items: center;">
                <span style="margin-right: 5px; font-size: 0.9em;">Type:</span>
                <div class="custom-radio">
                    <input type="radio" id="brief" name="brief_type" value="Brief">
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

    # Synchronisation des radio buttons personnalisés avec un widget Streamlit invisible
    brief_type = st.radio("", ["Brief", "Canevas"], key="gestion_brief_type_radio", horizontal=True, label_visibility="collapsed")
    if brief_type != st.session_state.gestion_brief_type:
        st.session_state.gestion_brief_type = brief_type

    col_main, col_side = st.columns([2, 1])
    with col_main:
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            manager_nom = st.text_input("Nom du manager *", key="manager_nom", value=st.session_state.get("manager_nom", ""))
        with col2:
            niveau_hierarchique = st.text_input("Poste à recruter", key="niveau_hierarchique", value=st.session_state.get("niveau_hierarchique", ""))
        with col3:
            affectation_type = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type", index=["", "Chantier", "Siège"].index(st.session_state.get("affectation_type", "")))

        col4, col5, col6 = st.columns(3)
        with col4:
            recruteur = st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur", index=["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"].index(st.session_state.get("recruteur", "")))
        with col5:
            affectation_nom = st.text_input("Nom de l'affectation", key="affectation_nom", value=st.session_state.get("affectation_nom", ""))
        with col6:
            date_brief = st.date_input("Date du Brief *", key="date_brief", value=st.session_state.get("date_brief", datetime.today().date()))

        # --- SAUVEGARDE - Bouton étendu
        if st.button("💾 Sauvegarder", type="primary", use_container_width=True, key="save_gestion"):
            if not all([manager_nom, recruteur, date_brief]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                
                # Charger les briefs existants
                existing_briefs = load_briefs()
                st.session_state.saved_briefs = existing_briefs

                # Créer ou mettre à jour le brief
                st.session_state.saved_briefs[brief_name] = {
                    "manager_nom": manager_nom,
                    "recruteur": recruteur,
                    "date_brief": str(date_brief),
                    "niveau_hierarchique": niveau_hierarchique,
                    "brief_type": st.session_state.gestion_brief_type,
                    "affectation_type": affectation_type,
                    "affectation_nom": affectation_nom,
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
                    "ksa_matrix": st.session_state.get("ksa_matrix", pd.DataFrame()).to_dict('records')
                }
                save_briefs()
                st.success(f"✅ {st.session_state.gestion_brief_type} '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name
                st.session_state.avant_brief_completed = False
                st.session_state.reunion_completed = False

    with col_side:
        # --- RECHERCHE & CHARGEMENT
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
                                # Mettre à jour les champs de l'état de session
                                for key, value in data.items():
                                    st.session_state[key] = value

                                # Convertir la date du brief en objet date pour le widget
                                if "date_brief" in data and isinstance(data["date_brief"], str):
                                    st.session_state.date_brief = datetime.strptime(data["date_brief"], '%Y-%m-%d').date()

                                # Convertir les données KSA en DataFrame
                                if "ksa_matrix" in data and data["ksa_matrix"]:
                                    st.session_state.ksa_matrix = pd.DataFrame(data["ksa_matrix"])
                                else:
                                    st.session_state.ksa_matrix = pd.DataFrame(columns=[
                                        "Rubrique", "Critère", "Cible / Standard attendu",
                                        "Échelle d'évaluation (1-5)", "Évaluateur"
                                    ])

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

    # JavaScript pour synchroniser les radio buttons personnalisés avec Streamlit
    st.markdown("""
    <script>
    // Synchroniser les radio buttons personnalisés avec Streamlit
    document.addEventListener('DOMContentLoaded', function() {
        const radioButtons = document.querySelectorAll('.custom-radio input[type="radio"]');
        radioButtons.forEach(radio => {
            radio.addEventListener('change', function() {
                const value = this.value;
                const streamlitRadio = parent.document.querySelector('div[data-testid="stRadio"] input[value="' + value + '"]');
                if (streamlitRadio) {
                    streamlitRadio.checked = true;
                    // Simuler le clic pour déclencher l'événement Streamlit
                    const event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    streamlitRadio.dispatchEvent(event);
                }
            });
        });
        
        // Synchroniser l'état initial
        const streamlitCheckedRadio = parent.document.querySelector('div[data-testid="stRadio"] input[type="radio"]:checked');
        if (streamlitCheckedRadio) {
            const streamlitValue = streamlitCheckedRadio.value;
            const customRadio = document.querySelector('.custom-radio input[value="' + streamlitValue + '"]');
            if (customRadio) {
                customRadio.checked = true;
            }
        }
    });
    </script>
    """, unsafe_allow_html=True)

# ---------------- ONGLET AVANT-BRIEF ----------------
with tabs[1]:
    if not can_access_avant_brief:
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.stop()
        
    st.markdown("<h3>🔄 Avant-brief (Préparation)</h3>", unsafe_allow_html=True)

    # Définition de la structure du tableau pour Avant-brief
    avant_brief_data = {
        "Contexte du poste": {
            "raison_ouverture": {"label": "Raison de l'ouverture", "placeholder": "Remplacement / Création / Évolution interne", "type": "textarea"},
            "impact_strategique": {"label": "Impact stratégique du poste", "placeholder": "En quoi le rôle contribue-t-il aux objectifs de l'entreprise ?", "type": "textarea"}
        },
        "Organisation": {
            "rattachement": {"label": "Rattachement hiérarchique et équipe", "placeholder": "À qui reporte le futur collaborateur ? Avec qui collabore-t-il ?", "type": "textarea"}
        },
        "Missions & Responsabilités": {
            "taches_principales": {"label": "Tâches principales et objectifs", "placeholder": "Lister les missions principales et les objectifs clés du poste", "type": "textarea"}
        }
    }
    
    # Rendu du tableau stylisé pour Avant-brief
    st.subheader("📋 Portrait robot candidat")
    for section, fields in avant_brief_data.items():
        st.markdown(f"<h4>{section}</h4>", unsafe_allow_html=True)
        for field_key, field_details in fields.items():
            col1, col2 = st.columns([0.25, 0.75])
            with col1:
                st.markdown(f"**{field_details['label']}**", unsafe_allow_html=True)
            with col2:
                st.session_state[field_key] = st.text_area(
                    field_details['label'],
                    value=st.session_state.get(field_key, ""),
                    placeholder=field_details['placeholder'],
                    key=f"avant_{field_key}",
                    label_visibility="collapsed"
                )
                if st.button("💡", key=f"btn_avant_{field_key}"):
                    st.session_state[f"avant_{field_key}"] = generate_checklist_advice("avant_brief", field_key)
                    st.rerun()
    
    st.divider()
    
    col_ab1, col_ab2 = st.columns([0.7, 0.3])
    with col_ab1:
        if st.button("🔄 Sauvegarder Avant-brief", type="primary", use_container_width=True, key="save_avant_brief"):
            brief_name = st.session_state.current_brief_name
            if brief_name:
                st.session_state.saved_briefs[brief_name]["raison_ouverture"] = st.session_state.get("avant_raison_ouverture", "")
                st.session_state.saved_briefs[brief_name]["impact_strategique"] = st.session_state.get("avant_impact_strategique", "")
                st.session_state.saved_briefs[brief_name]["rattachement"] = st.session_state.get("avant_rattachement", "")
                st.session_state.saved_briefs[brief_name]["taches_principales"] = st.session_state.get("avant_taches_principales", "")
                save_briefs()
                st.session_state.avant_brief_completed = True
                st.success("✅ Avant-brief sauvegardé avec succès et validé. Vous pouvez passer à l'onglet 'Réunion de brief'.")
            else:
                st.error("❌ Aucun brief n'est actuellement chargé.")
    with col_ab2:
        if st.button("🗑️ Supprimer ce brief", type="secondary", use_container_width=True, key="delete_avant_brief"):
            delete_current_brief()

# ---------------- ONGLET RÉUNION DE BRIEF ----------------
with tabs[2]:
    if not can_access_reunion:
        st.warning("⚠️ Veuillez valider l'étape 'Avant-brief' pour accéder à cet onglet.")
        st.stop()
    
    st.markdown("<h3>✅ Réunion de brief (Complétion)</h3>", unsafe_allow_html=True)
    
    step_options = {
        1: "Profil & Compétences",
        2: "Sourcing & Budget",
        3: "Matrice KSA"
    }
    
    # Barre de progression
    progress_bar = st.progress(st.session_state.reunion_step / 3)
    
    st.markdown(f"### Étape {st.session_state.reunion_step}: {step_options[st.session_state.reunion_step]}")

    if st.session_state.reunion_step == 1:
        st.subheader("📚 Profil et Compétences (Must-Have & Nice-to-Have)")
        
        # Définition de la structure du tableau pour Réunion de brief - Profil
        profil_data = {
            "Must-Have (Indispensable)": {
                "must_have_experience": {"label": "Expérience", "placeholder": "Expériences clés requises...", "type": "textarea"},
                "must_have_diplomes": {"label": "Diplômes & Certifications", "placeholder": "Diplômes / Certifications spécifiques...", "type": "textarea"},
                "must_have_competences": {"label": "Compétences techniques (Hard Skills)", "placeholder": "Compétences techniques incontournables...", "type": "textarea"},
                "must_have_softskills": {"label": "Compétences comportementales (Soft Skills)", "placeholder": "Qualités interpersonnelles essentielles...", "type": "textarea"}
            },
            "Nice-to-Have (Souhaitable)": {
                "nice_to_have_experience": {"label": "Expérience", "placeholder": "Expériences appréciées mais non obligatoires...", "type": "textarea"},
                "nice_to_have_diplomes": {"label": "Diplômes & Certifications", "placeholder": "Diplômes / Certifications souhaitables...", "type": "textarea"},
                "nice_to_have_competences": {"label": "Compétences techniques (Hard Skills)", "placeholder": "Compétences techniques appréciées...", "type": "textarea"},
            }
        }
        
        for section, fields in profil_data.items():
            st.markdown(f"<h4>{section}</h4>", unsafe_allow_html=True)
            for field_key, field_details in fields.items():
                col1, col2, col3 = st.columns([0.2, 0.65, 0.15])
                with col1:
                    st.markdown(f"**{field_details['label']}**", unsafe_allow_html=True)
                with col2:
                    st.session_state[field_key] = st.text_area(
                        field_details['label'],
                        value=st.session_state.get(field_key, ""),
                        placeholder=field_details['placeholder'],
                        key=f"reunion_{field_key}",
                        label_visibility="collapsed"
                    )
                with col3:
                    if st.button("💡", key=f"btn_reunion_{field_key}"):
                        st.session_state[f"reunion_{field_key}"] = generate_checklist_advice("reunion_brief_profil", field_key)
                        st.rerun()

    elif st.session_state.reunion_step == 2:
        st.subheader("🔍 Sourcing, Budget & Divers")

        # Définition de la structure pour le Sourcing & Budget
        sourcing_data = {
            "Sourcing": {
                "entreprises_profil": {"label": "Entreprises / Secteurs cibles", "placeholder": "Exemples d'entreprises où trouver le profil", "type": "textarea"},
                "canaux_profil": {"label": "Canaux de sourcing", "placeholder": "Plateformes d'emploi, réseaux sociaux, écoles...", "type": "textarea"},
                "synonymes_poste": {"label": "Synonymes du poste", "placeholder": "Autres titres de poste pertinents pour la recherche", "type": "textarea"}
            },
            "Budget": {
                "budget": {"label": "Budget du poste", "placeholder": "Ex: 30000 - 45000", "type": "text"},
                "commentaires": {"label": "Commentaires du manager", "placeholder": "Autres notes ou commentaires importants", "type": "textarea"}
            },
            "Divers": {
                "notes_libres": {"label": "Notes libres", "placeholder": "Ajoutez des informations supplémentaires ici", "type": "textarea"},
            }
        }
        for section, fields in sourcing_data.items():
            st.markdown(f"<h4>{section}</h4>", unsafe_allow_html=True)
            for field_key, field_details in fields.items():
                col1, col2, col3 = st.columns([0.2, 0.65, 0.15])
                with col1:
                    st.markdown(f"**{field_details['label']}**", unsafe_allow_html=True)
                with col2:
                    if field_details["type"] == "textarea":
                         st.session_state[field_key] = st.text_area(
                            field_details['label'],
                            value=st.session_state.get(field_key, ""),
                            placeholder=field_details['placeholder'],
                            key=f"reunion_{field_key}",
                            label_visibility="collapsed"
                        )
                    else:
                        st.session_state[field_key] = st.text_input(
                            field_details['label'],
                            value=st.session_state.get(field_key, ""),
                            placeholder=field_details['placeholder'],
                            key=f"reunion_{field_key}",
                            label_visibility="collapsed"
                        )
                with col3:
                    if st.button("💡", key=f"btn_reunion_{field_key}"):
                        st.session_state[f"reunion_{field_key}"] = generate_checklist_advice("reunion_brief_sourcing", field_key)
                        st.rerun()
        
    elif st.session_state.reunion_step == 3:
        render_ksa_matrix()
    
    st.divider()
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.session_state.reunion_step > 1:
            if st.button("⬅️ Précédent", use_container_width=True):
                st.session_state.reunion_step -= 1
                st.rerun()
    with col_nav2:
        if st.session_state.reunion_step < 3:
            if st.button("Suivant ➡️", type="primary", use_container_width=True):
                st.session_state.reunion_step += 1
                st.rerun()
        else:
            if st.button("✅ Terminer le brief", type="primary", use_container_width=True, key="finish_brief"):
                brief_name = st.session_state.current_brief_name
                if brief_name:
                    # Mettre à jour toutes les données du brief
                    st.session_state.saved_briefs[brief_name].update({
                        "must_have_experience": st.session_state.get("reunion_must_have_experience", ""),
                        "must_have_diplomes": st.session_state.get("reunion_must_have_diplomes", ""),
                        "must_have_competences": st.session_state.get("reunion_must_have_competences", ""),
                        "must_have_softskills": st.session_state.get("reunion_must_have_softskills", ""),
                        "nice_to_have_experience": st.session_state.get("reunion_nice_to_have_experience", ""),
                        "nice_to_have_diplomes": st.session_state.get("reunion_nice_to_have_diplomes", ""),
                        "nice_to_have_competences": st.session_state.get("reunion_nice_to_have_competences", ""),
                        "entreprises_profil": st.session_state.get("reunion_entreprises_profil", ""),
                        "canaux_profil": st.session_state.get("reunion_canaux_profil", ""),
                        "synonymes_poste": st.session_state.get("reunion_synonymes_poste", ""),
                        "budget": st.session_state.get("reunion_budget", ""),
                        "commentaires": st.session_state.get("reunion_commentaires", ""),
                        "notes_libres": st.session_state.get("reunion_notes_libres", ""),
                        "ksa_matrix": st.session_state.ksa_matrix.to_dict('records') if not st.session_state.ksa_matrix.empty else []
                    })
                    save_briefs()
                    st.session_state.reunion_completed = True
                    st.success("✅ Brief finalisé et sauvegardé ! Vous pouvez maintenant passer à l'onglet 'Synthèse'.")
                    st.session_state.brief_phase = "📝 Synthèse"
                    st.rerun()
                else:
                    st.error("❌ Aucun brief n'est actuellement chargé.")
    
# ---------------- ONGLET SYNTHÈSE ----------------
with tabs[3]:
    if not can_access_synthese:
        st.warning("⚠️ Veuillez valider les étapes précédentes pour accéder à cet onglet.")
        st.stop()
        
    st.markdown("<h3>📝 Synthèse du brief</h3>", unsafe_allow_html=True)
    
    current_brief_name = st.session_state.current_brief_name
    brief_data = st.session_state.saved_briefs.get(current_brief_name)
    
    if brief_data:
        st.info(f"Fiche de brief pour : **{current_brief_name}**")
        
        st.subheader("📋 Informations Générales")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Manager:** {brief_data.get('manager_nom', 'N/A')}")
            st.markdown(f"**Recruteur:** {brief_data.get('recruteur', 'N/A')}")
        with col2:
            st.markdown(f"**Poste:** {brief_data.get('niveau_hierarchique', 'N/A')}")
            st.markdown(f"**Date:** {brief_data.get('date_brief', 'N/A')}")
        with col3:
            st.markdown(f"**Affectation:** {brief_data.get('affectation_type', 'N/A')}")
            st.markdown(f"**Nom affectation:** {brief_data.get('affectation_nom', 'N/A')}")
            
        st.divider()

        st.subheader("🔄 Avant-brief")
        st.markdown(f"**Raison de l'ouverture:** {brief_data.get('raison_ouverture', 'N/A')}")
        st.markdown(f"**Impact stratégique:** {brief_data.get('impact_strategique', 'N/A')}")
        st.markdown(f"**Rattachement:** {brief_data.get('rattachement', 'N/A')}")
        st.markdown(f"**Tâches principales:** {brief_data.get('taches_principales', 'N/A')}")
        
        st.divider()

        st.subheader("✅ Réunion de brief")
        st.markdown("**Profil & Compétences (Must-Have):**")
        st.markdown(f"**Expérience:** {brief_data.get('must_have_experience', 'N/A')}")
        st.markdown(f"**Diplômes:** {brief_data.get('must_have_diplomes', 'N/A')}")
        st.markdown(f"**Compétences techniques:** {brief_data.get('must_have_competences', 'N/A')}")
        st.markdown(f"**Compétences comportementales:** {brief_data.get('must_have_softskills', 'N/A')}")

        st.markdown("**Profil & Compétences (Nice-to-Have):**")
        st.markdown(f"**Expérience:** {brief_data.get('nice_to_have_experience', 'N/A')}")
        st.markdown(f"**Diplômes:** {brief_data.get('nice_to_have_diplomes', 'N/A')}")
        st.markdown(f"**Compétences techniques:** {brief_data.get('nice_to_have_competences', 'N/A')}")
        
        st.markdown("**Sourcing & Budget:**")
        st.markdown(f"**Entreprises / Secteurs cibles:** {brief_data.get('entreprises_profil', 'N/A')}")
        st.markdown(f"**Canaux de sourcing:** {brief_data.get('canaux_profil', 'N/A')}")
        st.markdown(f"**Synonymes du poste:** {brief_data.get('synonymes_poste', 'N/A')}")
        st.markdown(f"**Budget du poste:** {brief_data.get('budget', 'N/A')}")
        st.markdown(f"**Notes du manager:** {brief_data.get('commentaires', 'N/A')}")
        st.markdown(f"**Notes libres:** {brief_data.get('notes_libres', 'N/A')}")

        st.subheader("📊 Matrice KSA")
        ksa_matrix_data = brief_data.get("ksa_matrix", [])
        if ksa_matrix_data:
            df_ksa = pd.DataFrame(ksa_matrix_data)
            st.dataframe(df_ksa, hide_index=True, use_container_width=True)
        else:
            st.info("Aucune matrice KSA n'a été complétée.")

        st.divider()

        st.subheader("📥 Export du brief")
        col_export1, col_export2, col_export3 = st.columns([0.4, 0.4, 0.2])
        if PDF_AVAILABLE:
            with col_export1:
                if st.button("Export en PDF 📄", use_container_width=True):
                    pdf_output = export_brief_pdf(brief_data)
                    st.download_button(
                        label="Télécharger le PDF",
                        data=pdf_output,
                        file_name=f"brief_{current_brief_name}.pdf",
                        mime="application/pdf"
                    )
        if WORD_AVAILABLE:
            with col_export2:
                if st.button("Export en Word 📝", use_container_width=True):
                    word_output = export_brief_word(brief_data)
                    st.download_button(
                        label="Télécharger le Word",
                        data=word_output,
                        file_name=f"brief_{current_brief_name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
        with col_export3:
            if st.button("🗑️ Supprimer ce brief", type="secondary", use_container_width=True, key="delete_synthese"):
                delete_current_brief()
    else:
        st.error("❌ Le brief n'a pas pu être chargé. Veuillez retourner à l'onglet 'Gestion'.")