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
        st.caption("💡 Besoin d’aide pour les synonymes ? Utilisez le Magicien de sourcing 🤖 ci-dessous :")
        st.page_link("pages/2_🔍_Tour_de_sourcing.py", label="👉 Cliquer ici → Magicien de sourcing", icon="🤖")
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
            colA, colB, colC = st.columns([1,1,1])
            with colA:
                if st.button("📋 Copier Boolean"):
                    st.toast("Requête copiée manuellement")
            with colB:
                if st.button("📚 Sauvegarder Boolean"):
                    st.session_state.library_entries.append(
                        {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste, "requete": boolean_query}
                    )
                    save_library_entries()
                    st.success("Sauvegardé dans la bibliothèque")
            with colC:
                if st.button("🔄 Réinit Boolean"):
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
        colA, colB = st.columns([1,1])
        with colA:
            if st.button("🌐 Ouvrir sur Google"):
                url = f"https://www.google.com/search?q={quote(xray_query)}"
                webbrowser.open_new_tab(url)
        with colB:
            if st.button("📚 Sauvegarder X-Ray"):
                st.session_state.library_entries.append(
                    {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray, "requete": xray_query}
                )
                save_library_entries()
                st.success("Sauvegardé")

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
        if st.button("🌐 Ouvrir résultats CSE"):
            webbrowser.open_new_tab(cse_url)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:")
    if st.button("🔎 Rechercher sur Dogpile"):
        url = f"https://www.dogpile.com/serp?q={quote(query)}"
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
            if emails:
                st.markdown("📧 Emails détectés:")
                st.write(", ".join(emails))

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")
    questions = [
        "Donne-moi des synonymes utiles",
        "Quels jobboards cibler ?",
        "Quelles soft skills clés ?",
        "Comment adapter la recherche pour seniors ?",
        "Quels mots-clés sectoriels utiliser ?",
        "Quelles tendances de recrutement récentes ?"
    ]
    q_select = st.selectbox("Choisir une question:", questions)
    if st.button("⚡ Poser la question"):
        result = ask_deepseek([{"role": "user", "content": q_select}], max_tokens=200)
        if "content" in result:
            reponse = result["content"]
            st.text_area("Réponse:", value=reponse, height=150)
            st.session_state.conversation_history.append({"q": q_select, "r": reponse})

    if st.session_state.conversation_history:
        st.subheader("📜 Historique")
        for i, conv in enumerate(st.session_state.conversation_history):
            with st.expander(f"Q{i+1}: {conv['q'][:40]}..."):
                st.write("**Vous:**", conv["q"])
                st.write("**Magicien 🤖:**", conv["r"])
        if st.button("🗑️ Effacer tout l’historique"):
            st.session_state.conversation_history.clear()

# -------------------- Email Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:")
    nom = st.text_input("Nom:")
    domaine = st.text_input("Domaine:", placeholder="ex: tgcc")
    if st.button("⚡ Générer emails"):
        emails = [
            f"{prenom}.{nom}@{domaine}.ma",
            f"{prenom}.{nom}@{domaine}.com",
            f"{prenom}{nom}@{domaine}.ma",
            f"{prenom}{nom}@{domaine}.com",
            f"{nom}{prenom}@{domaine}.ma",
            f"{prenom[0]}{nom}@{domaine}.com",
        ]
        st.text_area("Résultats:", value="\n".join(emails), height=150)
    st.caption("💡 Vérifiez vos adresses avec [Hunter.io](https://hunter.io) ou [NeverBounce](https://neverbounce.com)")

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
