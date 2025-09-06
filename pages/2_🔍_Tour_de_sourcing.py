import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
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

# -------------------- Initialisation --------------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Compteur tokens --------------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# -------------------- Boutons uniformes --------------------
def action_buttons(save_label, open_label, url, context="default"):
    """Deux boutons homogènes alignés à gauche"""
    col1, col2, _ = st.columns([1, 1, 6])

    with col1:
        if st.button(save_label, key=f"{context}_save", use_container_width=True):
            return "save"

    with col2:
        st.markdown(
            f"""
            <a href="{url}" target="_blank" style="text-decoration:none;">
                <div style="
                    display:inline-block;
                    padding:6px 12px;
                    background:#2b6cb0;
                    color:white;
                    border:none;
                    border-radius:6px;
                    font-size:13px;
                    text-align:center;
                    cursor:pointer;
                    width:100%;
                ">
                    {open_label}
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
    return None

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
        poste = st.text_input("Poste recherché:", placeholder="Ex: Ingénieur de travaux", key="poste")
        synonymes = st.text_input("Synonymes:", placeholder="Ex: Chef de projet, Responsable chantier", key="synonymes")
        st.caption("💡 Pour trouver plus de synonymes, utilisez le Magicien de sourcing 🤖")
        competences_obligatoires = st.text_input("Compétences obligatoires:", placeholder="Ex: Python, SQL", key="competences_obligatoires")
        secteur = st.text_input("Secteur d'activité:", placeholder="Ex: BTP, Informatique", key="secteur")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", placeholder="Ex: Excel, Communication", key="competences_optionnelles")
        exclusions = st.text_input("Mots à exclure:", placeholder="Ex: Stage, Alternance", key="exclusions")
        localisation = st.text_input("Localisation:", placeholder="Ex: Casablanca", key="localisation")
        employeur = st.text_input("Employeur actuel/précédent:", placeholder="Ex: TGCC", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)

        url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"

        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur LinkedIn", url_linkedin, context="boolean")

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste,
                     "requete": st.session_state["boolean_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", placeholder="Ex: Développeur Python", key="poste_xray")
    with col2:
        mots_cles = st.text_input("Mots-clés:", placeholder="Ex: Django, Flask", key="mots_cles_xray")
        localisation_xray = st.text_input("Localisation:", placeholder="Ex: Rabat", key="localisation_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"

        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Google", url, context="xray")

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray,
                     "requete": st.session_state["xray_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste:", placeholder="Ex: Data Analyst", key="poste_cse")
    competences_cse = st.text_input("Compétences clés:", placeholder="Ex: SQL, Power BI", key="competences_cse")
    localisation_cse = st.text_input("Localisation:", placeholder="Ex: Tanger", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", placeholder="Ex: TG ALU", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"

        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur CSE", cse_url, context="cse")

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse,
                     "requete": st.session_state["cse_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query_dogpile = st.text_input("Requête Dogpile:", placeholder="Ex: Ingénieur DevOps freelance Maroc", key="dogpile_query")

    if st.button("🔍 Lancer recherche Dogpile"):
        if query_dogpile:
            st.session_state["dogpile_url"] = f"https://www.dogpile.com/serp?q={quote(query_dogpile)}"

    if st.session_state.get("dogpile_url"):
        action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Dogpile", st.session_state["dogpile_url"], context="dogpile")

# -------------------- Web Scraper --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    url = st.text_input("URL à analyser:", placeholder="Ex: https://www.example.com", key="scraper_url")

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
    url_linkedin = st.text_input("URL du profil LinkedIn:", placeholder="Ex: https://linkedin.com/in/...", key="inmail_url")
    poste_accroche = st.text_input("Poste à pourvoir:", placeholder="Ex: Chef de projet digital", key="inmail_poste")
    entreprise = st.text_input("Entreprise:", placeholder="Ex: TGCC", key="inmail_entreprise")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + \
                                            f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    # Questions prédéfinies
    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de ?",
        "Quels outils ou logiciels sont liés au métier de ?",
        "Quels mots-clés pour cibler les juniors pour le poste de ?",
        "Quels intitulés de postes similaires à ?",
        "Quels sont les principaux KPI associés au métier de ?",
        "Quels canaux de sourcing sont les plus efficaces pour recruter un ?",
        "Quels hashtags LinkedIn sont populaires dans le domaine de ?",
        "Quels types de profils freelances peuvent correspondre au poste de ?",
        "Quelles certifications sont souvent exigées pour le métier de ?",
        "Quels sont les mots-clés pour trouver des profils seniors en ?",
    ]

    q_choice = st.selectbox("📌 Choisir une question prédéfinie:", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question:", value=q_choice if q_choice else "", key="magicien_question")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            while True:
                elapsed = int(time.time() - start_time)
                progress.progress(min(100, elapsed), text=f"⏳ Génération... {min(100, elapsed)}% - {elapsed}s")
                if elapsed > 2:  # simulation du temps de réponse
                    break
                time.sleep(1)
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds de manière concise et exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state["magicien_reponse"] = result["content"]

            if "magicien_history" not in st.session_state:
                st.session_state["magicien_history"] = []
            st.session_state["magicien_history"].append({"q": question, "a": result["content"]})

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)

    if "magicien_history" in st.session_state and st.session_state["magicien_history"]:
        st.subheader("📜 Historique")
        for i, item in enumerate(st.session_state["magicien_history"]):
            with st.expander(f"Q{i+1}: {item['q']}"):
                st.write(item["a"])
                if st.button(f"🗑️ Supprimer Q{i+1}", key=f"del_q{i}"):
                    st.session_state["magicien_history"].pop(i)
                    st.rerun()

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", placeholder="Ex: Ahmed", key="perm_prenom")
    nom = st.text_input("Nom:", placeholder="Ex: El Mansouri", key="perm_nom")
    entreprise = st.text_input("Nom de l'entreprise:", placeholder="Ex: tgcc", key="perm_domaine")

    if st.button("🔮 Générer permutations"):
        if prenom and nom and entreprise:
            st.session_state["perm_result"] = [
                f"{prenom.lower()}.{nom.lower()}@{entreprise}.com",
                f"{prenom[0].lower()}{nom.lower()}@{entreprise}.ma",
                f"{nom.lower()}.{prenom.lower()}@{entreprise}.com"
            ]

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester sur : [Hunter.io](https://hunter.io/) | [NeverBounce](https://neverbounce.com/)")

# -------------------- Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    if st.session_state.library_entries:
        search_term = st.text_input("🔎 Rechercher:", placeholder="Ex: Développeur")
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
