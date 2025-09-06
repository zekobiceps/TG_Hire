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
    ask_deepseek,
)

# Init session
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Sidebar token counter ----------------
with st.sidebar:
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.markdown(f"🔑 **Tokens utilisés (session)**: {used}")
    st.markdown(f"📊 **Total cumulé**: {total}")

# ---------------- Style bouton uniforme ----------------
def action_buttons(buttons):
    """Affiche plusieurs boutons alignés à gauche, même taille"""
    cols = st.columns(len(buttons))
    for i, (label, color, action) in enumerate(buttons):
        with cols[i]:
            if st.button(label, key=f"{label}_{i}", use_container_width=True):
                if action.startswith("http"):  # lien externe
                    st.markdown(f"<meta http-equiv='refresh' content='0; url={action}'>", unsafe_allow_html=True)
                elif action == "save":
                    return "save"

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Boolean",
    "🎯 X-Ray",
    "🔎 CSE",
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
        poste = st.text_input("Poste:", key="poste")
        synonymes = st.text_input("Synonymes:", key="synonymes")
        st.caption("💡 Pour plus de synonymes, utilisez le Magicien 🤖")
        comp_oblig = st.text_input("Compétences obligatoires:", key="comp_oblig")
        secteur = st.text_input("Secteur:", key="secteur")
    with col2:
        comp_opt = st.text_input("Compétences optionnelles:", key="comp_opt")
        exclusions = st.text_input("Exclusions:", key="exclusions")
        localisation = st.text_input("Localisation:", key="localisation")
        employeur = st.text_input("Employeur:", key="employeur")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, comp_oblig, comp_opt, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)

        url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"

        action = action_buttons([
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 LinkedIn", "#805ad5", url_linkedin),
        ])

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", "poste": poste,
                     "requete": st.session_state["boolean_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# ---------------- X-Ray ----------------
with tab2:
    st.header("🎯 X-Ray")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray")
    with col2:
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray")
        localisation_xray = st.text_input("Localisation:", key="localisation_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"

        action = action_buttons([
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 Google", "#d69e2e", url),
        ])

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray", "poste": poste_xray,
                     "requete": st.session_state["xray_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# ---------------- CSE ----------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste:", key="poste_cse")
    comp_cse = st.text_input("Compétences:", key="comp_cse")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse")

    if st.button("🔍 Lancer recherche CSE"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, comp_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"

        action = action_buttons([
            ("💾 Sauvegarder", "#38a169", "save"),
            ("🌐 CSE", "#d69e2e", cse_url),
        ])

        if action == "save":
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", "poste": poste_cse,
                     "requete": st.session_state["cse_query"]}
            st.session_state.library_entries.append(entry)
            save_library_entries()
            st.success("✅ Sauvegardé dans la bibliothèque")

# ---------------- Dogpile ----------------
with tab4:
    st.header("🐶 Dogpile")
    query_dog = st.text_input("Requête Dogpile:", key="dogpile_query")

    if st.button("🔍 Lancer Dogpile"):
        if query_dog:
            url_dog = f"https://www.dogpile.com/serp?q={quote(query_dog)}"
            st.session_state["dogpile_url"] = url_dog

    if st.session_state.get("dogpile_url"):
        action_buttons([
            ("🌐 Ouvrir Dogpile", "#2b6cb0", st.session_state["dogpile_url"])
        ])

# ---------------- Magicien ----------------
with tab7:
    st.header("🤖 Magicien de sourcing")

    questions_pretes = [
        "Quels sont les synonymes possibles pour le métier de ",
        "Quels outils ou logiciels sont liés au métier de ",
        "Quels mots-clés pour cibler les juniors pour le poste de ",
        "Quels arguments d’attraction utiliser pour recruter un ",
        "Quels hashtags LinkedIn utiliser pour trouver un ",
    ]
    question_type = st.selectbox("Choisissez une question:", questions_pretes)
    poste_magicien = st.text_input("Nom du poste:", key="poste_magicien")

    if st.button("✨ Poser la question", type="primary"):
        if poste_magicien:
            question = question_type + poste_magicien
            start_time = time.time()
            progress = st.progress(0, text="⏳ Génération en cours...")
            for i in range(1, 101):
                elapsed = int(time.time() - start_time)
                progress.progress(i, text=f"⏳ Génération... {i}% - {elapsed}s")
                time.sleep(0.01)
            messages = [
                {"role": "system", "content": "Tu es un expert en sourcing RH et recrutement. Réponds de manière concise et exploitable."},
                {"role": "user", "content": question}
            ]
            result = ask_deepseek(messages, max_tokens=300)
            st.session_state["magicien_reponse"] = result["content"]

    if st.session_state.get("magicien_reponse"):
        st.text_area("Réponse:", value=st.session_state["magicien_reponse"], height=200)
