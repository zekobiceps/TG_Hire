import streamlit as st
from utils import *
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import time
import threading

init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Compteur tokens
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

# -------------------- Fonction Copier universelle --------------------
def copier_button(label, text, key):
    html_button = f"""
    <button onclick="navigator.clipboard.writeText(`{text}`)" 
            style="padding:5px 10px; background:#2b6cb0; color:white; border:none; border-radius:5px; cursor:pointer;">
        📋 {label}
    </button>
    """
    st.markdown(html_button, unsafe_allow_html=True)

# -------------------- Boolean --------------------
with tab1:
    st.header("🔍 Recherche Boolean")
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="poste")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", key="synonymes")
        st.caption("💡 Pour + de synonymes, utilisez le Magicien 🤖")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires")
        secteur = st.text_input("Secteur d'activité:", key="secteur")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles")
        exclusions = st.text_input("Mots à exclure:", key="exclusions")
        localisation = st.text_input("Localisation:", key="localisation")
        employeur = st.text_input("Employeur actuel/précédent:", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary", key="gen_boolean"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)
        colA, colB, colC, _ = st.columns([1,1,1,6])
        with colA:
            copier_button("Copier", st.session_state["boolean_query"], "copy_boolean")
        with colB:
            if st.button("📚 Sauvegarder", key="save_boolean"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste, "requete": st.session_state["boolean_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colC:
            url = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
            st.markdown(f"<a href='{url}' target='_blank'><button style='padding:5px 10px;'>🌐 LinkedIn</button></a>", unsafe_allow_html=True)

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

    if st.button("🔍 Construire X-Ray", type="primary", key="gen_xray"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        colA, colB, colC, _ = st.columns([1,1,1,6])
        with colA:
            copier_button("Copier", st.session_state["xray_query"], "copy_xray")
        with colB:
            if st.button("📚 Sauvegarder", key="save_xray"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray, "requete": st.session_state["xray_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colC:
            url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
            st.markdown(f"<a href='{url}' target='_blank'><button style='padding:5px 10px;'>🌐 Google</button></a>", unsafe_allow_html=True)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE", key="gen_cse"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        colA, colB, colC, _ = st.columns([1,1,1,6])
        with colA:
            copier_button("Copier", st.session_state["cse_query"], "copy_cse")
        with colB:
            if st.button("📚 Sauvegarder", key="save_cse"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse, "requete": st.session_state["cse_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colC:
            url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
            st.markdown(f"<a href='{url}' target='_blank'><button style='padding:5px 10px;'>🌐 CSE</button></a>", unsafe_allow_html=True)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:", key="dogpile_query")

    if st.button("🔎 Rechercher sur Dogpile", key="gen_dogpile"):
        st.session_state["dogpile_result"] = query

    if st.session_state.get("dogpile_result"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_result"], height=100)
        colA, colB, colC, _ = st.columns([1,1,1,6])
        with colA:
            copier_button("Copier", st.session_state["dogpile_result"], "copy_dogpile")
        with colB:
            if st.button("📚 Sauvegarder", key="save_dogpile"):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", "poste": "", "requete": st.session_state["dogpile_result"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with colC:
            url = f"https://www.dogpile.com/serp?q={quote(st.session_state['dogpile_result'])}"
            st.markdown(f"<a href='{url}' target='_blank'><button style='padding:5px 10px;'>🌐 Dogpile</button></a>", unsafe_allow_html=True)

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

# -------------------- InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail")
    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste")
    entreprise = st.selectbox("Entreprise:", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)
        if st.button("📚 Sauvegarder InMail"):
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "InMail", "poste": poste_accroche, "requete": st.session_state["inmail_message"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles ?",
        "Quels mots-clés utiliser pour recruter ?",
        "Quelles compétences sont indispensables ?",
        "Quels termes techniques sont associés ?",
        "Quels intitulés similaires existent ?",
        "Quels diplômes ou certifications rechercher ?",
        "Quelles compétences comportementales sont attendues ?",
        "Quels outils ou logiciels sont liés ?",
        "Quels hashtags LinkedIn pourraient être utiles ?",
        "Quels intitulés anglais sont utilisés ?",
        "Quels mots-clés exclure pour gagner en précision ?",
        "Quels profils transverses peuvent correspondre ?",
        "Quels mots-clés utiliser pour cibler les juniors ?",
        "Quels mots-clés utiliser pour cibler les seniors ?",
        "Quels synonymes ou variantes régionales existent ?"
    ]

    q_choice = st.selectbox("📌 Choisir une question prédéfinie:", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question:", value=q_choice if q_choice else "", key="magicien_question")

    if st.button("✨ Poser la question", type="primary", key="gen_magicien"):
        if question:
            progress_bar = st.progress(0)
            timer_placeholder = st.empty()
            start_time = time.time()

            def fetch_response():
                messages = [
                    {"role": "system", "content": "Tu es un expert en recrutement et sourcing RH. Réponds de manière concise et exploitable."},
                    {"role": "user", "content": question}
                ]
                result = ask_deepseek(messages, max_tokens=300)
                st.session_state["magicien_reponse"] = result["content"]

            thread = threading.Thread(target=fetch_response)
            thread.start()

            percent = 0
            while thread.is_alive():
                percent = min(percent + 5, 90)
                progress_bar.progress(percent, text=f"⏳ {percent}%")
                elapsed = int(time.time() - start_time)
                timer_placeholder.write(f"⏱️ {elapsed}s")
                time.sleep(0.2)

            thread.join()
            progress_bar.progress(100, text="✅ 100%")

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)

# -------------------- Permutator --------------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom")
    nom = st.text_input("Nom:", key="perm_nom")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_entreprise")

    if st.button("🔮 Générer permutations", key="gen_perm"):
        if prenom and nom and entreprise:
            domaines = [entreprise.lower() + ".com", entreprise.lower() + ".ma"]
            permutations = []
            for d in domaines:
                permutations.extend([
                    f"{prenom.lower()}.{nom.lower()}@{d}",
                    f"{prenom[0].lower()}{nom.lower()}@{d}",
                    f"{nom.lower()}.{prenom.lower()}@{d}"
                ])
            st.session_state["perm_result"] = permutations

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester le fonctionnement d'une boîte mail : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")
        colA, colB, _ = st.columns([1,1,8])
        with colA:
            copier_button("Copier", "\n".join(st.session_state["perm_result"]), "copy_perm")
        with colB:
            if st.button("📚 Sauvegarder", key="save_perm"):
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
