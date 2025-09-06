import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote
from datetime import datetime
import json
import os

# -------------------- Configuration initiale --------------------
def init_session_state():
    """Initialise les variables de session"""
    if "api_usage" not in st.session_state:
        st.session_state.api_usage = {
            "current_session_tokens": 0,
            "used_tokens": 0
        }
    if "library_entries" not in st.session_state:
        st.session_state.library_entries = []
    if "magicien_history" not in st.session_state:
        st.session_state.magicien_history = []
    if "boolean_query" not in st.session_state:
        st.session_state.boolean_query = ""
    if "xray_query" not in st.session_state:
        st.session_state.xray_query = ""
    if "cse_query" not in st.session_state:
        st.session_state.cse_query = ""
    if "dogpile_query" not in st.session_state:
        st.session_state.dogpile_query = ""
    if "scraper_result" not in st.session_state:
        st.session_state.scraper_result = ""
    if "scraper_emails" not in st.session_state:
        st.session_state.scraper_emails = set()
    if "inmail_message" not in st.session_state:
        st.session_state.inmail_message = ""
    if "perm_result" not in st.session_state:
        st.session_state.perm_result = []

def save_library_entries():
    """Sauvegarde les entrées de la bibliothèque (simulation)"""
    pass

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

def generate_accroche_inmail(url_linkedin, poste_accroche):
    """Génère un message InMail"""
    return f"""Bonjour,

Votre profil sur LinkedIn a retenu mon attention, particulièrement votre expérience dans le domaine.

Je me permets de vous contacter concernant une opportunité de {poste_accroche} qui correspond parfaitement à votre profil. Votre expertise serait un atout précieux pour notre équipe.

Seriez-vous ouvert à un échange pour discuter de cette opportunité ?

Dans l'attente de votre retour,"""

def ask_deepseek(messages, max_tokens=300):
    """Simule l'appel à l'API DeepSeek"""
    time.sleep(2)  # Simulation de délai
    question = messages[0]["content"]
    
    # Réponses simulées selon le type de question
    if "synonymes" in question.lower():
        return {"content": "Ingénieur travaux, Chef de chantier, Conducteur de travaux, Responsable de projet BTP, Manager construction"}
    elif "outils" in question.lower() or "logiciels" in question.lower():
        return {"content": "• AutoCAD\n• Revit\n• Primavera P6\n• MS Project\n• Robot Structural Analysis\n• SketchUp"}
    elif "compétences" in question.lower():
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

# -------------------- Initialisation --------------------
init_session_state()
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques")
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.metric("🔑 Tokens (session)", used)
    st.metric("📊 Total cumulé", total)
    st.divider()
    st.info("💡 Assistant IA pour le sourcing et recrutement")

# -------------------- Onglets --------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Boolean", "🎯 X-Ray", "🔎 CSE LinkedIn", "🐶 Dogpile", 
    "🕷️ Web Scraper", "✉️ InMail", "🤖 Magicien", "📧 Permutateur", "📚 Bibliothèque"
])

# -------------------- Tab 1: Boolean Search --------------------
with tab1:
    st.header("🔍 Recherche Boolean")
    
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="poste", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes:", key="synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires", placeholder="Ex: Autocad, Robot Structural Analysis")
        secteur = st.text_input("Secteur d'activité:", key="secteur", placeholder="Ex: BTP, Construction")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles", placeholder="Ex: Primavera, ArchiCAD")
        exclusions = st.text_input("Mots à exclure:", key="exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="localisation", placeholder="Ex: Casablanca")
        employeur = st.text_input("Employeur:", key="employeur", placeholder="Ex: TGCC")

    if st.button("🪄 Générer la requête Boolean", type="primary", use_container_width=True):
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
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)
        
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

# -------------------- Tab 2: X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")

    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray", placeholder="Ex: Développeur Python")
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray", placeholder="Ex: Django, Flask")
    with col2:
        localisation_xray = st.text_input("Localisation:", key="localisation_xray", placeholder="Ex: Casablanca")
        exclusions_xray = st.text_input("Mots à exclure:", key="exclusions_xray", placeholder="Ex: Stage, Junior")

    if st.button("🔍 Construire X-Ray", type="primary", use_container_width=True):
        with st.spinner("⏳ Génération en cours..."):
            start_time = time.time()
            st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
            if exclusions_xray:
                st.session_state["xray_query"] += f' -("{exclusions_xray}")'
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
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

# -------------------- Tab 3: CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    
    col1, col2 = st.columns(2)
    with col1:
        poste_cse = st.text_input("Poste recherché:", key="poste_cse", placeholder="Ex: Développeur Python")
        competences_cse = st.text_input("Compétences clés:", key="competences_cse", placeholder="Ex: Django, Flask")
    with col2:
        localisation_cse = st.text_input("Localisation:", key="localisation_cse", placeholder="Ex: Casablanca")
        entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse", placeholder="Ex: TGCC")

    if st.button("🔍 Lancer recherche CSE", type="primary", use_container_width=True):
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
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        
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

# -------------------- Tab 4: Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    
    query = st.text_input("Requête Dogpile:", key="dogpile_input", placeholder="Ex: Python developer Casablanca")
    
    if st.button("🔍 Rechercher", key="dogpile_search", type="primary", use_container_width=True):
        if query:
            st.session_state["dogpile_query"] = query
            st.success("✅ Requête enregistrée")
    
    if st.session_state.get("dogpile_query"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_query"], height=80)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="dogpile_save", use_container_width=True):
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

# -------------------- Tab 5: Web Scraper --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    
    url = st.text_input("URL à analyser:", key="scraper_url", placeholder="https://exemple.com")

    if st.button("🚀 Scraper", use_container_width=True):
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
        st.text_area("Extrait du contenu:", value=st.session_state["scraper_result"], height=200)
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

# -------------------- Tab 6: InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail Personnalisé")

    # Ligne 1 : URL + Entreprise + Ton du message
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url", 
                                     placeholder="https://linkedin.com/in/nom-prenom")
    with col2:
        entreprise = st.selectbox("Entreprise:", [
            "TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL",
            "TG STONE", "TGEM", "TGCC Immobilier"
        ], key="inmail_entreprise")
    with col3:
        ton_message = st.selectbox("Ton du message:", 
                                   ["Persuasif", "Professionnel", "Convivial", "Direct"], 
                                   key="inmail_ton")

    # Ligne 2 : Poste + Longueur + Méthode d'analyse
    col4, col5, col6 = st.columns([2, 2, 2])
    with col4:
        poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste", 
                                      placeholder="Ex: Directeur Administratif et Financier")
    with col5:
        longueur_message = st.slider("Longueur (mots):", 50, 300, 150, key="inmail_longueur")
    with col6:
        methode_analyse = st.selectbox("Méthode d'analyse:", 
                                       ["API PDL", "Regex", "Manuel"], key="inmail_methode")

    # Ligne 3 : Genre + Call to Action
    col7, col8 = st.columns([2, 2])
    with col7:
        genre_profil = st.selectbox("Genre du profil:", ["Masculin", "Féminin"], key="inmail_genre")
    with col8:
        cta_option = st.selectbox("Call to Action (Conclusion):", [
            "Proposer un appel",
            "Partager le CV",
            "Découvrir l'opportunité sur notre site",
            "Accepter un rendez-vous"
        ], key="inmail_cta")

    # ---------------- Analyse Profil ----------------
    def analyser_profil(url, methode="Manuel"):
        """Analyse du profil selon la méthode choisie"""
        donnees = {
            "prenom": "Candidat",
            "nom": "",
            "poste_actuel": "",
            "entreprise_actuelle": "",
            "competences_cles": ["", "", ""],
            "experience_annees": "",
            "formation": "",
            "localisation": ""
        }

        if methode == "Regex" and "/in/" in url:
            parts = url.split("/in/")[1].split("/")[0].split('-')
            if parts:
                donnees["prenom"] = parts[0].title()
                donnees["nom"] = " ".join([p.title() for p in parts[1:] if len(p) > 1])

        elif methode == "API PDL":
            try:
                api_key = "de89b8bc7ad232693f6817010b409f3c384736971b8c876f379472778e8c17d1"
                resp = requests.get(
                    "https://api.peopledatalabs.com/v5/person/enrich",
                    params={"profile": url},
                    headers={"X-Api-Key": api_key}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data:
                        p = data["data"]
                        donnees["prenom"] = p.get("first_name", "Candidat")
                        donnees["nom"] = p.get("last_name", "")
                        donnees["poste_actuel"] = p.get("job_title", "")
                        donnees["entreprise_actuelle"] = p.get("job_company_name", "")
                        donnees["localisation"] = p.get("location_name", "")
                        skills = p.get("skills", [])
                        if skills:
                            donnees["competences_cles"] = skills[:3]
            except Exception as e:
                st.error(f"Erreur API PDL: {e}")

        return donnees

    def generate_cta(cta_type, prenom, genre):
        """Génère la conclusion avec genre du profil"""
        suffix = "" if genre == "Masculin" else "e"
        if cta_type == "Proposer un appel":
            return f"Seriez-vous disponible{suffix} pour un appel cette semaine ?"
        elif cta_type == "Partager le CV":
            return f"Accepteriez-vous de partager votre CV afin d'avancer ?"
        elif cta_type == "Découvrir l'opportunité sur notre site":
            return f"Souhaiteriez-vous consulter plus de détails sur notre site carrière ?"
        elif cta_type == "Accepter un rendez-vous":
            return f"Seriez-vous disponible{suffix} pour un rendez-vous afin d’échanger ?"
        return ""

    def generate_inmail(donnees, poste, entreprise, ton, genre, max_words, cta_type):
        """Génération du texte InMail"""
        prenom = donnees.get("prenom", "Candidat")
        cta_text = generate_cta(cta_type, prenom, genre)

        base_msg = f"Bonjour {prenom},\n\nVotre parcours semble correspondre au poste de {poste} au sein de {entreprise}.\n\n{cta_text}"

        words = base_msg.split()
        if len(words) > max_words:
            base_msg = " ".join(words[:max_words]) + "..."
        return base_msg

    # ---------------- Bouton Générer ----------------
    if st.button("🚀 Générer", type="primary", use_container_width=True):
        donnees_profil = analyser_profil(url_linkedin, methode_analyse)
        st.session_state["inmail_profil_data"] = donnees_profil

        result = generate_inmail(
            donnees=donnees_profil,
            poste=poste_accroche,
            entreprise=entreprise,
            ton=ton_message,
            genre=genre_profil,
            max_words=longueur_message,
            cta_type=cta_option
        )
        st.session_state["inmail_message"] = result
        st.session_state["inmail_generated"] = True

    # ---------------- Résultat ----------------
    if st.session_state.get("inmail_generated"):
        st.divider()
        st.subheader("📝 Message InMail Personnalisé")

        # Expander modifiable toujours affiché
        with st.expander("📊 Informations du profil analysé (modifiables)", expanded=True):
            edited = st.session_state.get("inmail_profil_data", {}).copy()
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                edited["prenom"] = st.text_input("Prénom:", value=edited["prenom"], key="edit_prenom")
                edited["poste_actuel"] = st.text_input("Poste actuel:", value=edited["poste_actuel"], key="edit_poste")
            with col_b:
                edited["nom"] = st.text_input("Nom:", value=edited["nom"], key="edit_nom")
                edited["entreprise_actuelle"] = st.text_input("Entreprise actuelle:", value=edited["entreprise_actuelle"], key="edit_entreprise")
            with col_c:
                edited["experience_annees"] = st.text_input("Expérience:", value=edited["experience_annees"], key="edit_exp")
                edited["formation"] = st.text_input("Formation:", value=edited["formation"], key="edit_form")

            edited["competences_cles"][0] = st.text_input("Compétence 1:", value=edited["competences_cles"][0], key="comp1")
            edited["competences_cles"][1] = st.text_input("Compétence 2:", value=edited["competences_cles"][1], key="comp2")
            edited["competences_cles"][2] = st.text_input("Compétence 3:", value=edited["competences_cles"][2], key="comp3")

            if st.button("💾 Appliquer les modifications"):
                st.session_state["inmail_profil_data"] = edited
                st.rerun()

        # Zone message
        message = st.session_state.get("inmail_message", "")
        st.text_area("✉️ Message:", value=message, height=250)

        # Actions
        col_x, col_y = st.columns(2)
        with col_x:
            if st.button("🔄 Régénérer avec modifications"):
                result = generate_inmail(
                    donnees=st.session_state["inmail_profil_data"],
                    poste=poste_accroche,
                    entreprise=entreprise,
                    ton=ton_message,
                    genre=genre_profil,
                    max_words=longueur_message,
                    cta_type=cta_option
                )
                st.session_state["inmail_message"] = result
                st.rerun()
        with col_y:
            if st.button("💾 Sauvegarder"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "InMail",
                    "poste": poste_accroche,
                    "requete": f"Message personnalisé - {poste_accroche}"
                }
                if 'library_entries' not in st.session_state:
                    st.session_state.library_entries = []
                st.session_state.library_entries.append(entry)
                st.success("✅ Sauvegardé")

# -------------------- Tab 7: Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de",
        "Quels outils ou logiciels sont liés au métier de",
        "Quels mots-clés pour cibler les juniors pour le poste de",
        "Quels intitulés similaires au poste de",
        "Quels critères éliminatoires fréquents pour le poste de",
        "Quels secteurs d'activité embauchent souvent pour le poste de",
        "Quelles certifications utiles pour le métier de",
        "Quels intitulés de poste équivalents dans le marché marocain pour",
        "Quels rôles proches à considérer lors du sourcing pour",
        "Quelles tendances de recrutement récentes pour le métier de"
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", [""] + questions_pretes, key="magicien_qchoice")
    
    if q_choice:
        default_question = q_choice
    else:
        default_question = ""
    
    question = st.text_area("Modifiez la question si nécessaire :", 
                          value=default_question, 
                          key="magicien_question", 
                          height=100,
                          placeholder="Posez votre question ici...")

    mode_rapide_magicien = st.checkbox("⚡ Mode rapide (réponse concise)", key="magicien_fast")

    if st.button("✨ Poser la question", type="primary", key="ask_magicien", use_container_width=True):
        if question:
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
                enhanced_question = question
                if "synonymes" in question.lower():
                    enhanced_question += ". Réponds uniquement avec une liste de synonymes séparés par des virgules, sans introduction."
                elif "outils" in question.lower() or "logiciels" in question.lower():
                    enhanced_question += ". Réponds avec une liste à puces des outils, sans introduction."
                elif "compétences" in question.lower() or "skills" in question.lower():
                    enhanced_question += ". Réponds avec une liste à puces, sans introduction."
                
                result = ask_deepseek([{"role": "user", "content": enhanced_question}], 
                                     max_tokens=150 if mode_rapide_magicien else 300)
                
                total_time = int(time.time() - start_time)
                st.success(f"✅ Réponse générée en {total_time}s")
                
                st.session_state.magicien_history.append({
                    "q": question, 
                    "r": result["content"], 
                    "time": total_time
                })
        else:
            st.warning("⚠️ Veuillez poser une question")

    if st.session_state.get("magicien_history"):
        st.subheader("📝 Historique des réponses")
        for i, item in enumerate(st.session_state.magicien_history[::-1]):
            with st.expander(f"❓ {item['q']} ({item['time']}s)"):
                st.write(item["r"])
                if st.button("🗑️ Supprimer", key=f"del_magicien_{i}"):
                    st.session_state.magicien_history.remove(item)
                    st.rerun()
        
        if st.button("🧹 Supprimer tout", key="clear_magicien_all", use_container_width=True):
            st.session_state.magicien_history.clear()
            st.success("✅ Historique vidé")
            st.rerun()

# -------------------- Tab 8: Permutateur --------------------
with tab8:
    st.header("📧 Permutateur Email")

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Jean")
        nom = st.text_input("Nom:", key="perm_nom", placeholder="Dupont")
    with col2:
        entreprise = st.text_input("Entreprise:", key="perm_entreprise", placeholder="TGCC")
        source = st.radio("Source de détection :", ["Site officiel", "Charika.ma"], key="perm_source", horizontal=True)

    if st.button("🔮 Générer permutations", use_container_width=True):
        if prenom and nom and entreprise:
            with st.spinner("⏳ Génération des permutations..."):
                start_time = time.time()
                permutations = []
                detected = get_email_from_charika(entreprise) if source == "Charika.ma" else None
                
                if detected:
                    st.info(f"📧 Format détecté : {detected}")
                    domain = detected.split("@")[1]
                else:
                    domain = f"{entreprise.lower().replace(' ', '')}.ma"
                
                # Génération des permutations
                patterns = [
                    f"{prenom.lower()}.{nom.lower()}@{domain}",
                    f"{prenom[0].lower()}{nom.lower()}@{domain}",
                    f"{nom.lower()}.{prenom.lower()}@{domain}",
                    f"{prenom.lower()}{nom.lower()}@{domain}",
                    f"{prenom.lower()}-{nom.lower()}@{domain}",
                    f"{nom.lower()}{prenom[0].lower()}@{domain}",
                    f"{prenom[0].lower()}.{nom.lower()}@{domain}",
                    f"{nom.lower()}.{prenom[0].lower()}@{domain}"
                ]
                
                total_time = time.time() - start_time
                st.session_state["perm_result"] = list(set(patterns))
                st.success(f"✅ {len(patterns)} permutations générées en {total_time:.1f}s")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs")

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("🔍 Tester sur : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

# -------------------- Tab 9: Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    
    if st.session_state.library_entries:
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔎 Rechercher:", placeholder="Rechercher par poste ou requête")
        with col2:
            sort_by = st.selectbox("📌 Trier par:", ["Date récente", "Date ancienne", "Type", "Poste"], key="sort_by")

        entries = st.session_state.library_entries
        
        if search_term:
            entries = [e for e in entries if search_term.lower() in e["requete"].lower() or 
                     search_term.lower() in e["poste"].lower() or search_term.lower() in e["type"].lower()]

        if sort_by == "Type":
            entries = sorted(entries, key=lambda x: x["type"])
        elif sort_by == "Poste":
            entries = sorted(entries, key=lambda x: x["poste"])
        elif sort_by == "Date ancienne":
            entries = sorted(entries, key=lambda x: x["date"])
        else:
            entries = sorted(entries, key=lambda x: x["date"], reverse=True)

        st.info(f"📊 {len(entries)} recherche(s) trouvée(s)")
        
        for i, entry in enumerate(entries):
            with st.expander(f"{entry['date']} - {entry['type']} - {entry['poste']}"):
                st.text_area("Requête:", value=entry['requete'], height=100, key=f"req_{i}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Supprimer", key=f"del_{i}"):
                        st.session_state.library_entries.remove(entry)
                        save_library_entries()
                        st.success("✅ Recherche supprimée")
                        st.rerun()
                with col2:
                    if entry['type'] == 'Boolean':
                        url = f"https://www.linkedin.com/search/results/people/?keywords={quote(entry['requete'])}"
                        st.link_button("🌐 Ouvrir", url)
                    elif entry['type'] == 'X-Ray':
                        url = f"https://www.google.com/search?q={quote(entry['requete'])}"
                        st.link_button("🌐 Ouvrir", url)
    else:
        st.info("📝 Aucune recherche sauvegardée pour le moment")

# -------------------- CSS pour masquer le prompt en bas --------------------
st.markdown("""
    <style>
    .stTextArea textarea[aria-label*='Modifiez la question'] {
        display: none;
    }
    .stTextArea label[aria-label*='Modifiez la question'] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)