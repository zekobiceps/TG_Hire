import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import time
from urllib.parse import quote
from datetime import datetime

# Import depuis utils
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

# -------------------- Compteur Tokens --------------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# -------------------- Style boutons uniformes --------------------
def action_buttons(buttons):
    """Affiche plusieurs boutons uniformes alignés à gauche"""
    cols = st.columns(len(buttons))
    for i, (label, color, action) in enumerate(buttons):
        with cols[i]:
            if action == "save":
                if st.button(label, key=f"{label}_{i}", use_container_width=False):
                    return "save"
            else:
                st.markdown(
                    f"""
                    <a href="{action}" target="_blank">
                        <button style="
                            padding:6px 12px;
                            margin-right:4px;
                            background:{color};
                            color:white;
                            border:none;
                            border-radius:6px;
                            cursor:pointer;
                            font-size:14px;">
                            {label}
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
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
        poste = st.text_input("Poste recherché:", key="poste")
        synonymes = st.text_input("Synonymes (séparés par des virgules):", key="synonymes")
        st.caption("💡 Pour trouver plus de synonymes, utilisez le Magicien de sourcing 🤖")
        comp_oblig = st.text_input("Compétences obligatoires:", key="comp_oblig")
        secteur = st.text_input("Secteur d'activité:", key="secteur")
    with col2:
        comp_opt = st.text_input("Compétences optionnelles:", key="comp_opt")
        exclusions = st.text_input("Mots à exclure:", key="exclusions")
        localisation = st.text_input("Localisation:", key="localisation")
        employeur = st.text_input("Employeur actuel/précédent:", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, comp_oblig, comp_opt, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)

        url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
        buttons = [
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 LinkedIn", "#805ad5", url_linkedin)
        ]
        action = action_buttons(buttons)

        if action == "save":
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "Boolean",
                "poste": poste,
                "requete": st.session_state["boolean_query"]
            }
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
        poste_xray = st.text_input("Poste:", key="poste_xray")
    with col2:
        mots_cles = st.text_input("Mots-clés:", key="mots_cles")
        localisation_xray = st.text_input("Localisation:", key="localisation_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"

        buttons = [
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 Google", "#d69e2e", url)
        ]
        action = action_buttons(buttons)

        if action == "save":
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "X-Ray",
                "poste": poste_xray,
                "requete": st.session_state["xray_query"]
            }
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse")
    comp_cse = st.text_input("Compétences clés:", key="comp_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE", type="primary"):
        st.session_state["cse_query"] = " ".join(
            filter(None, [poste_cse, comp_cse, localisation_cse, entreprise_cse])
        )

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"

        buttons = [
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 CSE", "#d69e2e", cse_url)
        ]
        action = action_buttons(buttons)

        if action == "save":
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "CSE",
                "poste": poste_cse,
                "requete": st.session_state["cse_query"]
            }
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Recherche:", key="dogpile_query")

    if st.button("🔎 Rechercher sur Dogpile", type="primary"):
        st.session_state["dogpile_result"] = query
        st.session_state["dogpile_url"] = f"https://www.dogpile.com/serp?q={quote(query)}"

    if st.session_state.get("dogpile_result"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_result"], height=100)

        buttons = [
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 Dogpile", "#3182ce", st.session_state["dogpile_url"])
        ]
        action = action_buttons(buttons)

        if action == "save":
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": "Dogpile",
                "poste": "",
                "requete": st.session_state["dogpile_result"]
            }
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
    ])
    url = st.text_input("URL à analyser:", key="scraper_url")

    if st.button("🚀 Scraper", type="primary"):
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
    entreprise = st.selectbox("Entreprise:", [
        "TGCC", "TG ALU", "TG COVER", "TG WOOD",
        "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"
    ], key="inmail_entreprise")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = (
            generate_accroche_inmail(url_linkedin, poste_accroche)
            + f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."
        )

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# -------------------- Magicien --------------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de Développeur Python ?",
        "Quels outils ou logiciels sont liés au métier de Data Scientist ?",
        "Quels mots-clés pour cibler les juniors pour le poste de Chef de projet ?",
        "Quels intitulés similaires à Ingénieur DevOps ?",
        "Quelles certifications rechercher pour un Administrateur Réseau ?"
    ]

    q_choice = st.selectbox("📌 Choisir une question prédéfinie:", [""] + questions_pretes)
    question = st.text_area("Votre question:", value=q_choice if q_choice else "", key="magicien_question")

    if st.button("✨ Poser la question", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            for i in range(1, 101):
                elapsed = int(time.time() - start_time)
                progress.progress(i, text=f"⏳ Génération... {i}% - {elapsed}s")
                time.sleep(0.02)
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds de manière concise et exploitable."},
                {"role": "user", "content": question}
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
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_entreprise")

    if st.button("🔮 Générer permutations", type="primary"):
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
        sort_by = st.selectbox("📌 Trier par:", ["Date", "Type", "Poste"])

        entries = st.session_state.library_entries
        if search_term:
            entries = [
                e for e in entries
                if search_term.lower() in e["requete"].lower() or search_term.lower() in e["poste"].lower()
            ]

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
