import sys, os
import streamlit as st
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote
import hashlib

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

# -------------------- FONCTIONS SOURCING --------------------
def generate_boolean_query(poste, synonymes, competences_obligatoires, 
                          competences_optionnelles, exclusions, localisation, secteur):
    """Génère une requête boolean"""
    query_parts = []
    if poste: query_parts.append(f'"{poste}"')
    if synonymes: query_parts.append(f'("{synonymes}")')
    if competences_obligatoires: query_parts.append(f'("{competences_obligatoires}")')
    if competences_optionnelles: query_parts.append(f'("{competences_optionnelles}" OR "{competences_optionnelles}")')
    if localisation: query_parts.append(f'"{localisation}"')
    if secteur: query_parts.append(f'"{secteur}"')
    if exclusions: query_parts.append(f'NOT ("{exclusions}")')
    
    return " AND ".join(query_parts)

def generate_xray_query(site_cible, poste, mots_cles, localisation):
    """Génère une requête X-Ray"""
    site_map = {"LinkedIn": "site:linkedin.com/in", "GitHub": "site:github.com"}
    site = site_map.get(site_cible, "site:linkedin.com/in")
    
    query_parts = [site]
    if poste: query_parts.append(f'"{poste}"')
    if mots_cles: query_parts.append(f'"{mots_cles}"')
    if localisation: query_parts.append(f'"{localisation}"')
    
    return " ".join(query_parts)

def ask_deepseek(messages, max_tokens=300):
    """Simule l'appel à l'API DeepSeek"""
    time.sleep(1)  # Simulation de délai
    question = messages[0]["content"].lower()
    
    if "synonymes" in question:
        return {"content": "Ingénieur travaux, Chef de chantier, Conducteur de travaux, Responsable de projet BTP, Manager construction"}
    elif "outils" in question or "logiciels" in question:
        return {"content": "• AutoCAD\n• Revit\n• Primavera P6\n• MS Project\n• Robot Structural Analysis\n• SketchUp"}
    elif "compétences" in question:
        return {"content": "• Gestion de projet\n• Lecture de plans techniques\n• Management d'équipe\n• Budget et planning\n• Conformité réglementaire\n• Négociation fournisseurs"}
    else:
        return {"content": "Voici des informations pertinentes concernant votre demande. N'hésitez pas à préciser votre question pour une réponse plus ciblée."}

def get_email_from_charika(entreprise):
    """Simule la détection de format d'email depuis Charika"""
    formats = [
        "prenom.nom@entreprise.com",
        "pnom@entreprise.com",
        "prenom@entreprise.com",
        "nom.prenom@entreprise.com",
        "initialenom@entreprise.com"
    ]
    return formats[0]

def save_library_entries():
    """Sauvegarde les entrées de la bibliothèque (simulation)"""
    pass

# ---------------- FONCTIONS BRIEF EXISTANTES ----------------
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

# ---------------- INITIALISATION --------------------
init_session_state()

# Initialiser les variables de sourcing
sourcing_defaults = {
    "api_usage": {"current_session_tokens": 0, "used_tokens": 0},
    "library_entries": [],
    "magicien_history": [],
    "boolean_query": "",
    "xray_query": "",
    "cse_query": "",
    "dogpile_query": "",
    "scraper_result": "",
    "scraper_emails": set(),
    "inmail_message": "",
    "perm_result": [],
    "inmail_objet": "",
    "inmail_generated": False,
    "inmail_profil_data": {},
}

for k, v in sourcing_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.set_page_config(page_title="TG-Hire IA - Brief", page_icon="🤖", layout="wide")

if "brief_phase" not in st.session_state:
    st.session_state.brief_phase = "📁 Gestion"

if "sourcing_tab" not in st.session_state:
    st.session_state.sourcing_tab = "🔍 Boolean"

if "reunion_step" not in st.session_state:
    st.session_state.reunion_step = 1

if "filtered_briefs" not in st.session_state:
    st.session_state.filtered_briefs = {}

# ---------------- NAVIGATION PRINCIPALE ----------------
st.title("💡 Briefs") 

# ============ ONGLETS DE SOURCING EN HAUT ============
st.markdown("### Outils de Sourcing")

# Onglets de sourcing
sourcing_tabs = [
    "🔍 Boolean", "🎯 X-Ray", "🔎 CSE LinkedIn", "🐶 Dogpile", 
    "🕷️ Web Scraper", "✉️ InMail", "🤖 Magicien", "📧 Permutateur", "📚 Bibliothèque"
]

# CSS pour les onglets de sourcing
st.markdown("""
    <style>
    .sourcing-nav {
        border-bottom: 2px solid #0066cc;
        margin-bottom: 20px;
        padding-bottom: 10px;
    }
    .sourcing-nav .stButton > button {
        background-color: #0066cc !important;
        color: white !important;
        border: none !important;
        margin-right: 5px !important;
        border-radius: 5px !important;
        font-size: 12px !important;
        padding: 5px 8px !important;
    }
    .sourcing-nav .stButton > button:hover {
        background-color: #0052a3 !important;
    }
    .active-sourcing-tab {
        background-color: #004d99 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# Navigation des onglets de sourcing
with st.container():
    st.markdown('<div class="sourcing-nav">', unsafe_allow_html=True)
    cols_sourcing = st.columns(len(sourcing_tabs))
    
    for i, tab_name in enumerate(sourcing_tabs):
        with cols_sourcing[i]:
            if st.button(tab_name, key=f"sourcing_{i}"):
                st.session_state.sourcing_tab = tab_name
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ============ CONTENU DES ONGLETS DE SOURCING ============
if st.session_state.sourcing_tab == "🔍 Boolean":
    st.header("🔍 Recherche Boolean")
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="boolean_poste", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes:", key="boolean_synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="boolean_comp_oblig", placeholder="Ex: Autocad, Robot Structural Analysis")
        secteur = st.text_input("Secteur d'activité:", key="boolean_secteur", placeholder="Ex: BTP, Construction")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="boolean_comp_opt", placeholder="Ex: Primavera, ArchiCAD")
        exclusions = st.text_input("Mots à exclure:", key="boolean_exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="boolean_loc", placeholder="Ex: Casablanca")
        employeur = st.text_input("Employeur:", key="boolean_employeur", placeholder="Ex: TGCC")

    if st.button("🪄 Générer la requête Boolean", type="primary", use_container_width=True, key="boolean_generate"):
        with st.spinner("⏳ Génération en cours..."):
            start_time = time.time()
            st.session_state["boolean_query"] = generate_boolean_query(
                poste, synonymes, competences_obligatoires,
                competences_optionnelles, exclusions, localisation, secteur
            )
            if employeur:
                st.session_state["boolean_query"] += f' AND ("{employeur}")'
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120, key="boolean_area")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="boolean_save", use_container_width=True):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "Boolean", 
                    "poste": poste, 
                    "requete": st.session_state["boolean_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
            st.link_button("🌐 Ouvrir sur LinkedIn", url_linkedin, use_container_width=True)

elif st.session_state.sourcing_tab == "🎯 X-Ray":
    st.header("🎯 X-Ray Google")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="xray_site")
        poste_xray = st.text_input("Poste:", key="xray_poste", placeholder="Ex: Développeur Python")
        mots_cles = st.text_input("Mots-clés:", key="xray_mots_cles", placeholder="Ex: Django, Flask")
    with col2:
        localisation_xray = st.text_input("Localisation:", key="xray_loc", placeholder="Ex: Casablanca")
        exclusions_xray = st.text_input("Mots à exclure:", key="xray_exclusions", placeholder="Ex: Stage, Junior")

    if st.button("🔍 Construire X-Ray", type="primary", use_container_width=True, key="xray_build"):
        with st.spinner("⏳ Génération en cours..."):
            start_time = time.time()
            st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
            if exclusions_xray:
                st.session_state["xray_query"] += f' -("{exclusions_xray}")'
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120, key="xray_area")
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="xray_save", use_container_width=True):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "X-Ray",
                    "poste": poste_xray, 
                    "requete": st.session_state["xray_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            st.link_button("🌐 Ouvrir sur Google", url, use_container_width=True)
        with col3:
            st.link_button("🔎 Recherche avancée", f"https://www.google.com/advanced_search?q={quote(st.session_state['xray_query'])}", use_container_width=True)

elif st.session_state.sourcing_tab == "🔎 CSE LinkedIn":
    st.header("🔎 CSE LinkedIn")
    col1, col2 = st.columns(2)
    with col1:
        poste_cse = st.text_input("Poste recherché:", key="cse_poste", placeholder="Ex: Développeur Python")
        competences_cse = st.text_input("Compétences clés:", key="cse_comp", placeholder="Ex: Django, Flask")
    with col2:
        localisation_cse = st.text_input("Localisation:", key="cse_loc", placeholder="Ex: Casablanca")
        entreprise_cse = st.text_input("Entreprise:", key="cse_ent", placeholder="Ex: TGCC")

    if st.button("🔍 Lancer recherche CSE", type="primary", use_container_width=True, key="cse_search"):
        with st.spinner("⏳ Construction de la requête..."):
            start_time = time.time()
            query_parts = []
            if poste_cse: query_parts.append(poste_cse)
            if competences_cse: query_parts.append(competences_cse)
            if localisation_cse: query_parts.append(localisation_cse)
            if entreprise_cse: query_parts.append(entreprise_cse)
            st.session_state["cse_query"] = " ".join(query_parts)
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100, key="cse_area")
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="cse_save", use_container_width=True):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "CSE", 
                    "poste": poste_cse, 
                    "requete": st.session_state["cse_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
            st.link_button("🌐 Ouvrir sur CSE", cse_url, use_container_width=True)

elif st.session_state.sourcing_tab == "🐶 Dogpile":
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", key="dogpile_query_input", placeholder="Ex: Python developer Casablanca")
    if st.button("🔍 Rechercher", key="dogpile_search_btn", type="primary", use_container_width=True):
        if query:
            st.session_state["dogpile_query"] = query
            st.success("✅ Requête enregistrée")
    if st.session_state.get("dogpile_query"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_query"], height=80, key="dogpile_area")
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="dogpile_save_btn", use_container_width=True):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "Dogpile", 
                    "poste": "Recherche Dogpile", 
                    "requete": st.session_state["dogpile_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            dogpile_url = f"http://www.dogpile.com/serp?q={quote(st.session_state['dogpile_query'])}"
            st.link_button("🌐 Ouvrir sur Dogpile", dogpile_url, use_container_width=True)

elif st.session_state.sourcing_tab == "🕷️ Web Scraper":
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choice")
    url = st.text_input("URL à analyser:", key="scraper_url", placeholder="https://exemple.com")
    if st.button("🚀 Scraper", use_container_width=True, key="scraper_btn"):
        if url:
            try:
                with st.spinner("⏳ Scraping en cours..."):
                    start_time = time.time()
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    soup = BeautifulSoup(r.text, "html.parser")
                    texte = soup.get_text()[:1200]
                    emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte))
                    st.session_state["scraper_result"] = texte
                    st.session_state["scraper_emails"] = emails
                    total_time = time.time() - start_time
                    st.success(f"✅ Scraping terminé en {total_time:.1f}s - {len(emails)} email(s) trouvé(s)")
            except Exception as e:
                st.error(f"❌ Erreur scraping : {e}")
    if st.session_state.get("scraper_result"):
        st.text_area("Extrait du contenu:", value=st.session_state["scraper_result"], height=200, key="scraper_area")
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

elif st.session_state.sourcing_tab == "✉️ InMail":
    st.header("✉️ Générateur d'InMail Personnalisé")
    st.info("Fonctionnalité InMail intégrée - Version simplifiée")
    
    col1, col2 = st.columns(2)
    with col1:
        url_linkedin = st.text_input("Profil LinkedIn", key="inmail_url_brief", placeholder="linkedin.com/in/nom-prenom")
        poste_accroche = st.text_input("Poste à pourvoir", key="inmail_poste_brief", placeholder="Ex: Directeur Financier")
    with col2:
        entreprise = st.selectbox("Entreprise", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise_brief")
        ton_message = st.selectbox("Ton du message", ["Persuasif", "Professionnel", "Convivial", "Direct"], key="inmail_ton_brief")
    
    if st.button("✨ Générer InMail", type="primary", use_container_width=True, key="generate_inmail_brief"):
        if poste_accroche and entreprise:
            message_simple = f"""Bonjour,

Votre profil sur LinkedIn a retenu mon attention, particulièrement votre expérience dans le domaine.

Je me permets de vous contacter concernant une opportunité de {poste_accroche} au sein de {entreprise}. Votre expertise serait un atout précieux pour notre équipe.

Seriez-vous ouvert à un échange pour discuter de cette opportunité ?

Dans l'attente de votre retour,"""
            
            st.text_area("Message InMail généré:", value=message_simple, height=200, key="inmail_result_brief")
        else:
            st.error("Veuillez remplir au minimum le poste et l'entreprise")

elif st.session_state.sourcing_tab == "🤖 Magicien":
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de",
        "Quels outils ou logiciels sont liés au métier de",
        "Quels mots-clés pour cibler les juniors pour le poste de",
        "Quels intitulés similaires au poste de",
        "Quels critères éliminatoires fréquents pour le poste de",
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", [""] + questions_pretes, key="magicien_qchoice_brief")
    
    if q_choice:
        default_question = q_choice
    else:
        default_question = ""
    
    question = st.text_area("Modifiez la question si nécessaire :", 
                          value=default_question, 
                          key="magicien_question_brief", 
                          height=100,
                          placeholder="Posez votre question ici...")

    if st.button("✨ Poser la question", type="primary", key="ask_magicien_brief", use_container_width=True):
        if question:
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
                result = ask_deepseek([{"role": "user", "content": question}], max_tokens=300)
                total_time = int(time.time() - start_time)
                st.success(f"✅ Réponse générée en {total_time}s")
                
                st.session_state.magicien_history.append({
                    "q": question, 
                    "r": result["content"], 
                    "time": total_time
                })
                
                st.text_area("Réponse:", value=result["content"], height=150, key=f"magicien_response_{len(st.session_state.magicien_history)}")
        else:
            st.warning("⚠️ Veuillez poser une question")

elif st.session_state.sourcing_tab == "📧 Permutateur":
    st.header("📧 Permutateur Email")

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom:", key="perm_prenom_brief", placeholder="Jean")
        nom = st.text_input("Nom:", key="perm_nom_brief", placeholder="Dupont")
    with col2:
        entreprise = st.text_input("Entreprise:", key="perm_entreprise_brief", placeholder="TGCC")

    if st.button("🔮 Générer permutations", use_container_width=True, key="perm_generate_brief"):
        if prenom and nom and entreprise:
            with st.spinner("⏳ Génération des permutations..."):
                domain = f"{entreprise.lower().replace(' ', '')}.ma"
                
                patterns = [
                    f"{prenom.lower()}.{nom.lower()}@{domain}",
                    f"{prenom[0].lower()}{nom.lower()}@{domain}",
                    f"{nom.lower()}.{prenom.lower()}@{domain}",
                    f"{prenom.lower()}{nom.lower()}@{domain}",
                    f"{prenom.lower()}-{nom.lower()}@{domain}",
                ]
                
                st.session_state["perm_result"] = list(set(patterns))
                st.success(f"✅ {len(patterns)} permutations générées")
                
                st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150, key="perm_results_brief")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs")

elif st.session_state.sourcing_tab == "📚 Bibliothèque":
    st.header("📚 Bibliothèque des recherches")
    
    if st.session_state.library_entries:
        st.info(f"📊 {len(st.session_state.library_entries)} recherche(s) sauvegardée(s)")
        
        for i, entry in enumerate(st.session_state.library_entries[-5:]):  # Afficher les 5 dernières
            with st.expander(f"{entry['date']} - {entry['type']} - {entry['poste']}"):
                st.text_area("Requête:", value=entry['requete'], height=80, key=f"lib_req_{i}")
    else:
        st.info("📝 Aucune recherche sauvegardée pour le moment")

# ============ SÉPARATEUR VISUEL ============
st.markdown("---")
st.markdown("### Gestion des Briefs")

# ============ NAVIGATION BRIEFS (existante) ============
onglets = {
    "Gestion": "📁 Gestion", 
    "Avant-brief": "🔄 Avant-brief",
    "Réunion de brief": "✅ Réunion de brief",
    "Synthèse": "📝 Synthèse"
}

# Style CSS pour le menu de navigation et les boutons
st.markdown("""
    <style>
    /* Cache les onglets par défaut de Streamlit */
    .st-emotion-cache-16ya5a5 { 
        display: none !important;
    }

    /* Conteneur principal des boutons de navigation pour le style de la ligne */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) > div[data-testid="stHorizontalBlock"] {
        border-bottom: 3px solid #ff4b4b; /* Ligne rouge vif */
        padding-bottom: 0px; 
        margin-bottom: 0px; 
    }

    /* Conteneur des colonnes individuelles de navigation */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex-grow: 0 !important; /* Empêche les colonnes de prendre de l'espace supplémentaire */
        flex-shrink: 0 !important; /* Empêche les colonnes de rétrécir */
        flex-basis: auto !important; /* La taille est basée sur le contenu */
        width: auto !important; /* Largeur automatique */
        padding-left: 0px !important; /* Pas de padding à gauche */
        padding-right: 0px !important; /* Pas de padding à droite */
        margin-right: 5px !important; /* Petite marge entre les boutons pour les séparer légèrement */
    }

    /* Styles généraux pour tous les boutons de navigation (non-actifs et actifs) */
    .stButton > button {
        background-color: #D20000 !important; /* Rouge plus foncé pour les onglets inactifs */
        color: white !important; 
        border: none !important;
        box-shadow: none !important;
        font-size: 14px !important;
        padding: 5px 10px !important; /* Réduit le padding pour rapprocher texte/bord */
        border-radius: 0px !important; /* Coins carrés */
        white-space: nowrap; /* Empêche le texte de passer à la ligne */
        margin: 0 !important; /* Annule toutes les marges */
        display: inline-flex; /* Permet un bon alignement icône/texte et le rapprochement */
        align-items: center;
        justify-content: center;
        gap: 5px; /* Espace entre icône et texte */
        height: auto !important; /* La hauteur s'ajuste au contenu */
    }
    
    /* Style pour le bouton de navigation ACTIF */
    .stButton > button.active-tab {
        background-color: #ff4b4b !important; /* Rouge vif pour le bouton actif */
        color: white !important;
        font-weight: bold !important;
        border-bottom: 3px solid #ff4b4b !important; /* Ligne rouge vif en dessous */
        margin-bottom: -3px !important; /* Soulève légèrement pour couvrir la ligne du conteneur */
    }
    </style>
""", unsafe_allow_html=True)

# Créer les colonnes pour les boutons de navigation
cols = st.columns(len(onglets)) 
    
for i, (key_label, full_label) in enumerate(onglets.items()):
    with cols[i]:
        is_active = (st.session_state.brief_phase == full_label)
        
        if st.button(full_label, key=f"tab_{key_label}", use_container_width=False):
            st.session_state.brief_phase = full_label
            st.rerun()
        
        if is_active:
            st.markdown(f"""
                <script>
                var buttonElement = document.querySelector('[data-testid="stVerticalBlock"] > div:nth-child(2) > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child({i+1}) button');
                if (buttonElement) {{
                    buttonElement.classList.add("active-tab");
                }}
                </script>
            """, unsafe_allow_html=True)

# ---------------- ONGLET GESTION ----------------
if st.session_state.brief_phase == "📁 Gestion":
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
            st.selectbox("Recruteur *", ["", "Zakaria", "Sara", "Sara", "Jalal", "Bouchra", "Ghita"], key="recruteur")
        with col3:
            st.selectbox("Affectation", ["", "Chantier", "Siège"], key="affectation_type")
            st.text_input("Nom de l'affectation", key="affectation_nom")
        
        st.date_input("Date du Brief *", key="date_brief", value=datetime.today().date()) 

        # --- SAUVEGARDE
        if st.button("💾 Sauvegarder le Brief", type="primary", use_container_width=True):
            if not all([st.session_state.poste_intitule, st.session_state.manager_nom, st.session_state.recruteur, st.session_state.date_brief]):
                st.error("Veuillez remplir tous les champs obligatoires (*)")
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
                    "ksa_data": st.session_state.get("ksa_data", {})
                }
                save_briefs()
                st.success(f"✅ Brief '{brief_name}' sauvegardé avec succès !")
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
            affectation = st.selectbox("Affectation", ["", "Chantier", "Siège"], key="search_affectation")

        if st.button("🔎 Rechercher", type="secondary", use_container_width=True):
            briefs = load_briefs()
            st.session_state.filtered_briefs = filter_briefs(briefs, month, recruteur, poste, manager, affectation)
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
                            safe_keys = [k for k in data.keys() if k not in ['ksa_data'] or data[k]]
                            for k in safe_keys:
                                if k in data and data[k]:
                                    st.session_state[k] = data[k]
                            st.session_state.current_brief_name = name
                            st.success(f"✅ Brief '{name}' chargé avec succès!")
                            st.rerun()
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
elif st.session_state.brief_phase == "🔄 Avant-brief":
    st.subheader("🔄 Avant-brief (Préparation)")
    st.info("Remplissez les informations préparatoires avant la réunion avec le manager.")

    conseil_button("Raison ouverture", "Contexte", "Pourquoi ce poste est-il ouvert?", key="raison_ouverture")
    conseil_button("Impact stratégique", "Contexte", "Impact stratégique du poste", key="impact_strategique")
    st.text_area("Rattachement hiérarchique", key="rattachement")
    st.text_area("Défis principaux", key="defis_principaux")

    if st.button("💾 Sauvegarder Avant-brief", type="primary", use_container_width=True):
        if "current_brief_name" in st.session_state and st.session_state.current_brief_name in st.session_state.saved_briefs:
            brief_name = st.session_state.current_brief_name
            st.session_state.saved_briefs[brief_name].update({
                "raison_ouverture": st.session_state.get("raison_ouverture", ""),
                "impact_strategique": st.session_state.get("impact_strategique", ""),
                "rattachement": st.session_state.get("rattachement", ""),
                "defis_principaux": st.session_state.get("defis_principaux", "")
            })
            save_briefs()
            st.success("✅ Modifications sauvegardées")
        else:
            st.error("❌ Veuillez d'abord créer et sauvegarder un brief dans l'onglet Gestion")

# ---------------- RÉUNION (Wizard interne) ----------------
elif st.session_state.brief_phase == "✅ Réunion de brief":
    st.subheader("✅ Réunion de brief avec le Manager")

    total_steps = 4
    step = st.session_state.reunion_step
    st.progress(int((step / total_steps) * 100), text=f"Étape {step}/{total_steps}")

    if step == 1:
        st.subheader("1️⃣ Incidents Critiques")
        st.text_area("Réussite exceptionnelle - Contexte", key="reussite_contexte")
        st.text_area("Réussite exceptionnelle - Actions", key="reussite_actions")
        st.text_area("Réussite exceptionnelle - Résultat", key="reussite_resultat")
        st.text_area("Échec significatif - Contexte", key="echec_contexte")
        st.text_area("Échec significatif - Causes", key="echec_causes")
        st.text_area("Échec significatif - Impact", key="echec_impact")

    elif step == 2:
        st.subheader("2️⃣ Questions Comportementales")
        st.text_area("Comment le candidat devrait-il gérer [situation difficile] ?", key="comp_q1")
        st.text_area("Réponse attendue", key="comp_rep1")
        st.text_area("Compétences évaluées", key="comp_eval1")

    elif step == 3:
        st.subheader("3️⃣ Validation Matrice KSA")
        render_ksa_section()

    elif step == 4:
        st.subheader("4️⃣ Stratégie Recrutement")
        st.multiselect("Canaux prioritaires", ["LinkedIn", "Jobboards", "Cooptation"], key="canaux_prioritaires")
        st.text_area("Critères d'exclusion", key="criteres_exclusion")
        st.text_area("Processus d'évaluation (détails)", key="processus_evaluation")

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
elif st.session_state.brief_phase == "📝 Synthèse":
    st.subheader("📝 Synthèse du Brief")
    
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
            st.success("✅ Brief final confirmé et sauvegardé")
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