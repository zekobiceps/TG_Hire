import streamlit as st
from utils import *
import pyperclip
import webbrowser
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
        st.caption("💡 Besoin d’aide pour les synonymes ? Utilisez le **Magicien de sourcing 🤖** pour générer automatiquement.")
        competences_obligatoires = st.text_input("Compétences obligatoires:", placeholder="Ex: Python, Django")
        secteur = st.text_input("Secteur d'activité:", placeholder="Ex: Informatique, Finance, Santé")
        employeur = st.text_input("Employeur actuel/précédent:", placeholder="Ex: OCP, IBM")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", placeholder="Ex: React, AWS")
        exclusions = st.text_input("Mots à exclure:", placeholder="Ex: Manager, Senior")
        localisation = st.text_input("Localisation:", placeholder="Ex: Casablanca, Maroc")

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
                if st.button("📋 Copier résultat"):
                    pyperclip.copy(boolean_query)
                    st.success("Requête copiée !")
            with colB:
                if st.button("📚 Sauvegarder"):
                    lib_entry = {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "Boolean",
                        "poste": poste,
                        "requete": boolean_query,
                        "localisation": localisation,
                        "secteur": secteur
                    }
                    st.session_state.library_entries.append(lib_entry)
                    save_library_entries()
                    st.success("Sauvegardé dans la bibliothèque")
            with colC:
                if st.button("🔄 Réinitialiser"):
                    st.experimental_rerun()

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub", "Indeed"])
        poste_xray = st.text_input("Poste:", placeholder="Ex: Data Scientist")
    with col2:
        mots_cles = st.text_input("Mots-clés:", placeholder="Ex: Machine Learning, Python")
        localisation_xray = st.text_input("Localisation:", placeholder="Ex: Rabat")

    if st.button("🔍 Construire X-Ray", type="primary"):
        xray_query = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
        if xray_query:
            st.success("✅ Requête X-Ray générée")
            st.text_area("Requête:", value=xray_query, height=120)
            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("📋 Copier résultat X-Ray"):
                    pyperclip.copy(xray_query)
                    st.success("Copié !")
            with colB:
                if st.button("📚 Sauvegarder X-Ray"):
                    lib_entry = {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "X-Ray",
                        "poste": poste_xray,
                        "requete": xray_query,
                        "localisation": localisation_xray
                    }
                    st.session_state.library_entries.append(lib_entry)
                    save_library_entries()
                    st.success("Sauvegardé")
            with colC:
                if st.button("🔄 Réinitialiser X-Ray"):
                    st.experimental_rerun()

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", placeholder="Ex: Commercial B2B")
    competences_cse = st.text_input("Compétences clés:", placeholder="Ex: Vente, Négociation, CRM")
    localisation_cse = st.text_input("Localisation:", placeholder="Ex: Maroc")
    entreprise_cse = st.text_input("Entreprise:", placeholder="Ex: OCP, Maroc Telecom")

    if st.button("🔍 Lancer recherche CSE"):
        parts = [poste_cse, competences_cse, localisation_cse, entreprise_cse]
        cse_query = " ".join([p for p in parts if p])
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(cse_query)}"
        st.success("✅ Requête CSE générée")
        st.text_area("Requête:", value=cse_query, height=100)
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("📋 Copier CSE"):
                pyperclip.copy(cse_query)
                st.success("Copié !")
        with colB:
            if st.button("📚 Sauvegarder CSE"):
                lib_entry = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "CSE",
                    "poste": poste_cse,
                    "requete": cse_query,
                    "localisation": localisation_cse
                }
                st.session_state.library_entries.append(lib_entry)
                save_library_entries()
                st.success("Sauvegardé")
        with colC:
            if st.button("🔄 Réinitialiser CSE"):
                st.experimental_rerun()

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:", placeholder="Ex: CV Data Scientist Maroc")
    if st.button("🔎 Rechercher sur Dogpile"):
        url = f"https://www.dogpile.com/serp?q={quote(query)}"
        st.markdown(f"**[🔗 Voir résultats Dogpile]({url})**")

# -------------------- Web Scraping --------------------
with tab5:
    st.header("🕷️ Web Scraping")
    st.info("Prototype d’outil de collecte automatique de profils (à développer avec BeautifulSoup / Scrapy).")
    url = st.text_input("URL à scrapper:")
    if st.button("🚀 Lancer scraping"):
        st.warning("⚠️ Scraping pas encore implémenté (à sécuriser légalement).")

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d’InMail")
    url_linkedin = st.text_input("Profil LinkedIn:", placeholder="Ex: https://linkedin.com/in/nom")
    poste_accroche = st.text_input("Poste à pourvoir:", placeholder="Ex: Chef de projet digital")
    if st.button("💌 Générer InMail"):
        accroche = generate_accroche_inmail(url_linkedin, poste_accroche)
        st.text_area("Accroche:", value=accroche, height=150)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")
    questions = [
        "Donne-moi des synonymes pour {poste}",
        "Variante Boolean pour un profil junior en {poste}",
        "Jobboards à cibler pour {poste}",
        "Soft skills clés pour {poste}",
        "Adapter recherche pour profils seniors en {poste}",
        "Mots-clés sectoriels pour {poste}"
    ]
    poste_q = st.text_input("Nom du poste pour le Magicien:", placeholder="Ex: Développeur Python")
    q_select = st.selectbox("Question:", [""] + [q.format(poste=poste_q) for q in questions])
    question_magicien = st.text_area("Votre question:", value=q_select, height=100)

    if st.button("🤖 Poser la question"):
        messages = [
            {"role": "system", "content": "Réponds toujours de manière concise et actionnable. Pour les synonymes: Nom,Nom,Nom."},
            {"role": "user", "content": question_magicien}
        ]
        result = ask_deepseek(messages, max_tokens=300)
        if "content" in result:
            reponse = result["content"]
            st.markdown("**Réponse:**")
            st.markdown(reponse)
            st.session_state.conversation_history.append({"q": question_magicien, "r": reponse})

    if st.session_state.conversation_history:
        st.subheader("📜 Historique")
        for i, conv in enumerate(st.session_state.conversation_history):
            with st.expander(f"Q{i+1}: {conv['q'][:40]}..."):
                st.write("**Vous:**", conv["q"])
                st.write("**Magicien 🤖:**", conv["r"])

# -------------------- Email Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:")
    nom = st.text_input("Nom:")
    domaine = st.text_input("Domaine:", placeholder="exemple.com")
    if st.button("⚡ Générer emails"):
        emails = [
            f"{prenom}.{nom}@{domaine}",
            f"{prenom}{nom}@{domaine}",
            f"{nom}{prenom}@{domaine}",
            f"{prenom[0]}{nom}@{domaine}",
        ]
        st.text_area("Résultats:", value="\n".join(emails), height=120)

# -------------------- Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque Interne")
    for entry in st.session_state.library_entries:
        with st.expander(f"{entry['date']} - {entry['type']} - {entry['poste']}"):
            st.text_area("Requête:", value=entry['requete'], height=80)
