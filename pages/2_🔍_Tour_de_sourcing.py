import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote
from datetime import datetime

from utils import (
    init_session_state,
    save_library_entries,
    generate_boolean_query,
    generate_xray_query,
    generate_accroche_inmail,
    ask_deepseek,
    get_email_from_charika,
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

# -------------------- Boutons CORRIGÉ --------------------
def action_buttons(save_label, open_label, url, context="default"):
    col1, col2, _ = st.columns([1, 2, 7])
    clicked = None
    with col1:
        if st.button(save_label, key=f"{context}_save", use_container_width=True):
            clicked = "save"
    with col2:
        # Utilisation de st.link_button au lieu de HTML personnalisé
        st.link_button(open_label, url, use_container_width=True)
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
    "📧 Permutateur Email",
    "📚 Bibliothèque"
])

# -------------------- Boolean --------------------
with tab1:
    st.header("🔍 Recherche Boolean")

    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="poste", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes:", key="synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="competences_obligatoires", placeholder="Ex: Autocad, Robot Structural Analysis")
        secteur = st.text_input("Secteur d'activité:", key="secteur", placeholder="Ex: BTP, Construction")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="competences_optionnelles", placeholder="Ex: Primavera, ArchiCAD")
        exclusions = st.text_input("Mots à exclure:", key="exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="localisation", placeholder="Ex: Casablanca")
        employeur = st.text_input("Employeur:", key="employeur", placeholder="Ex: TGCC")

    if st.button("🪄 Générer la requête Boolean", type="primary"):
        st.session_state["boolean_query"] = generate_boolean_query(
            poste, synonymes, competences_obligatoires,
            competences_optionnelles, exclusions, localisation, secteur
        )
        if employeur:
            st.session_state["boolean_query"] += f' AND ("{employeur}")'

    if st.session_state.get("boolean_query"):
        st.text_area("Requête Boolean:", value=st.session_state["boolean_query"], height=120)
        
        # CORRECTION: Utilisation du même modèle que X-Ray
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="boolean_save", use_container_width=True):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Boolean", 
                         "poste": poste, "requete": st.session_state["boolean_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
            st.link_button("🌐 Ouvrir sur LinkedIn", url_linkedin, use_container_width=True)

# -------------------- X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")

    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="site_cible")
        poste_xray = st.text_input("Poste:", key="poste_xray")
        mots_cles = st.text_input("Mots-clés:", key="mots_cles_xray")
    with col2:
        localisation_xray = st.text_input("Localisation:", key="localisation_xray")
        exclusions_xray = st.text_input("Mots à exclure:", key="exclusions_xray")

    if st.button("🔍 Construire X-Ray", type="primary"):
        st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
        if exclusions_xray:
            st.session_state["xray_query"] += f' -("{exclusions_xray}")'

    if st.session_state.get("xray_query"):
        st.text_area("Requête X-Ray:", value=st.session_state["xray_query"], height=120)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"

        # CORRECTION: Utilisation correcte des boutons pour X-Ray
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="xray_save", use_container_width=True):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "X-Ray",
                         "poste": poste_xray, "requete": st.session_state["xray_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            st.link_button("🌐 Ouvrir sur Google", url, use_container_width=True)
        with col3:
            st.link_button("🔎 Recherche avancée", f"https://www.google.com/advanced_search?q={quote(st.session_state['xray_query'])}", use_container_width=True)

# -------------------- CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    poste_cse = st.text_input("Poste recherché:", key="poste_cse", placeholder="Ex: Développeur Python")
    competences_cse = st.text_input("Compétences clés:", key="competences_cse", placeholder="Ex: Django, Flask")
    localisation_cse = st.text_input("Localisation:", key="localisation_cse", placeholder="Ex: Casablanca")
    entreprise_cse = st.text_input("Entreprise:", key="entreprise_cse", placeholder="Ex: TGCC")

    if st.button("🔍 Lancer recherche CSE", type="primary"):
        st.session_state["cse_query"] = " ".join(filter(None, [poste_cse, competences_cse, localisation_cse, entreprise_cse]))

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100)
        
        # CORRECTION: Utilisation du même modèle que X-Ray
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="cse_save", use_container_width=True):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "CSE", 
                         "poste": poste_cse, "requete": st.session_state["cse_query"]}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
            st.link_button("🌐 Ouvrir sur CSE", cse_url, use_container_width=True)

# -------------------- Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", key="dogpile_query", placeholder="Ex: Python developer Casablanca")
    
    if st.button("🔍 Rechercher", key="dogpile_search", type="primary"):
        st.session_state.dogpile_query = query
    
    if st.session_state.get("dogpile_query"):
        st.text_area("Requête Dogpile:", value=st.session_state.dogpile_query, height=80)
        
        # CORRECTION: Utilisation du même modèle que X-Ray
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="dogpile_save", use_container_width=True):
                entry = {"date": datetime.now().strftime("%Y-%m-%d"), "type": "Dogpile", 
                         "poste": "Recherche Dogpile", "requete": st.session_state.dogpile_query}
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            dogpile_url = f"http://www.dogpile.com/serp?q={quote(st.session_state.dogpile_query)}"
            st.link_button("🌐 Ouvrir sur Dogpile", dogpile_url, use_container_width=True)

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

    url_linkedin = st.text_input("URL du profil LinkedIn:", key="inmail_url")
    poste_accroche = st.text_input("Poste à pourvoir:", key="inmail_poste")

    entreprise = st.selectbox("Entreprise:", [
        "TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL",
        "TG STONE", "TGEM", "TGCC Immobilier"
    ], key="inmail_entreprise")

    mode_rapide_inmail = st.checkbox("⚡ Mode rapide (réponse concise)", key="inmail_fast")

    if st.button("💌 Générer InMail", type="primary"):
        with st.spinner("⏳ Génération en cours..."):
            # Appel direct à l'API sans simulation de progression
            result = generate_accroche_inmail(url_linkedin, poste_accroche)

            # CORRECTION: Nettoyage du texte d'introduction
            if result.startswith("Voici une accroche") or "Bonjour" in result[:100]:
                # Trouver le début du message réel
                lines = result.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith(("Voici", "Bonjour", "[Votre")):
                        result = '\n'.join(lines[i:])
                        break

            # CORRECTION: Ajout de la signature personnalisée
            signature = f"\n\nJe suis [Votre prénom] et je fais partie de l'équipe recrutement de {entreprise}, et nous serions ravis d'échanger avec vous."
            st.session_state["inmail_message"] = result + signature

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
        "Quels secteurs d'activité embauchent souvent pour le poste de",
        "Quelles certifications utiles pour le métier de",
        "Quels intitulés de poste équivalents dans le marché marocain pour",
        "Quels rôles proches à considérer lors du sourcing pour",
        "Quelles tendances de recrutement récentes pour le métier de"
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", [""] + questions_pretes, key="magicien_qchoice")
    question = st.text_area("Votre question :", value=q_choice if q_choice else "", key="magicien_question")

    mode_rapide_magicien = st.checkbox("⚡ Mode rapide (réponse concise)", key="magicien_fast")

    if st.button("✨ Poser la question", type="primary", key="ask_magicien"):
        if question:
            start_time = time.time()
            with st.spinner("⏳ Génération en cours..."):
                # Amélioration du prompt pour des réponses plus structurées
                enhanced_question = question
                if "synonymes" in question.lower():
                    enhanced_question += ". Réponds uniquement avec une liste de synonymes séparés par des virgules, sans introduction."
                elif "outils" in question.lower() or "logiciels" in question.lower():
                    enhanced_question += ". Réponds avec une liste à puces des outils, sans introduction."
                elif "compétences" in question.lower() or "skills" in question.lower():
                    enhanced_question += ". Réponds avec une liste à puces, sans introduction."
                
                result = ask_deepseek([{"role": "user", "content": enhanced_question}], 
                                     max_tokens=150 if mode_rapide_magicien else 300)
                
                total_time = int(time.time() - start_time)
                
                st.session_state.magicien_history.append({
                    "q": question, 
                    "r": result["content"], 
                    "time": total_time
                })

    if st.session_state.get("magicien_history"):
        st.subheader("📝 Historique des réponses")
        for i, item in enumerate(st.session_state.magicien_history[::-1]):
            with st.expander(f"❓ {item['q']} ({item['time']}s)"):
                st.write(item["r"])
                if st.button("🗑️ Supprimer", key=f"del_magicien_{i}"):
                    st.session_state.magicien_history.remove(item)
                    st.rerun()
        if st.button("🧹 Supprimer tout", key="clear_magicien_all"):
            st.session_state.magicien_history.clear()
            st.rerun()

# -------------------- Permutateur --------------------
with tab8:
    st.header("📧 Permutateur Email")

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom:", key="perm_prenom")
        nom = st.text_input("Nom:", key="perm_nom")
    with col2:
        entreprise = st.text_input("Entreprise:", key="perm_domaine")

    source = st.radio("Source de détection :", ["Site officiel", "Charika.ma"], key="perm_source", horizontal=True)

    if st.button("🔮 Générer permutations"):
        if prenom and nom and entreprise:
            permutations = []
            detected = get_email_from_charika(entreprise) if source == "Charika.ma" else None
            if detected:
                st.info(f"📧 Format détecté : {detected}")
                domain = detected.split("@")[1]
                permutations.append(f"{prenom.lower()}.{nom.lower()}@{domain}")
                permutations.append(f"{prenom[0].lower()}{nom.lower()}@{domain}")
                permutations.append(f"{nom.lower()}.{prenom.lower()}@{domain}")
                permutations.append(f"{prenom.lower()}{nom.lower()}@{domain}")
                permutations.append(f"{prenom.lower()}-{nom.lower()}@{domain}")
                permutations.append(f"{nom.lower()}.{prenom[0].lower()}@{domain}")
            st.session_state["perm_result"] = list(set(permutations))

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("Tester sur : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

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

# -------------------- Suppression de l'espace de prompt en bas de page --------------------
# Ce code doit être placé UNE SEULE FOIS à la fin du fichier

# Masquer spécifiquement le prompt qui apparaît en bas de tous les onglets
st.markdown("""
    <style>
    /* Cibler uniquement le prompt en bas de page sans affecter les autres champs */
    div[data-testid="stVerticalBlock"]:last-child div[data-testid="stVerticalBlock"]:last-child .stTextArea textarea {
        display: none;
    }
    div[data-testid="stVerticalBlock"]:last-child div[data-testid="stVerticalBlock"]:last-child .stTextArea label {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)