import streamlit as st
from utils import *
import webbrowser
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

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
        st.caption("💡 Besoin d’aide pour les synonymes ? Utilisez le Magicien de sourcing 🤖 pour générer automatiquement. [Cliquer ici](#magicien-de-sourcing)")
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
            st.success("✅ Requête Boolean générée")
            st.text_area("Requête prête à copier:", value=boolean_query, height=120)

            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("📋 Copier"):
                    st.write("👉 Copiez manuellement depuis la zone ci-dessus")
            with colB:
                if st.button("📚 Sauvegarder"):
                    entry = {"date": datetime.now().strftime("%Y-%m-%d"),
                             "type": "Boolean", "poste": poste, "requete": boolean_query}
                    st.session_state.library_entries.append(entry)
                    save_library_entries()
                    st.success("Sauvegardé !")
            with colC:
                if st.button("🔄 Réinitialiser"):
                    st.experimental_rerun()

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    st.caption("🔎 Permet d’utiliser Google comme moteur de recherche ciblé (LinkedIn, GitHub...).")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"])
        poste_xray = st.text_input("Poste:", placeholder="Ex: Data Scientist")
    with col2:
        mots_cles = st.text_input("Mots-clés:", placeholder="Ex: Machine Learning, Python")
        localisation_xray = st.text_input("Localisation:", placeholder="Ex: Rabat")

    if st.button("🔍 Construire X-Ray", type="primary"):
        xray_query = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
        st.text_area("Requête:", value=xray_query, height=120)
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("📋 Copier X-Ray"):
                st.write("👉 Copiez manuellement")
        with colB:
            if st.button("📚 Sauvegarder X-Ray"):
                st.session_state.library_entries.append(
                    {"date": datetime.now().strftime("%Y-%m-%d"),
                     "type": "X-Ray", "poste": poste_xray, "requete": xray_query}
                )
                save_library_entries()
                st.success("Sauvegardé")
        with colC:
            if st.button("🔄 Réinit X-Ray"):
                st.experimental_rerun()

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE (Custom Search Engine) LinkedIn :")
    st.caption("Permet d’interroger Google CSE pré-configuré pour les profils LinkedIn.")
    poste_cse = st.text_input("Poste recherché:")
    competences_cse = st.text_input("Compétences clés:")
    localisation_cse = st.text_input("Localisation:")
    entreprise_cse = st.text_input("Entreprise:")

    if st.button("🔍 Lancer recherche CSE"):
        cse_query = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(cse_query)}"
        st.text_area("Requête:", value=cse_query, height=100)
        if st.button("🌐 Ouvrir résultats"):
            webbrowser.open_new_tab(cse_url)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:")
    if st.button("🔎 Rechercher sur Dogpile"):
        url = f"https://www.dogpile.com/serp?q={quote(query)}"
        webbrowser.open_new_tab(url)

# -------------------- Web Scraping --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ])
    st.info("Cet outil est un prototype de scraping (BeautifulSoup)")

    url = st.text_input("URL à analyser:")
    if st.button("🚀 Scraper"):
        if url:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            texte = soup.get_text()[:1000]
            st.text_area("Extrait:", value=texte, height=200)

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d’InMail")
    url_linkedin = st.text_input("Profil LinkedIn:")
    poste_accroche = st.text_input("Poste à pourvoir:")
    entreprise = st.selectbox("Entreprise:", ["TGCC", "TG ALU", "TG COVER", "TG WOOD",
                                              "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"])
    if st.button("💌 Générer InMail"):
        accroche = generate_accroche_inmail(url_linkedin, poste_accroche)
        message = f"{accroche}\n\nNous serions ravis de vous compter dans notre équipe {entreprise}. Seriez-vous disponible pour en discuter ?"
        st.text_area("InMail:", value=message, height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")
    questions = [
        "Donne-moi des synonymes pour {poste}",
        "Quels jobboards cibler pour {poste} ?",
        "Quelles soft skills clés pour {poste} ?",
        "Comment adapter la recherche pour des profils seniors {poste} ?",
        "Quels mots-clés sectoriels pour {poste} ?"
    ]
    q_select = st.selectbox("Choisir une question:", questions)
    question_magicien = st.text_area("Votre question:", value=q_select, height=100)

    if st.button("⚡ Poser la question"):
        result = ask_deepseek([{"role": "user", "content": question_magicien}], max_tokens=200)
        if "content" in result:
            reponse = result["content"]
            st.text_area("Réponse:", value=reponse, height=150)
            st.session_state.conversation_history.append({"q": question_magicien, "r": reponse})

    if st.session_state.conversation_history:
        st.subheader("📜 Historique")
        for i, conv in enumerate(st.session_state.conversation_history):
            with st.expander(f"Q{i+1}: {conv['q'][:40]}..."):
                st.write("**Vous:**", conv["q"])
                st.write("**Magicien 🤖:**", conv["r"])
        if st.button("🗑️ Effacer l’historique complet"):
            st.session_state.conversation_history.clear()
            st.success("Historique effacé")

# -------------------- Email Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:")
    nom = st.text_input("Nom:")
    domaine = st.text_input("Domaine:", placeholder="ex: tgcc.ma")
    if st.button("⚡ Générer emails"):
        emails = [
            f"{prenom}.{nom}@{domaine}",
            f"{prenom}{nom}@{domaine}",
            f"{nom}{prenom}@{domaine}",
            f"{prenom[0]}{nom}@{domaine}",
        ]
        st.text_area("Résultats:", value="\n".join(emails), height=150)
    st.caption("💡 Vérification possible via outils externes comme Hunter.io ou NeverBounce")

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
        st.info("Aucune recherche sauvegardée pour le moment.")
