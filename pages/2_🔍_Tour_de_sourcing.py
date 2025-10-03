import streamlit as st
from utils import save_sourcing_entry_to_gsheet, load_sourcing_entries_from_gsheet

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

# Fonctions pour gestion des tokens Google Sheets
@st.cache_resource
def get_tokens_gsheet_client():
    """Connexion spécifique à la feuille Tokens"""
    try:
        import gspread
        from utils import _build_service_account_info_from_st_secrets
        
        service_account_info = _build_service_account_info_from_st_secrets()
        gc = gspread.service_account_from_dict(service_account_info)
        
        # Utiliser la même URL que pour Sourcing DB mais feuille "Tokens"
        SOURCING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Yw99SS4vU5v0DuD7S1AwaEispJCo-cwioxSsAYnzRkE/edit"
        spreadsheet = gc.open_by_url(SOURCING_SHEET_URL)
        
        # Essayer d'accéder à la feuille Tokens, la créer si elle n'existe pas
        try:
            worksheet = spreadsheet.worksheet("Tokens")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Tokens", rows="1000", cols="10")
            # Ajouter les en-têtes
            headers = ["timestamp", "type", "function", "user", "tokens", "cumulative_total", "action"]
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.warning(f"Connexion Tokens Google Sheets indisponible: {e}")
        return None

def save_tokens_to_gsheet(tokens, function_name="General", user="Unknown", reset=False):
    """Sauvegarde les tokens utilisés dans Google Sheets avec historique"""
    try:
        worksheet = get_tokens_gsheet_client()
        if worksheet is None:
            return False
        
        if reset:
            # Entrée de reset total
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Token Reset",
                "Reset Total", 
                user,
                0,
                0,
                "RESET TOTAL"
            ]
        else:
            # Récupérer le total actuel
            current_total = st.session_state.get("api_usage", {}).get("used_tokens", 0)
            
            # Entrée d'usage normal
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Token Usage",
                function_name,
                user,
                tokens,
                current_total,
                "USAGE"
            ]
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.warning(f"Erreur sauvegarde tokens: {e}")
        return False

def load_total_tokens_from_gsheet():
    """Charge le total cumulé des tokens depuis Google Sheets"""
    try:
        worksheet = get_tokens_gsheet_client()
        if worksheet is None:
            return 0
        
        # Récupérer toutes les entrées
        records = worksheet.get_all_records()
        
        if records:
            # Trouver la dernière entrée pour récupérer le total cumulé
            for record in reversed(records):
                if record.get("action") == "RESET TOTAL":
                    return 0  # Si le dernier était un reset, commencer à 0
                elif record.get("action") == "USAGE":
                    return int(record.get("cumulative_total", 0))
        
        return 0  # Aucune entrée trouvée, commencer à 0
    except Exception as e:
        st.warning(f"Erreur chargement tokens: {e}")
        return 0

# Configuration pour l'appel à l'IA DeepSeek
SYSTEM_PROMPT = """
Tu es 'TG-Hire Assistant', un expert IA spécialisé dans le recrutement pour le secteur du BTP (Bâtiment et Travaux Publics) au Maroc.
Ton rôle est d'aider un recruteur humain à optimiser ses tâches quotidiennes.
Tes réponses doivent être :
1.  **Contextualisées** : Toujours adaptées au marché de l'emploi marocain et aux spécificités du secteur du BTP.
2.  **Professionnelles et Précises** : Fournis des informations concrètes et structurées.
3.  **Orientées Action** : Propose des listes, des questions, des modèles de texte, etc.
4.  **Adaptables** : Tu dois ajuster la longueur de ta réponse (courte, normale, détaillée) selon la demande.
"""

def get_deepseek_response(prompt, history, length, function_name="General"):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: return {"content": "Erreur: Clé API DeepSeek manquante.", "usage": 0}
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": final_prompt}]
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages, "max_tokens": 2048}
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {}).get("total_tokens", 0)
        
        # Mettre à jour les statistiques de tokens
        if "api_usage" not in st.session_state:
            st.session_state["api_usage"] = {"current_session_tokens": 0, "used_tokens": 0}
        
        st.session_state["api_usage"]["current_session_tokens"] += usage
        st.session_state["api_usage"]["used_tokens"] += usage
        
        # Sauvegarder dans Google Sheets avec détails de la fonction
        user = st.session_state.get("user", "Unknown")
        save_tokens_to_gsheet(usage, function_name, user)
        
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API DeepSeek: {e}", "usage": 0}

# Fonction de debug pour l'analyse LinkedIn
def debug_linkedin_analysis(url, ia_result):
    """Debug détaillé pour l'analyse LinkedIn"""
    debug_info = {
        "url_fournie": url,
        "url_valide": bool(url and ("linkedin.com" in url or "linkedin" in url.lower())),
        "reponse_api": ia_result,
        "contenu_present": bool(ia_result.get("content")),
        "longueur_contenu": len(str(ia_result.get("content", ""))) if ia_result.get("content") else 0
    }
    return debug_info

# Import optionnel pour l'extraction PDF
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

# Fichier de persistance pour la bibliothèque
LIB_FILE = "library_entries.json"

# Fonction pour générer des messages InMail
def generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil, context):
    """
    Génère un message InMail personnalisé basé sur les paramètres fournis.
    """
    # Adaptation du ton
    tone = "formel" if ton_message == "Formel" else "décontracté"
    
    # Adaptation de la longueur
    if longueur_message == "Court":
        max_words = 50
    elif longueur_message == "Moyen":
        max_words = 100
    else:
        max_words = 150
    
    # Construction du message de base
    greeting = f"Bonjour {'Madame' if genre_profil == 'Féminin' else 'Monsieur'},"
    
    # Corps du message adapté au contexte
    if context == "entreprise":
        body = f"""
Je suis impressionné(e) par votre profil et votre expérience. Nous avons une opportunité {poste_accroche} chez {entreprise} qui pourrait vous intéresser.

Vos compétences correspondent parfaitement à ce que nous recherchons. Cette position offre de belles perspectives d'évolution dans un environnement stimulant.
        """.strip()
    else:
        body = f"Votre profil pour le poste de {poste_accroche} chez {entreprise} a retenu notre attention."
    
    # Call-to-action
    if cta_option == "Appel téléphonique":
        cta = "Seriez-vous disponible pour un bref appel téléphonique cette semaine ?"
    elif cta_option == "Rencontre":
        cta = "Seriez-vous intéressé(e) par une rencontre pour discuter de cette opportunité ?"
    else:
        cta = "N'hésitez pas à me contacter si cette opportunité vous intéresse."
    
    # Assembly du message final
    message = f"{greeting}\n\n{body}\n\n{cta}\n\nCordialement"
    
    # Limitation de la longueur si nécessaire
    words = message.split()
    if len(words) > max_words:
        message = " ".join(words[:max_words]) + "..."
    
    return message

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
    # Charger le total cumulé depuis Google Sheets au premier chargement
    if "tokens_loaded" not in st.session_state:
        total_from_sheets = load_total_tokens_from_gsheet()
        st.session_state["tokens_loaded"] = True
        api_usage = {"current_session_tokens": 0, "used_tokens": total_from_sheets}
    else:
        api_usage = st.session_state.get("api_usage", {"current_session_tokens": 0, "used_tokens": 0})
    
    defaults = {
        "api_usage": api_usage,
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
    if poste or synonymes:
        # Combine poste and synonyms with OR
        poste_and_synonyms = _or_group([poste] + _split_terms(synonymes) if poste else _split_terms(synonymes))
        parts.append(poste_and_synonyms)
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
    return ' '.join(parts)

def generate_accroche_inmail(url_linkedin, poste_accroche):
    """Génère un message InMail basique"""
    return f"""Bonjour,

Votre profil sur LinkedIn a retenu mon attention, particulièrement votre expérience dans le domaine.

Je me permets de vous contacter concernant une opportunité de {poste_accroche} qui correspond parfaitement à votre profil. Votre expertise serait un atout précieux pour notre équipe.

Seriez-vous ouvert à un échange pour discuter de cette opportunité ?

Dans l'attente de votre retour,"""

def ask_deepseek(messages, max_tokens=300):
    """Simule l'appel à l'API DeepSeek avec une logique d'enrichissement."""
    time.sleep(1)  # Simulation de délai
    question = messages[0]["content"].lower()
    
    # 1. Extraction des critères de base
    def extract_field(field_name, content):
        match = re.search(f"{field_name}:\\s*(.*?)(?:\\n|$)", content, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    poste = extract_field("poste", messages[0]["content"])
    synonymes = extract_field("synonymes", messages[0]["content"])
    comp_ob = extract_field("compétences obligatoires", messages[0]["content"])
    
    # 2. Logique pour simuler l'enrichissement par l'IA
    
    # Cas 1 : Génération de la requête Boolean (enrichissement des synonymes et des compétences)
    if "génère une requête boolean" in question:
        
        # Approche MINIMALISTE pour éviter 0 résultat sur LinkedIn
        # Seulement enrichir les synonymes, pas trop de compétences obligatoires
        
        if "ingénieur de travaux" in poste.lower() or "ingénieur travaux" in poste.lower():
            # Synonymes conservateurs
            ia_syns = f"{synonymes}, Conducteur de travaux, Chef de chantier" if synonymes else "Conducteur de travaux, Chef de chantier"
            # Compétences très légères ou vides si rien n'est saisi
            ia_comp_ob = comp_ob if comp_ob else ""  # Ne pas ajouter de compétences obligatoires si vide
        elif "ged" in poste.lower() or "gestion électronique" in poste.lower() or "archivage" in poste.lower():
            ia_syns = f"{synonymes}, Gestionnaire documentaire, Archiviste, Document manager" if synonymes else "Gestionnaire documentaire, Archiviste, Document manager"
            ia_comp_ob = comp_ob if comp_ob else ""
        elif "chargé de recrutement" in poste.lower() or "recruteur" in poste.lower():
            ia_syns = f"{synonymes}, Talent acquisition, Sourcing" if synonymes else "Talent acquisition, Sourcing"
            ia_comp_ob = comp_ob if comp_ob else ""
        elif "développeur" in poste.lower() or "developer" in poste.lower():
            ia_syns = f"{synonymes}, Software engineer, Programmeur" if synonymes else "Software engineer, Programmeur"
            ia_comp_ob = comp_ob if comp_ob else ""
        elif "comptable" in poste.lower() or "finance" in poste.lower():
            ia_syns = f"{synonymes}, Expert comptable, Contrôleur gestion" if synonymes else "Expert comptable, Contrôleur gestion"
            ia_comp_ob = comp_ob if comp_ob else ""
        elif "responsable" in poste.lower() or "manager" in poste.lower() or "directeur" in poste.lower():
            # Synonymes pour postes de management/responsabilité
            ia_syns = f"{synonymes}, Manager, Chef de service, Directeur" if synonymes else "Manager, Chef de service, Directeur"
            ia_comp_ob = comp_ob if comp_ob else ""
        else:
            # Pour les postes non reconnus, ajouter seulement des synonymes génériques
            ia_syns = f"{synonymes}, Senior, Expert" if synonymes else "Senior, Expert"
            ia_comp_ob = comp_ob  # Garder ce que l'utilisateur a saisi
        
        return {"content": ia_syns, "comp_ob_ia": ia_comp_ob}
    
    # Cas 2 : Analyse de fiche de poste
    elif "analyse cette fiche de poste" in question:
        # Extraire seulement le contenu de la fiche de poste (après les deux points)
        full_content = messages[0]["content"]
        
        # Trouver le début réel de la fiche de poste (après "clés:" ou similaire)
        if ":" in full_content:
            # Chercher après le dernier ":" qui marque la fin du prompt
            parts = full_content.split('\n')
            fiche_lines = []
            found_content = False
            
            for line in parts:
                if found_content or (not line.startswith('analyse') and not line.startswith('extrait') and ':' not in line):
                    if line.strip():  # Ignorer les lignes vides au début
                        found_content = True
                        fiche_lines.append(line)
                elif line.strip().endswith(':') or '5. Mots à exclure' in line:
                    found_content = True  # Commencer à capturer après cette ligne
            
            fiche_content = '\n'.join(fiche_lines)
        else:
            fiche_content = full_content
        
        fiche_lower = fiche_content.lower()
        
        # Extraire le titre du poste (première ligne souvent)
        lines = fiche_content.strip().split('\n')
        titre_candidat = ""
        
        # Chercher le titre dans les premières lignes
        for line in lines[:5]:  # Regarder les 5 premières lignes
            line = line.strip()
            if line and not line.startswith('opportunité') and not line.startswith('rejoignez') and not line.startswith('tgcc recrute'):
                if len(line) < 100 and not line.lower().startswith('missions') and not line.lower().startswith('analyse'):  # Probablement un titre
                    titre_candidat = line
                    break
        
        suggestions = []
        
        # Cas spécifiques basés sur le contenu
        if "ged" in fiche_lower or "gestion électronique" in fiche_lower or "archivage" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Responsable GED & Archivage'}")
            suggestions.append("Synonymes: Gestionnaire documentaire, Archiviste, Document manager")
            suggestions.append("Compétences obligatoires: GED, Archivage, Dématérialisation")
            suggestions.append("Compétences optionnelles: Gouvernance documentaire, Normes ISO, Métadonnées")
        elif "ingénieur" in fiche_lower and "travaux" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Ingénieur de travaux'}")
            suggestions.append("Synonymes: Conducteur de travaux, Chef de chantier")
            suggestions.append("Compétences obligatoires: AutoCAD, Gestion projet")
            suggestions.append("Compétences optionnelles: Primavera, Management équipe")
        elif "développeur" in fiche_lower or "developer" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Développeur'}")
            suggestions.append("Synonymes: Software engineer, Programmeur")
            suggestions.append("Compétences obligatoires: Programming, Git")
            suggestions.append("Compétences optionnelles: Framework, Base de données")
        elif "comptable" in fiche_lower or "finance" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Comptable'}")
            suggestions.append("Synonymes: Expert comptable, Contrôleur gestion")
            suggestions.append("Compétences obligatoires: SAGE, Fiscalité")
            suggestions.append("Compétences optionnelles: Audit, Consolidation")
        elif "responsable" in fiche_lower or "manager" in fiche_lower or "directeur" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Responsable'}")
            suggestions.append("Synonymes: Manager, Chef de service, Directeur")
            
            # Extraire les compétences mentionnées dans la fiche
            comp_obligatoires = []
            comp_optionnelles = []
            
            if "leadership" in fiche_lower:
                comp_obligatoires.append("Leadership")
            if "management" in fiche_lower or "encadrer" in fiche_lower:
                comp_obligatoires.append("Management")
            if "gestion" in fiche_lower:
                comp_obligatoires.append("Gestion")
            if "pilotage" in fiche_lower or "piloter" in fiche_lower:
                comp_optionnelles.append("Pilotage projet")
            if "reporting" in fiche_lower:
                comp_optionnelles.append("Reporting")
            if "analyse" in fiche_lower:
                comp_optionnelles.append("Esprit d'analyse")
                
            suggestions.append(f"Compétences obligatoires: {', '.join(comp_obligatoires) if comp_obligatoires else 'Management, Leadership'}")
            suggestions.append(f"Compétences optionnelles: {', '.join(comp_optionnelles) if comp_optionnelles else 'Pilotage projet, Communication'}")
        elif "directeur" in fiche_lower and "capital humain" in fiche_lower:
            suggestions.append(f"Titre: {titre_candidat if titre_candidat else 'Directeur du Capital Humain'}")
            suggestions.append("Synonymes: Chief Human Resources Officer, DRH (Directeur des Ressources Humaines), DRH (Directeur Capital Humain)")
            suggestions.append("Compétences obligatoires: Paie & Administration du personnel, Recrutement, Développement des talents")
            suggestions.append("Compétences optionnelles: Pilotage projet, Esprit d'analyse")
        else:
            # Essayer d'extraire quand même des informations génériques
            if titre_candidat:
                suggestions.append(f"Titre: {titre_candidat}")
                suggestions.append("Synonymes: Expert, Spécialiste, Senior")
            else:
                suggestions.append("Analyse: Titre non détecté clairement")
            
            # Rechercher des compétences dans le texte
            competences_trouvees = []
            mots_competences = ["gestion", "management", "leadership", "pilotage", "analyse", "organisation", 
                              "supervision", "coordination", "planification", "suivi", "contrôle"]
            for mot in mots_competences:
                if mot in fiche_lower:
                    competences_trouvees.append(mot.capitalize())
            
            if competences_trouvees:
                suggestions.append(f"Compétences détectées: {', '.join(competences_trouvees[:3])}")
            else:
                suggestions.append("Conseil: Remplissez manuellement les champs ci-dessous")
            
        return {"content": "\n".join(suggestions)}
    
    # Cas 3 : Outils/Logiciels
    elif "outils" in question or "logiciels" in question:
        return {"content": "• AutoCAD\n• Revit\n• Primavera P6\n• MS Project\n• Robot Structural Analysis\n• SketchUp"}
        
    # Cas 4 : Compétences
    elif "compétences" in question:
        return {"content": "• Gestion de projet\n• Lecture de plans techniques\n• Management d'équipe\n• Budget et planning\n• Conformité réglementaire\n• Négociation fournisseurs"}
        
    # Cas par défaut : Génère une réponse intelligente selon le contexte
    if "synonymes" in question:
        # Analyser le métier spécifique pour donner des synonymes pertinents
        if "chargé de recrutement" in question or "chargée de recrutement" in question:
            return {"content": "Recruteur, Talent Acquisition Specialist, Responsable Recrutement, Consultant en Recrutement, RH Recrutement, Chasseur de têtes, Sourcing Specialist"}
        elif "développeur" in question or "programmeur" in question:
            return {"content": "Développeur, Programmeur, Ingénieur logiciel, Software Engineer, Codeur, Dev, Analyste programmeur"}
        elif "commercial" in question or "vente" in question:
            return {"content": "Commercial, Vendeur, Conseiller commercial, Business Developer, Account Manager, Sales Representative, Ingénieur commercial"}
        elif "comptable" in question or "finance" in question:
            return {"content": "Comptable, Contrôleur de gestion, Analyste financier, Gestionnaire comptable, Assistant comptable, Expert-comptable"}
        elif "ingénieur" in question:
            return {"content": "Ingénieur, Engineer, Technicien supérieur, Ingénieur d'études, Ingénieur de conception, Consultant technique"}
        elif "manager" in question or "responsable" in question:
            return {"content": "Manager, Responsable, Chef d'équipe, Superviseur, Directeur, Coordinateur, Team Leader"}
        else:
            # Synonymes génériques si métier non reconnu
            return {"content": "Responsable, Spécialiste, Consultant, Expert, Coordinateur, Assistant, Chargé de mission"}
    elif any(word in question for word in ["junior", "débutant", "junior"]):
        return {"content": "• Junior\n• Débutant\n• Assistant\n• Stagiaire\n• Alternant\n• En formation\n• Premier emploi\n• Entry level"}
    elif "outils" in question or "logiciels" in question:
        if "recrutement" in question:
            return {"content": "• LinkedIn Recruiter\n• Indeed\n• Workday\n• BambooHR\n• Greenhouse\n• Lever\n• SmartRecruiters\n• Taleo"}
        else:
            return {"content": "• MS Office\n• Google Workspace\n• CRM\n• ERP\n• Slack\n• Teams\n• Zoom\n• Project management tools"}
    elif "secteur" in question:
        return {"content": "• BTP\n• Construction\n• Technologie\n• Finance\n• Santé\n• Industrie\n• Services\n• Consulting\n• E-commerce"}
    elif "certification" in question:
        if "recrutement" in question or "rh" in question:
            return {"content": "• CPRP (Certified Professional in Recruitment)\n• PHR (Professional in Human Resources)\n• SHRM-CP\n• CIPD\n• Certification LinkedIn Recruiter"}
        else:
            return {"content": "• PMP\n• ISO 27001\n• ITIL\n• Agile/Scrum\n• Six Sigma\n• PRINCE2"}
    else:
        # Réponse générale pour toute autre question
        return {"content": "Voici quelques suggestions pertinentes pour votre recherche de sourcing :\n• Variez les mots-clés selon le métier ciblé\n• Utilisez des synonymes spécifiques au domaine\n• Pensez aux compétences transversales\n• Considérez le niveau d'expérience requis\n• Adaptez selon le secteur d'activité\n• Incluez les outils métiers spécialisés"}

def extract_text_from_pdf(uploaded_file):
    """Extrait le texte d'un fichier PDF uploadé"""
    try:
        if not PDF_AVAILABLE:
            return "Extraction PDF non disponible - Librairies PyPDF2 ou pdfplumber manquantes"

        # Lire les octets et travailler sur un BytesIO (plus fiable avec les librairies)
        try:
            import io
            uploaded_file.seek(0)
            data = uploaded_file.read()
            bio = io.BytesIO(data)
        except Exception:
            # Si on ne peut pas lire le buffer, tenter d'utiliser le fichier tel quel
            bio = uploaded_file

        # 1) pdfplumber
        try:
            import pdfplumber
            bio.seek(0)
            with pdfplumber.open(bio) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text = "\n".join(text_parts).strip()
                if text:
                    return text
        except Exception as e:
            print(f"Erreur pdfplumber: {e}")

        # 2) PyPDF2
        try:
            import PyPDF2
            bio.seek(0)
            reader = PyPDF2.PdfReader(bio)
            text_parts = []
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                except Exception:
                    page_text = None
                if page_text:
                    text_parts.append(page_text)
            text = "\n".join(text_parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"Erreur PyPDF2: {e}")

        # 3) pypdf / pypdf.PdfReader (au cas où)
        try:
            from pypdf import PdfReader as PypdfReader
            bio.seek(0)
            reader = PypdfReader(bio)
            text_parts = []
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                except Exception:
                    page_text = None
                if page_text:
                    text_parts.append(page_text)
            text = "\n".join(text_parts).strip()
            if text:
                return text
        except Exception as e:
            print(f"Erreur pypdf: {e}")

        # 4) Fallback OCR si installé (pdf2image + pytesseract)
        try:
            # Importer dynamiquement pour éviter que Pylance signale une erreur
            import importlib
            convert_mod = importlib.import_module('pdf2image')
            pytesseract = importlib.import_module('pytesseract')
            convert_from_bytes = getattr(convert_mod, 'convert_from_bytes')
            bio.seek(0)
            images = convert_from_bytes(bio.read(), dpi=200)
            ocr_text_parts = []
            for img in images:
                try:
                    # petite réduction si très grande
                    ocr_text = pytesseract.image_to_string(img, lang='fra+eng')
                    if ocr_text:
                        ocr_text_parts.append(ocr_text)
                except Exception:
                    continue
            ocr_text = "\n".join(ocr_text_parts).strip()
            if ocr_text:
                return ocr_text
        except Exception as e:
            # Si pdf2image/pytesseract non installés ou erreur OCR, ignorer
            print(f"OCR fallback unavailable or failed: {e}")

        # Si on arrive ici, aucune librairie n'a extrait du texte
        return "Aucun texte lisible trouvé. Le PDF est peut-être un scan (images) ou protégé par mot de passe."

    except Exception as e:
        return f"Erreur lors de l'extraction PDF: {str(e)}"

def get_email_from_charika(entreprise):
    """Recherche d'email d'entreprise depuis Charika.ma avec amélioration"""
    try:
        # Rechercher sur Charika.ma
        search_url = f"https://www.charika.ma/search?q={quote(entreprise)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher le lien vers la page de l'entreprise - approche améliorée
        company_links = soup.find_all('a', href=True)
        company_url = None
        
        # Approche améliorée pour trouver les liens d'entreprise
        # 1. Chercher d'abord les liens avec "entreprise" ou "fiche" dans l'URL
        for link in company_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            if ('entreprise' in href or 'fiche' in href or 'company' in href) and any(word in text for word in entreprise.lower().split()):
                company_url = "https://www.charika.ma" + href if href.startswith('/') else href
                break
        
        # 2. Si pas trouvé, chercher plus largement
        if not company_url:
            for link in company_links:
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                # Recherche plus souple dans le texte du lien
                if href and href.startswith('/') and len(href) > 5:  # URLs relatives significatives
                    # Vérifier si le nom de l'entreprise est dans le texte
                    if (entreprise.lower() in text or 
                        any(word.lower() in text for word in entreprise.split() if len(word) > 2)):
                        company_url = "https://www.charika.ma" + href
                        break
        
        # 3. Essayer des URLs construites directement (fallback)
        if not company_url:
            # Essayer différents formats d'URL possibles
            possible_urls = [
                f"https://www.charika.ma/entreprise/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/fiche/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/company/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/entreprise/{entreprise.lower().replace(' ', '').replace('-', '')}",
            ]
            
            for test_url in possible_urls:
                try:
                    test_response = requests.get(test_url, headers=headers, timeout=10)
                    # Vérifier si la page existe et n'est pas une page d'erreur
                    if test_response.status_code == 200 and 'Page manquante' not in test_response.text:
                        company_url = test_url
                        break
                except:
                    continue
        
        if company_url:
            # Accéder à la page de l'entreprise
            company_response = requests.get(company_url, headers=headers, timeout=10)
            company_soup = BeautifulSoup(company_response.content, 'html.parser')
            
            # Méthode améliorée basée sur l'inspection de la structure HTML de Charika.ma
            # Structure identifiée: <span class="dropdown"> avec <span class="mrg-fiche3"> contenant "E-mail" et lien mailto
            
            # Méthode 1: Chercher spécifiquement la structure HTML observée
            # Pattern: <span class="dropdown"> contenant "E-mail" et un lien mailto
            dropdown_spans = company_soup.find_all('span', class_='dropdown')
            for dropdown in dropdown_spans:
                dropdown_html = str(dropdown)
                # Vérifier si ce dropdown contient "E-mail" ET un lien mailto
                if 'E-mail' in dropdown_html and 'mailto:' in dropdown_html:
                    # Extraire directement l'email du HTML avec regex (plus fiable)
                    mailto_pattern = r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
                    matches = re.findall(mailto_pattern, dropdown_html)
                    for email in matches:
                        if 'charika.ma' not in email.lower():
                            return email
                
                # Méthode alternative avec BeautifulSoup
                mrg_spans = dropdown.find_all('span', class_='mrg-fiche3')
                for mrg_span in mrg_spans:
                    if 'E-mail' in mrg_span.get_text():
                        # Chercher les liens mailto dans ce dropdown
                        mailto_links = dropdown.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                        for link in mailto_links:
                            email = link.get('href').replace('mailto:', '').strip()
                            if '@' in email and '.' in email.split('@')[1]:
                                # Vérifier que ce n'est pas l'email de Charika
                                if 'charika.ma' not in email.lower():
                                    return email
            
            # Méthode 2: Chercher tous les liens mailto dans la page (en excluant Charika)
            mailto_links = company_soup.find_all('a', href=lambda x: x and x.startswith('mailto:'))
            for link in mailto_links:
                email = link.get('href').replace('mailto:', '').strip()
                if '@' in email and '.' in email.split('@')[1]:
                    # Filtrer les emails génériques et celui de Charika
                    excluded = ['noreply', 'no-reply', 'donotreply', 'example', 'test', 'charika.ma', 'contact@charika']
                    if not any(generic in email.lower() for generic in excluded):
                        return email
            
            # Méthode 3: Chercher dans les éléments contenant "E-mail" avec pattern spécifique
            # Chercher <span class="mrg-fiche3"> contenant "E-mail"
            email_elements = company_soup.find_all('span', class_='mrg-fiche3')
            for element in email_elements:
                if 'E-mail' in element.get_text():
                    # Chercher dans le parent (dropdown) ou les éléments suivants
                    parent = element.parent
                    if parent:
                        # Chercher les liens mailto dans le parent
                        mailto_links = parent.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                        for link in mailto_links:
                            email = link.get('href').replace('mailto:', '').strip()
                            if '@' in email and '.' in email.split('@')[1] and 'charika.ma' not in email.lower():
                                return email
                    
                    # Chercher aussi dans les éléments suivants (siblings)
                    for sibling in element.next_siblings:
                        if hasattr(sibling, 'find_all'):
                            mailto_links = sibling.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                            for link in mailto_links:
                                email = link.get('href').replace('mailto:', '').strip()
                                if '@' in email and '.' in email.split('@')[1] and 'charika.ma' not in email.lower():
                                    return email
            
            # Méthode 4: Fallback - regex dans tout le texte (en excluant Charika)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            all_text = company_soup.get_text()
            emails = re.findall(email_pattern, all_text)
            if emails:
                # Filtrer les emails génériques et celui de Charika
                excluded = ['noreply', 'no-reply', 'donotreply', 'example', 'test', 'charika.ma']
                for email in emails:
                    if not any(generic in email.lower() for generic in excluded):
                        return email
        
        # Retourner None si pas trouvé pour permettre la gestion d'erreur
        return None
        
    except Exception as e:
        print(f"Erreur lors de la recherche sur Charika: {e}")
        return None

def get_charika_search_url(entreprise):
    """Génère l'URL de recherche Google pour trouver l'entreprise sur Charika"""
    search_query = f"{entreprise} charika.ma"
    return f"https://www.google.com/search?q={quote(search_query)}"

def search_email_on_website(entreprise):
    """Recherche d'email sur le site officiel de l'entreprise"""
    try:
        # Essayer de trouver le site web de l'entreprise
        search_query = f"{entreprise} site:ma OR site:com contact"
        search_url = f"https://www.google.com/search?q={quote(search_query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire les URLs des résultats de recherche
        result_links = soup.find_all('a', href=True)
        potential_websites = []
        
        for link in result_links:
            href = link.get('href', '')
            if href.startswith('/url?q='):
                actual_url = href.split('/url?q=')[1].split('&')[0]
                if any(domain in actual_url for domain in ['.ma', '.com']) and 'google' not in actual_url:
                    potential_websites.append(actual_url)
        
        # Visiter les sites potentiels pour chercher des emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for website in potential_websites[:3]:  # Limiter à 3 sites
            try:
                site_response = requests.get(website, headers=headers, timeout=8)
                site_content = site_response.text
                
                # Chercher spécifiquement dans les pages contact
                if 'contact' in site_content.lower():
                    emails = re.findall(email_pattern, site_content)
                    # Filtrer les emails génériques
                    for email in emails:
                        if not any(generic in email.lower() for generic in ['noreply', 'no-reply', 'donotreply']):
                            return email
                            
            except Exception:
                continue
        
        # Format par défaut si rien trouvé
        domain = f"{entreprise.lower().replace(' ', '').replace('-', '')}.ma"
        return f"contact@{domain}"
        
    except Exception as e:
        print(f"Erreur lors de la recherche d'email: {e}")
        # Format par défaut
        domain = f"{entreprise.lower().replace(' ', '').replace('-', '')}.ma"
        return f"contact@{domain}"

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
    # Section des statistiques tokens centralisée
    st.subheader("📊 Statistiques")
    
    session_tokens = st.session_state.get("api_usage", {}).get("current_session_tokens", 0)
    total_tokens = st.session_state.get("api_usage", {}).get("used_tokens", 0)
    
    # Affichage centré des métriques
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔑 Session", session_tokens)
    with col2:
        st.metric("📊 Total", total_tokens)
    
    st.markdown("---")
    st.info("💡 Assistant IA pour le sourcing et recrutement")

# -------------------- Onglets --------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🔍 Boolean", "🎯 X-Ray", "🔎 CSE LinkedIn", "🐶 Dogpile", 
    "🕷️ Web Scraper", "✉️ InMail", "🤖 Magicien", "📧 Permutateur", "📚 Bibliothèque", "📄 Nomination"
])

# -------------------- Tab 1: Boolean Search --------------------
with tab1:
    st.header("🔍 Recherche Boolean")
    
    # Option fiche de poste pour l'IA
    with st.expander("📄 Fiche de poste (optionnel - pour enrichissement IA)", expanded=False):
        st.markdown("**Choisissez votre méthode d'import :**")
        
        # Onglets pour les deux méthodes
        tab_text, tab_pdf = st.tabs(["📝 Coller le texte", "📄 Uploader PDF"])
        
        fiche_content = ""
        
        with tab_text:
            fiche_poste = st.text_area(
                "Collez ici la fiche de poste complète:",
                height=180,
                key="boolean_fiche_poste",
                placeholder="Mission: ...\nProfil recherché: ...\nCompétences requises: ...\nExpérience: ...\nFormation: ...\nAvantages: ..."
            )
            if fiche_poste:
                fiche_content = fiche_poste
        
        with tab_pdf:
            uploaded_file = st.file_uploader(
                "Choisissez votre fichier PDF:",
                type=['pdf'],
                key="boolean_pdf_uploader",
                help="Formats acceptés: PDF (max 10MB)"
            )
            
            if uploaded_file is not None:
                try:
                    # Vérification de la taille du fichier (max 10MB)
                    if uploaded_file.size > 10 * 1024 * 1024:
                        st.error("❌ Fichier trop volumineux (max 10MB)")
                    else:
                        st.success(f"✅ Fichier '{uploaded_file.name}' uploadé avec succès!")
                        
                        with st.spinner("📄 Extraction du texte en cours..."):
                            # Extraction réelle du PDF
                            extracted_text = extract_text_from_pdf(uploaded_file)
                            
                            if extracted_text and "Erreur" not in extracted_text and not extracted_text.strip().startswith("Aucun texte lisible trouvé"):
                                fiche_content = extracted_text
                                st.success("✅ Texte extrait avec succès!")
                                
                                # Aperçu du contenu avec possibilité d'édition
                                fiche_content = st.text_area(
                                    "Aperçu et édition du contenu extrait:",
                                    value=extracted_text[:3000] + ("..." if len(extracted_text) > 3000 else ""),
                                    height=200,
                                    help="Vous pouvez modifier le texte extrait si nécessaire"
                                )
                            else:
                                # Afficher un message plus clair selon la raison
                                if extracted_text and extracted_text.strip().startswith("Aucun texte lisible trouvé"):
                                    st.error("❌ Aucun texte lisible trouvé dans le PDF. Il s'agit probablement d'un PDF scanné (images) ou protégé.\n💡 Collez manuellement le contenu dans l'onglet 'Coller le texte' ou utilisez un OCR externe.")
                                else:
                                    st.error(f"❌ {extracted_text}")
                                # Fallback: permettre à l'utilisateur de coller le texte manuellement
                                st.warning("💡 Collez manuellement le contenu dans l'onglet 'Coller le texte'")
                                
                except Exception as e:
                    st.error(f"❌ Erreur lors du traitement du PDF: {str(e)}")
                    st.warning("💡 Collez manuellement le contenu dans l'onglet 'Coller le texte'")
        
        # Bouton d'analyse commun
        if fiche_content and st.button("🤖 Analyser la fiche et pré-remplir", key="analyze_fiche", use_container_width=True):
            with st.spinner("🔍 Analyse de la fiche en cours..."):
                # Simulation d'analyse de fiche de poste
                analyze_prompt = f"Analyse cette fiche de poste et extrait les éléments clés:\n{fiche_content}\n\nExtrait:\n1. Titre du poste\n2. 2-3 synonymes du poste\n3. 2-3 compétences obligatoires\n4. 2-3 compétences optionnelles\n5. Mots à exclure si mentionnés"
                result = ask_deepseek([{"role": "user", "content": analyze_prompt}], max_tokens=200)
                
                if result["content"].strip():
                    st.success("✅ Analyse terminée ! Utilisez les suggestions ci-dessous pour remplir les champs.")
                    
                    # Affichage des suggestions de manière plus structurée
                    with st.container():
                        st.markdown("### 💡 Suggestions de l'IA:")
                        suggestions = result["content"].split('\n')
                        for suggestion in suggestions:
                            if suggestion.strip():
                                st.markdown(f"• {suggestion.strip()}")
                    
                    st.info("� Copiez ces suggestions dans les champs correspondants ci-dessous")
                else:
                    st.warning("⚠️ Impossible d'analyser la fiche. Remplissez manuellement les champs ci-dessous.")
    
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

    # Mode avancé LinkedIn pour Boolean
    with st.expander("⚙️ Mode avancé LinkedIn", expanded=False):
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            specialite = st.text_input("Spécialité", key="boolean_specialite", placeholder="Ex: Génie Civil, Informatique")
            entreprises_precedentes = st.text_input("Entreprises précédentes", key="boolean_entreprises_prec", placeholder="Ex: OCP, TGCC")
        with col_adv2:
            ecoles_cibles = st.text_input("Écoles/Universités", key="boolean_ecoles", placeholder="Ex: EMI, ENSA")
            certifications_bool = st.text_input("Certifications", key="boolean_certifications", placeholder="Ex: PMP, ISO 27001")

    gen_mode = st.selectbox("Générer la requête Boolean par :", ["Algorithme", "Intelligence artificielle"], key="boolean_gen_mode")
    if gen_mode == "Intelligence artificielle":
        st.caption("💡 L'IA enrichit les synonymes de façon conservatrice pour maximiser les résultats LinkedIn")
    
    gen_btn = st.button("🔍 Générer", type="primary", key="boolean_generate_main", use_container_width=True)
    if gen_btn:
        if gen_mode == "Algorithme":
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
                base_query = generate_boolean_query(
                    poste, synonymes, competences_obligatoires,
                    competences_optionnelles, exclusions, localisation, secteur
                )
                if employeur:
                    base_query += f' AND ("{employeur}")'
                
                # Add advanced LinkedIn filters
                advanced_parts = []
                if specialite:
                    advanced_parts.append(f'"{specialite}"')
                if entreprises_precedentes:
                    ent_terms = _split_terms(entreprises_precedentes)
                    if ent_terms:
                        advanced_parts.append(_or_group(ent_terms))
                if ecoles_cibles:
                    ecole_terms = _split_terms(ecoles_cibles)
                    if ecole_terms:
                        advanced_parts.append(_or_group(ecole_terms))
                if certifications_bool:
                    cert_terms = _split_terms(certifications_bool)
                    if cert_terms:
                        advanced_parts.append(_or_group(cert_terms))
                
                if advanced_parts:
                    st.session_state["boolean_query"] = base_query + " AND " + " AND ".join(advanced_parts)
                else:
                    st.session_state["boolean_query"] = base_query
                
                st.session_state["boolean_snapshot"] = {
                    "poste": poste,
                    "synonymes": synonymes,
                    "comp_ob": competences_obligatoires,
                    "comp_opt": competences_optionnelles,
                    "exclusions": exclusions,
                    "localisation": localisation,
                    "secteur": secteur,
                    "employeur": employeur or "",
                    "mode": gen_mode,
                    "specialite": specialite,
                    "entreprises_precedentes": entreprises_precedentes,
                    "ecoles_cibles": ecoles_cibles,
                    "certifications_bool": certifications_bool
                }
                total_time = time.time() - start_time
                st.success(f"✅ Requête générée en {total_time:.1f}s")
                st.rerun()  # Force la mise à jour de l'affichage
        else:
            with st.spinner("🤖 Génération Intelligence artificielle en cours..."):
                start_time = time.time()
                
                # Construct the AI prompt dynamically to avoid redundant fields
                prompt_parts = [
                    f"Poste: {poste}",
                    f"Synonymes: {synonymes}" if synonymes else "",
                    f"Compétences obligatoires: {competences_obligatoires}" if competences_obligatoires else "",
                    f"Compétences optionnelles: {competences_optionnelles}" if competences_optionnelles else "",
                    f"Exclusions: {exclusions}" if exclusions else "",
                    f"Localisation: {localisation}" if localisation else "",
                    f"Secteur: {secteur}" if secteur else "",
                    f"Employeur: {employeur}" if employeur else ""
                ]
                prompt = "Génère une requête Boolean pour le sourcing avec les critères suivants:\n" + "\n".join(filter(None, prompt_parts))

                ia_result = ask_deepseek([{"role": "user", "content": prompt}], max_tokens=200)

                # Extract enriched synonyms and mandatory skills
                synonymes_ia = ia_result.get("content", synonymes) if ia_result.get("content", "").strip() else synonymes
                comp_ob_ia = ia_result.get("comp_ob_ia", competences_obligatoires)

                # Generate the Boolean query with advanced fields
                base_query = generate_boolean_query(
                    poste, synonymes_ia, comp_ob_ia,
                    competences_optionnelles, exclusions, localisation, secteur, employeur
                )
                
                # Add advanced LinkedIn filters
                advanced_parts = []
                if specialite:
                    advanced_parts.append(f'"{specialite}"')
                if entreprises_precedentes:
                    ent_terms = _split_terms(entreprises_precedentes)
                    if ent_terms:
                        advanced_parts.append(_or_group(ent_terms))
                if ecoles_cibles:
                    ecole_terms = _split_terms(ecoles_cibles)
                    if ecole_terms:
                        advanced_parts.append(_or_group(ecole_terms))
                if certifications_bool:
                    cert_terms = _split_terms(certifications_bool)
                    if cert_terms:
                        advanced_parts.append(_or_group(cert_terms))
                
                if advanced_parts:
                    st.session_state["boolean_query"] = base_query + " AND " + " AND ".join(advanced_parts)
                else:
                    st.session_state["boolean_query"] = base_query

                # Ensure the query ends with NOT if exclusions are specified
                if exclusions:
                    st.session_state["boolean_query"] = st.session_state["boolean_query"].rstrip(" AND") + " NOT"

                # Save the snapshot with the actual values used
                st.session_state["boolean_snapshot"] = {
                    "poste": poste,
                    "synonymes": synonymes_ia,
                    "comp_ob": comp_ob_ia,
                    "comp_opt": competences_optionnelles,
                    "exclusions": exclusions,
                    "localisation": localisation,
                    "secteur": secteur,
                    "employeur": employeur or "",
                    "mode": gen_mode
                }
                total_time = time.time() - start_time
                st.success(f"✅ Requête Boolean générée par Intelligence artificielle en {total_time:.1f}s")
                if synonymes_ia != synonymes or comp_ob_ia != competences_obligatoires:
                    st.info("🤖 L'IA a enrichi vos critères pour optimiser les résultats LinkedIn")
                st.rerun()  # Force la mise à jour de l'affichage

    # Affichage unifié de la requête Boolean
    snap = st.session_state.get("boolean_snapshot", {})
    query_value = st.session_state.get("boolean_query", "")
    
    # Vérifier si les paramètres ont changé pour l'indication visuelle
    params_changed = False
    if snap and query_value:
        params_changed = any([
            snap.get("poste") != poste,
            snap.get("comp_ob") != competences_obligatoires,
            snap.get("comp_opt") != competences_optionnelles,
            snap.get("exclusions") != exclusions,
            snap.get("localisation") != localisation,
            snap.get("secteur") != secteur,
            snap.get("employeur") != (employeur or ""),
            snap.get("specialite") != specialite,
            snap.get("entreprises_precedentes") != entreprises_precedentes,
            snap.get("ecoles_cibles") != ecoles_cibles,
            snap.get("certifications_bool") != certifications_bool
        ])
    
    # Label avec indication si obsolète
    label = "Requête Boolean:"
    if params_changed:
        label += " ⚠️ (Requête obsolète - critères modifiés - Régénérez pour mettre à jour)"
    
    # Widget unifié - SANS KEY pour permettre la mise à jour automatique
    placeholder_text = "Remplissez les critères ci-dessus puis cliquez sur 'Générer la requête Boolean'" if not query_value else ""
    st.text_area(label, value=query_value, height=120, placeholder=placeholder_text)
    
    # Boutons et actions (seulement si requête existe)
    if st.session_state.get("boolean_query"):
        # Zone commentaire
        boolean_commentaire = st.text_input("Commentaire (optionnel)", value=st.session_state.get("boolean_commentaire", ""), key="boolean_commentaire")
        # Boutons organisés : Copier, Sauvegarder, LinkedIn
        cols_actions = st.columns([0.2,0.4,0.4])
        with cols_actions[0]:
            safe_boolean = st.session_state.get('boolean_query', '').replace('"', '&quot;')
            st.markdown(f'<button data-copy="{safe_boolean}">📋 Copier</button>', unsafe_allow_html=True)
        with cols_actions[1]:
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
        with cols_actions[2]:
            url_linkedin = f"https://www.linkedin.com/search/results/people/?keywords={quote(st.session_state['boolean_query'])}"
            st.link_button("🌐 Ouvrir sur LinkedIn", url_linkedin, use_container_width=True)

    # Variantes (seulement si requête existe)
    if st.session_state.get("boolean_query"):
        # Générer les variantes avec les valeurs ACTUELLES des champs
        variants = generate_boolean_variants(st.session_state["boolean_query"], synonymes, competences_optionnelles)
        
        st.caption("🔀 Variantes proposées")
        if variants:
            for idx, (title, vq) in enumerate(variants):
                # Supprimer la key pour permettre la mise à jour automatique
                st.text_area(f"{title}", value=vq, height=80)
                st.text_input(f"Commentaire variante {idx+1}", value=st.session_state.get(f"boolean_commentaire_var_{idx}", ""), key=f"boolean_commentaire_var_{idx}")
                cols_var = st.columns([0.2,0.4,0.4])
                with cols_var[0]:
                    safe_vq = vq.replace('"', '&quot;')
                    st.markdown(f'<button data-copy="{safe_vq}">📋 Copier</button>', unsafe_allow_html=True)
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
        else:
            st.info("Aucune variante générée pour la requête actuelle.")



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

    if st.button("🔍 Construire X-Ray", type="primary", key="xray_build", use_container_width=True):
        with st.spinner("⏳ Génération en cours..."):
            start_time = time.time()
            # Logic for X-Ray query generation
            xray_query = generate_xray_query(site_cible, poste_xray, mots_cles, localisation_xray)
            
            # Add exclusions if any
            if exclusions_xray:
                exclusion_terms = _split_terms(exclusions_xray)
                if exclusion_terms:
                    xray_query += " -" + " -".join(exclusion_terms)
            
            st.session_state["xray_query"] = xray_query
            st.session_state["xray_snapshot"] = {
                "site": site_cible,
                "poste": poste_xray,
                "mots_cles": mots_cles,
                "localisation": localisation_xray,
                "exclusions": exclusions_xray
            }
            total_time = time.time() - start_time
            st.success(f"✅ Requête X-Ray générée en {total_time:.1f}s")

    # Affichage unifié de la requête X-Ray
    snapx = st.session_state.get("xray_snapshot", {})
    query_value_xray = st.session_state.get("xray_query", "")
    
    # Vérifier si les paramètres ont changé pour l'indication visuelle
    params_changed_xray = False
    if snapx and query_value_xray:
        params_changed_xray = any([
            snapx.get("site") != site_cible,
            snapx.get("poste") != poste_xray,
            snapx.get("mots_cles") != mots_cles,
            snapx.get("localisation") != localisation_xray,
            snapx.get("exclusions") != exclusions_xray
        ])
    
    # Label avec indication si obsolète
    label_xray = "Requête X-Ray:"
    if params_changed_xray:
        label_xray += " ⚠️ (Requête obsolète - paramètres modifiés - Reconstruire pour mettre à jour)"
    
    # Widget unifié - SANS KEY pour permettre la mise à jour automatique
    placeholder_text_xray = "Remplissez les critères ci-dessus puis cliquez sur 'Construire X-Ray'" if not query_value_xray else ""
    st.text_area(label_xray, value=query_value_xray, height=120, placeholder=placeholder_text_xray)
    
    # Commentaires et actions
    if st.session_state.get("xray_query"):
        # Zone commentaire
        xray_commentaire = st.text_input("Commentaire (optionnel)", value=st.session_state.get("xray_commentaire", ""), key="xray_commentaire")
        # Boutons organisés : Copier, Sauvegarder, LinkedIn
        cols_actions = st.columns([0.2, 0.4, 0.4])
        with cols_actions[0]:
            safe_xray = st.session_state.get('xray_query', '').replace('"', '&quot;')
            st.markdown(f'<button data-copy="{safe_xray}">📋 Copier</button>', unsafe_allow_html=True)
        with cols_actions[1]:
            if st.button("💾 Sauvegarder", key="xray_save", use_container_width=True):
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "X-Ray",
                    "poste": poste_xray,
                    "requete": st.session_state["xray_query"],
                    "utilisateur": st.session_state.get("user", ""),
                    "source": "X-Ray",
                    "commentaire": st.session_state.get("xray_commentaire", "")
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                save_sourcing_entry_to_gsheet(entry)
                st.success("✅ Sauvegardé")
        with cols_actions[2]:
            url_xray = f"https://www.google.com/search?q={quote(st.session_state['xray_query'])}"
            st.link_button("🌐 Ouvrir sur Google", url_xray, use_container_width=True)

    # Variantes
    if st.session_state.get("xray_query"):
        x_vars = generate_xray_variants(st.session_state["xray_query"], poste_xray, mots_cles, localisation_xray)
        if x_vars:
            st.caption("🔀 Variantes proposées")
            for i, (title, qv) in enumerate(x_vars):
                st.text_area(title, value=qv, height=80, key=f"xray_var_{i}")
                st.text_input(f"Commentaire variante {i+1}", value=st.session_state.get(f"xray_commentaire_var_{i}", ""), key=f"xray_commentaire_var_{i}")
                cols_var = st.columns([0.33, 0.33, 0.34])
                with cols_var[0]:
                    safe_qv = qv.replace('"', '&quot;')
                    st.markdown(f'<button data-copy="{safe_qv}">📋 Copier</button>', unsafe_allow_html=True)
                with cols_var[1]:
                    if st.button("💾 Sauvegarder", key=f"xray_save_var_{i}", use_container_width=True):
                        entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "type": "X-Ray Variante",
                            "poste": poste_xray,
                            "requete": qv,
                            "utilisateur": st.session_state.get("user", ""),
                            "source": "X-Ray",
                            "commentaire": st.session_state.get(f"xray_commentaire_var_{i}", "")
                        }
                        st.session_state.library_entries.append(entry)
                        save_library_entries()
                        save_sourcing_entry_to_gsheet(entry)
                        st.success("✅ Sauvegardé")
                with cols_var[2]:
                    url_var = f"https://www.google.com/search?q={quote(qv)}"
                    st.link_button("🌐 Ouvrir", url_var, use_container_width=True)
        else:
            st.info("Aucune variante générée pour la requête actuelle.")

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
        
        # Boutons alignés : Copier, Sauvegarder, Ouvrir
        cols_actions = st.columns([0.33, 0.33, 0.34])
        with cols_actions[0]:
            safe_cse = st.session_state.get('cse_query', '').replace('"', '&quot;')
            st.markdown(f'<button data-copy="{safe_cse}">📋 Copier</button>', unsafe_allow_html=True)
        with cols_actions[1]:
            if st.button("💾 Sauvegarder", key="cse_save", use_container_width=True):
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "CSE",
                    "poste": poste_cse,
                    "requete": st.session_state["cse_query"],
                    "utilisateur": st.session_state.get("user", ""),
                    "source": "CSE",
                    "commentaire": ""
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                save_sourcing_entry_to_gsheet(entry)
                st.success("✅ Sauvegardé")
        with cols_actions[2]:
            cse_url = f"https://cse.google.fr/cse?cx=004681564711251150295:d-_vw4klvjg&q={quote(st.session_state['cse_query'])}"
            st.link_button("🌐 Ouvrir sur CSE", cse_url, use_container_width=True)

# -------------------- Tab 4: Dogpile --------------------
with tab4:
    st.header("🐶 Dogpile Search")
    query = st.text_input("Requête Dogpile:", key="dogpile_query_input", placeholder="Ex: Python developer Casablanca")
    if st.button("🔍 Rechercher", key="dogpile_search_btn", type="primary", use_container_width=True):
        if query:
            st.session_state["dogpile_query"] = query
            st.session_state["dogpile_snapshot"] = query
            st.success("✅ Requête enregistrée")
            st.rerun()

    # Affichage uniquement si une requête a été générée
    if st.session_state.get("dogpile_query"):
        # Affichage unifié avec détection de changement
        snap_dogpile = st.session_state.get("dogpile_snapshot", "")
        query_value_dogpile = st.session_state.get("dogpile_query", "")
        
        # Vérifier si les paramètres ont changé
        params_changed_dogpile = False
        if snap_dogpile and query_value_dogpile:
            params_changed_dogpile = snap_dogpile != query
        
        # Label avec indication si obsolète
        label_dogpile = "Requête Dogpile:"
        if params_changed_dogpile:
            label_dogpile += " ⚠️ (Requête obsolète - paramètres modifiés - Rechercher pour mettre à jour)"
        
        # Widget unifié
        st.text_area(label_dogpile, value=query_value_dogpile, height=80)
    
    # Boutons et commentaires (seulement si requête existe)
    if st.session_state.get("dogpile_query"):
        # Zone commentaire
        dogpile_commentaire = st.text_input("Commentaire (optionnel)", value=st.session_state.get("dogpile_commentaire", ""), key="dogpile_commentaire")
        
        # Boutons organisés : Copier, Sauvegarder, Ouvrir
        cols_actions = st.columns([0.33, 0.33, 0.34])
        with cols_actions[0]:
            safe_dogpile = st.session_state.get('dogpile_query', '').replace('"', '&quot;')
            st.markdown(f'<button data-copy="{safe_dogpile}">📋 Copier</button>', unsafe_allow_html=True)
        with cols_actions[1]:
            if st.button("💾 Sauvegarder", key="dogpile_save_btn", use_container_width=True):
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "Dogpile",
                    "poste": "Recherche Dogpile",
                    "requete": st.session_state["dogpile_query"],
                    "utilisateur": st.session_state.get("user", ""),
                    "source": "Dogpile",
                    "commentaire": st.session_state.get("dogpile_commentaire", "")
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                save_sourcing_entry_to_gsheet(entry)
                st.success("✅ Sauvegardé")
        with cols_actions[2]:
            dogpile_url = f"http://www.dogpile.com/serp?q={quote(st.session_state['dogpile_query'])}"
            st.link_button("🌐 Ouvrir sur Dogpile", dogpile_url, use_container_width=True)

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
        longueur_message = st.slider("Longueur (mots)", 10, 200, 50, key="inmail_longueur")
    with col7:
        analyse_profil = st.selectbox("Méthode d'analyse du profil LinkedIn", ["Manuel", "Intelligence artificielle"], index=0, key="inmail_analyse")
        if analyse_profil == "Intelligence artificielle":
            # Vérifier si l'API est disponible
            api_key = st.secrets.get("DEEPSEEK_API_KEY")
            if not api_key:
                st.warning("⚠️ API non configurée")
    with col8:
        cta_option = st.selectbox("Call to action (Conclusion)", ["Proposer un appel", "Partager le CV", "Découvrir l'opportunité sur notre site", "Accepter un rendez-vous"], key="inmail_cta")

    # --------- INFORMATIONS CANDIDAT ---------
    with st.expander("📊 Informations candidat", expanded=False):
        default_profil = {
            "prenom": "",
            "nom": "",
            "poste_actuel": "",
            "entreprise_actuelle": "",
            "competences_cles": ["", "", ""],
            "experience_annees": "",
            "formation": "",
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

    # Garder les données du profil à jour
    if not st.session_state.get("inmail_profil_data"):
        st.session_state["inmail_profil_data"] = profil_data
    else:
        # Mettre à jour avec les nouvelles valeurs
        st.session_state["inmail_profil_data"].update(profil_data)

    # --------- GÉNÉRATION ---------
    if st.button("✨ Générer", type="primary", use_container_width=True, key="btn_generate_inmail"):
        donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
        
        # Si Intelligence artificielle est sélectionnée, avertir de la limitation LinkedIn
        if analyse_profil == "Intelligence artificielle" and url_linkedin.strip():
            st.warning("⚠️ **Limitation** : L'IA ne peut pas accéder directement aux profils LinkedIn pour des raisons de sécurité et de confidentialité.")
            st.info("💡 **Recommandation** : Veuillez remplir manuellement les informations du candidat ci-dessus pour une génération d'InMail précise et personnalisée.")
            
            # Désactiver l'analyse automatique LinkedIn et utiliser les données manuelles
            # with st.spinner("🤖 Analyse IA du profil LinkedIn..."):
            #     analyse_prompt = f"""
            #     IMPORTANT: Tu ne peux pas accéder aux profils LinkedIn réels. 
            #     Au lieu d'inventer des informations, réponds avec ce JSON d'erreur :
            #     {{
            #         "erreur": "Impossible d'accéder au profil LinkedIn",
            #         "message": "Veuillez remplir les informations manuellement"
            #     }}
            #     """

        
        # Utiliser l'IA pour générer le message
        ia_prompt = f"""
        Génère UNIQUEMENT le contenu du message InMail personnalisé (sans objet, sans titre) avec les informations suivantes:
        - Candidat: {donnees_profil.get('prenom', '')} {donnees_profil.get('nom', '')}
        - Poste actuel: {donnees_profil.get('poste_actuel', '')}
        - Entreprise actuelle: {donnees_profil.get('entreprise_actuelle', '')}
        - Compétences: {', '.join(filter(None, donnees_profil.get('competences_cles', [])))}
        - Formation: {donnees_profil.get('formation', '')}
        - Expérience: {donnees_profil.get('experience_annees', '')} ans
        - Localisation: {donnees_profil.get('localisation', '')}
        
        Poste à pourvoir: {poste_accroche}
        Entreprise: {entreprise}
        Ton: {ton_message}
        Genre: {genre_profil}
        Call-to-action: {cta_option}
        
        Le message doit faire environ {longueur_message} mots, être {ton_message.lower()}, et commencer directement par la salutation (ex: Bonjour {donnees_profil.get('prenom', 'Candidat')},).
        Ne pas inclure d'objet, de titre ou de formatage en gras pour l'objet.
        """
        
        with st.spinner("🤖 Génération IA en cours..."):
            ia_result = get_deepseek_response(ia_prompt, [], "normale", "InMail Generation")
            if ia_result.get("content") and "Erreur: Clé API DeepSeek manquante" not in ia_result["content"]:
                msg = ia_result["content"]
            elif "Erreur: Clé API DeepSeek manquante" in str(ia_result.get("content", "")):
                st.error("🔑 **Configuration manquante** : La clé API DeepSeek n'est pas configurée.")
                st.info("💡 **Solution** : Contactez l'administrateur pour configurer la clé API DeepSeek dans les secrets Streamlit.")
                st.warning("⚠️ **Mode de secours** : Génération d'un message de base sans IA.")
                # Fallback avec un message générique
                msg = f"""Bonjour {donnees_profil.get('prenom', 'Candidat')},

Votre profil a retenu notre attention chez {entreprise}. Nous recherchons actuellement un {poste_accroche} et pensons que votre expérience pourrait correspondre à nos besoins.

Seriez-vous disponible pour échanger sur cette opportunité ?

Cordialement."""
            else:
                # Fallback si l'IA ne répond pas
                msg = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil, "entreprise")
        
        st.session_state["inmail_message"] = msg
        st.session_state["inmail_objet"] = "Nouvelle opportunité: " + poste_accroche
        st.session_state["inmail_generated"] = True
        st.session_state["inmail_snapshot"] = {
            "poste_accroche": poste_accroche,
            "entreprise": entreprise,
            "ton_message": ton_message,
            "longueur_message": longueur_message,
            "cta_option": cta_option,
            "genre_profil": genre_profil,
            "profil_data": donnees_profil.copy()
        }

    # --------- RÉSULTAT ---------
    if st.session_state.get("inmail_generated"):
        # Vérifier si les paramètres ont changé
        snap_inmail = st.session_state.get("inmail_snapshot", {})
        current_profil = st.session_state.get("inmail_profil_data", profil_data)
        
        params_changed_inmail = False
        if snap_inmail:
            params_changed_inmail = any([
                snap_inmail.get("poste_accroche") != poste_accroche,
                snap_inmail.get("entreprise") != entreprise,
                snap_inmail.get("ton_message") != ton_message,
                snap_inmail.get("longueur_message") != longueur_message,
                snap_inmail.get("cta_option") != cta_option,
                snap_inmail.get("genre_profil") != genre_profil,
                snap_inmail.get("profil_data") != current_profil
            ])
        
        # Titre avec indication si obsolète
        titre_inmail = "📝 Message InMail généré"
        if params_changed_inmail:
            titre_inmail += " ⚠️ (Paramètres modifiés - Régénérer pour mettre à jour)"
        
        st.subheader(titre_inmail)
        st.text_input("📧 Objet", st.session_state.get("inmail_objet", ""), key="inmail_objet_display")
        
        # Debug: Afficher les informations du message
        msg = st.session_state.get("inmail_message", "")
        if not msg:
            msg = "Aucun message généré"
        
        # Utiliser une clé dynamique pour forcer la mise à jour du contenu
        import time
        dynamic_key = f"inmail_msg_display_{int(time.time() * 1000) % 10000}"
        
        try:
            st.text_area("Message", value=msg, height=250, key=dynamic_key)
        except Exception as e:
            st.error(f"Erreur affichage message: {e}")
            st.text_area("Message", msg, height=250, key=f"fallback_{dynamic_key}")
        st.caption(f"📏 {len(msg.split())} mots | {len(msg)} caractères")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Régénérer (nouvelle version)", key="btn_regen_inmail"):
                donnees_profil = st.session_state.get("inmail_profil_data", profil_data)
                
                # Générer une nouvelle version avec l'IA
                ia_prompt = f"""
                Génère une NOUVELLE version d'un message InMail UNIQUEMENT LE CONTENU (sans objet, sans titre) différente de la précédente avec:
                - Candidat: {donnees_profil.get('prenom', '')} {donnees_profil.get('nom', '')}
                - Poste actuel: {donnees_profil.get('poste_actuel', '')}
                - Entreprise actuelle: {donnees_profil.get('entreprise_actuelle', '')}
                - Compétences: {', '.join(filter(None, donnees_profil.get('competences_cles', [])))}
                - Formation: {donnees_profil.get('formation', '')}
                - Expérience: {donnees_profil.get('experience_annees', '')} ans
                
                Poste à pourvoir: {poste_accroche}
                Entreprise: {entreprise}
                Ton: {ton_message}
                
                Génère une approche différente, avec un angle nouveau mais professionnel.
                Commence directement par la salutation (ex: Bonjour {donnees_profil.get('prenom', 'Candidat')},).
                Ne pas inclure d'objet, de titre ou de formatage en gras.
                """
                
                with st.spinner("🔄 Régénération IA en cours..."):
                    ia_result = get_deepseek_response(ia_prompt, [], "normale", "InMail Regeneration")
                    if ia_result.get("content"):
                        new_msg = ia_result["content"]
                    else:
                        new_msg = generate_inmail(donnees_profil, poste_accroche, entreprise, ton_message, longueur_message, cta_option, genre_profil, "entreprise")
                
                st.session_state["inmail_message"] = new_msg
                st.session_state["inmail_objet"] = "Nouvelle opportunité: " + poste_accroche
                # Forcer le rechargement de la page pour mettre à jour l'affichage
                st.rerun()
        with col2:
            if st.button("💾 Sauvegarder comme modèle", key="btn_save_inmail"):
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "InMail",
                    "poste": poste_accroche,
                    "requete": st.session_state["inmail_message"],
                    "utilisateur": st.session_state.get("user", ""),
                    "source": "InMail",
                    "commentaire": f"Ton: {ton_message}, Longueur: {longueur_message} mots"
                }
                st.session_state.library_entries.append(entry)
                save_library_entries()
                save_sourcing_entry_to_gsheet(entry)
                st.success(f"✅ Modèle '{poste_accroche} - {entry['timestamp']}' sauvegardé")


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

    # Zone unique fusionnée : selectbox avec option "Autre" pour saisie libre
    option_choisie = st.selectbox(
        "📌 Choisissez une question ou tapez la vôtre :",
        questions_pretes + ["Autre (tapez votre question)"],
        help="Sélectionnez une question prête ou choisissez 'Autre' pour taper votre propre question."
    )
    
    # Zone de saisie unique selon le choix
    if option_choisie == "Autre (tapez votre question)":
        question_complete = st.text_input(
            "Votre question :",
            placeholder="Ex: Quelles sont les compétences clés pour un chef de projet BTP ?"
        )
    else:
        question_complete = st.text_input(
            "Complétez la question :",
            value=option_choisie + " ",
            placeholder="Ex: " + option_choisie + " développeur web"
        )

    mode_rapide_magicien = st.checkbox("⚡ Réponse concise", key="magicien_fast")
    
    if st.button("✨ Poser la question à l'IA", type="primary", key="ask_magicien", use_container_width=True):
        if question_complete and question_complete.strip():
            with st.spinner("⏳ Génération en cours..."):
                start_time = time.time()
                prompt = question_complete.strip()
                # Ajout d'une instruction pour forcer une liste d'intitulés/synonymes si la question le demande
                if "synonymes" in prompt.lower() or "intitulés similaires" in prompt.lower():
                    prompt += ". Réponds uniquement par une liste de synonymes ou intitulés similaires, séparés par des virgules, sans introduction."
                elif "outils" in prompt.lower() or "logiciels" in prompt.lower():
                    prompt += ". Réponds avec une liste à puces des outils, sans introduction."
                elif "compétences" in prompt.lower() or "skills" in prompt.lower():
                    prompt += ". Réponds avec une liste à puces, sans introduction."
                if mode_rapide_magicien:
                    prompt += " Réponse concise et directe."
                result = get_deepseek_response(prompt, [], "normale" if not mode_rapide_magicien else "courte", "Magicien Sourcing")
                total_time = int(time.time() - start_time)
                st.success(f"✅ Réponse générée en {total_time}s")
                if result.get("content"):
                    st.subheader("💡 Réponse :")
                    st.write(result["content"])
                    if not hasattr(st.session_state, 'magicien_history'):
                        st.session_state.magicien_history = []
                    st.session_state.magicien_history.append({
                        "q": prompt,
                        "r": result["content"],
                        "time": total_time
                    })
                else:
                    st.error("❌ Aucune réponse générée. Veuillez reformuler votre question.")
        else:
            st.warning("⚠️ Veuillez saisir une question")

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

    # Génération de noms marocains aléatoires
    if "random_names" not in st.session_state:
        import random
        noms_masculins = ["Ahmed", "Mohamed", "Youssef", "Omar", "Khalid", "Rachid", "Hassan", "Abdelkader", "Mustapha", "Saïd"]
        noms_feminins = ["Fatima", "Aicha", "Khadija", "Zineb", "Salma", "Nadia", "Houda", "Laila", "Amina", "Sanaa"]
        noms_famille = ["Alami", "Bennani", "Cherkaoui", "Filali", "Idrissi", "Jamal", "Kettani", "Lahlou", "Mahfoudi", "Naciri", "Ouazzani", "Qadiri"]
        
        # Sélectionner aléatoirement
        random_prenom_m = random.choice(noms_masculins)
        random_prenom_f = random.choice(noms_feminins)
        random_nom = random.choice(noms_famille)
        
        st.session_state["random_names"] = {
            "masculin": f"{random_prenom_m}",
            "feminin": f"{random_prenom_f}",
            "nom": random_nom
        }

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom:", key="perm_prenom", placeholder=st.session_state['random_names']['masculin'])
        nom = st.text_input("Nom:", key="perm_nom", placeholder=st.session_state['random_names']['nom'])
    with col2:
        entreprise = st.text_input("Entreprise:", key="perm_entreprise", placeholder="TGCC")
        source = st.radio("Source de détection :", ["Site officiel", "Charika.ma"], key="perm_source", horizontal=True)
    



    if st.button("🔮 Générer permutations", use_container_width=True):
        if prenom and nom and entreprise:
            with st.spinner("⏳ Génération des permutations..."):
                start_time = time.time()
                permutations = []
                detected = get_email_from_charika(entreprise) if source == "Charika.ma" else None
                
                if detected and source == "Charika.ma":
                    st.info(f"📧 Format détecté sur Charika.ma : {detected}")
                    domain = detected.split("@")[1]
                elif source == "Charika.ma":
                    # Email non détecté sur Charika
                    st.error(f"❌ Format d'email non détecté sur Charika.ma pour '{entreprise}'")
                    domain = f"{entreprise.lower().replace(' ', '').replace('-', '')}.ma"
                    # Ajout du bouton/lien Google
                    google_url = get_charika_search_url(entreprise)
                    st.markdown(f"<a href='{google_url}' target='_blank' style='font-size:16px;'>🔎 Rechercher sur Google</a>", unsafe_allow_html=True)
                else:
                    domain = f"{entreprise.lower().replace(' ', '').replace('-', '')}.ma"
                
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

# -------------------- Tab 10: Documents de Nomination --------------------
with tab10:
    st.header("📄 Générateur de Documents de Nomination")
    
    # Fonction pour générer le document Word de nomination
    def generate_nomination_document(nom, prenom, poste, departement_rattachement, date_effet):
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from io import BytesIO
            
            doc = Document()
            
            # En-tête TGCC
            header_p = doc.add_paragraph()
            header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = header_p.add_run("TGCC\nCONSTRUISONS ENSEMBLE")
            run.font.size = Pt(16)
            run.bold = True
            
            # Espacement
            doc.add_paragraph()
            doc.add_paragraph()
            
            # Objet
            objet_p = doc.add_paragraph()
            objet_run = objet_p.add_run(f"Objet : Annonce de nomination — {prenom} {nom}")
            objet_run.bold = True
            
            doc.add_paragraph()
            
            # Corps du message
            doc.add_paragraph("Chers Collaborateurs,")
            doc.add_paragraph()
            
            message_p = doc.add_paragraph()
            message_p.add_run(f"Nous avons le plaisir de vous annoncer la nomination de {prenom} {nom} au poste de ")
            run_poste = message_p.add_run(poste)
            run_poste.bold = True
            message_p.add_run(f", effective à compter du {date_effet}.")
            
            doc.add_paragraph()
            
            rattachement_p = doc.add_paragraph()
            rattachement_p.add_run(f"{prenom} {nom} sera rattaché au ")
            run_dept = rattachement_p.add_run(departement_rattachement)
            run_dept.bold = True
            rattachement_p.add_run(" et aura pour mission de piloter la stratégie des ressources humaines de TGCC, en accompagnant notre croissance et en renforçant notre culture d'entreprise.")
            
            doc.add_paragraph()
            
            doc.add_paragraph("Nous lui souhaitons la bienvenue au sein de notre groupe et lui exprimons notre entière confiance pour relever les défis à venir.")
            doc.add_paragraph()
            doc.add_paragraph("Restons mobilisés pour construire ensemble !")
            doc.add_paragraph()
            
            # Ligne de séparation
            doc.add_paragraph("---")
            doc.add_paragraph()
            
            # Signature
            signature_p = doc.add_paragraph()
            signature_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            signature_run = signature_p.add_run(f"{departement_rattachement}\nTGCC — CONSTRUISONS ENSEMBLE")
            signature_run.bold = True
            
            # Sauvegarder dans un buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()
            
        except ImportError:
            st.error("Erreur: La bibliothèque python-docx n'est pas installée")
            return None
        except Exception as e:
            st.error(f"Erreur lors de la génération du document: {str(e)}")
            return None
    
    # Interface utilisateur
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nom du collaborateur:", key="nom_nomination", placeholder="DUPONT")
        poste = st.text_input("Poste:", key="poste_nomination", placeholder="Directeur du Capital Humain")
        date_effet = st.date_input("Date d'effet:", key="date_nomination")
    
    with col2:
        prenom = st.text_input("Prénom du collaborateur:", key="prenom_nomination", placeholder="Jean")
        departement_rattachement = st.text_input("Département de rattachement:", key="dept_nomination", placeholder="Pôle des Affaires Générales")
    
    if st.button("📄 Générer Document de Nomination", type="primary", use_container_width=True):
        if nom and prenom and poste and departement_rattachement:
            with st.spinner("📄 Génération du document en cours..."):
                doc_data = generate_nomination_document(
                    nom, prenom, poste, departement_rattachement, 
                    date_effet.strftime("%d %B %Y") if date_effet else "Date à définir"
                )
                
                if doc_data:
                    filename = f"Nomination_{prenom}_{nom}_{date_effet.strftime('%Y%m%d') if date_effet else 'DateADefinir'}.docx"
                    st.download_button(
                        label="📥 Télécharger le Document Word",
                        data=doc_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    st.success("✅ Document généré avec succès !")
                else:
                    st.error("❌ Erreur lors de la génération du document")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs obligatoires")
    
    # Prévisualisation du contenu
    if nom and prenom and poste and departement_rattachement:
        st.subheader("👁️ Prévisualisation du contenu")
        with st.expander("Voir le contenu du document", expanded=False):
            preview_content = f"""
**TGCC**
**CONSTRUISONS ENSEMBLE**

---

**Objet : Annonce de nomination — {prenom} {nom}**

Chers Collaborateurs,

Nous avons le plaisir de vous annoncer la nomination de **{prenom} {nom}** au poste de **{poste}**, effective à compter du **{date_effet.strftime('%d %B %Y') if date_effet else 'Date à définir'}**.

{prenom} {nom} sera rattaché au **{departement_rattachement}** et aura pour mission de piloter la stratégie des ressources humaines de TGCC, en accompagnant notre croissance et en renforçant notre culture d'entreprise.

Nous lui souhaitons la bienvenue au sein de notre groupe et lui exprimons notre entière confiance pour relever les défis à venir.

Restons mobilisés pour construire ensemble !

---

**{departement_rattachement}**
**TGCC — CONSTRUISONS ENSEMBLE**
            """
            st.markdown(preview_content)

# -------------------- CSS pour masquer le prompt en bas --------------------