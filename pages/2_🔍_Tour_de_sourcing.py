import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
from urllib.parse import quote

# Import explicite depuis utils.py
from utils import (
    init_session_state,
    save_library_entries,
    generate_boolean_query,
    generate_xray_query,
    generate_accroche_inmail,
    ask_deepseek
)

# -------------------- Initialiser session --------------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Compteur tokens global --------------------
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
                <button style="padding:6px 12px; background:#3182ce; color:white; border:none;
                               border-radius:6px; cursor:pointer; font-size:14px;">
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
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", placeholder="Ex: AutoCAD, Gestion de projet")
        secteur = st.text_input("Secteur d'activité:", placeholder="Ex: BTP, Industrie")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", placeholder="Ex: Anglais, Lean management")
        exclusions = st.text_input("Mots à exclure:", placeholder="Ex: stage, alternance")
        localisation = st.text_input("Localisation:", placeholder="Ex: Casablanca, Maroc")
        employeur = st.text_input("Employeur actuel/précédent:", placeholder="Ex: TGCC, SGTM")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)

        # Boutons Sauvegarder + LinkedIn
        url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
        clicked = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur LinkedIn", url_linkedin, context="boolean")

        if clicked == "save":
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
        poste_xray = st.text_input("Poste:", placeholder="Ex: Développeur Python")
    with col2:
        mots_cles = st.text_input("Mots-clés:", placeholder="Ex: Django, Flask")
        localisation_xray = st.text_input("Localisation:", placeholder="Ex: Paris")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"

        clicked = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Google", url, context="xray")

        if clicked == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray,
                     "requete": st.session_state["xray_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE (Custom Search Engine) LinkedIn :")
    poste_cse = st.text_input("Poste recherché:", placeholder="Ex: Responsable RH")
    competences_cse = st.text_input("Compétences clés:", placeholder="Ex: SIRH, Formation")
    localisation_cse = st.text_input("Localisation:", placeholder="Ex: Rabat")
    entreprise_cse = st.text_input("Entreprise:", placeholder="Ex: OCP, BMCE")

    if st.button("🔍 Lancer recherche CSE"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"

        clicked = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur CSE", cse_url, context="cse")

        if clicked == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse,
                     "requete": st.session_state["cse_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", placeholder="Ex: Data Engineer Maroc")
    if st.button("🔎 Lancer recherche Dogpile"):
        st.session_state["dogpile_query"] = query

    if st.session_state.get("dogpile_query"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_query"], height=100)
        dogpile_url = f"https://www.dogpile.com/serp?q={quote(st.session_state['dogpile_query'])}"

        clicked = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Dogpile", dogpile_url, context="dogpile")

        if clicked == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", "poste": query,
                     "requete": st.session_state["dogpile_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

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
                texte = soup.get_text()[:1200]  # extrait limité pour lecture
                emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte))
                st.session_state["scraper_result"] = texte
                st.session_state["scraper_emails"] = emails
            except Exception as e:
                st.error(f"Erreur lors du scraping : {e}")

    if st.session_state.get("scraper_result"):
        st.text_area("Extrait du contenu:", value=st.session_state["scraper_result"], height=200)
        if st.session_state.get("scraper_emails"):
            st.info("📧 Emails détectés: " + ", ".join(st.session_state["scraper_emails"]))

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail")
    url_linkedin = st.text_input("URL du profil LinkedIn:", placeholder="https://www.linkedin.com/in/nom-prenom/")
    poste_accroche = st.text_input("Poste à pourvoir:", placeholder="Ex: Chef de projet digital")
    entreprise = st.text_input("Entreprise:", placeholder="Ex: TGCC")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + \
                                            f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de Développeur Python ?",
        "Quels outils ou logiciels sont liés au métier de Data Scientist ?",
        "Quels mots-clés pour cibler les juniors pour le poste de Chef de projet IT ?",
        "Quels intitulés similaires au poste d’Ingénieur DevOps ?",
        "Quels critères éliminatoires fréquents pour un Responsable RH ?"
    ]
    q_choice = st.selectbox("📌 Questions prêtes :", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question :", value=q_choice if q_choice else "", key="magicien_question",
                            placeholder="Ex: Quels sont les synonymes possibles pour le métier de Développeur Python ?")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            percent = 0
            while percent < 100:
                elapsed = int(time.time() - start_time)
                percent = min(99, percent + 1)  # ne jamais bloquer à 100 avant la fin
                progress.progress(percent, text=f"⏳ Génération... {percent}% - {elapsed}s")
                time.sleep(0.05)

            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds de manière concise, claire et exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state.magicien_reponse = result["content"]
            st.session_state.magicien_history = st.session_state.get("magicien_history", [])
            st.session_state.magicien_history.append({"q": question, "r": result["content"]})

    # Historique
    if st.session_state.get("magicien_history"):
        st.subheader("📝 Historique des réponses")
        for i, item in enumerate(st.session_state.magicien_history[::-1]):  # dernier en premier
            with st.expander(f"❓ {item['q'][:60]}..."):
                st.write(item["r"])
                if st.button("🗑️ Supprimer", key=f"del_magicien_{i}"):
                    st.session_state.magicien_history.remove(item)
                    st.experimental_rerun()

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Ex: Ahmed")
    nom = st.text_input("Nom:", key="perm_nom", placeholder="Ex: El Mansouri")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_domaine", placeholder="Ex: jet-contractors")

    if st.button("🔮 Générer permutations"):
        if prenom and nom and entreprise:
            domaines_possibles = [f"{entreprise}.com", f"{entreprise}.ma"]
            permutations = []
            for domaine in domaines_possibles:
                permutations.append(f"{prenom.lower()}.{nom.lower()}@{domaine}")
                permutations.append(f"{prenom[0].lower()}{nom.lower()}@{domaine}")
                permutations.append(f"{nom.lower()}.{prenom.lower()}@{domaine}")

            st.session_state["perm_result"] = list(set(permutations))

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester le fonctionnement d'une boîte mail sur : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

# -------------------- Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    if st.session_state.library_entries:
        search_term = st.text_input("🔎 Rechercher:", placeholder="Ex: développeur")
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
