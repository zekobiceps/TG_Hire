import streamlit as st
from utils import *
import webbrowser
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import re

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
        poste = st.text_input("Poste recherché:", placeholder="Ex: Développeur Python")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", placeholder="Ex: Developer, Programmeur, Ingénieur")
        st.caption("💡 Besoin d’aide pour les synonymes ? Utilisez le Magicien de sourcing 🤖 ci-dessous.")
        competences_obligatoires = st.text_input("Compétences obligatoires:", placeholder="Ex: Python, Django")
        secteur = st.text_input("Secteur d'activité:", placeholder="Ex: Informatique, Finance, Santé")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", placeholder="Ex: React, AWS")
        exclusions = st.text_input("Mots à exclure:", placeholder="Ex: Manager, Senior")
        localisation = st.text_input("Localisation:", placeholder="Ex: Casablanca, Maroc")
        employeur = st.text_input("Employeur actuel/précédent:", placeholder="Ex: OCP, IBM")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        boolean_query = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            boolean_query += f' AND ("{employeur}")'

        if boolean_query:
            st.text_area("Requête Boolean:", value=boolean_query, height=120)

            colA, colB, colC = st.columns(3)
            safe_query = boolean_query.replace("`", "")
            with colA:
                st.markdown(
                    f'<button onclick="navigator.clipboard.writeText(`{safe_query}`)">📋 Copier</button>',
                    unsafe_allow_html=True
                )
            with colB:
                if st.button("📚 Sauvegarder Boolean"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste, "requete": boolean_query}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.toast("✅ Sauvegardé dans la bibliothèque")
            with colC:
                if st.button("🔄 Réinit Boolean"):
                    st.session_state.clear()
                    st.experimental_rerun()

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    st.caption("🔎 Utilise Google pour cibler directement les profils sur LinkedIn ou GitHub.")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"])
        poste_xray = st.text_input("Poste:", placeholder="Ex: Data Scientist")
    with col2:
        mots_cles = st.text_input("Mots-clés:", placeholder="Ex: Machine Learning, Python")
        localisation_xray = st.text_input("Localisation:", placeholder="Ex: Rabat")

    if st.button("🔍 Construire X-Ray", type="primary"):
        xray_query = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
        st.text_area("Requête X-Ray:", value=xray_query, height=120)

        colA, colB, colC = st.columns(3)
        safe_query = xray_query.replace("`", "")
        with colA:
            st.markdown(
                f'<button onclick="navigator.clipboard.writeText(`{safe_query}`)">📋 Copier</button>',
                unsafe_allow_html=True
            )
        with colB:
            if st.button("📚 Sauvegarder X-Ray"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray, "requete": xray_query}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.toast("✅ Sauvegardé dans la bibliothèque")
        with colC:
            if st.button("🌐 Ouvrir sur Google"):
                url = f"https://www.google.com/search?q={quote(xray_query)}"
                webbrowser.open_new_tab(url)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE (Custom Search Engine) LinkedIn :")
    st.caption("🔎 Google CSE préconfiguré pour chercher uniquement dans les profils LinkedIn.")
    poste_cse = st.text_input("Poste recherché:")
    competences_cse = st.text_input("Compétences clés:")
    localisation_cse = st.text_input("Localisation:")
    entreprise_cse = st.text_input("Entreprise:")

    if st.button("🔍 Lancer recherche CSE"):
        cse_query = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(cse_query)}"
        st.text_area("Requête CSE:", value=cse_query, height=100)

        colA, colB, colC = st.columns(3)
        safe_query = cse_query.replace("`", "")
        with colA:
            st.markdown(
                f'<button onclick="navigator.clipboard.writeText(`{safe_query}`)">📋 Copier</button>',
                unsafe_allow_html=True
            )
        with colB:
            if st.button("📚 Sauvegarder CSE"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse, "requete": cse_query}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.toast("✅ Sauvegardé dans la bibliothèque")
        with colC:
            if st.button("🌐 Ouvrir résultats CSE"):
                webbrowser.open_new_tab(cse_url)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:")
    if st.button("🔎 Rechercher sur Dogpile"):
        if query:
            url = f"https://www.dogpile.com/serp?q={quote(query)}"
            st.text_area("Requête Dogpile:", value=query, height=100)
            colA, colB, colC = st.columns(3)
            safe_query = query.replace("`", "")
            with colA:
                st.markdown(
                    f'<button onclick="navigator.clipboard.writeText(`{safe_query}`)">📋 Copier</button>',
                    unsafe_allow_html=True
                )
            with colB:
                if st.button("📚 Sauvegarder Dogpile"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", "poste": "", "requete": query}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.toast("✅ Sauvegardé dans la bibliothèque")
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
    ])
    url = st.text_input("URL à analyser:")
    if st.button("🚀 Scraper"):
        if url:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            texte = soup.get_text()[:800]
            emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte))
            st.text_area("Extrait:", value=texte, height=200)
            colA, colB, colC = st.columns(3)
            safe_text = texte.replace("`", "")
            with colA:
                st.markdown(
                    f'<button onclick="navigator.clipboard.writeText(`{safe_text}`)">📋 Copier</button>',
                    unsafe_allow_html=True
                )
            with colB:
                if st.button("📚 Sauvegarder Scraper"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Scraper", "poste": choix, "requete": url}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.toast("✅ Sauvegardé dans la bibliothèque")
            with colC:
                if st.button("🔄 Réinit Scraper"):
                    st.session_state.clear()
                    st.experimental_rerun()

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
