import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from urllib.parse import quote

# Import utils
from utils import (
    init_session_state,
    save_library_entries,
    generate_boolean_query,
    generate_xray_query,
    generate_accroche_inmail,
    ask_deepseek
)

# Init session
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Sidebar Tokens --------------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# -------------------- Tabs --------------------
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
        st.caption("💡 Pour plus de synonymes, utilisez le Magicien de sourcing 🤖")
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

        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("💾 Sauvegarder", key="save_boolean"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste,
                         "requete": st.session_state["boolean_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")

        with col2:
            if st.button("🌐 LinkedIn", key="linkedin_boolean"):
                url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
                st.markdown(f"<script>window.open('{url_linkedin}')</script>", unsafe_allow_html=True)

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

        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("💾 Sauvegarder", key="save_xray"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray,
                         "requete": st.session_state["xray_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")

        with col2:
            if st.button("🌐 Google", key="google_xray"):
                url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
                st.markdown(f"<script>window.open('{url}')</script>", unsafe_allow_html=True)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE (Custom Search Engine) LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE"):
        st.session_state["cse_query"] = " ".join(
            filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse])
        )

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)

        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("💾 Sauvegarder", key="save_cse"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse,
                         "requete": st.session_state["cse_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")

        with col2:
            if st.button("🌐 CSE", key="cse_button"):
                cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
                st.markdown(f"<script>window.open('{cse_url}')</script>", unsafe_allow_html=True)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query_dog = st.text_input("Votre recherche:", key="dogpile_query")

    if st.button("🔍 Lancer Dogpile"):
        if query_dog:
            st.session_state["dogpile_url"] = f"https://www.dogpile.com/serp?q={quote(query_dog)}"

    if st.session_state.get("dogpile_url"):
        col1, _ = st.columns([1, 9])
        with col1:
            if st.button("🌐 Dogpile", key="dogpile_button"):
                st.markdown(f"<script>window.open('{st.session_state['dogpile_url}')</script>", unsafe_allow_html=True)

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
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail")
    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste")
    entreprise = st.selectbox("Entreprise:", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL",
                                             "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + \
                                            f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de",
        "Quels outils ou logiciels sont liés au métier de",
        "Quels mots-clés pour cibler les juniors pour le poste de",
        "Quels mots-clés pour cibler les seniors pour le poste de",
        "Quels intitulés de poste alternatifs pour",
        "Quels hashtags LinkedIn utiliser pour",
        "Quels mots-clés techniques obligatoires pour",
        "Quels soft skills importants pour",
        "Quels diplômes ou certifications liés à",
        "Quelles associations ou fédérations liées à",
        "Quels sites spécialisés pour recruter sur le poste de",
        "Quels groupes LinkedIn utiles pour le métier de",
        "Quels mots-clés à exclure pour éviter les hors-sujet sur",
        "Quels synonymes anglais pour le poste de",
        "Quels intitulés de poste proches mais différents de"
    ]

    question = st.selectbox("Choisir une question prête :", [""] + questions_pretes, key="magicien_select")
    custom_question = st.text_input("Ou écrivez votre propre question:", key="magicien_custom")

    final_question = custom_question if custom_question else question

    if st.button("✨ Poser la question", type="primary"):
        if final_question:
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds de manière concise et exploitable."},
                {"role": "user", "content": final_question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state["magicien_reponse"] = result["content"]

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom")
    nom = st.text_input("Nom:", key="perm_nom")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_domaine")

    if st.button("🔮 Générer permutations"):
        if prenom and nom and entreprise:
            st.session_state["perm_result"] = [
                f"{prenom.lower()}.{nom.lower()}@{entreprise}.com",
                f"{prenom[0].lower()}{nom.lower()}@{entreprise}.ma",
                f"{nom.lower()}.{prenom.lower()}@{entreprise}.com"
            ]

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester le fonctionnement d'une boite mail : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

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
                    st.rerun()
    else:
        st.info("Aucune recherche sauvegardée")
