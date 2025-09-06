import streamlit as st
from utils import *
import webbrowser
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Onglets --------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Recherche Boolean",
    "🎯 X-Ray",
    "🔎 CSE LinkedIn",
    "🐶 Dogpile",
    "🕷️ Web Scraper",
    "✉️ InMail",
    "🤖 Magicien de sourcing",
    "📧 Email Permutator",
    "📚 Bibliothèque"
])

# -------------------- Boolean --------------------
with tab1:
    st.header("🔍 Recherche Boolean")
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="poste")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", key="synonymes")
        st.caption("💡 Besoin d’aide pour les synonymes ? Utilisez le Magicien de sourcing 🤖 ci-dessous.")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires")
        secteur = st.text_input("Secteur d'activité:", key="secteur")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles")
        exclusions = st.text_input("Mots à exclure:", key="exclusions")
        localisation = st.text_input("Localisation:", key="localisation")
        employeur = st.text_input("Employeur actuel/précédent:", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        boolean_query = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            boolean_query += f' AND ("{employeur}")'

        if boolean_query:
            st.text_area("Requête Boolean:", value=boolean_query, height=120)

            colA, colB = st.columns(2)
            with colA:
                if st.button("📚 Sauvegarder Boolean"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste, "requete": boolean_query}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.success("✅ Sauvegardé dans la bibliothèque")
            with colB:
                if st.button("🔄 Réinit Boolean"):
                    for key in ["poste","synonymes","competences_obligatoires","secteur",
                                "competences_optionnelles","exclusions","localisation","employeur"]:
                        st.session_state[key] = ""
                    st.warning("⚠️ Champs réinitialisés")

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    st.caption("🔎 Utilise Google pour cibler directement les profils sur LinkedIn ou GitHub.")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray")
    with col2:
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray")
        localisation_xray = st.text_input("Localisation:", key="localisation_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        xray_query = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
        st.text_area("Requête X-Ray:", value=xray_query, height=120)

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("📚 Sauvegarder X-Ray"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray, "requete": xray_query}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé dans la bibliothèque")
        with colB:
            if st.button("🔄 Réinit X-Ray"):
                for key in ["poste_xray","mots_cles_xray","localisation_xray"]:
                    st.session_state[key] = ""
                st.warning("⚠️ Champs réinitialisés")
        with colC:
            if st.button("🌐 Ouvrir sur Google"):
                url = f"https://www.google.com/search?q={quote(xray_query)}"
                webbrowser.open_new_tab(url)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE (Custom Search Engine) LinkedIn :")
    st.caption("🔎 Google CSE préconfiguré pour chercher uniquement dans les profils LinkedIn.")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE"):
        cse_query = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(cse_query)}"
        st.text_area("Requête CSE:", value=cse_query, height=100)

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("📚 Sauvegarder CSE"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse, "requete": cse_query}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé dans la bibliothèque")
        with colB:
            if st.button("🔄 Réinit CSE"):
                for key in ["poste_cse","competences_cse","localisation_cse","entreprise_cse"]:
                    st.session_state[key] = ""
                st.warning("⚠️ Champs réinitialisés")
        with colC:
            if st.button("🌐 Ouvrir résultats CSE"):
                webbrowser.open_new_tab(cse_url)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:", key="dogpile_query")
    if st.button("🔎 Rechercher sur Dogpile"):
        if query:
            url = f"https://www.dogpile.com/serp?q={quote(query)}"
            st.text_area("Requête Dogpile:", value=query, height=100)

            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("📚 Sauvegarder Dogpile"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", "poste": "", "requete": query}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.success("✅ Sauvegardé dans la bibliothèque")
            with colB:
                if st.button("🔄 Réinit Dogpile"):
                    st.session_state["dogpile_query"] = ""
                    st.warning("⚠️ Champs réinitialisés")
            with colC:
                if st.button("🌐 Ouvrir sur Dogpile"):
                    webbrowser.open_new_tab(url)

# -------------------- Web Scraper --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    url = st.text_input("URL à analyser:", key="scraper_url")
    if st.button("🚀 Scraper"):
        if url:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            texte = soup.get_text()[:800]
            emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte))
            st.text_area("Extrait:", value=texte, height=200)

            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("📚 Sauvegarder Scraper"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Scraper", "poste": choix, "requete": url}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.success("✅ Sauvegardé dans la bibliothèque")
            with colB:
                if st.button("🔄 Réinit Scraper"):
                    st.session_state["scraper_url"] = ""
                    st.warning("⚠️ Champs réinitialisés")
            with colC:
                if emails:
                    st.info("📧 Emails détectés: " + ", ".join(emails))

# -------------------- Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    if st.session_state.library_entries:
        for i, entry in enumerate(st.session_state.library_entries):
            with st.expander(f"{entry['date']} - {entry['type']} - {entry['poste']}"):
                st.text_area("Requête:", value=entry['requete'], height=100)
                if st.button("🗑️ Supprimer", key=f"del_{i}"):
                    st.session_state.library_entries.remove(entry)
                    save_library_entries()
                    st.experimental_rerun()
    else:
        st.info("Aucune recherche sauvegardée")
