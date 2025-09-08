import sys, os
import streamlit as st
from datetime import datetime
import json

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

# ---------------- FONCTIONS MANQUANTES ----------------
def conseil_button(titre, categorie, conseil, key):
    """Crée un bouton avec conseil pour un champ"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_area(titre, key=key)
    with col2:
        if st.button("💡", key=f"btn_{key}"):
            st.session_state[key] = generate_checklist_advice(categorie, titre)
            st.rerun()

def render_ksa_section():
    """Affiche la section KSA (Knowledge, Skills, Abilities)"""
    st.info("Matrice des compétences requises (KSA)")
    
    if "ksa_data" not in st.session_state:
        st.session_state.ksa_data = {
            "Connaissances": {},
            "Compétences": {},
            "Aptitudes": {}
        }
    
    with st.expander("➕ Ajouter une compétence"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_cat = st.selectbox("Catégorie", ["Connaissances", "Compétences", "Aptitudes"], key="new_cat")
        with col2:
            new_comp = st.text_input("Compétence", key="new_comp")
        with col3:
            new_score = st.slider("Importance", 1, 5, 3, key="new_score")
        
        if st.button("Ajouter", key="add_comp"):
            if new_comp:
                st.session_state.ksa_data[new_cat][new_comp] = {"score": new_score}
                st.success(f"✅ {new_comp} ajouté à {new_cat}")
                st.rerun()
    
    for categorie, competences in st.session_state.ksa_data.items():
        with st.expander(f"{categorie} ({len(competences)})"):
            if competences:
                for comp, details in competences.items():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{comp}**")
                    with col2:
                        st.write(f"Importance: {details.get('score', 'N/A')}/5")
                    with col3:
                        if st.button("🗑️", key=f"del_{categorie}_{comp}"):
                            del st.session_state.ksa_data[categorie][comp]
                            st.rerun()
            else:
                st.info("Aucune compétence définie")

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
        
        # Choix entre créer un brief ou un canevas
        creation_type = st.radio("Type de création", ["Créer un brief", "Créer un canevas"], horizontal=True)
        
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Nom du manager *", key="manager_nom")
        with col2:
            st.text_input("Poste à recruter *", key="niveau_hierarchique")
            # Date du Brief placée à droite du recruteur
            st.date_input("Date du Brief *", key="date_brief", value=datetime.today().date())
        with col3:
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
            st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type")
            st.text_input("Nom de l'affectation", key="affectation_nom")
        
        # Placeholder pour les messages d'erreur/confirmation
        message_placeholder = st.empty()

        # --- SAUVEGARDE
        if st.button("💾 Sauvegarder le Brief", type="primary", use_container_width=True):
            # Utiliser niveau_hierarchique comme intitulé du poste
            st.session_state.poste_intitule = st.session_state.niveau_hierarchique
            
            if not all([st.session_state.niveau_hierarchique, st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                message_placeholder.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                brief_name = generate_automatic_brief_name()
                if "saved_briefs" not in st.session_state:
                    st.session_state.saved_briefs = {}
                
                st.session_state.saved_briefs[brief_name] = {
                    "poste_intitule": st.session_state.niveau_hierarchique,
                    "manager_nom": st.session_state.manager_nom,
                    "recruteur": st.session_state.recruteur,
                    "date_brief": str(st.session_state.date_brief),
                    "niveau_hierarchique": st.session_state.niveau_hierarchique,
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
                    "creation_type": creation_type
                }
                save_briefs()
                message_placeholder.success(f"✅ {creation_type} '{brief_name}' sauvegardé avec succès !")
                st.session_state.current_brief_name = brief_name
                st.session_state.brief_created = True

    with col_side:
        st.subheader("Recherche & Chargement")
        
        # --- RECHERCHE & CHARGEMENT (2 colonnes)
        col1, col2 = st.columns(2)
        with col1:
            months = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            month = st.selectbox("Mois", months)
            poste = st.text_input("Poste")
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
                
                # Filtrage par recruteur
                if recruteur and recruteur != "" and data.get("recruteur") != recruteur:
                    continue
                
                # Filtrage par poste
                if poste and poste != "" and poste.lower() not in data.get("poste_intitule", "").lower():
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
            for name, data in st.session_state.filtered_briefs.items():
                with st.expander(f"📌 {name}"):
                    st.write(f"**Poste:** {data.get('poste_intitule', '')}")
                    st.write(f"**Manager:** {data.get('manager_nom', '')}")
                    st.write(f"**Recruteur:** {data.get('recruteur', '')}")
                    st.write(f"**Type:** {data.get('creation_type', 'Brief')}")
                    st.write(f"**Affectation:** {data.get('affectation_type', '')} - {data.get('affectation_nom', '')}")
                    st.write(f"**Date:** {data.get('date_brief', '')}")
                    
                    colA, colB = st.columns(2)
                    with colA:
                        if st.button(f"📂 Charger", key=f"load_{name}"):
                            try:
                                # Stocker les données sans modifier directement les widgets
                                st.session_state.current_brief_data = data
                                st.session_state.current_brief_name = name
                                st.session_state.brief_created = True
                                
                                # Mettre à jour les champs non-widgets
                                non_widget_keys = ["raison_ouverture", "impact_strategique", "rattachement", 
                                                  "defis_principaux", "entreprises_profil", "canaux_profil",
                                                  "synonymes_poste", "budget", "commentaires"]
                                
                                for key in non_widget_keys:
                                    if key in data:
                                        st.session_state[key] = data[key]
                                
                                # Gestion spéciale pour les données KSA
                                if "ksa_data" in data:
                                    st.session_state.ksa_data = data["ksa_data"]
                                
                                st.success(f"✅ {data.get('creation_type', 'Brief')} '{name}' chargé avec succès!")
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
                                st.warning(f"❌ {data.get('creation_type', 'Brief')} '{name}' supprimé.")
                                st.rerun()

# ---------------- AVANT-BRIEF ----------------
with tab2:
    # Vérification si un brief a été créé
    if not st.session_state.get("brief_created", False):
        st.warning("⚠️ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        st.stop()
    
    # Afficher les informations du brief en cours
    poste_info = st.session_state.get('niveau_hierarchique', 'Non défini')
    manager_info = st.session_state.get('manager_nom', 'Non défini')
    recruteur_info = st.session_state.get('recruteur', 'Non défini')
    affectation_info = st.session_state.get('affectation_nom', 'Non défini')
    
    # Nouveau format d'en-tête
    st.subheader(f"🔄 Avant-brief (Préparation) - {poste_info} - {manager_info} - {recruteur_info} - {affectation_info}")

    # Méthode rapide (15-30 min) - Jeu des 7 différences
    with st.expander("⚡️ Méthode rapide (15-30 min) - Jeu des 7 différences"):
        st.markdown("""
        **Confronter les infos données par le manager aux données du terrain.**
        
        L'idée : identifier les incohérences ou les angles morts.
        
        Concentrez-vous en priorité :
        
        1. **Sur l'adéquation intitulé de poste / missions** - Vérifiez que les autres sources décrivent les mêmes missions pour l'intitulé de poste donné par le manager (peut-être du jargon interne).
        
        2. **Sur les critères demandés** (diplômes, expérience, tâches à maîtriser, compétences sociales) - Comparez avec les profils réels sur le marché.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Intitulé de poste vs Missions réelles", key="verif_intitule", height=100)
        with col2:
            st.text_area("Critères demandés vs Réalité marché", key="verif_criteres", height=100)

    # Méthode complète (30min-1h)
    with st.expander("🧠 Méthode complète (30min-1h) - Analyse comparative"):
        st.markdown("""
        **Remplir ce tableau avec 2-3 sources**
        """)
        
        # Tableau d'analyse comparative amélioré
        st.markdown("""
        <table class="comparison-table">
            <tr>
                <th>Catégories</th>
                <th>Mes infos de départ</th>
                <th>Source 1</th>
                <th>Source 2</th>
                <th>Source 3</th>
            </tr>
            <tr>
                <td>Intitulé du poste</td>
                <td><input type="text" style="width: 100%;"></td>
                <td><input type="text" style="width: 100%;"></td>
                <td><input type="text" style="width: 100%;"></td>
                <td><input type="text" style="width: 100%;"></td>
            </tr>
            <tr>
                <td>Les tâches/missions</td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
            </tr>
            <tr>
                <td>Les connaissances</td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
            </tr>
            <tr>
                <td>Diplômes/certifications demandés</td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
            </tr>
            <tr>
                <td>Les compétences et outils à maîtriser</td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
            </tr>
            <tr>
                <td>Salaires, avantages et plus values</td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
                <td><textarea style="width: 100%; height: 60px;"></textarea></td>
            </tr>
        </table>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**Points à éclaircir avec le manager**")
        st.text_area("Questions pour ouvrir la discussion", key="questions_discussion", height=100)

    # Disposition en colonnes pour les champs simples
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_area("Raison ouverture", key="raison_ouverture", height=100)
        st.text_area("Impact stratégique", key="impact_strategique", height=100)
        st.text_area("Rattachement hiérarchique", key="rattachement", height=100)
        st.text_area("Défis principaux", key="defis_principaux", height=100)
    
    with col2:
        st.text_area("Entreprises où trouver ce profil", key="entreprises_profil", height=100)
        st.text_area("Canaux à utiliser", key="canaux_profil", height=100)
        st.text_area("Synonymes de postes", key="synonymes_poste", height=100)
        st.text_input("Budget", key="budget")
    
    # Commentaires libres en bas
    st.text_area("Commentaires libres", key="commentaires", height=100)

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_name = st.session_state.current_brief_name
            st.session_state.saved_briefs[brief_name].update({
                "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                "impact_strategique": st.session_state.get("impact_strategique", ""),
                "rattachement": st.session_state.get("rattachement", ""),
                "defis_principaux": st.session_state.get("defis_principaux", ""),
                "entreprises_profil": st.session_state.get("entreprises_profil", ""),
                "canaux_profil": st.session_state.get("canaux_profil", ""),
                "synonymes_poste": st.session_state.get("synonymes_poste", ""),
                "budget": st.session_state.get("budget", ""),
                "commentaires": st.session_state.get("commentaires", ""),
                "verif_intitule": st.session_state.get("verif_intitule", ""),
                "verif_criteres": st.session_state.get("verif_criteres", ""),
                "questions_discussion": st.session_state.get("questions_discussion", "")
            })
            
            save_briefs()
            st.session_state.avant_brief_saved = True
            st.success("✅ Modifications sauvegardées")
        else:
            st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

# ---------------- RÉUNION (Wizard interne) ----------------
with tab3:
    # Vérification si l'avant-brief a été sauvegardé
    if not st.session_state.get("avant_brief_saved", False):
        st.warning("⚠️ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        st.stop()
    
    # Afficher les informations du brief en cours
    poste_info = st.session_state.get('niveau_hierarchique', 'Non défini')
    manager_info = st.session_state.get('manager_nom', 'Non défini')
    recruteur_info = st.session_state.get('recruteur', 'Non défini')
    affectation_info = st.session_state.get('affectation_nom', 'Non défini')
    
    # Nouveau format d'en-tête
    st.subheader(f"✅ Réunion de brief avec le Manager - {poste_info} - {manager_info} - {recruteur_info} - {affectation_info}")

    total_steps = 4
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("1️⃣ Incidents Critiques")
        st.text_area("Réussite exceptionnelle - Contexte", key="reussite_contexte", height=100)
        st.text_area("Réussite exceptionnelle - Actions", key="reussite_actions", height=100)
        st.text_area("Réussite exceptionnelle - Résultat", key="reussite_resultat", height=100)
        st.text_area("Échec significatif - Contexte", key="echec_contexte", height=100)
        st.text_area("Échec significatif - Causes", key="echec_causes", height=100)
        st.text_area("Échec significatif - Impact", key="echec_impact", height=100)

    elif step == 2:
        st.subheader("2️⃣ Questions Comportementales")
        st.text_area("Comment le candidat devrait-il gérer [situation difficile] ?", key="comp_q1", height=100)
        st.text_area("Réponse attendue", key="comp_rep1", height=100)
        st.text_area("Compétences évaluées", key="comp_eval1", height=100)

    elif step == 3:
        st.subheader("3️⃣ Validation Matrice KSA")
        render_ksa_section()

    elif step == 4:
        st.subheader("4️⃣ Stratégie Recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation", "Réseaux sociaux", "Chasse de tête"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion", height=100)
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation", height=100)

        if st.button("💾 Enregistrer réunion", type="primary", use_container_width=True):
            if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
                brief_name = st.session_state.current_brief_name
                st.session_state.saved_briefs[brief_name].update({
                    "ksa_data": st.session_state.get("ksa_data", {})
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
        st.warning("⚠️ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")
        st.stop()
    
    # Afficher les informations du brief en cours
    poste_info = st.session_state.get('niveau_hierarchique', 'Non défini')
    manager_info = st.session_state.get('manager_nom', 'Non défini')
    recruteur_info = st.session_state.get('recruteur', 'Non défini')
    affectation_info = st.session_state.get('affectation_nom', 'Non défini')
    
    # Nouveau format d'en-tête
    st.subheader(f"📝 Synthèse - {poste_info} - {manager_info} - {recruteur_info} - {affectation_info}")
    
    st.subheader("Résumé des informations")
    st.json({
        "Poste": st.session_state.get("niveau_hierarchique", ""),
        "Manager": st.session_state.get("manager_nom", ""),
        "Recruteur": st.session_state.get("recruteur", ""),
        "Affectation": f"{st.session_state.get('affectation_type','')} - {st.session_state.get('affectation_nom','')}",
        "Date": str(st.session_state.get("date_brief", "")),
        "Raison ouverture": st.session_state.get("raison_ouverture", ""),
        "Impact stratégique": st.session_state.get("impact_strategique", ""),
        "Défis principaux": st.session_state.get("defis_principaux", ""),
        "Entreprises profil": st.session_state.get("entreprises_profil", ""),
        "Canaux": st.session_state.get("canaux_profil", ""),
        "Budget": st.session_state.get("budget", ""),
    })

    st.subheader("📊 Calcul automatique du Score Global")
    score_total = 0
    count = 0
    if "ksa_data" in st.session_state:
        for cat, comps in st.session_state.ksa_data.items():
            for comp, details in comps.items():
                score_total += int(details.get("score") or 0)
                count += 1
    score_global = (score_total / count) if count else 0
    st.metric("Score Global Cible", f"{score_global:.2f}/5")

    if st.button("💾 Confirmer sauvegarde", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state:
            save_briefs()
            st.success(f"✅ Brief sauvegardé avec succès !")
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