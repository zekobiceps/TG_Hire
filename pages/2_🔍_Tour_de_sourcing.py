import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import quote
import time

# Import utils
from utils import (
    init_session_state,
    save_library_entries,
    generate_boolean_query,
    generate_xray_query,
    generate_accroche_inmail,
    ask_deepseek
)

# ---------------- Initialisation ----------------
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Compteur Tokens (Sidebar) ----------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# ---------------- Boutons uniformes ----------------
def action_buttons(save_label, open_label, url, context="default"):
    """Deux petits boutons alignés à gauche"""
    col1, col2, _ = st.columns([1, 1, 6])
    with col1:
        if st.button(save_label, key=f"{context}_save", use_container_width=True):
            return "save"
    with col2:
        st.markdown(
            f"""
            <a href="{url}" target="_blank">
                <button style="
                    width:100%;
                    padding:5px 10px;
                    background:#2b6cb0;
                    color:white;
                    border:none;
                    border-radius:5px;
                    cursor:pointer;
                    font-size:13px;">
                    {open_label}
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )
    return None

# ---------------- Onglets ----------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Boolean",
    "🎯 X-Ray",
    "🔎 CSE LinkedIn",
    "🐶 Dogpile",
    "🕷️ Web Scraper",
    "✉️ InMail",
    "🤖 Magicien",
    "📧 Permutator",
    "📚 Bibliothèque"
])

# ---------------- Boolean ----------------
with tab1:
    st.header("🔍 Recherche Boolean")
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="poste", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes:", key="synonymes", placeholder="Ex: Chef de projet, Conducteur de travaux")
        comp_oblig = st.text_input("Compétences obligatoires:", key="comp_oblig", placeholder="Ex: AutoCAD, Gestion de chantier")
        secteur = st.text_input("Secteur:", key="secteur", placeholder="Ex: BTP, Immobilier")
    with col2:
        comp_opt = st.text_input("Compétences optionnelles:", key="comp_opt", placeholder="Ex: Excel, Anglais")
        exclusions = st.text_input("Exclusions:", key="exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="localisation", placeholder="Ex: Casablanca")
        employeur = st.text_input("Employeur:", key="employeur", placeholder="Ex: TGCC")

    if st.button("🪄 Générer", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, comp_oblig, comp_opt, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête:", value=st.session_state["boolean_query"], height=120)
        url = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur LinkedIn", url, "boolean")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean",
                     "poste": poste, "requete": st.session_state["boolean_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")

# ---------------- X-Ray ----------------
with tab2:
    st.header("🎯 X-Ray")
    col1, col2 = st.columns(2)
    with col1:
        site = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site")
        poste_x = st.text_input("Poste:", key="poste_xray", placeholder="Ex: Data Scientist")
    with col2:
        mots = st.text_input("Mots-clés:", key="mots_xray", placeholder="Ex: Python, Machine Learning")
        loc = st.text_input("Localisation:", key="loc_xray", placeholder="Ex: Rabat")

    if st.button("🔍 Construire", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site, poste_x, mots, loc)

    if st.session_state.get("xray_query"):
        st.text_area("Requête:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Google", url, "xray")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray",
                     "poste": poste_x, "requete": st.session_state["xray_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")

# ---------------- CSE ----------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste:", key="poste_cse", placeholder="Ex: Chef de projet IT")
    comp_cse = st.text_input("Compétences:", key="comp_cse", placeholder="Ex: Agile, PMP")
    loc_cse = st.text_input("Localisation:", key="loc_cse", placeholder="Ex: Marrakech")
    ent_cse = st.text_input("Entreprise:", key="ent_cse", placeholder="Ex: OCP")

    if st.button("🔍 Lancer CSE"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, comp_cse, loc_cse, ent_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête:", value=st.session_state["cse_query"], height=100)
        url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
        action = action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur CSE", url, "cse")
        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE",
                     "poste": poste_cse, "requete": st.session_state["cse_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé")

# ---------------- Dogpile ----------------
with tab4:
    st.header("🐶 Dogpile")
    query = st.text_input("Requête Dogpile:", key="dogpile_query", placeholder="Ex: ingénieur civil Casablanca TGCC")

    if st.button("🔍 Lancer Dogpile"):
        if query:
            st.session_state["dogpile_url"] = f"https://www.dogpile.com/serp?q={quote(query)}"

    if st.session_state.get("dogpile_url"):
        url = st.session_state["dogpile_url"]
        action_buttons("💾 Sauvegarder", "🌐 Ouvrir sur Dogpile", url, "dogpile")

# ---------------- Web Scraper ----------------
with tab5:
    st.header("🕷️ Web Scraper")
    choix = st.selectbox("Objectif:", [
        "Veille salariale & marché",
        "Intelligence concurrentielle",
        "Contact personnalisé",
        "Collecte de CV / emails / téléphones"
    ], key="scraper_choix")
    url = st.text_input("URL à analyser:", key="scraper_url", placeholder="Ex: https://exemple.com")

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

# ---------------- InMail ----------------
with tab6:
    st.header("✉️ Générateur d'InMail")
    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url", placeholder="Ex: https://www.linkedin.com/in/nom")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste", placeholder="Ex: Responsable RH")
    entreprise = st.text_input("Entreprise:", key="inmail_entreprise", placeholder="Ex: TGCC")

    if st.button("💌 Générer InMail", type="primary"):
        st.session_state["inmail_message"] = generate_accroche_inmail(url_linkedin, poste_accroche) + \
                                            f"\n\nNous serions ravis de discuter avec vous chez {entreprise}."

    if st.session_state.get("inmail_message"):
        st.text_area("Message InMail:", value=st.session_state["inmail_message"], height=200)

# ---------------- Magicien ----------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    if "magicien_history" not in st.session_state:
        st.session_state.magicien_history = []

    question = st.text_area("Votre question:", key="magicien_question",
                            placeholder="Ex: Quels sont les synonymes possibles pour le métier de Développeur Python ?")

    if st.button("✨ Poser", type="primary"):
        if question:
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            i = 0
            while True:
                elapsed = int(time.time() - start_time)
                if i < 80:
                    i += 1
                    progress.progress(i, text=f"⏳ {i}% - {elapsed}s")
                    time.sleep(0.05)
                else:
                    progress.progress(i, text=f"⏳ En attente... {elapsed}s")
                    time.sleep(0.2)

                messages = [
                    {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement."},
                    {"role": "user", "content": question}
                ]
                result = ask_deepseek(messages, max_tokens=300)
                if result and "content" in result:
                    st.session_state.magicien_history.append({"q": question, "r": result["content"]})
                    progress.progress(100, text=f"✅ Terminé en {elapsed}s")
                    break

    if st.session_state.magicien_history:
        st.subheader("📜 Historique")
        for i, item in enumerate(st.session_state.magicien_history):
            with st.expander(f"Q{i+1}: {item['q']}"):
                st.text_area("Réponse:", value=item["r"], height=200, key=f"rep_{i}")
                if st.button("🗑️ Supprimer", key=f"del_{i}"):
                    st.session_state.magicien_history.pop(i)
                    st.experimental_rerun()

# ---------------- Permutator ----------------
with tab8:
    st.header("📧 Email Permutator")
    prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Ex: Ali")
    nom = st.text_input("Nom:", key="perm_nom", placeholder="Ex: Benjelloun")
    entreprise = st.text_input("Nom de l'entreprise:", key="perm_domaine", placeholder="Ex: TGCC")

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

# ---------------- Bibliothèque ----------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    if st.session_state.library_entries:
        search_term = st.text_input("🔎 Rechercher:", placeholder="Ex: Data Scientist")
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
                if st.button("🗑️ Supprimer", key=f"del_lib_{i}"):
                    st.session_state.library_entries.remove(entry)
                    save_library_entries()
                    st.experimental_rerun()
    else:
        st.info("Aucune recherche sauvegardée")
