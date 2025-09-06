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

# Compteur de tokens dans la sidebar
with st.sidebar:
    st.metric("🔢 Tokens utilisés", st.session_state.get("token_counter", 0))

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
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires")
        secteur = st.text_input("Secteur d'activité:", key="secteur")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles")
        exclusions = st.text_input("Mots à exclure:", key="exclusions")
        localisation = st.text_input("Localisation:", key="localisation")
        employeur = st.text_input("Employeur actuel/précédent:", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)
        st.button("📋 Copier la requête")
        colA, colB = st.columns(2)
        with colA:
            if st.button("📚 Sauvegarder Boolean"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste, "requete": st.session_state["boolean_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colB:
            if st.button("🌐 Ouvrir sur LinkedIn"):
                url = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
                webbrowser.open_new_tab(url)

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray")
    with col2:
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray")
        localisation_xray = st.text_input("Localisation:", key="localisation_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        st.button("📋 Copier la requête")
        colA, colB = st.columns(2)
        with colA:
            if st.button("📚 Sauvegarder X-Ray"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray, "requete": st.session_state["xray_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colB:
            if st.button("🌐 Ouvrir sur Google"):
                url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
                webbrowser.open_new_tab(url)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        st.button("📋 Copier la requête")
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
        colA, colB = st.columns(2)
        with colA:
            if st.button("📚 Sauvegarder CSE"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse, "requete": st.session_state["cse_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colB:
            if st.button("🌐 Ouvrir résultats CSE"):
                webbrowser.open_new_tab(cse_url)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:", key="dogpile_query")

    if st.button("🔎 Rechercher sur Dogpile"):
        st.session_state["dogpile_result"] = query

    if st.session_state.get("dogpile_result"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_result"], height=100)
        st.button("📋 Copier la requête")
        url = f"https://www.dogpile.com/serp?q={quote(st.session_state['dogpile_result'])}"
        colA, colB = st.columns(2)
        with colA:
            if st.button("📚 Sauvegarder Dogpile"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", "poste": "", "requete": st.session_state["dogpile_result"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colB:
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
            st.session_state["scraper_result"] = texte
            st.session_state["scraper_emails"] = emails

    if st.session_state.get("scraper_result"):
        st.text_area("Extrait:", value=st.session_state["scraper_result"], height=200)
        if st.button("📚 Sauvegarder Scraper"):
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Scraper", "poste": choix, "requete": url}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de ... ?",
        "Quels mots-clés utiliser pour recruter sur le poste de ... ?",
        "Quelles compétences sont indispensables pour le poste de ... ?",
        "Quels termes techniques sont associés au métier de ... ?",
        "Quels intitulés similaires existent pour le poste de ... ?",
        "Quels diplômes ou certifications rechercher pour le métier de ... ?",
        "Quelles compétences comportementales sont attendues pour le poste de ... ?",
        "Quels outils ou logiciels sont liés au métier de ... ?",
        "Quels hashtags LinkedIn pourraient être utiles pour le poste de ... ?",
        "Quels intitulés anglais sont utilisés pour le métier de ... ?",
        "Quels mots-clés exclure pour gagner en précision sur le poste de ... ?",
        "Quels profils transverses peuvent correspondre au poste de ... ?",
        "Quels mots-clés utiliser pour cibler les juniors pour le poste de ... ?",
        "Quels mots-clés utiliser pour cibler les seniors pour le poste de ... ?",
        "Quels synonymes ou variantes régionales existent pour le métier de ... ?"
    ]

    q_choice = st.selectbox("📌 Choisir une question prédéfinie:", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question:", value=q_choice if q_choice else "", key="magicien_question")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing. Réponds de manière concise et exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state["magicien_reponse"] = result["content"]

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)
        st.button("📋 Copier la requête")
        colA, colB = st.columns(2)
        with colA:
            if st.button("📚 Sauvegarder Magicien"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Magicien", "poste": "", "requete": st.session_state["magicien_reponse"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colB:
            if st.button("🗑️ Supprimer historique Magicien"):
                for key in ["magicien_question","magicien_reponse"]:
                    st.session_state[key] = ""
                st.success("🧹 Historique effacé")

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom")
    nom = st.text_input("Nom:", key="perm_nom")
    domaine = st.text_input("Domaine (ex: TGCC):", key="perm_domaine")

    if st.button("🔮 Générer permutations"):
        if prenom and nom and domaine:
            domaines = [domaine, domaine + ".com", domaine + ".ma"]
            permutations = []
            for d in set(domaines):
                permutations.extend([
                    f"{prenom.lower()}.{nom.lower()}@{d}",
                    f"{prenom[0].lower()}{nom.lower()}@{d}",
                    f"{nom.lower()}.{prenom.lower()}@{d}"
                ])
            st.session_state["perm_result"] = permutations

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.button("📋 Copier la requête")
        st.caption("Tester le fonctionnement d'une boite mail : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")
        if st.button("📚 Sauvegarder Permutator"):
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Permutator", "poste": "", "requete": ", ".join(st.session_state["perm_result"])}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")

# -------------------- Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")

    if st.session_state.library_entries:
        search_term = st.text_input("🔎 Rechercher dans la bibliothèque:")
        sort_by = st.selectbox("📌 Trier par:", ["Date", "Type", "Poste"], key="sort_by")

        entries = st.session_state.library_entries
        if search_term:
            entries = [e for e in entries if search_term.lower() in e["requete"].lower() or search_term.lower() in e["poste"].lower()]

        if sort_by == "Type":
            entries = sorted(entries, key=lambda x: x["type"])
        elif sort_by == "Poste":
            entries = sorted(entries, key=lambda x: x["poste"])
        else:
            entries = sorted(entries, key=lambda x: x["date"], reverse=True)

        for i, entry in enumerate(entries):
            with st.expander(f"{entry['date']} - {entry['type']} - {entry['poste']}"):
                st.text_area("Requête:", value=entry['requete'], height=100)
                if st.button("🗑️ Supprimer", key=f"del_{i}"):
                    st.session_state.library_entries.remove(entry)
                    save_library_entries()
                    st.experimental_rerun()
    else:
        st.info("Aucune recherche sauvegardée")
