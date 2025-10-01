import streamlit as st
from utils import save_sourcing_entry_to_gsheet, load_sourcing_entries_from_gsheet

# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote
from datetime import datetime
import json
import os
import hashlib
import pandas as pd
from collections import Counter

# Fichier de persistance pour la bibliothèque
LIB_FILE = "library_entries.json"

# --- CSS pour augmenter la taille du texte des onglets ---
st.markdown("""
<style>
div[data-testid="stTabs"] button p {
    font-size: 18px; 
}
</style>
<script>
function copyToClipboard(text){
    navigator.clipboard.writeText(text).then(()=>{
        const ev = new Event('clipboard-copied');
        document.dispatchEvent(ev);
    });
}
document.addEventListener('click', function(e){
    if(e.target && e.target.dataset && e.target.dataset.copy){
         copyToClipboard(e.target.dataset.copy);
    }
});
</script>
""", unsafe_allow_html=True)

# -------------------- Configuration initiale --------------------
def _load_library_entries():
    if os.path.exists(LIB_FILE):
        try:
            with open(LIB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            return []
    return []

def init_session_state():
    """Initialise les variables de session"""
    defaults = {
        "api_usage": {"current_session_tokens": 0, "used_tokens": 0},
        "library_entries": _load_library_entries(),
        "magicien_history": [],
        "boolean_query": "",
        "boolean_snapshot": {},
        "xray_query": "",
        "xray_snapshot": {},
        "cse_query": "",
        "dogpile_query": "",
        "scraper_result": "",
        "scraper_emails": set(),
        "inmail_message": "",
        "perm_result": [],
        "inmail_objet": "",
        "inmail_generated": False,
        "inmail_profil_data": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def save_library_entries():
    """Sauvegarde les entrées de la bibliothèque en JSON"""
    try:
        with open(LIB_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.library_entries, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ Échec de sauvegarde bibliothèque: {e}")

def _split_terms(raw: str) -> list:
    if not raw:
        return []
    # support virgule / point-virgule / saut de ligne
    separators = [',', ';', '\n']
    for sep in separators:
        raw = raw.replace(sep, '|')
    terms = [t.strip() for t in raw.split('|') if t.strip()]
    # déduplication en conservant l'ordre
    seen = set(); ordered = []
    for t in terms:
        low = t.lower()
        if low not in seen:
            seen.add(low); ordered.append(t)
    return ordered

def _or_group(terms: list[str]) -> str:
    if not terms:
        return ''
    if len(terms) == 1:
        return f'"{terms[0]}"'
    return '(' + ' OR '.join(f'"{t}"' for t in terms) + ')'

def _and_group(terms: list[str]) -> str:
    if not terms:
        return ''
    if len(terms) == 1:
        return f'"{terms[0]}"'
    return '(' + ' AND '.join(f'"{t}"' for t in terms) + ')'

def generate_boolean_query(poste: str, synonymes: str, competences_obligatoires: str,
                           competences_optionnelles: str, exclusions: str, localisation: str, secteur: str,
                           employeur: str | None = None) -> str:
    """Génère une requête boolean normalisée.
    - Support multi-termes (virgule / ; / retour ligne)
    - Déduplication
    - Groupes OR / AND corrects
    """
    parts: list[str] = []
    if poste:
        parts.append(f'"{poste}"')
    syns = _split_terms(synonymes)
    if syns:
        parts.append(_or_group(syns))
    comp_ob = _split_terms(competences_obligatoires)
    if comp_ob:
        parts.append(_and_group(comp_ob))
    comp_opt = _split_terms(competences_optionnelles)
    if comp_opt:
        parts.append(_or_group(comp_opt))
    if localisation:
        parts.append(f'"{localisation}"')
    if secteur:
        parts.append(f'"{secteur}"')
    # exclusions → NOT group OR
    excl = _split_terms(exclusions)
    if excl:
        parts.append('NOT ' + _or_group(excl))
    if employeur:
        parts.append(f'("{employeur}")')
    return ' AND '.join(filter(None, parts))

def generate_boolean_variants(base_query: str, synonymes: str, comp_opt: str) -> list:
    """Génère quelques variantes simples:
    - Variante 1: sans compétences optionnelles
    - Variante 2: synonymes en fin
    - Variante 3: suppression des guillemets sur poste/synonymes (si applicable)
    """
    variants = []
    try:
        if not base_query:
            return []
        # Variante 1: retirer groupe optionnel si présent
        if comp_opt:
            opt_terms = _split_terms(comp_opt)
            if opt_terms:
                opt_group = _or_group(opt_terms)
                v1 = base_query.replace(f" AND {opt_group}", "")
                variants.append(("Sans compétences optionnelles", v1))
        # Variante 2: déplacer synonymes à la fin
        if synonymes:
            syn_terms = _split_terms(synonymes)
            syn_group = _or_group(syn_terms)
            if syn_group in base_query:
                parts = base_query.split(" AND ")
                reordered = [p for p in parts if p != syn_group] + [syn_group]
                variants.append(("Synonymes en fin", ' AND '.join(reordered)))
        # Variante 3: retirer guillemets des synonymes individuels si pas d'espaces
        if synonymes:
            syn_terms = _split_terms(synonymes)
            if syn_terms and all(' ' not in t for t in syn_terms):
                syn_group = _or_group(syn_terms)
                no_quotes = '(' + ' OR '.join(syn_terms) + ')'
                variants.append(("Synonymes sans guillemets", base_query.replace(syn_group, no_quotes)))
    except Exception:
        pass
    # déduplication titres
    seen = set(); final=[]
    for title, q in variants:
        if q not in seen:
            seen.add(q); final.append((title, q))
    return final[:3]

def generate_xray_query(site_cible: str, poste: str, mots_cles: str, localisation: str) -> str:
    """Génère une requête X-Ray améliorée.
    - Support multi mots-clés / localisations
    - Groupes OR pour élargir la recherche
    """
    site_map = {"LinkedIn": "site:linkedin.com/in", "GitHub": "site:github.com"}
    site = site_map.get(site_cible, "site:linkedin.com/in")
    parts = [site]
    if poste:
        parts.append(f'"{poste}"')
    kws = _split_terms(mots_cles)
    if kws:
        parts.append(_or_group(kws))
    locs = _split_terms(localisation)
    if locs:
        parts.append(_or_group(locs))
    return ' '.join(parts)

def generate_xray_variants(query: str, poste: str, mots_cles: str, localisation: str) -> list:
    variants = []
    try:
        if not query:
            return []
        # intitle sur poste
        if poste:
            v1 = query.replace(f'"{poste}"', f'intitle:"{poste}"') if f'"{poste}"' in query else query + f' intitle:"{poste}"'
            variants.append(("intitle: poste", v1))
        # Séparer mots-clés en OR explicite si plusieurs
        kws = _split_terms(mots_cles)
        if kws and len(kws) > 1:
            or_block = '(' + ' OR '.join(f'"{k}"' for k in kws) + ')'
            base_no = re.sub(r'\([^)]*\)', '', query)  # tentative retrait ancien groupe
            variants.append(("OR explicite mots-clés", f"{base_no} {or_block}".strip()))
        # Localisations en OR avec pattern "(Casablanca OR Rabat)"
        locs = _split_terms(localisation)
        if locs and len(locs) > 1:
            loc_block = '(' + ' OR '.join(f'"{l}"' for l in locs) + ')'
            if any(l in query for l in locs):
                variants.append(("Localisations OR", query + ' ' + loc_block))
    except Exception:
        pass
    # dédup
    seen=set(); final=[]
    for t,q in variants:
        if q not in seen:
            seen.add(q); final.append((t,q))
    return final[:3]

def build_xray_linkedin(poste: str, mots_cles: list[str], localisations: list[str],
                        langues: list[str], entreprises: list[str], ecoles: list[str],
                        seniority: str | None) -> str:
    """Construit une requête X-Ray LinkedIn plus riche.
    seniority peut être: 'junior','senior','manager'
    """
    parts = ["site:linkedin.com/in"]
    if poste:
        parts.append(f'("{poste}" OR intitle:"{poste}")')
    if mots_cles:
        parts.append('(' + ' OR '.join(f'"{m}"' for m in mots_cles) + ')')
    if localisations:
        parts.append('(' + ' OR '.join(f'"{l}"' for l in localisations) + ')')
    if langues:
        # tente de cibler la langue via mots fréquents
        for lg in langues:
            if lg.lower().startswith('fr'):
                parts.append('("Français" OR "French")')
            elif lg.lower().startswith('en'):
                parts.append('("Anglais" OR "English")')
            elif lg.lower().startswith('ar'):
                parts.append('("Arabe" OR "Arabic")')
    if entreprises:
        parts.append('("' + '" OR "'.join(entreprises) + '")')
    if ecoles:
        parts.append('("' + '" OR "'.join(ecoles) + '")')
    if seniority:
        if seniority == 'junior':
            parts.append('("junior" OR "débutant" OR "1 an" OR "2 ans")')
        elif seniority == 'senior':
            parts.append('("senior" OR "expérimenté" OR "8 ans" OR "10 ans")')
        elif seniority == 'manager':
            parts.append('("manager" OR "lead" OR "chef" OR "head")')
    return ' '.join(parts)

def generate_accroche_inmail(url_linkedin, poste_accroche):
    """Génère un message InMail basique"""
    return f"""Bonjour,

Votre profil sur LinkedIn a retenu mon attention, particulièrement votre expérience dans le domaine.

Je me permets de vous contacter concernant une opportunité de {poste_accroche} qui correspond parfaitement à votre profil. Votre expertise serait un atout précieux pour notre équipe.

Seriez-vous ouvert à un échange pour discuter de cette opportunité ?

Dans l'attente de votre retour,"""

def ask_deepseek(messages, max_tokens=300):
    """Simule l'appel à l'API DeepSeek"""
    time.sleep(1)  # Simulation de délai
    question = messages[0]["content"].lower()
    
    if "synonymes" in question:
        return {"content": "Ingénieur travaux, Chef de chantier, Conducteur de travaux, Responsable de projet BTP, Manager construction"}
    elif "outils" in question or "logiciels" in question:
        return {"content": "• AutoCAD\n• Revit\n• Primavera P6\n• MS Project\n• Robot Structural Analysis\n• SketchUp"}
    elif "compétences" in question:
        return {"content": "• Gestion de projet\n• Lecture de plans techniques\n• Management d'équipe\n• Budget et planning\n• Conformité réglementaire\n• Négociation fournisseurs"}
    else:
        return {"content": "Voici des informations pertinentes concernant votre demande. N'hésitez pas à préciser votre question pour une réponse plus ciblée."}

def get_email_from_charika(entreprise):
    """Simule la détection de format d'email depuis Charika"""
    formats = [
        "prenom.nom@entreprise.com",
        "pnom@entreprise.com",
        "prenom@entreprise.com",
        "nom.prenom@entreprise.com",
        "initialenom@entreprise.com"
    ]
    return formats[0]

# -------------------- Initialisation --------------------
init_session_state()
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Sidebar --------------------
with st.sidebar:
    st.title("📊 Statistiques")
    used = st.session_state.api_usage["current_session_tokens"]
    total = st.session_state.api_usage["used_tokens"]
    st.metric("🔑 Tokens (session)", used)
    st.metric("📊 Total cumulé", total)
    st.divider()
    st.info("💡 Assistant IA pour le sourcing et recrutement")

# -------------------- Onglets --------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔍 Boolean", "🎯 X-Ray", "🔎 CSE LinkedIn", "🐶 Dogpile", 
    "🕷️ Web Scraper", "✉️ InMail", "🤖 Magicien", "📧 Permutateur", "📚 Bibliothèque"
])

# -------------------- Tab 1: Boolean Search --------------------
with tab1:
    st.header("🔍 Recherche Boolean")
    col1, col2 = st.columns(2)
    with col1:
        poste = st.text_input("Poste recherché:", key="boolean_poste", placeholder="Ex: Ingénieur de travaux")
        synonymes = st.text_input("Synonymes:", key="boolean_synonymes", placeholder="Ex: Conducteur de travaux, Chef de chantier")
        competences_obligatoires = st.text_input("Compétences obligatoires:", key="boolean_comp_oblig", placeholder="Ex: Autocad, Robot Structural Analysis")
        secteur = st.text_input("Secteur d'activité:", key="boolean_secteur", placeholder="Ex: BTP, Construction")
    with col2:
        competences_optionnelles = st.text_input("Compétences optionnelles:", key="boolean_comp_opt", placeholder="Ex: Primavera, ArchiCAD")
        exclusions = st.text_input("Mots à exclure:", key="boolean_exclusions", placeholder="Ex: Stage, Alternance")
        localisation = st.text_input("Localisation:", key="boolean_loc", placeholder="Ex: Casablanca")
        employeur = st.text_input("Employeur:", key="boolean_employeur", placeholder="Ex: TGCC")

    col_gen = st.columns([2,2])
    with col_gen[0]:
        if st.button("Générer la requête Boolean par l'algorithme", type="primary", key="boolean_generate_algo"):
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
                st.session_state["boolean_query"] = generate_boolean_query(
                    poste, synonymes, competences_obligatoires,
                    competences_optionnelles, exclusions, localisation, secteur
                )
                if employeur:
                    st.session_state["boolean_query"] += f' AND ("{employeur}")'
                # snapshot des paramètres pour détection obsolescence
                st.session_state["boolean_snapshot"] = {
                    "poste": poste,
                    "synonymes": synonymes,
                    "comp_ob": competences_obligatoires,
                    "comp_opt": competences_optionnelles,
                    "exclusions": exclusions,
                    "localisation": localisation,
                    "secteur": secteur,
                    "employeur": employeur or ""
                }
                st.session_state["boolean_commentaire"] = st.session_state.get("boolean_commentaire", "")
                total_time = time.time() - start_time
                st.success(f"✅ Requête générée en {total_time:.1f}s")
    with col_gen[1]:
        if st.button("Générer la requête Boolean par l'IA", type="primary", key="boolean_generate_ia"):
            with st.spinner("🤖 Génération IA en cours..."):
                prompt = f"Génère une requête Boolean pour le sourcing avec les critères suivants:\nPoste: {poste}\nSynonymes: {synonymes}\nCompétences obligatoires: {competences_obligatoires}\nCompétences optionnelles: {competences_optionnelles}\nExclusions: {exclusions}\nLocalisation: {localisation}\nSecteur: {secteur}\nEmployeur: {employeur}"
                ia_result = ask_deepseek([{"role": "user", "content": prompt}], max_tokens=200)
                st.session_state["boolean_query"] = ia_result["content"].strip()
                st.session_state["boolean_snapshot"] = {
                    "poste": poste,
                    "synonymes": synonymes,
                    "comp_ob": competences_obligatoires,
                    "comp_opt": competences_optionnelles,
                    "exclusions": exclusions,
                    "localisation": localisation,
                    "secteur": secteur,
                    "employeur": employeur or ""
                }
                st.session_state["boolean_commentaire"] = st.session_state.get("boolean_commentaire", "")
                st.success("✅ Requête Boolean générée par IA")

    if st.session_state.get("boolean_query"):
        snap = st.session_state.get("boolean_snapshot", {})
        current_changed = any([
            snap.get("poste") != poste,
            snap.get("synonymes") != synonymes,
            snap.get("comp_ob") != competences_obligatoires,
            snap.get("comp_opt") != competences_optionnelles,
            snap.get("exclusions") != exclusions,
            snap.get("localisation") != localisation,
            snap.get("secteur") != secteur,
            snap.get("employeur") != (employeur or "")
        ]) if snap else False
        label_boolean = "Requête Boolean:" + (" 🔄 (obsolète - paramètres modifiés)" if current_changed else "")
        st.text_area(label_boolean, value=st.session_state["boolean_query"], height=120, key="boolean_area")
        # Zone commentaire
        st.session_state["boolean_commentaire"] = st.text_input("Commentaire (optionnel)", value=st.session_state.get("boolean_commentaire", ""), key="boolean_commentaire")
        # Boutons sur la même ligne à droite
        cols_btn = st.columns([1,1,1])
        with cols_btn[0]:
            st.markdown(f"<button data-copy=\"{st.session_state['boolean_query'].replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
        with cols_btn[1]:
            if st.button("💾 Sauvegarder", key="boolean_save", use_container_width=True):
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "Boolean",
                    "poste": poste,
                    "requete": st.session_state["boolean_query"],
                    "utilisateur": st.session_state.get("user", ""),
                    "source": "Boolean",
                    "commentaire": st.session_state.get("boolean_commentaire", "")
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                save_sourcing_entry_to_gsheet(entry)
                st.success("✅ Sauvegardé")
        with cols_btn[2]:
            url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
            st.link_button("🌐 Ouvrir sur LinkedIn", url_linkedin, use_container_width=True)
        # Variantes
        variants = generate_boolean_variants(st.session_state["boolean_query"], synonymes, competences_optionnelles)
        if variants:
            st.caption("🔀 Variantes proposées")
            for idx, (title, vq) in enumerate(variants):
                st.text_area(f"{title}", value=vq, height=80, key=f"bool_var_{idx}")
                st.session_state[f"boolean_commentaire_var_{idx}"] = st.text_input(f"Commentaire variante {idx+1}", value=st.session_state.get(f"boolean_commentaire_var_{idx}", ""), key=f"boolean_commentaire_var_{idx}")
                cols_var = st.columns([1,1,1])
                with cols_var[0]:
                    st.markdown(f"<button data-copy=\"{vq.replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
                with cols_var[1]:
                    if st.button(f"💾 Sauvegarder {idx+1}", key=f"bool_save_{idx}", use_container_width=True):
                        entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "type": "Boolean",
                            "poste": poste,
                            "requete": vq,
                            "utilisateur": st.session_state.get("user", ""),
                            "source": f"Boolean Variante {idx+1}",
                            "commentaire": st.session_state.get(f"boolean_commentaire_var_{idx}", "")
                        }
                        st.session_state.library_entries.append(entry)
                        save_library_entries()
                        save_sourcing_entry_to_gsheet(entry)
                        st.success(f"✅ Variante {idx+1} sauvegardée")
                with cols_var[2]:
                    url_var = f"https://www.linkedin.com/search/results/people/?keywords={quote(vq)}"
                    st.link_button(f"🌐 LinkedIn {idx+1}", url_var, use_container_width=True)

# -------------------- Tab 2: X-Ray --------------------
with tab2:
    st.header("🎯 X-Ray Google")
    col1, col2 = st.columns(2)
    with col1:
        site_cible = st.selectbox("Site cible:", ["LinkedIn", "GitHub"], key="xray_site")
        poste_xray = st.text_input("Poste:", key="xray_poste", placeholder="Ex: Développeur Python")
        mots_cles = st.text_input("Mots-clés:", key="xray_mots_cles", placeholder="Ex: Django, Flask")
    with col2:
        localisation_xray = st.text_input("Localisation:", key="xray_loc", placeholder="Ex: Casablanca")
        exclusions_xray = st.text_input("Mots à exclure:", key="xray_exclusions", placeholder="Ex: Stage, Junior")

    with st.expander("⚙️ Mode avancé LinkedIn", expanded=False):
        coladv1, coladv2, coladv3 = st.columns(3)
        with coladv1:
            seniority = st.selectbox("Séniorité", ["", "junior", "senior", "manager"], key="xray_senior")
            langues_adv = st.text_input("Langues (fr,en,ar)", key="xray_langs", placeholder="fr,en")
        with coladv2:
            entreprises_adv = st.text_input("Entreprises cibles", key="xray_ent_adv", placeholder="OCP, TGCC")
            ecoles_adv = st.text_input("Écoles / Universités", key="xray_ecoles", placeholder="EMI, ENSA")
        with coladv3:
            gen_avance = st.checkbox("Utiliser builder avancé", key="xray_use_adv")
            hint = st.caption("Construit une requête enrichie multi-filtres")

    if st.button("🔍 Construire X-Ray", type="primary", width="stretch", key="xray_build"):
        with st.spinner("⏳ Génération en cours..."):
            start_time = time.time()
            if st.session_state.get("xray_use_adv"):
                mots_list = _split_terms(mots_cles)
                loc_list = _split_terms(localisation_xray)
                langs_list = [l.strip() for l in st.session_state.get("xray_langs", "").split(',') if l.strip()]
                ent_list = [e.strip() for e in st.session_state.get("xray_ent_adv", "").split(',') if e.strip()]
                ecol_list = [e.strip() for e in st.session_state.get("xray_ecoles", "").split(',') if e.strip()]
                st.session_state["xray_query"] = build_xray_linkedin(poste_xray, mots_list, loc_list, langs_list, ent_list, ecol_list, st.session_state.get("xray_senior") or None)
            else:
                st.session_state["xray_query"] = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
            if exclusions_xray:
                st.session_state["xray_query"] += f' -("{exclusions_xray}")'
            st.session_state["xray_snapshot"] = {
                "site": site_cible,
                "poste": poste_xray,
                "mots_cles": mots_cles,
                "localisation": localisation_xray,
                "exclusions": exclusions_xray
            }
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("xray_query"):
        snapx = st.session_state.get("xray_snapshot", {})
        changed_x = any([
            snapx.get("site") != site_cible,
            snapx.get("poste") != poste_xray,
            snapx.get("mots_cles") != mots_cles,
            snapx.get("localisation") != localisation_xray,
            snapx.get("exclusions") != exclusions_xray
        ]) if snapx else False
        label_x = "Requête X-Ray:" + (" 🔄 (obsolète - paramètres modifiés)" if changed_x else "")
        st.text_area(label_x, value=st.session_state["xray_query"], height=120, key="xray_area")
        st.markdown(f"<button style='margin-top:4px' data-copy=\"{st.session_state['xray_query'].replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
        # Variantes
        x_vars = generate_xray_variants(st.session_state["xray_query"], poste_xray, mots_cles, localisation_xray)
        if x_vars:
            st.caption("🔀 Variantes proposées")
            for i,(title, qv) in enumerate(x_vars):
                st.text_area(title, value=qv, height=80, key=f"xray_var_{i}")
                st.markdown(f"<button data-copy=\"{qv.replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
        url = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="xray_save", width="stretch"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "X-Ray",
                    "poste": poste_xray, 
                    "requete": st.session_state["xray_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            st.link_button("🌐 Ouvrir sur Google", url, width="stretch")
        with col3:
            st.link_button("🔎 Recherche avancée", f"https://www.google.com/advanced_search?q={quote(st.session_state['xray_query'])}", width="stretch")

# -------------------- Tab 3: CSE --------------------
with tab3:
    st.header("🔎 CSE LinkedIn")
    col1, col2 = st.columns(2)
    with col1:
        poste_cse = st.text_input("Poste recherché:", key="cse_poste", placeholder="Ex: Développeur Python")
        competences_cse = st.text_input("Compétences clés:", key="cse_comp", placeholder="Ex: Django, Flask")
    with col2:
        localisation_cse = st.text_input("Localisation:", key="cse_loc", placeholder="Ex: Casablanca")
        entreprise_cse = st.text_input("Entreprise:", key="cse_ent", placeholder="Ex: TGCC")

    if st.button("🔍 Lancer recherche CSE", type="primary", width="stretch", key="cse_search"):
        with st.spinner("⏳ Construction de la requête..."):
            start_time = time.time()
            query_parts = []
            if poste_cse: query_parts.append(poste_cse)
            if competences_cse: query_parts.append(competences_cse)
            if localisation_cse: query_parts.append(localisation_cse)
            if entreprise_cse: query_parts.append(entreprise_cse)
            st.session_state["cse_query"] = " ".join(query_parts)
            total_time = time.time() - start_time
            st.success(f"✅ Requête générée en {total_time:.1f}s")

    if st.session_state.get("cse_query"):
        st.text_area("Requête CSE:", value=st.session_state["cse_query"], height=100, key="cse_area")
        st.markdown(f"<button style='margin-top:4px' data-copy=\"{st.session_state['cse_query'].replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="cse_save", width="stretch"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "CSE", 
                    "poste": poste_cse, 
                    "requete": st.session_state["cse_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
            st.link_button("🌐 Ouvrir sur CSE", cse_url, width="stretch")

# -------------------- Tab 4: Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", key="dogpile_query_input", placeholder="Ex: Python developer Casablanca")
    if st.button("🔍 Rechercher", key="dogpile_search_btn", type="primary", width="stretch"):
        if query:
            st.session_state["dogpile_query"] = query
            st.success("✅ Requête enregistrée")
    if st.session_state.get("dogpile_query"):
        st.text_area("Requête Dogpile:", value=st.session_state["dogpile_query"], height=80, key="dogpile_area")
        st.markdown(f"<button style='margin-top:4px' data-copy=\"{st.session_state['dogpile_query'].replace('"','&quot;')}\">📋 Copier</button>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Sauvegarder", key="dogpile_save_btn", width="stretch"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "type": "Dogpile", 
                    "poste": "Recherche Dogpile", 
                    "requete": st.session_state["dogpile_query"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success("✅ Sauvegardé")
        with col2:
            dogpile_url = f"http://www.dogpile.com/serp?q={quote(st.session_state['dogpile_query'])}"
            st.link_button("🌐 Ouvrir sur Dogpile", dogpile_url, width="stretch")

# -------------------- Tab 5: Web Scraper - Analyse Concurrentielle --------------------
# -------------------- Tab 5: Web Scraper - Analyse Concurrentielle --------------------
with tab5:
    st.header("🔍 Analyse Concurrentielle - Offres d'Emploi")
    
    # Configuration du scraping
    with st.expander("⚙️ Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            concurrents = st.text_area(
                "Sites des concurrents à analyser (1 par ligne):", 
                placeholder="https://jobs.vinci.com/fr/recherche-d'offres/Maroc\nhttps://www.rekrute.com/sogea-maroc-emploi.html",
                height=100
            )
            max_pages = st.slider("Nombre maximum de pages à analyser par site:", 1, 20, 5)
        
        with col2:
            mots_cles = st.text_input(
                "Mots-clés à rechercher (séparés par des virgules):",
                placeholder="ingénieur, coordinateur, mécanicien, acheteur"
            )
            delay = st.slider("Délai entre les requêtes (secondes):", 1, 10, 3)
    
    # Options d'analyse
    with st.expander("📊 Options d'analyse", expanded=False):
        analyse_options = st.multiselect(
            "Éléments à analyser:",
            ["Compétences recherchées", "Niveaux d'expérience", "Avantages proposés", 
             "Types de contrats", "Localisations", "Salaires mentionnés", "Processus de recrutement"],
            default=["Compétences recherchées", "Niveaux d'expérience", "Avantages proposés"]
        )
    
    if st.button("🚀 Lancer l'analyse concurrentielle", width="stretch", key="scraper_btn"):
        if concurrents:
            concurrents_list = [url.strip() for url in concurrents.split('\n') if url.strip()]
            mots_cles_list = [mot.strip().lower() for mot in mots_cles.split(',')] if mots_cles else []
            
            # Initialiser les résultats
            results = {
                "concurrent": [],
                "url": [],
                "titre_poste": [],
                "competences": [],
                "experience": [],
                "avantages": [],
                "mots_cles_trouves": []
            }
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, url in enumerate(concurrents_list):
                status_text.text(f"Analyse de {url}...")
                
                try:
                    # Simulation de scraping - À remplacer par votre logique réelle
                    time.sleep(delay)  # Respect du délai
                    
                    # Vérifier si c'est le site Vinci
                    if "vinci.com" in url:
                        try:
                            # Tentative de scraping réel du site Vinci
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            response = requests.get(url, headers=headers, timeout=10)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Chercher les éléments qui contiennent les offres d'emploi
                            # (Cette sélecteur est un exemple et doit être adapté au site réel)
                            offres = soup.select('.job-listing, .offer-item, .job-title, [class*="job"]')
                            
                            if offres:
                                for offre in offres[:20]:  # Limiter à 20 offres
                                    try:
                                        titre = offre.get_text(strip=True)
                                        if titre and len(titre) > 10:  # Filtrer les textes trop courts
                                            results["concurrent"].append("Vinci")
                                            results["url"].append(url)
                                            results["titre_poste"].append(titre)
                                            results["competences"].append("À analyser")
                                            results["experience"].append("Non spécifié")
                                            results["avantages"].append("À analyser")
                                            
                                            # Vérifier quels mots-clés correspondent
                                            mots_trouves = []
                                            for mot in mots_cles_list:
                                                if mot in titre.lower():
                                                    mots_trouves.append(mot)
                                            results["mots_cles_trouves"].append(", ".join(mots_trouves))
                                    except:
                                        continue
                            else:
                                st.warning(f"Aucune offre trouvée sur {url}. Utilisation des données simulées.")
                                # Fallback aux données simulées si le scraping échoue
                                postes_vinci = [
                                    {"titre": "Coordinateur HSE", "competences": "HSE, Normes de sécurité, Gestion des risques", "experience": "5+ ans", "avantages": "Assurance, Formation, Transport"},
                                    {"titre": "Ingénieur électromécanicien - Traitement des Eaux", "competences": "Électromécanique, Traitement des eaux, Maintenance", "experience": "3+ ans", "avantages": "Logement, Transport, Mutuelle"},
                                    # ... (ajouter d'autres postes simulés)
                                ]
                                
                                for poste in postes_vinci:
                                    results["concurrent"].append("Vinci")
                                    results["url"].append(url)
                                    results["titre_poste"].append(poste["titre"])
                                    results["competences"].append(poste["competences"])
                                    results["experience"].append(poste["experience"])
                                    results["avantages"].append(poste["avantages"])
                                    mots_trouves = []
                                    for mot in mots_cles_list:
                                        if mot in poste["titre"].lower() or mot in poste["competences"].lower():
                                            mots_trouves.append(mot)
                                    results["mots_cles_trouves"].append(", ".join(mots_trouves))
                                
                        except Exception as e:
                            st.error(f"Erreur lors du scraping de {url}: {str(e)}")
                            # Fallback aux données simulées en cas d'erreur
                            # ... (code de fallback similaire à ci-dessus)
                    
                    # Vérifier si c'est le site Rekrute (Sogea Maroc)
                    elif "rekrute.com" in url and "sogea" in url:
                        try:
                            # Tentative de scraping réel du site Rekrute
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            response = requests.get(url, headers=headers, timeout=10)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Chercher les éléments qui contiennent les offres d'emploi
                            # (Cette sélecteur est un exemple et doit être adapté au site réel)
                            offres = soup.select('.job-item, .offer-title, [class*="job"]')
                            
                            if offres:
                                for offre in offres[:10]:  # Limiter à 10 offres
                                    try:
                                        titre = offre.get_text(strip=True)
                                        if titre and len(titre) > 10:  # Filtrer les textes trop courts
                                            results["concurrent"].append("Sogea Maroc (Vinci)")
                                            results["url"].append(url)
                                            results["titre_poste"].append(titre)
                                            results["competences"].append("À analyser")
                                            results["experience"].append("Non spécifié")
                                            results["avantages"].append("À analyser")
                                            
                                            # Vérifier quels mots-clés correspondent
                                            mots_trouves = []
                                            for mot in mots_cles_list:
                                                if mot in titre.lower():
                                                    mots_trouves.append(mot)
                                            results["mots_cles_trouves"].append(", ".join(mots_trouves))
                                    except:
                                        continue
                            else:
                                st.warning(f"Aucune offre trouvée sur {url}. Utilisation des données simulées.")
                                # Fallback aux données simulées si le scraping échoue
                                postes_sogea = [
                                    {"titre": "Directeur de Travaux Hydraulique (H/F)", "competences": "Hydraulique, Gestion de projet, Management", "experience": "10+ ans", "avantages": "Voiture de fonction, Logement, Assurance"},
                                    {"titre": "Mécanicien Atelier", "competences": "Mécanique, Réparation, Maintenance", "experience": "3+ ans", "avantages": "Transport, Formation, Prime de performance"},
                                    # ... (ajouter d'autres postes simulés)
                                ]
                                
                                for poste in postes_sogea:
                                    results["concurrent"].append("Sogea Maroc (Vinci)")
                                    results["url"].append(url)
                                    results["titre_poste"].append(poste["titre"])
                                    results["competences"].append(poste["competences"])
                                    results["experience"].append(poste["experience"])
                                    results["avantages"].append(poste["avantages"])
                                    mots_trouves = []
                                    for mot in mots_cles_list:
                                        if mot in poste["titre"].lower() or mot in poste["competences"].lower():
                                            mots_trouves.append(mot)
                                    results["mots_cles_trouves"].append(", ".join(mots_trouves))
                                
                        except Exception as e:
                            st.error(f"Erreur lors du scraping de {url}: {str(e)}")
                            # Fallback aux données simulées en cas d'erreur
                            # ... (code de fallback similaire à ci-dessus)
                    
                    # Pour les autres sites
                    else:
                        try:
                            # Tentative de scraping générique pour les autres sites
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            response = requests.get(url, headers=headers, timeout=10)
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Chercher les éléments qui pourraient contenir des offres d'emploi
                            # (Cette approche est très générale et peut ne pas fonctionner)
                            potential_selectors = [
                                '.job', '.offer', '.employment', '.career', 
                                '[class*="job"]', '[class*="offer"]', '[class*="employment"]',
                                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'  # Les titres peuvent contenir des offres
                            ]
                            
                            offres_trouvees = False
                            for selector in potential_selectors:
                                offres = soup.select(selector)
                                for offre in offres[:5]:  # Limiter à 5 offres par sélecteur
                                    try:
                                        texte = offre.get_text(strip=True)
                                        if texte and len(texte) > 20 and len(texte) < 200:  # Filtrer les textes
                                            # Vérifier si le texte ressemble à un titre d'offre d'emploi
                                            mots_emploi = ["emploi", "job", "offre", "recrutement", "poste", "h/f", "f/h"]
                                            if any(mot in texte.lower() for mot in mots_emploi):
                                                results["concurrent"].append("Autre entreprise")
                                                results["url"].append(url)
                                                results["titre_poste"].append(texte)
                                                results["competences"].append("À analyser")
                                                results["experience"].append("Non spécifié")
                                                results["avantages"].append("À analyser")
                                                
                                                # Vérifier quels mots-clés correspondent
                                                mots_trouves = []
                                                for mot in mots_cles_list:
                                                    if mot in texte.lower():
                                                        mots_trouves.append(mot)
                                                results["mots_cles_trouves"].append(", ".join(mots_trouves))
                                                offres_trouvees = True
                                    except:
                                        continue
                            
                            if not offres_trouvees:
                                st.warning(f"Aucune offre détectée sur {url}. Le site peut nécessiter une configuration spécifique.")
                                # Ajouter une entrée générique
                                results["concurrent"].append("Autre entreprise")
                                results["url"].append(url)
                                results["titre_poste"].append("Poste varié - Analyse manuelle requise")
                                results["competences"].append("Compétences diverses")
                                results["experience"].append("Non spécifié")
                                results["avantages"].append("Avantages standards")
                                results["mots_cles_trouves"].append("")
                                
                        except Exception as e:
                            st.error(f"Erreur lors du scraping de {url}: {str(e)}")
                            # Ajouter une entrée d'erreur
                            results["concurrent"].append("Erreur de scraping")
                            results["url"].append(url)
                            results["titre_poste"].append(f"Erreur: {str(e)}")
                            results["competences"].append("N/A")
                            results["experience"].append("N/A")
                            results["avantages"].append("N/A")
                            results["mots_cles_trouves"].append("")
                
                except Exception as e:
                    st.error(f"Erreur avec {url}: {str(e)}")
                    # Ajouter une entrée d'erreur
                    results["concurrent"].append("Erreur")
                    results["url"].append(url)
                    results["titre_poste"].append(f"Erreur: {str(e)}")
                    results["competences"].append("N/A")
                    results["experience"].append("N/A")
                    results["avantages"].append("N/A")
                    results["mots_cles_trouves"].append("")
                
                progress_bar.progress((i + 1) / len(concurrents_list))
            
            status_text.text("Analyse terminée!")
            
            # Affichage des résultats
            if results["concurrent"]:
                total_postes = len(results["concurrent"])
                st.success(f"✅ {total_postes} postes trouvés sur {len(concurrents_list)} sites")
                
                # Création d'un DataFrame pour une meilleure visualisation
                try:
                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, width="stretch")
                    
                    # Afficher un résumé par entreprise
                    st.subheader("📊 Résumé par entreprise")
                    entreprises = {}
                    for i, entreprise in enumerate(results["concurrent"]):
                        if entreprise not in entreprises:
                            entreprises[entreprise] = 0
                        entreprises[entreprise] += 1
                    
                    for entreprise, count in entreprises.items():
                        st.write(f"- **{entreprise}**: {count} poste(s)")
                        
                except NameError:
                    st.error("Erreur: pandas n'est pas installé. Impossible de créer le DataFrame.")
                    # On continue sans DataFrame
                    for i, concurrent in enumerate(results["concurrent"]):
                        st.write(f"**{concurrent}** - {results['titre_poste'][i]}")
                        st.write(f"Compétences: {results['competences'][i]}")
                        st.write(f"Expérience: {results['experience'][i]}")
                        st.write(f"Avantages: {results['avantages'][i]}")
                        st.write("---")
                
                # Analyses avancées
                st.subheader("📈 Analyses")
                
                # Nuage de mots des compétences recherchées
                if "Compétences recherchées" in analyse_options:
                    st.write("**Compétences les plus recherchées:**")
                    all_skills = ", ".join(results["competences"]).lower()
                    skills_counter = Counter([skill.strip() for skill in all_skills.split(',')])
                    
                    if skills_counter:
                        # Affichage simplifié des compétences (sans nuage de mots)
                        st.write("Répartition des compétences:")
                        for skill, count in skills_counter.most_common(10):
                            st.write(f"- {skill}: {count} occurrence(s)")
                
                # Analyse des niveaux d'expérience
                if "Niveaux d'expérience" in analyse_options:
                    st.write("**Niveaux d'expérience requis:**")
                    exp_counter = Counter(results["experience"])
                    for exp, count in exp_counter.items():
                        st.write(f"- {exp}: {count} offre(s)")
                
                # Export des résultats (uniquement si pandas est disponible)
                try:
                    csv_data = df_results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Télécharger les résultats (CSV)",
                        data=csv_data,
                        file_name="analyse_concurrentielle_emplois.csv",
                        mime="text/csv",
                        width="stretch"
                    )
                except NameError:
                    st.warning("Impossible de générer le fichier CSV car pandas n'est pas disponible.")
            else:
                st.warning("Aucun résultat à afficher.")
        else:
            st.error("Veuillez entrer au moins une URL de concurrent à analyser.")
    
    # Section d'aide
    with st.expander("❓ Comment utiliser cet outil", expanded=False):
        st.markdown("""
        ### Guide d'utilisation de l'analyse concurrentielle
        
        1. **Listez les sites de vos concurrents** - Entrez les URLs des pages carrières ou offres d'emploi
        2. **Définissez les mots-clés** - Spécifiez les compétences ou postes qui vous intéressent
        3. **Configurez l'analyse** - Choisissez ce que vous voulez analyser précisément
        4. **Lancez l'extraction** - L'outil parcourt les sites et extrait les informations
        5. **Consultez les résultats** - Visualisez les tendances et téléchargez les données
        
        ### Conseils pour de meilleurs résultats:
        - Ciblez des pages listant plusieurs offres d'emploi
        - Utilisez des mots-clés précis liés à vos besoins
        - Augmentez le délai entre les requêtes pour éviter le blocage
        - Testez d'abord avec 2-3 sites pour valider la configuration
        
        ### Limitations:
        - Le scraping web peut être bloqué par certains sites
        - La structure des pages peut changer, nécessitant une mise à jour des sélecteurs
        - Certains sites utilisent JavaScript pour charger le contenu, ce qui peut ne pas être compatible avec cette approche
        """)

# -------------------- Tab 6: InMail --------------------
with tab6:
    st.header("✉️ Générateur d'InMail Personnalisé")

    # --------- FONCTIONS UTILES ---------
    def generate_cta(cta_type, prenom, genre):
        suffix = "e" if genre == "Féminin" else ""
        if cta_type == "Proposer un appel":
            return f"Je serai ravi{suffix} d'échanger avec vous par téléphone cette semaine afin d’en discuter davantage."
        elif cta_type == "Partager le CV":
            return f"Seriez-vous intéressé{suffix} à partager votre CV afin que je puisse examiner cette opportunité avec vous ?"
        elif cta_type == "Découvrir l'opportunité sur notre site":
            return f"Souhaiteriez-vous consulter plus de détails sur cette opportunité via notre site carrière ?"
        elif cta_type == "Accepter un rendez-vous":
            return f"Je serai ravi{suffix} de convenir d’un rendez-vous afin d’échanger sur cette opportunité."
        return ""

    def generate_inmail(donnees_profil, poste, entreprise, ton, max_words, cta_type, genre):
        terme_organisation = "groupe" if entreprise == "TGCC" else "filiale"
        objet = f"Opportunité de {poste} au sein du {terme_organisation} {entreprise}"

        # Accroche IA simulée
        accroche_prompt = f"""
        Tu es un recruteur marocain qui écrit des accroches pour InMail.
        Génère une accroche persuasive adaptée au ton "{ton}".
        Infos candidat: {donnees_profil}.
        Poste à pourvoir: {poste}, Entreprise: {entreprise}.
        L'accroche doit être concise, unique et engageante.
        """
        accroche_result = ask_deepseek([{"role": "user", "content": accroche_prompt}], max_tokens=80)
        accroche = accroche_result["content"].strip()

        # 🔧 sécurisation des données
        prenom = donnees_profil.get("prenom", "Candidat")
        mission = donnees_profil.get("mission", "")
        competences = donnees_profil.get("competences_cles", ["", "", ""])

        cta_text = generate_cta(cta_type, prenom, genre)

        response = f"""Bonjour {prenom},

{accroche}

Votre mission actuelle {mission} ainsi que vos compétences principales ({", ".join(filter(None, competences))}) 
démontrent un potentiel fort pour le poste de {poste} au sein de notre {terme_organisation} {entreprise}.

{cta_text}
"""

        # Ajustement de longueur
        words = response.split()
        if len(words) > max_words:
            response = " ".join(words[:max_words]) + "..."
        elif len(words) < int(max_words * 0.8):
            extend_prompt = f"Développe ce message en {max_words} mots environ sans répétitions :\n{response}"
            extend_result = ask_deepseek([{"role": "user", "content": extend_prompt}], max_tokens=max_words * 2)
            response = extend_result["content"]

        return response.strip(), objet

    # --------- IMPORTER UN MODÈLE ---------
    if st.session_state.library_entries:
        templates = [f"{e['poste']} - {e['date']}" for e in st.session_state.library_entries if e['type'] == "InMail"]
        selected_template = st.selectbox("📂 Importer un modèle sauvegardé :", [""] + templates, key="import_template_inmail")
        if selected_template:
            template_entry = next(e for e in st.session_state.library_entries if f"{e['poste']} - {e['date']}" == selected_template)
            st.session_state["inmail_profil_data"] = {
                "prenom": "Candidat",
                "nom": "",
                "poste_actuel": "",
                "entreprise_actuelle": "",
                "competences_cles": ["", "", ""],
                "experience_annees": "",
                "formation": "",
                "mission": "",
                "localisation": ""
            }
            st.session_state["inmail_message"] = template_entry["requete"]
            st.success("📥 Modèle importé et infos candidat prêtes")

    # --------- PARAMÈTRES GÉNÉRAUX ---------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        url_linkedin = st.text_input("Profil LinkedIn", key="inmail_url", placeholder="linkedin.com/in/nom-prenom")
    with col2:
        entreprise = st.selectbox("Entreprise", ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"], key="inmail_entreprise")
    with col3:
        ton_message = st.selectbox("Ton du message", ["Persuasif", "Professionnel", "Convivial", "Direct"], key="inmail_ton")
    with col4:
        genre_profil = st.selectbox("Genre du profil", ["Masculin", "Féminin"], key="inmail_genre")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        poste_accroche = st.text_input("Poste à pourvoir", key="inmail_poste", placeholder="Ex: Directeur Financier")
    with col6:
        longueur_message = st.slider("Longueur (mots)", 50, 300, 150, key="inmail_longueur")
    with col7:
        analyse_profil = st.selectbox("Méthode analyse", ["Manuel", "Regex", "Compét API"], index=0, key="inmail_analyse")
    with col8:
        cta_option = st.selectbox("Call to action (Conclusion)", ["Proposer un appel", "Partager le CV", "Découvrir l'opportunité sur notre site", "Accepter un rendez-vous"], key="inmail_cta")

    # --------- INFORMATIONS CANDIDAT ---------
    st.subheader("📊 Informations candidat")

    default_profil = {
        "prenom": "Candidat",
        "nom": "",
        "poste_actuel": "",
        "entreprise_actuelle": "",
        "competences_cles": ["", "", ""],
        "experience_annees": "",
        "formation": "",
        "mission": "",
        "localisation": ""
    }
    profil_data = {**default_profil, **st.session_state.get("inmail_profil_data", {})}

    cols = st.columns(5)
    profil_data["prenom"] = cols[0].text_input("Prénom", profil_data.get("prenom", ""), key="inmail_prenom")
    profil_data["nom"] = cols[1].text_input("Nom", profil_data.get("nom", ""), key="inmail_nom")
    profil_data["poste_actuel"] = cols[2].text_input("Poste actuel", profil_data.get("poste_actuel", ""), key="inmail_poste_actuel")
    profil_data["entreprise_actuelle"] = cols[3].text_input("Entreprise actuelle", profil_data.get("entreprise_actuelle", ""), key="inmail_entreprise_actuelle")
    profil_data["experience_annees"] = cols[4].text_input("Années d'expérience", profil_data.get("experience_annees", ""), key="inmail_exp")

    cols2 = st.columns(5)
    profil_data["formation"] = cols2[0].text_input("Domaine de formation", profil_data.get("formation", ""), key="inmail_formation")
    profil_data["competences_cles"][0] = cols2[1].text_input("Compétence 1", profil_data["competences_cles"][0], key="inmail_comp1")
    profil_data["competences_cles"][1] = cols2[2].text_input("Compétence 2", profil_data["competences_cles"][1], key="inmail_comp2")
    profil_data["competences_cles"][2] = cols2[3].text_input("Compétence 3", profil_data["competences_cles"][2], key="inmail_comp3")
    profil_data["localisation"] = cols2[4].text_input("Localisation", profil_data.get("localisation", ""), key="inmail_loc")

    profil_data["mission"] = st.text_area("Mission du poste", profil_data.get("mission", ""), height=80, key="inmail_mission")

    col_ap1, col_ap2 = st.columns(2)
    with col_ap1:
        if st.button("🔍 Analyser profil", key="btn_analyse_inmail"):
            profil_data.update({"poste_actuel": "Manager", "entreprise_actuelle": "ExempleCorp"})
            st.session_state["inmail_profil_data"] = profil_data
            st.success("✅ Profil pré-rempli automatiquement")
    with col_ap2:
        if st.button("💾 Appliquer infos candidat", key="btn_apply_inmail"):
            st.session_state["inmail_profil_data"] = profil_data
            st.success("✅ Infos candidat mises à jour")

    # --------- GÉNÉRATION ---------
    if st.button("✨ Générer", type="primary", width="stretch", key="btn_generate_inmail"):
        donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
        msg, objet_auto = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil)
        st.session_state["inmail_message"] = msg
        st.session_state["inmail_objet"] = objet_auto
        st.session_state["inmail_generated"] = True

    # --------- RÉSULTAT ---------
    if st.session_state.get("inmail_generated"):
        st.subheader("📝 Message InMail généré")
        st.text_input("📧 Objet", st.session_state.get("inmail_objet", ""), key="inmail_objet_display")
        msg = st.session_state["inmail_message"]
        st.text_area("Message", msg, height=250, key="inmail_msg_display")
        st.caption(f"📏 {len(msg.split())} mots | {len(msg)} caractères")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Régénérer avec mêmes paramètres", key="btn_regen_inmail"):
                donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
                msg, objet_auto = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil)
                st.session_state["inmail_message"] = msg
                st.session_state["inmail_objet"] = objet_auto
                st.rerun()
        with col2:
            if st.button("💾 Sauvegarder comme modèle", key="btn_save_inmail"):
                entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "InMail",
                    "poste": poste_accroche,
                    "requete": st.session_state["inmail_message"]
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                st.success(f"✅ Modèle '{poste_accroche} - {entry['date']}' sauvegardé")


# -------------------- Tab 7: Magicien --------------------
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
        "Quels rôles proches à considérer lors du sourcing pour",
        "Quelles tendances de recrutement récentes pour le métier de"
    ]

    q_choice = st.selectbox("📌 Questions prêtes :", 
                            [""] + questions_pretes, key="magicien_qchoice")

    if q_choice:
        default_question = q_choice
    else:
        default_question = ""

    question = st.text_area("Modifiez la question si nécessaire :", 
                          value=default_question, 
                          key="magicien_question", 
                          height=100,
                          placeholder="Posez votre question ici...")

    mode_rapide_magicien = st.checkbox("⚡ Mode rapide (réponse concise)", key="magicien_fast")

    if st.button("✨ Poser la question", type="primary", key="ask_magicien", width="stretch"):
        if question:
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
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
                st.success(f"✅ Réponse générée en {total_time}s")
                
                st.session_state.magicien_history.append({
                    "q": question, 
                    "r": result["content"], 
                    "time": total_time
                })
        else:
            st.warning("⚠️ Veuillez poser une question")

    if st.session_state.get("magicien_history"):
        st.subheader("📝 Historique des réponses")
        for i, item in enumerate(st.session_state.magicien_history[::-1]):
            with st.expander(f"❓ {item['q']} ({item['time']}s)"):
                st.write(item["r"])
                if st.button("🗑️ Supprimer", key=f"del_magicien_{i}"):
                    st.session_state.magicien_history.remove(item)
                    st.rerun()
        
        if st.button("🧹 Supprimer tout", key="clear_magicien_all", width="stretch"):
            st.session_state.magicien_history.clear()
            st.success("✅ Historique vidé")
            st.rerun()
            
# -------------------- Tab 8: Permutateur --------------------
with tab8:
    st.header("📧 Permutateur Email")

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom:", key="perm_prenom", placeholder="Jean")
        nom = st.text_input("Nom:", key="perm_nom", placeholder="Dupont")
    with col2:
        entreprise = st.text_input("Entreprise:", key="perm_entreprise", placeholder="TGCC")
        source = st.radio("Source de détection :", ["Site officiel", "Charika.ma"], key="perm_source", horizontal=True)

    if st.button("🔮 Générer permutations", width="stretch"):
        if prenom and nom and entreprise:
            with st.spinner("⏳ Génération des permutations..."):
                start_time = time.time()
                permutations = []
                detected = get_email_from_charika(entreprise) if source == "Charika.ma" else None
                
                if detected:
                    st.info(f"📧 Format détecté : {detected}")
                    domain = detected.split("@")[1]
                else:
                    domain = f"{entreprise.lower().replace(' ', '')}.ma"
                
                # Génération des permutations
                patterns = [
                    f"{prenom.lower()}.{nom.lower()}@{domain}",
                    f"{prenom[0].lower()}{nom.lower()}@{domain}",
                    f"{nom.lower()}.{prenom.lower()}@{domain}",
                    f"{prenom.lower()}{nom.lower()}@{domain}",
                    f"{prenom.lower()}-{nom.lower()}@{domain}",
                    f"{nom.lower()}{prenom[0].lower()}@{domain}",
                    f"{prenom[0].lower()}.{nom.lower()}@{domain}",
                    f"{nom.lower()}.{prenom[0].lower()}@{domain}"
                ]
                
                total_time = time.time() - start_time
                st.session_state["perm_result"] = list(set(patterns))
                st.success(f"✅ {len(patterns)} permutations générées en {total_time:.1f}s")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs")

    if st.session_state.get("perm_result"):
        st.text_area("Résultats:", value="\n".join(st.session_state["perm_result"]), height=150)
        st.caption("🔍 Tester sur : [Hunter.io](https://hunter.io/) ou [NeverBounce](https://neverbounce.com/)")

# -------------------- Tab 9: Bibliothèque --------------------
with tab9:
    st.header("📚 Bibliothèque des recherches")
    # Actualisation auto depuis Google Sheets
    entries_local = st.session_state.library_entries if st.session_state.library_entries else []
    entries_gsheet = load_sourcing_entries_from_gsheet()
    # Fusion et déduplication (par requête + type + poste)
    all_entries = entries_local.copy()
    for e in entries_gsheet:
        if not any((e.get("requete") == x.get("requete") and e.get("type") == x.get("type") and e.get("poste") == x.get("poste")) for x in all_entries):
            all_entries.append(e)
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("🔎 Rechercher:", placeholder="Rechercher par poste ou requête")
    with col2:
        sort_by = st.selectbox("📌 Trier par:", ["Date récente", "Date ancienne", "Type", "Poste"], key="sort_by")

    entries = all_entries
    if search_term:
        entries = [e for e in entries if search_term.lower() in str(e.get("requete","")) .lower() or 
                 search_term.lower() in str(e.get("poste","")) .lower() or search_term.lower() in str(e.get("type","")) .lower()]

    # Utilise timestamp si présent, sinon date
    def get_date(e):
        return e.get("timestamp") or e.get("date") or ""

    if sort_by == "Type":
        entries = sorted(entries, key=lambda x: x.get("type",""))
    elif sort_by == "Poste":
        entries = sorted(entries, key=lambda x: x.get("poste",""))
    elif sort_by == "Date ancienne":
        entries = sorted(entries, key=get_date)
    else:
        entries = sorted(entries, key=get_date, reverse=True)

    st.info(f"📊 {len(entries)} recherche(s) trouvée(s)")
    for i, entry in enumerate(entries):
        with st.expander(f"{get_date(entry)} - {entry.get('type','')} - {entry.get('poste','')}"):
            st.text_area("Requête:", value=entry.get('requete',''), height=100, key=f"req_{i}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"del_{i}"):
                    if entry in st.session_state.library_entries:
                        st.session_state.library_entries.remove(entry)
                        save_library_entries()
                        st.success("✅ Recherche supprimée")
                        st.rerun()
            with col2:
                if entry.get('type') == 'Boolean':
                    url = f"https://www.linkedin.com/search/results/people/?keywords={quote(entry.get('requete',''))}"
                    st.link_button("🌐 Ouvrir", url)
                elif entry.get('type') == 'X-Ray':
                    url = f"https://www.google.com/search?q={quote(entry.get('requete',''))}"
                    st.link_button("🌐 Ouvrir", url)
    if not entries:
        st.info("📝 Aucune recherche sauvegardée pour le moment")

# -------------------- CSS pour masquer le prompt en bas --------------------
st.markdown("""
    <style>
    .stTextArea textarea[aria-label*='Modifiez la question'] {
        display: none;
    }
    .stTextArea label[aria-label*='Modifiez la question'] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)