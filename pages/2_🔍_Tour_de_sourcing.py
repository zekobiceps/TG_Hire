import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import quote
from datetime import datetime

from utils import (
    init_session_state,
    save_library_entries,
    generate_boolean_query,
    generate_xray_query,
    generate_accroche_inmail,
    ask_deepseek,
)

# Initialiser la session
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Compteur Tokens --------------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# -------------------- Boutons uniformes --------------------
def action_buttons(save_label, open_label, url, context="default"):
    """Boutons Sauvegarder + Ouvrir alignés à gauche"""
    col1, col2, _ = st.columns([2, 2, 6])
    clicked = None
    with col1:
        if st.button(save_label, key=f"{context}_save", use_container_width=True):
            clicked = "save"
    with col2:
        st.markdown(
            f"""
            <a href="{url}" target="_blank">
                <button style="padding:6px 10px; background:#3182ce; color:white; border:none;
                               border-radius:6px; cursor:pointer; font-size:13px; width:100%;">
                    {open_label}
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )
    return clicked

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
    poste = st.text_input("Poste recherché:", key="poste", placeholder="Ex: Ingénieur de travaux")
    synonymes = st.text_input("Synonymes (séparés par des virgules):", key="synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
    st.caption("💡 Pour plus de synonymes, utilisez le Magicien de sourcing 🤖")
    competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires", placeholder="Ex: Autocad, Robot Structural Analysis")
    secteur = st.text_input("Secteur d'activité:", key="secteur", placeholder="Ex: BTP, Construction")
    competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles", placeholder="Ex: Primavera, ArchiCAD")
    exclusions = st.text_input("Mots à exclure:", key="exclusions", placeholder="Ex: Stage, Alternance")
    localisation = st.text_input("Localisation:", key="localisation", placeholder="Ex: Casablanca")
    employeur = st.text_input("Employeur actuel/précédent:", key="employeur", placeholder="Ex: TGCC")

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

        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur LinkedIn", url_linkedin, "boolean")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste,
                     "requete": st.session_state["boolean_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
    poste_xray = st.text_input("Poste:", key="poste_xray", placeholder="Ex: Développeur Fullstack")
    mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray", placeholder="Ex: Python, Django, API")
    localisation_xray = st.text_input("Localisation:", key="localisation_xray", placeholder="Ex: Rabat")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Google", url, "xray")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray,
                     "requete": st.session_state["xray_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse", placeholder="Ex: Architecte logiciel")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse", placeholder="Ex: Java, Spring")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse", placeholder="Ex: Marrakech")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse", placeholder="Ex: OCP")

    if st.button("🔍 Lancer recherche CSE", type="primary"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur CSE", cse_url, "cse")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse,
                     "requete": st.session_state["cse_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", key="dogpile_query", placeholder="Ex: Ingénieur réseaux Cisco Maroc")
    if query:
        dogpile_url = f"http://www.dogpile.com/serp?q={quote(query)}"
        action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Dogpile", dogpile_url, "dogpile")

# -------------------- Web Scraper --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    url = st.text_input("URL à analyser:", key="scraper_url", placeholder="Ex: https://www.exemple.com")

    if st.button("🚀 Scraper"):
        if url:
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")
                texte = soup.get_text()[:1200]
                emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte))
                st.session_state["scraper_result"] = texte
                st.session_state["scraper_emails"] = emails
            except Exception as e:
                st.error(f"Erreur scraping : {e}")

    if st.session_state.get("scraper_result"):
        st.text_area("Extrait du contenu:", value=st.session_state["scraper_result"], height=200)
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail")
    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url", placeholder="Ex: https://www.linkedin.com/in/nom-prenom/")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste", placeholder="Ex: Chef de projet BTP")
    entreprise = st.selectbox("Entreprise:", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de",
        "Quels outils ou logiciels sont liés au métier de",
        "Quels mots-clés pour cibler les juniors pour le poste de",
        "Quels intitulés similaires au poste de",
        "Quels critères éliminatoires fréquents pour le poste de",
        "Quels secteurs d’activité embauchent souvent pour le poste de",
        "Quelles certifications utiles pour le métier de",
        "Quels intitulés de poste équivalents dans le marché marocain pour",
        "Quels rôles proches à considérer lors du sourcing pour",
        "Quelles tendances de recrutement récentes pour le métier de"
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question :", value=q_choice if q_choice else "", key="magicien_question",
                            placeholder="Ex: Quels sont les synonymes possibles pour le métier de Développeur Python ?")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            elapsed = 0
            for i in range(100):
                elapsed = int(time.time() - start_time)
                progress.progress(i + 1, text=f"⏳ Génération... {i+1}% - {elapsed}s")
                time.sleep(0.2)  # ~20s max
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH au Maroc. Réponds de façon concise et directement exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state.magicien_reponse = result["content"]
            st.session_state.magicien_history = st.session_state.get("magicien_history", [])
            st.session_state.magicien_history.append({"q": question, "r": result["content"]})

    if st.session_state.get("magicien_history"):
        st.subheader("📝 Historique des réponses")
        for i, item in enumerate(st.session_state.magicien_history[::-1]):
            with st.expander(f"❓ {item['q']}"):
                st.write(item["r"])
                if st.button("🗑️ Supprimer", key=f"del_magicien_{i}"):
                    st.session_state.magicien_history.remove(item)
                    st.experimental_rerun()

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Ex: Ahmed")
    nom = st.text_input("Nom:", key="perm_nom", placeholder="Ex: El Mansouri")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_domaine", placeholder="Ex: tgcc")

    if st.button("🔮 Générer permutations"):
        if prenom and nom and entreprise:
            domaines_possibles = [f"{entreprise}.com", f"{entreprise}.ma"]
            permutations = []
            for domaine in domaines_possibles:
                permutations.append(f"{prenom.lower()}.{nom.lower()}@{domaine}")
                permutations.append(f"{prenom[0].lower()}{nom.lower()}@{domaine}")
                permutations.append(f"{nom.lower()}.{prenom.lower()}@{domaine}")

            # Recherche sur le site web
            try:
                site_url = f"http://www.{entreprise}.ma"
                r = requests.get(site_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                soup = BeautifulSoup(r.text, "html.parser")
                found_emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", soup.get_text()))
                if found_emails:
                    st.info("📧 Formats détectés sur le site : " + ", ".join(found_emails))
            except:
                st.warning("⚠️ Impossible de récupérer des emails sur le site officiel")

            st.session_state["perm_result"] = list(set(permutations))

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester le fonctionnement d'une boîte mail sur : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

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
