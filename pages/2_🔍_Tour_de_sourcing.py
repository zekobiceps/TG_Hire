import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote
from datetime import datetime
import json
import os
import hashlib
import pandas as pd
from collections import Counter


# -------------------- Configuration initiale --------------------
def init_session_state():
    """Initialise les variables de session"""
    defaults = {
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
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

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
    """Génère un message InMail basique"""
    return f"""Bonjour,

Votre profil sur LinkedIn a retenu mon attention, particulièrement votre expérience dans le domaine.

Je me permets de vous contacter concernant une opportunité de {poste_accroche} qui correspond parfaitement à votre profil. Votre expertise serait un atout précieux pour notre équipe.

Seriez-vous ouvert à un échange pour discuter de cette opportunité ?

Dans l'attente de votre retour,"""

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

# -------------------- Tab 2: X-Ray --------------------
with tab2:
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

# -------------------- Tab 3: CSE --------------------
with tab3:
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

# -------------------- Tab 4: Dogpile --------------------
with tab4:
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

# -------------------- Tab 5: Web Scraper - Analyse Concurrentielle --------------------
# -------------------- Tab 5: Web Scraper - Analyse Concurrentielle --------------------
with tab5:
    st.header("🔍 Analyse Concurrentielle - Offres d'Emploi")
    
    # Configuration du scraping
    with st.expander("⚙️ Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            concurrents = st.text_area(
                "Sites des concurrents à analyser (1 par ligne):", 
                placeholder="https://www.entreprise1.com/carrieres\nhttps://www.entreprise2.com/emplois",
                height=100
            )
            max_pages = st.slider("Nombre maximum de pages à analyser par site:", 1, 20, 5)
        
        with col2:
            mots_cles = st.text_input(
                "Mots-clés à rechercher (séparés par des virgules):",
                placeholder="data scientist, python, cloud, IA"
            )
            delay = st.slider("Délai entre les requêtes (secondes):", 1, 10, 3)
    
    # Options d'analyse
    with st.expander("📊 Options d'analyse", expanded=False):
        analyse_options = st.multiselect(
            "Éléments à analyser:",
            ["Compétences recherchées", "Niveaux d'expérience", "Avantages proposés", 
             "Types de contrats", "Localisations", "Salaires mentionnés", "Processus de recrutement"],
            default=["Compétences recherchées", "Niveaux d'expérience", "Avantages proposés"]
        )
    
    if st.button("🚀 Lancer l'analyse concurrentielle", use_container_width=True, key="scraper_btn"):
        if concurrents:
            concurrents_list = [url.strip() for url in concurrents.split('\n') if url.strip()]
            mots_cles_list = [mot.strip().lower() for mot in mots_cles.split(',')] if mots_cles else []
            
            # Initialiser les résultats
            results = {
                "concurrent": [],
                "url": [],
                "titre_poste": [],
                "competences": [],
                "experience": [],
                "avantages": [],
                "mots_cles_trouves": []
            }
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, url in enumerate(concurrents_list):
                status_text.text(f"Analyse de {url}...")
                
                try:
                    # Simulation de scraping - À remplacer par votre logique réelle
                    # Cette partie devrait être adaptée selon la structure des sites cibles
                    time.sleep(delay)  # Respect du délai
                    
                    # Vérifier si c'est le site Vinci
                    if "vinci.com" in url:
                        results["concurrent"].append("Vinci")
                        results["url"].append(url)
                        results["titre_poste"].append("Ingénieur BTP")
                        results["competences"].append("Gestion de projet, AutoCAD, Management d'équipe")
                        results["experience"].append("5+ ans")
                        results["avantages"].append("Télétravail partiel, Mutuelle, Évolution")
                        results["mots_cles_trouves"].append("ingénieur, btp, management")
                    
                    # Exemple de données simulées pour d'autres sites
                    elif "entreprise1" in url:
                        results["concurrent"].append("Entreprise 1")
                        results["url"].append(url)
                        results["titre_poste"].append("Data Scientist Senior")
                        results["competences"].append("Python, Machine Learning, SQL, Cloud")
                        results["experience"].append("5+ ans")
                        results["avantages"].append("Télétravail, CE, Mutuelle")
                        results["mots_cles_trouves"].append("data scientist, python, cloud")
                    
                    elif "entreprise2" in url:
                        results["concurrent"].append("Entreprise 2")
                        results["url"].append(url)
                        results["titre_poste"].append("Développeur Full Stack")
                        results["competences"].append("JavaScript, React, Node.js, AWS")
                        results["experience"].append("3+ ans")
                        results["avantages"].append("RTT, Titre-restaurant, Évolution")
                        results["mots_cles_trouves"].append("javascript, react, aws")
                    
                    else:
                        results["concurrent"].append("Autre entreprise")
                        results["url"].append(url)
                        results["titre_poste"].append("Poste varié")
                        results["competences"].append("Compétences diverses")
                        results["experience"].append("Non spécifié")
                        results["avantages"].append("Avantages standards")
                        results["mots_cles_trouves"].append("")
                
                except Exception as e:
                    st.error(f"Erreur avec {url}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(concurrents_list))
            
            status_text.text("Analyse terminée!")
            
            # Affichage des résultats
            if results["concurrent"]:
                st.success(f"✅ Analyse de {len(results['concurrent'])} sites concurrents terminée")
                
                # Création d'un DataFrame pour une meilleure visualisation
                try:
                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, use_container_width=True)
                except NameError:
                    st.error("Erreur: pandas n'est pas installé. Impossible de créer le DataFrame.")
                    # On continue sans DataFrame
                    for i, concurrent in enumerate(results["concurrent"]):
                        st.write(f"**{concurrent}** - {results['titre_poste'][i]}")
                        st.write(f"Compétences: {results['competences'][i]}")
                        st.write(f"Expérience: {results['experience'][i]}")
                        st.write(f"Avantages: {results['avantages'][i]}")
                        st.write("---")
                
                # Analyses avancées
                st.subheader("📈 Analyses")
                
                # Nuage de mots des compétences recherchées
                if "Compétences recherchées" in analyse_options:
                    st.write("**Compétences les plus recherchées:**")
                    all_skills = ", ".join(results["competences"]).lower()
                    skills_counter = Counter([skill.strip() for skill in all_skills.split(',')])
                    
                    if skills_counter:
                        # Affichage simplifié des compétences (sans nuage de mots)
                        st.write("Répartition des compétences:")
                        for skill, count in skills_counter.most_common(10):
                            st.write(f"- {skill}: {count} occurrence(s)")
                
                # Analyse des niveaux d'expérience
                if "Niveaux d'expérience" in analyse_options:
                    st.write("**Niveaux d'expérience requis:**")
                    exp_counter = Counter(results["experience"])
                    for exp, count in exp_counter.items():
                        st.write(f"- {exp}: {count} offre(s)")
                
                # Export des résultats (uniquement si pandas est disponible)
                try:
                    csv_data = df_results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Télécharger les résultats (CSV)",
                        data=csv_data,
                        file_name="analyse_concurrentielle_emplois.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except NameError:
                    st.warning("Impossible de générer le fichier CSV car pandas n'est pas disponible.")
            else:
                st.warning("Aucun résultat à afficher.")
        else:
            st.error("Veuillez entrer au moins une URL de concurrent à analyser.")
    
    # Section d'aide
    with st.expander("❓ Comment utiliser cet outil", expanded=False):
        st.markdown("""
        ### Guide d'utilisation de l'analyse concurrentielle
        
        1. **Listez les sites de vos concurrents** - Entrez les URLs des pages carrières ou offres d'emploi
        2. **Définissez les mots-clés** - Spécifiez les compétences ou postes qui vous intéressent
        3. **Configurez l'analyse** - Choisissez ce que vous voulez analyser précisément
        4. **Lancez l'extraction** - L'outil parcourt les sites et extrait les informations
        5. **Consultez les résultats** - Visualisez les tendances et téléchargez les données
        
        ### Conseils pour de meilleurs résultats:
        - Ciblez des pages listant plusieurs offres d'emploi
        - Utilisez des mots-clés précis liés à vos besoins
        - Augmentez le délai entre les requêtes pour éviter le blocage
        - Testez d'abord avec 2-3 sites pour valider la configuration
        """)

# -------------------- Tab 6: InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail Personnalisé")

    # --------- FONCTIONS UTILES ---------
    def generate_cta(cta_type, prenom, genre):
        suffix = "e" if genre == "Féminin" else ""
        if cta_type == "Proposer un appel":
            return f"Je serai ravi{suffix} d'échanger avec vous par téléphone cette semaine afin d’en discuter davantage."
        elif cta_type == "Partager le CV":
            return f"Seriez-vous intéressé{suffix} à partager votre CV afin que je puisse examiner cette opportunité avec vous ?"
        elif cta_type == "Découvrir l'opportunité sur notre site":
            return f"Souhaiteriez-vous consulter plus de détails sur cette opportunité via notre site carrière ?"
        elif cta_type == "Accepter un rendez-vous":
            return f"Je serai ravi{suffix} de convenir d’un rendez-vous afin d’échanger sur cette opportunité."
        return ""

    def generate_inmail(donnees_profil, poste, entreprise, ton, max_words, cta_type, genre):
        terme_organisation = "groupe" if entreprise == "TGCC" else "filiale"
        objet = f"Opportunité de {poste} au sein du {terme_organisation} {entreprise}"

        # Accroche IA simulée
        accroche_prompt = f"""
        Tu es un recruteur marocain qui écrit des accroches pour InMail.
        Génère une accroche persuasive adaptée au ton "{ton}".
        Infos candidat: {donnees_profil}.
        Poste à pourvoir: {poste}, Entreprise: {entreprise}.
        L'accroche doit être concise, unique et engageante.
        """
        accroche_result = ask_deepseek([{"role": "user", "content": accroche_prompt}], max_tokens=80)
        accroche = accroche_result["content"].strip()

        # 🔧 sécurisation des données
        prenom = donnees_profil.get("prenom", "Candidat")
        mission = donnees_profil.get("mission", "")
        competences = donnees_profil.get("competences_cles", ["", "", ""])

        cta_text = generate_cta(cta_type, prenom, genre)

        response = f"""Bonjour {prenom},

{accroche}

Votre mission actuelle {mission} ainsi que vos compétences principales ({", ".join(filter(None, competences))}) 
démontrent un potentiel fort pour le poste de {poste} au sein de notre {terme_organisation} {entreprise}.

{cta_text}
"""

        # Ajustement de longueur
        words = response.split()
        if len(words) > max_words:
            response = " ".join(words[:max_words]) + "..."
        elif len(words) < int(max_words * 0.8):
            extend_prompt = f"Développe ce message en {max_words} mots environ sans répétitions :\n{response}"
            extend_result = ask_deepseek([{"role": "user", "content": extend_prompt}], max_tokens=max_words * 2)
            response = extend_result["content"]

        return response.strip(), objet

    # --------- IMPORTER UN MODÈLE ---------
    if st.session_state.library_entries:
        templates = [f"{e['poste']} - {e['date']}" for e in st.session_state.library_entries if e['type'] == "InMail"]
        selected_template = st.selectbox("📂 Importer un modèle sauvegardé :", [""] + templates, key="import_template_inmail")
        if selected_template:
            template_entry = next(e for e in st.session_state.library_entries if f"{e['poste']} - {e['date']}" == selected_template)
            st.session_state["inmail_profil_data"] = {
                "prenom": "Candidat",
                "nom": "",
                "poste_actuel": "",
                "entreprise_actuelle": "",
                "competences_cles": ["", "", ""],
                "experience_annees": "",
                "formation": "",
                "mission": "",
                "localisation": ""
            }
            st.session_state["inmail_message"] = template_entry["requete"]
            st.success("📥 Modèle importé et infos candidat prêtes")

    # --------- PARAMÈTRES GÉNÉRAUX ---------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        url_linkedin = st.text_input("Profil LinkedIn", key="inmail_url", placeholder="linkedin.com/in/nom-prenom")
    with col2:
        entreprise = st.selectbox("Entreprise", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise")
    with col3:
        ton_message = st.selectbox("Ton du message", ["Persuasif", "Professionnel", "Convivial", "Direct"], key="inmail_ton")
    with col4:
        genre_profil = st.selectbox("Genre du profil", ["Masculin", "Féminin"], key="inmail_genre")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        poste_accroche = st.text_input("Poste à pourvoir", key="inmail_poste", placeholder="Ex: Directeur Financier")
    with col6:
        longueur_message = st.slider("Longueur (mots)", 50, 300, 150, key="inmail_longueur")
    with col7:
        analyse_profil = st.selectbox("Méthode analyse", ["Manuel", "Regex", "Compét API"], index=0, key="inmail_analyse")
    with col8:
        cta_option = st.selectbox("Call to action (Conclusion)", ["Proposer un appel", "Partager le CV", "Découvrir l'opportunité sur notre site", "Accepter un rendez-vous"], key="inmail_cta")

    # --------- INFORMATIONS CANDIDAT ---------
    st.subheader("📊 Informations candidat")

    default_profil = {
        "prenom": "Candidat",
        "nom": "",
        "poste_actuel": "",
        "entreprise_actuelle": "",
        "competences_cles": ["", "", ""],
        "experience_annees": "",
        "formation": "",
        "mission": "",
        "localisation": ""
    }
    profil_data = {**default_profil, **st.session_state.get("inmail_profil_data", {})}

    cols = st.columns(5)
    profil_data["prenom"] = cols[0].text_input("Prénom", profil_data.get("prenom", ""), key="inmail_prenom")
    profil_data["nom"] = cols[1].text_input("Nom", profil_data.get("nom", ""), key="inmail_nom")
    profil_data["poste_actuel"] = cols[2].text_input("Poste actuel", profil_data.get("poste_actuel", ""), key="inmail_poste_actuel")
    profil_data["entreprise_actuelle"] = cols[3].text_input("Entreprise actuelle", profil_data.get("entreprise_actuelle", ""), key="inmail_entreprise_actuelle")
    profil_data["experience_annees"] = cols[4].text_input("Années d'expérience", profil_data.get("experience_annees", ""), key="inmail_exp")

    cols2 = st.columns(5)
    profil_data["formation"] = cols2[0].text_input("Domaine de formation", profil_data.get("formation", ""), key="inmail_formation")
    profil_data["competences_cles"][0] = cols2[1].text_input("Compétence 1", profil_data["competences_cles"][0], key="inmail_comp1")
    profil_data["competences_cles"][1] = cols2[2].text_input("Compétence 2", profil_data["competences_cles"][1], key="inmail_comp2")
    profil_data["competences_cles"][2] = cols2[3].text_input("Compétence 3", profil_data["competences_cles"][2], key="inmail_comp3")
    profil_data["localisation"] = cols2[4].text_input("Localisation", profil_data.get("localisation", ""), key="inmail_loc")

    profil_data["mission"] = st.text_area("Mission du poste", profil_data.get("mission", ""), height=80, key="inmail_mission")

    col_ap1, col_ap2 = st.columns(2)
    with col_ap1:
        if st.button("🔍 Analyser profil", key="btn_analyse_inmail"):
            profil_data.update({"poste_actuel": "Manager", "entreprise_actuelle": "ExempleCorp"})
            st.session_state["inmail_profil_data"] = profil_data
            st.success("✅ Profil pré-rempli automatiquement")
    with col_ap2:
        if st.button("💾 Appliquer infos candidat", key="btn_apply_inmail"):
            st.session_state["inmail_profil_data"] = profil_data
            st.success("✅ Infos candidat mises à jour")

    # --------- GÉNÉRATION ---------
    if st.button("✨ Générer", type="primary", use_container_width=True, key="btn_generate_inmail"):
        donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
        msg, objet_auto = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil)
        st.session_state["inmail_message"] = msg
        st.session_state["inmail_objet"] = objet_auto
        st.session_state["inmail_generated"] = True

    # --------- RÉSULTAT ---------
    if st.session_state.get("inmail_generated"):
        st.subheader("📝 Message InMail généré")
        st.text_input("📧 Objet", st.session_state.get("inmail_objet", ""), key="inmail_objet_display")
        msg = st.session_state["inmail_message"]
        st.text_area("Message", msg, height=250, key="inmail_msg_display")
        st.caption(f"📏 {len(msg.split())} mots | {len(msg)} caractères")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Régénérer avec mêmes paramètres", key="btn_regen_inmail"):
                donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
                msg, objet_auto = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil)
                st.session_state["inmail_message"] = msg
                st.session_state["inmail_objet"] = objet_auto
                st.rerun()
        with col2:
            if st.button("💾 Sauvegarder comme modèle", key="btn_save_inmail"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "InMail",
                    "poste": poste_accroche,
                    "requete": st.session_state["inmail_message"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success(f"✅ Modèle '{poste_accroche} - {entry['date']}' sauvegardé")


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
        "Quels rôles proches à considérer lors du sourcing pour",
        "Quelles tendances de recrutement récentes pour le métier de"
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", 
                            [""] + questions_pretes, key="magicien_qchoice")

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