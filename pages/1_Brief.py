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
        
        # --- INFOS DE BASE (3 colonnes)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Intitulé du poste *", key="poste_intitule")
            st.text_input("Nom du manager *", key="manager_nom")
        with col2:
            st.text_input("Poste à recruter", key="niveau_hierarchique")
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
        with col3:
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
                    "ksa_data": st.session_state.get("ksa_data", {})
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
                                                  "synonymes_poste", "budget", "commentaires"]
                                
                                for key in non_widget_keys:
                                    if key in data:
                                        st.session_state[key] = data[key]
                                
                                # Gestion spéciale pour les données KSA
                                if "ksa_data" in data:
                                    st.session_state.ksa_data = data["ksa_data"]
                                
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

# ---------------- AVANT-BRIEF ----------------
with tab2:
    # Vérification si un brief est chargé
    if "current_brief_name" not in st.session_state or st.session_state.current_brief_name == "":
        st.warning("⚠️ Veuillez d'abord créer ou charger un brief dans l'onglet Gestion")
        st.info("💡 Utilisez l'onglet Gestion pour créer un nouveau brief ou charger un template existant")
        st.stop()  # Arrête le rendu de cet onglet
    
    # Afficher les informations du brief en cours
    st.subheader(f"🔄 Avant-brief (Préparation) - {st.session_state.get('poste_intitule', '')}")
    st.info(f"Manager: {st.session_state.get('manager_nom', '')} | Recruteur: {st.session_state.get('recruteur', '')}")
    
    st.info("Remplissez les informations préparatoires avant la réunion avec le manager.")

    # Organisation structurée sous forme de tableau
    with st.expander("📋 Organisation structurée du poste", expanded=True):
        st.markdown("""
        <style>
        .custom-table {
            width: 100%;
            border-collapse: collapse;
        }
        .custom-table th, .custom-table td {
            border: 1px solid #424242;
            padding: 8px;
            text-align: left;
        }
        .custom-table th {
            background-color: #262730;
            font-weight: bold;
        }
        .section-col {
            width: 20%;
        }
        .details-col {
            width: 40%;
        }
        .info-col {
            width: 40%;
        }
        .info-textarea {
            width: 100%;
            height: 120px;
            background-color: #262730;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
        }
        </style>
        
        <table class="custom-table">
            <tr>
                <th class="section-col">Section</th>
                <th class="details-col">Détails</th>
                <th class="info-col">Infos de départ</th>
            </tr>
            <tr>
                <td><strong>Contexte du poste</strong></td>
                <td>
                    Raison de l'ouverture: Remplacement / Création / Évolution interne<br><br>
                    Mission globale: Résumé du rôle et objectif principal<br><br>
                    Défis principaux: Ex. gestion de projet complexe, coordination multi-sites, respect délais et budget
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Raison de l'ouverture..." 
                              onfocus="if(this.value==''){this.value='Raison de l\\'ouverture: '}" 
                              onblur="if(this.value=='Raison de l\\'ouverture: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Mission globale..." 
                              onfocus="if(this.value==''){this.value='Mission globale: '}" 
                              onblur="if(this.value=='Mission globale: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Défis principaux..." 
                              onfocus="if(this.value==''){this.value='Défis principaux: '}" 
                              onblur="if(this.value=='Défis principaux: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Organisation et hiérarchie</strong></td>
                <td>
                    Rattachement hiérarchique: Responsable direct, département / service<br><br>
                    Équipe: Taille, rôle des collaborateurs, interaction avec autres services
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Rattachement hiérarchique..." 
                              onfocus="if(this.value==''){this.value='Rattachement hiérarchique: '}" 
                              onblur="if(this.value=='Rattachement hiérarchique: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Équipe..." 
                              onfocus="if(this.value==''){this.value='Équipe: '}" 
                              onblur="if(this.value=='Équipe: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Profil recherché</strong></td>
                <td>
                    Expérience: Nombre d'années minimum, expériences similaires dans le secteur<br><br>
                    Connaissances / Diplômes / Certifications: Diplômes exigés, certifications spécifiques<br><br>
                    Compétences / Outils: Techniques, logiciels, méthodes à maîtriser<br><br>
                    Soft skills / aptitudes comportementales: Leadership, rigueur, communication, autonomie
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Expérience..." 
                              onfocus="if(this.value==''){this.value='Expérience: '}" 
                              onblur="if(this.value=='Expérience: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Connaissances/Diplômes/Certifications..." 
                              onfocus="if(this.value==''){this.value='Connaissances/Diplômes/Certifications: '}" 
                              onblur="if(this.value=='Connaissances/Diplômes/Certifications: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Compétences/Outils..." 
                              onfocus="if(this.value==''){this.value='Compétences/Outils: '}" 
                              onblur="if(this.value=='Compétences/Outils: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Soft skills..." 
                              onfocus="if(this.value==''){this.value='Soft skills: '}" 
                              onblur="if(this.value=='Soft skills: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Sourcing et marché</strong></td>
                <td>
                    Entreprises où trouver ce profil: Concurrents, secteurs similaires<br><br>
                    Synonymes / intitulés proches: Titres alternatifs pour affiner le sourcing<br><br>
                    Canaux à utiliser: LinkedIn, jobboards, cabinet, cooptation, réseaux professionnels
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Entreprises où trouver ce profil..." 
                              onfocus="if(this.value==''){this.value='Entreprises où trouver ce profil: '}" 
                              onblur="if(this.value=='Entreprises où trouver ce profil: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Synonymes de postes..." 
                              onfocus="if(this.value==''){this.value='Synonymes de postes: '}" 
                              onblur="if(this.value=='Synonymes de postes: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Canaux à utiliser..." 
                              onfocus="if(this.value==''){this.value='Canaux à utiliser: '}" 
                              onblur="if(this.value=='Canaux à utiliser: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Conditions et contraintes</strong></td>
                <td>
                    Localisation: Site principal, télétravail, déplacements<br><br>
                    Budget recrutement: Salaire indicatif, avantages, primes éventuelles
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Localisation..." 
                              onfocus="if(this.value==''){this.value='Localisation: '}" 
                              onblur="if(this.value=='Localisation: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Budget recrutement..." 
                              onfocus="if(this.value==''){this.value='Budget recrutement: '}" 
                              onblur="if(this.value=='Budget recrutement: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Missions / Tâches</strong></td>
                <td>
                    Tâches principales: 4-6 missions détaillées<br><br>
                    Autres responsabilités: Points additionnels ou spécifiques à préciser
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Tâches principales..." 
                              onfocus="if(this.value==''){this.value='Tâches principales: '}" 
                              onblur="if(this.value=='Tâches principales: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Autres responsabilités..." 
                              onfocus="if(this.value==''){this.value='Autres responsabilités: '}" 
                              onblur="if(this.value=='Autres responsabilités: '){this.value=''}"></textarea>
                </td>
            </tr>
            <tr>
                <td><strong>Notes libres</strong></td>
                <td>
                    Points à discuter ou à clarifier avec le manager<br><br>
                    Case libre: Pour tout point additionnel ou remarque spécifique
                </td>
                <td>
                    <textarea class="info-textarea" placeholder="Points à discuter..." 
                              onfocus="if(this.value==''){this.value='Points à discuter: '}" 
                              onblur="if(this.value=='Points à discuter: '){this.value=''}"></textarea>
                    <textarea class="info-textarea" placeholder="Case libre..." 
                              onfocus="if(this.value==''){this.value='Case libre: '}" 
                              onblur="if(this.value=='Case libre: '){this.value=''}"></textarea>
                </td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_name = st.session_state.current_brief_name
            # Ici vous devriez ajouter la logique pour récupérer les données des textareas
            # et les sauvegarder dans st.session_state.saved_briefs[brief_name]
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