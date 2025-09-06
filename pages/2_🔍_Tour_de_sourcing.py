import streamlit as st
import webbrowser
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime

# Import explicite depuis utils.py
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
    initial_sidebar_state="expanded",
)

# -------------------- Compteur de tokens global (sidebar) --------------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# -------------------- Style bouton uniforme --------------------
def action_buttons(save_label, open_label, url, context="default"):
    """Deux boutons homogènes alignés à gauche"""
    col1, col2, _ = st.columns([1, 1, 8])

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
            unsafe_allow_html=True,
        )
    return None

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
        poste = st.text_input("Poste recherché:", key="poste", placeholder="Ex: Ingénieur travaux")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", key="synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires", placeholder="Ex: AutoCAD, MS Project")
        secteur = st.text_input("Secteur d'activité:", key="secteur", placeholder="Ex: BTP, Construction")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles", placeholder="Ex: BIM, Revit")
        exclusions = st.text_input("Mots à exclure:", key="exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="localisation", placeholder="Ex: Casablanca, Rabat")
        employeur = st.text_input("Employeur actuel/précédent:", key="employeur", placeholder="Ex: TGCC, SGTM")

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
    st.caption("🔎 Utilise Google pour cibler directement les profils sur LinkedIn ou GitHub.")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray", placeholder="Ex: Data Scientist")
    with col2:
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray", placeholder="Ex: Python, Machine Learning")
        localisation_xray = st.text_input("Localisation:", key="localisation_xray", placeholder="Ex: Maroc, France")

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
    st.header("🔎 CSE (Custom Search Engine) LinkedIn :")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse", placeholder="Ex: Responsable RH")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse", placeholder="Ex: Recrutement, Paie")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse", placeholder="Ex: Casablanca")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse", placeholder="Ex: TGCC")

    if st.button("🔍 Lancer recherche CSE"):
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
    query = st.text_input("Votre recherche:", key="dogpile_query", placeholder="Ex: Ingénieur DevOps Maroc")
    if st.button("🔍 Rechercher sur Dogpile"):
        if query:
            dogpile_url = f"https://www.dogpile.com/serp?q={quote(query)}"
            st.markdown(f"[👉 Ouvrir Dogpile]({dogpile_url})", unsafe_allow_html=True)

# -------------------- Web Scraper --------------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Choisir un objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    url = st.text_input("URL à analyser:", key="scraper_url", placeholder="Ex: https://www.site.com")

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
    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url", placeholder="Ex: https://www.linkedin.com/in/nom-prenom/")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste", placeholder="Ex: Chef de projet digital")
    entreprise = st.text_input("Entreprise:", key="inmail_entreprise", placeholder="Ex: TGCC")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + \
                                            f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")
    question = st.text_area("Votre question:", key="magicien_question",
                            placeholder="Ex: Quels sont les synonymes possibles pour le métier de Développeur Python ?")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")

            # Barre + compteur dynamique
            percent = 0
            while percent < 100:
                elapsed = int(time.time() - start_time)
                percent = min(99, elapsed * 5)
                progress.progress(percent, text=f"⏳ Génération... {percent}% - {elapsed}s")
                time.sleep(1)
                if elapsed > 30:
                    break

            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds toujours de manière concise et directement exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)

            elapsed = int(time.time() - start_time)
            progress.progress(100, text=f"✅ Terminé en {elapsed}s")
            st.session_state["magicien_reponse"] = result["content"]

            # Historique
            if "magicien_history" not in st.session_state:
                st.session_state["magicien_history"] = []
            st.session_state["magicien_history"].append({"q": question, "a": result["content"]})

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)

    # Historique
    if "magicien_history" in st.session_state and st.session_state["magicien_history"]:
        st.subheader("📜 Historique des questions")
        for i, item in enumerate(st.session_state["magicien_history"]):
            with st.expander(f"❓ {item['q']}"):
                st.write(item["a"])
                if st.button("🗑️ Supprimer", key=f"del_q_{i}"):
                    st.session_state["magicien_history"].pop(i)
                    st.rerun()

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Ex: Yassine")
    nom = st.text_input("Nom:", key="perm_nom", placeholder="Ex: El Amrani")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_domaine", placeholder="Ex: tgcc")

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
        search_term = st.text_input("🔎 Rechercher dans la bibliothèque:", placeholder="Ex: Ingénieur")
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
