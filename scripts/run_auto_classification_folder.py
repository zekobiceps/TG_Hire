import os
import re
import json
import time
import argparse
from typing import Tuple

import requests

try:
    import tomllib  # Py 3.11+
except Exception:  # pragma: no cover
    tomllib = None

# -------------------- PROMPT (copié depuis Analyse_CV.py) --------------------
NON_CLASSE_SUBCATEGORY = "Divers / Hors périmètre"
PRODUCTION_ALLOWED_SUBCATEGORIES = [
    "PRODUCTION - ÉTUDES (BUREAU)",
    "PRODUCTION - TRAVAUX (CHANTIER)",
    "PRODUCTION - QUALITÉ",
]

SUBDIRECTION_TO_MACRO = {
    "RH": "Fonctions supports",
    "RESSOURCES HUMAINES": "Fonctions supports",
    "RECRUTEMENT": "Fonctions supports",
    "PAIE": "Fonctions supports",
    "FORMATION": "Fonctions supports",
    "FINANCE": "Fonctions supports",
    "COMPTABILITÉ": "Fonctions supports",
    "COMPTABILITE": "Fonctions supports",
    "TRÉSORERIE": "Fonctions supports",
    "TRESORERIE": "Fonctions supports",
    "CONTRÔLE DE GESTION": "Fonctions supports",
    "CONTROLE DE GESTION": "Fonctions supports",
    "AUDIT": "Fonctions supports",
    "ACHATS": "Fonctions supports",
    "ACHAT": "Fonctions supports",
    "DSI": "Fonctions supports",
    "INFORMATIQUE": "Fonctions supports",
    "IT": "Fonctions supports",
    "SUPPORT IT": "Fonctions supports",
    "QHSE": "Fonctions supports",
    "QUALITÉ": "Fonctions supports",
    "QUALITE": "Fonctions supports",
    "HSE": "Fonctions supports",
    "JURIDIQUE": "Fonctions supports",
    "LEGAL": "Fonctions supports",
    "COMMUNICATION": "Fonctions supports",
    "MARKETING": "Fonctions supports",
    "ADMINISTRATION": "Fonctions supports",
    "ASSISTANAT": "Fonctions supports",
    "SECRÉTARIAT": "Fonctions supports",
    "SECRETARIAT": "Fonctions supports",
    "SUPPLY CHAIN": "Logistique",
    "APPROVISIONNEMENT": "Fonctions supports",
    "TRANSPORT": "Logistique",
    "ENTREPÔT": "Logistique",
    "ENTREPOT": "Logistique",
    "STOCKS": "Logistique",
    "PRÉPARATION": "Logistique",
    "PREPARATION": "Logistique",
    "DISTRIBUTION": "Logistique",
    "PRODUCTION - ÉTUDES (BUREAU)": "Production/Technique",
    "PRODUCTION - TRAVAUX (CHANTIER)": "Production/Technique",
    "PRODUCTION - QUALITÉ": "Production/Technique",
}

CATEGORIES_PROMPT = """
Agis comme un expert en recrutement. Tu dois classer STRICTEMENT le CV dans UNE et UNE SEULE des quatre macro-catégories suivantes :

1) Fonctions supports
    - Ce sont les fonctions transverses qui soutiennent l'activité opérationnelle.
    - ⚠️ ATTENTION : La sous-catégorie doit être le NOM de la SOUS-DIRECTION (pas l'intitulé du poste) !

    **Sous-directions disponibles :**
    • **DSI** : Développeur, Business Analyst IT, Data Analyst, Product Owner, Chef de projet IT/digital, Consultant IT, AMOA, Transformation digitale, Administrateur système, Support IT, Ingénieur réseau, RSSI...
    • **Finance** : Comptable, Contrôleur de gestion, DAF, Auditeur, Trésorier, M&A, Corporate Finance, Consultant Finance, Financement...
    • **Achats** : Acheteur, Ingénieur achats, Directeur achats, Approvisionneur, Sourcing...
    • **RH** : Recruteur, Responsable RH, DRH, Gestionnaire paie, Chargé de formation, Relations sociales...
    • **QHSE** : Responsable qualité, Coordinateur HSE, Ingénieur sécurité, Auditeur qualité...
    • **Juridique** : Juriste, Avocat, Directeur juridique, Compliance...
    • **Communication** : Chargé de communication, Community manager, Responsable marketing, Chef de produit...
    • **Administration** : Assistant, Secrétaire, Office manager...

    - ⚠️ RÈGLE ABSOLUE : DSI, Informatique, IT, Développement, Data = TOUJOURS Fonctions supports (jamais Production).
    - ⚠️ RÈGLE ABSOLUE : Achats, Approvisionnement = TOUJOURS Fonctions supports.
    - **La sous-catégorie doit être UNIQUEMENT : \"DSI\", \"RH\", \"Finance\", \"Achats\", \"QHSE\", \"Juridique\", \"Communication\" ou \"Administration\".**
    - **NE RETOURNE JAMAIS l'intitulé du poste comme sous-catégorie !**

2) Production/Technique
    - Métiers de la production, du BTP, de l'industrie, de la maintenance, du bureau d'études.
    - ⚠️ Exclut TOUS les métiers IT/Digital (ceux-là vont en Fonctions supports - DSI).
    - Exemples : Ingénieur BTP, Conducteur de travaux, Chef de chantier, Technicien maintenance, Opérateur production, Ingénieur méthodes, Dessinateur projeteur.
    - TU DOIS choisir UNE SEULE sous-catégorie parmi :
        • "PRODUCTION - ÉTUDES (BUREAU)" → Bureau d'études, méthodes, prix, planification technique
        • "PRODUCTION - TRAVAUX (CHANTIER)" → Chantier, conduite de travaux, chef de chantier, conducteur d'engins
        • "PRODUCTION - QUALITÉ" → Qualité production, contrôle qualité sur site

3) Logistique
    - Métiers centrés sur la gestion des flux physiques : transport, entrepôt, stocks, distribution.
    - Exemples : Responsable entrepôt, Préparateur de commandes, Gestionnaire de stocks, Responsable transport, Supply chain (flux physiques).
    - Sous-catégorie : le type de métier logistique (ex : "Transport", "Entrepôt", "Stocks").

4) Non classé
    - Utilise cette catégorie seulement si le CV est hors périmètre (autre secteur) ou illisible.
    - Sous-catégorie OBLIGATOIRE : "Divers / Hors périmètre".
"""


def get_classification_prompt(text: str, hint_name: str | None) -> str:
    return f"""
    Agis comme un expert en recrutement qui analyse un CV.
    Lis attentivement le texte du CV ci-dessous et extrais les informations suivantes.
    Réponds UNIQUEMENT avec un objet JSON valide.

    CV TEXTE :
    ---
    {text[:8000]}
    ---

    Réponds UNIQUEMENT avec le format JSON suivant :
    {{
        "candidate_name": "Prénom NOM",
        "macro_category": "...",
        "sub_category": "...",
        "years_experience": 0,
        "profile_summary": "..."
    }}
    """


def clean_json_string(json_str: str) -> str:
    if "```" in json_str:
        json_str = re.sub(r"```json\s*", "", json_str)
        json_str = re.sub(r"```\s*", "", json_str)
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end != -1:
        return json_str[start:end + 1]
    return json_str


def extract_name_smart_email(text):
    """
    Extrait le nom via l'email ET vérifie sa présence dans le texte pour confirmer.
    Gère les formats : prenom.nom, prenom_nom, nom.prenom
    """
    if not text:
        return None

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)

    ignore_emails = ['contact', 'info', 'recrutement', 'job', 'stages', 'rh', 'email', 'gmail', 'yahoo']

    for email in emails:
        user_part = email.split('@')[0]
        if any(bad in user_part.lower() for bad in ignore_emails):
            continue

        parts = re.split(r'[._-]', user_part)
        valid_parts = [p for p in parts if p.isalpha() and len(p) >= 3]

        if len(valid_parts) >= 2:
            header_text = text[:1000]
            found_parts = []
            for part in valid_parts:
                match = re.search(r'\b' + re.escape(part) + r'\b', header_text, re.IGNORECASE)
                if match:
                    found_parts.append(match.group(0))

            if len(found_parts) >= 2:
                return {"name": " ".join(found_parts), "confidence": 0.99, "method_used": "smart_email_cross_check"}

    return None


def is_valid_name_candidate(text: str) -> bool:
    if not text or len(text) < 2:
        return False
    text = text.strip()
    if len(text) > 50 and ' ' not in text:
        return False
    if re.search(r'\d', text):
        return False
    if re.search(r'[@€$£%&:]', text):
        return False
    if text.count('-') > 3:
        return False
    if not re.search(r'[aeiouyàâäéèêëïîôöùûü]', text.lower()):
        return False
    clean_chars = re.sub(r'[\s\-\.]', '', text)
    if not clean_chars:
        return False
    return True


def is_likely_name_line(line: str) -> bool:
    line_lower = line.lower().strip()
    words = line_lower.split()
    forbidden_words = [
        'cv', 'curriculum', 'vitae', 'resume', 'profil', 'profile',
        'expérience', 'experience', 'formation', 'education',
        'compétences', 'skills', 'langues', 'languages',
        'projet', 'project', 'contact', 'téléphone', 'email', 'adresse',
        'page', 'date', 'diplômes', 'formations', 'certifications', 'hobbies', 'loisirs',
        'permis', 'vehicule', 'véhicule', 'conduite', 'driver', 'driving', 'b', 'voiture',
        'centres', 'intérêt', 'projets', 'réalisés', 'professionnelles',
        'coordonnées', 'spécialisations', 'management', 'onboarding', 'performance',
        'sommaire', 'summary', 'objectif', 'objective', 'propos', 'about', 'me', 'moi',
        'bac', 'baccalauréat', 'baccalaureate', 'degree', 'niveau', 'level',
        'logiciels', 'maîtrisés', 'activités', 'associatives',
        'école', 'ecole', 'school', 'business', 'university', 'université',
        'master', 'bachelor', 'licence', 'mba', 'diplôme', 'diplome', 'msc',
        'excel', 'vba', 'power', 'bi', 'crm', 'python', 'java', 'sql', 'office',
        'google', 'cloud', 'aws', 'azure', 'sap', 'erp',
        'bnp', 'paribas', 'société', 'générale', 'crédit', 'agricole', 'sncf',
        'groupe', 'group', 'bank', 'banque',
        'france', 'paris', 'maroc', 'casablanca', 'rabat',
        'non', 'trouvé',
        'analyste', 'financière', 'contrôleuse', 'gestion', 'ingénieur',
        'directeur', 'directrice', 'manager', 'consultant', 'développeur', 'responsable',
        'job', 'étudiant', 'etudiant', 'student', 'intern', 'internship', 'stage',
        'engineer', 'developer', 'designer', 'analyst', 'specialist', 'coordinator',
        'soft', 'hard', 'skills', 'outils', 'logiciels', 'agile', 'scrum',
    ]

    fatal_substrings = [
        'compétence', 'competence', 'formation', 'education',
        'projets', 'réalisés', 'experience', 'expérience',
        'sommaire', 'summary', 'profil', 'profile',
        'soft', 'hard', 'skills', 'outils', 'logiciels',
        'management', 'agile', 'scrum', 'methodologie', 'méthodologie'
    ]
    if any(fs in line_lower for fs in fatal_substrings):
        return False

    if any(w in forbidden_words for w in words):
        return False
    if ':' in line or '&' in line:
        return False
    if any(p in line for p in ['.', '(', ')', '/', ',']) or any(c.isdigit() for c in line):
        return False

    if len(words) < 2 or len(words) > 5:
        return False

    stop_words = ['de', 'du', 'des', 'le', 'la', 'les', 'van', 'von', 'da', 'di']
    if all(w in stop_words for w in words):
        return False

    if not line.isupper() and not any(w[0].isupper() for w in line.split() if w):
        return False

    return True


def score_name_candidate(text: str) -> float:
    score = 0.0
    words = text.split()
    if 2 <= len(words) <= 3:
        score += 0.3
    elif len(words) == 4:
        score += 0.2

    if text.isupper():
        score += 0.2
    elif all(w[0].isupper() for w in words if w):
        score += 0.2
    elif len(words) >= 2 and words[-1].isupper() and words[0][0].isupper():
        score += 0.3

    if is_valid_name_candidate(text):
        score += 0.2
    else:
        return 0

    return min(score, 1.0)


def clean_merged_text_pdf(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'([a-zà-ÿ])([A-ZÀ-Ÿ])', r'\1 \2', text)
    text = re.sub(r'([0-9])([a-zA-Z]{2,})', r'\1 \2', text)
    return text


def extract_name_from_cv_text(text):
    if not text or len(text.strip()) < 10:
        return {"name": None, "confidence": 0, "method_used": "text_too_short"}

    text = clean_merged_text_pdf(text)
    lines = text.split('\n')

    SCAN_LIMIT = 200
    cleaned_lines = []
    for line in lines[:SCAN_LIMIT]:
        clean = line.strip()
        clean = re.sub(r'^##\s*', '', clean)
        clean = re.sub(r'^\*\*\s*', '', clean)
        clean = re.sub(r'\s*\*\*$', '', clean)
        clean = re.sub(r'^[-•➢–]\s*', '', clean)
        clean = re.sub(r'^[o]\s*', '', clean)
        if not clean:
            continue
        cleaned_lines.append(clean)

    candidates = []
    for idx, line in enumerate(cleaned_lines):
        if not is_likely_name_line(line):
            continue
        score = score_name_candidate(line)
        if score > 0:
            position_penalty = min(idx / 50.0, 0.5)
            score = max(0.0, score - position_penalty)
            candidates.append((score, line))

    candidates.sort(reverse=True, key=lambda x: x[0])
    if candidates:
        best_score, best_name = candidates[0]
        return {"name": best_name, "confidence": best_score, "method_used": "text_heuristic"}

    return {"name": None, "confidence": 0, "method_used": "no_candidate"}


def normalize_classification_labels(raw_macro: str | None, raw_sub: str | None, full_text: str | None = "") -> Tuple[str, str]:
    macro = (raw_macro or "").strip()
    sub = (raw_sub or "").strip()
    text_lower = (full_text or "").lower()
    sub_upper = sub.upper()

    if sub_upper in SUBDIRECTION_TO_MACRO:
        forced_macro = SUBDIRECTION_TO_MACRO[sub_upper]
        if forced_macro != macro:
            macro = forced_macro
        if macro != "Production/Technique":
            return macro, sub

    if any(kw in sub_upper for kw in ["DSI", "INFORMATIQUE", "IT", "SUPPORT IT", "SYSTÈME", "SYSTEME", "RÉSEAU", "RESEAU", "CYBER",
                                        "DÉVELOPPEUR", "DEVELOPPEUR", "DEV ", "FULL-STACK", "FULL STACK", "BACKEND", "FRONTEND",
                                        "DATA ANALYST", "DATA ENGINEER", "DATA SCIENTIST", "BI", "BUSINESS INTELLIGENCE",
                                        "PRODUCT OWNER", "SCRUM MASTER", "CHEF DE PROJET IT", "CHEF DE PROJET DIGITAL",
                                        "DIGITALISATION", "DIGITAL", "TRANSFORMATION DIGITALE", "NUMÉRIQUE", "NUMERIQUE",
                                        "BUSINESS ANALYST IT", "ANALYSTE IT", "CONSULTANT IT", "AMOA", "MOA"]):
        return "Fonctions supports", "DSI"
    if any(kw in text_lower for kw in [" dsi ", "direction des systèmes", "direction système", "infrastructure it", "support informatique",
                                         "administrateur système", "ingénieur système", "développeur", "developpeur", "full stack", "full-stack",
                                         "data analyst", "data engineer", "data scientist", "business intelligence", "product owner",
                                         "scrum master", "chef de projet it", "digitalisation", "transformation digitale", "business analyst it"]):
        return "Fonctions supports", "DSI"

    if any(kw in sub_upper for kw in ["RH", "RESSOURCES HUMAINES", "RECRUTEMENT", "PAIE", "FORMATION"]):
        return "Fonctions supports", "RH"
    if any(kw in text_lower for kw in ["ressources humaines", "recruteur", "chargé de recrutement", "gestionnaire paie", "responsable formation"]):
        return "Fonctions supports", "RH"

    if any(kw in sub_upper for kw in ["FINANCE", "COMPTAB", "TRÉSOR", "AUDIT", "CONTRÔLE DE GESTION", "CONTROLE DE GESTION",
                                        "M&A", "CORPORATE FINANCE", "FINANCEMENT", "INVESTISSEMENT", "GESTION FINANCIÈRE", "GESTION FINANCIERE",
                                        "CONTRÔLEU", "CONTROLEU", "DAF", "RAF"]):
        return "Fonctions supports", "Finance"
    if any(kw in text_lower for kw in ["comptable", "contrôleur de gestion", "controleur de gestion", "auditeur", "trésorier",
                                         "directeur financier", "daf", "m&a", "corporate finance", "financement", "finance manager",
                                         "consultant finance", "consultante finance"]):
        return "Fonctions supports", "Finance"

    if any(kw in sub_upper for kw in ["ACHAT", "APPROVISIONNEMENT", "SOURCING"]):
        return "Fonctions supports", "Achats"
    if any(kw in text_lower for kw in ["acheteur", "ingénieur achats", "directeur achats", "responsable achats", "approvisionneur"]):
        return "Fonctions supports", "Achats"

    if any(kw in sub_upper for kw in ["JURIDIQUE", "LEGAL", "DROIT"]):
        return "Fonctions supports", "Juridique"
    if any(kw in text_lower for kw in ["juriste", "avocat", "directeur juridique", "conseil juridique"]):
        return "Fonctions supports", "Juridique"

    if any(kw in sub_upper for kw in ["COMMUNICATION", "MARKETING", "COM ", "RESPONSABLE MARKETING", "CHARGÉ COM", "CHARGE COM"]):
        return "Fonctions supports", "Communication"
    if any(kw in text_lower for kw in ["chargé de communication", "charge de communication", "community manager", "responsable marketing",
                                         "chef de produit", "responsable communication"]):
        return "Fonctions supports", "Communication"

    if any(kw in sub_upper for kw in ["ADMINISTRATION", "ASSISTANAT", "SECRÉTARIAT", "SECRETARIAT", "ASSISTANT"]):
        return "Fonctions supports", "Administration"
    if any(kw in text_lower for kw in ["assistant", "secrétaire", "office manager", "assistant de direction"]):
        return "Fonctions supports", "Administration"

    if "support" in macro.lower():
        macro = "Fonctions supports"
    elif "logist" in macro.lower():
        macro = "Logistique"
    elif "production" in macro.lower() or "tech" in macro.lower():
        macro = "Production/Technique"
    else:
        macro = "Non classé"

    if macro == "Production/Technique":
        for allowed in PRODUCTION_ALLOWED_SUBCATEGORIES:
            if allowed.upper() == sub_upper:
                return macro, allowed

        if any(keyword in sub_upper for keyword in ["QUAL", "QC", "QHSE", "HSE"]) or any(keyword in text_lower for keyword in ["qualit", "qse", "controle qual", "control quality"]):
            return macro, "PRODUCTION - QUALITÉ"
        if any(keyword in sub_upper for keyword in ["METH", "PLAN", "ETU", "MÉTR", "METR", "BUREAU", "PRIX"]) or any(keyword in text_lower for keyword in ["méthode", "method", "planning", "planificateur", "métr", "etude de prix", "bureau d'etude"]):
            return macro, "PRODUCTION - ÉTUDES (BUREAU)"
        if any(keyword in sub_upper for keyword in ["TRAVAUX", "CHANTIER", "CONDUCTEUR", "DIRECTEUR", "CHEF DE PROJET", "CHEF D'ÉQUIPE", "CHEF D'EQUIPE", "OPC"]) or any(keyword in text_lower for keyword in ["chantier", "conducteur", "chef de chantier", "travaux", "opc"]):
            return macro, "PRODUCTION - TRAVAUX (CHANTIER)"
        return macro, "PRODUCTION - AUTRES"

    if macro == "Non classé":
        return macro, NON_CLASSE_SUBCATEGORY

    if not sub:
        if macro == "Fonctions supports":
            return macro, "Support"
        if macro == "Logistique":
            return macro, "Logistique"

    return macro, sub


# -------------------- PDF Extraction --------------------

def extract_text_from_pdf_path(path: str) -> str:
    import io
    with open(path, "rb") as f:
        data = f.read()
    bio = io.BytesIO(data)

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=bio, filetype="pdf")
        parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            parts.append(page.get_text("text", sort=True))
        text = "\n".join(parts).strip()
        if len(text) > 50:
            return text
    except Exception:
        pass

    try:
        import pdfplumber
        bio.seek(0)
        with pdfplumber.open(bio) as pdf:
            parts = []
            for page in pdf.pages:
                pt = page.extract_text()
                if pt:
                    parts.append(pt)
            text = "\n".join(parts).strip()
            if text:
                return text
    except Exception:
        pass

    try:
        import PyPDF2
        bio.seek(0)
        reader = PyPDF2.PdfReader(bio)
        parts = []
        for page in reader.pages:
            try:
                pt = page.extract_text()
            except Exception:
                pt = None
            if pt:
                parts.append(pt)
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    try:
        from pypdf import PdfReader as PypdfReader
        bio.seek(0)
        reader = PypdfReader(bio)
        parts = []
        for page in reader.pages:
            pt = page.extract_text()
            if pt:
                parts.append(pt)
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    return ""


def load_deepseek_key() -> str | None:
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key
    secrets_path = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "secrets.toml")
    secrets_path = os.path.abspath(secrets_path)
    if not os.path.exists(secrets_path):
        return None
    if tomllib is None:
        return None
    try:
        with open(secrets_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("DEEPSEEK_API_KEY")
    except Exception:
        return None


def call_deepseek(prompt: str, api_key: str) -> dict:
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    response.raise_for_status()
    raw_content = response.json()["choices"][0]["message"]["content"]
    clean_content = clean_json_string(raw_content)
    try:
        return json.loads(clean_content)
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Auto-classification CVs (DeepSeek)")
    parser.add_argument("--input", default="/workspaces/TG_Hire/LOGO/CVS", help="Dossier contenant les PDFs")
    parser.add_argument("--output", default="/workspaces/TG_Hire/LOGO/CVS/classification_results.csv", help="CSV de sortie")
    parser.add_argument("--sleep", type=float, default=0.2, help="Pause entre appels API (s)")
    args = parser.parse_args()

    api_key = load_deepseek_key()
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY introuvable dans env ou secrets.toml")

    pdfs = sorted([p for p in os.listdir(args.input) if p.lower().endswith(".pdf")])
    if not pdfs:
        raise SystemExit("Aucun PDF trouvé.")

    results = []
    for idx, filename in enumerate(pdfs, start=1):
        path = os.path.join(args.input, filename)
        text = extract_text_from_pdf_path(path)
        extracted = extract_name_smart_email(text) or extract_name_from_cv_text(text)
        hint_name = extracted.get("name") if extracted and extracted.get("name") else os.path.splitext(filename)[0]
        prompt = get_classification_prompt(text, hint_name)
        data = call_deepseek(prompt, api_key)

        macro, sub = normalize_classification_labels(data.get("macro_category"), data.get("sub_category"), text)

        candidate_name = data.get("candidate_name", "Candidat")
        if extracted and extracted.get("confidence", 0) >= 0.99 and extracted.get("name"):
            candidate_name = extracted.get("name")

        results.append({
            "file": filename,
            "candidate_name": candidate_name,
            "macro_category": macro,
            "sub_category": sub,
            "years_experience": data.get("years_experience", 0),
            "profile_summary": data.get("profile_summary", ""),
        })

        print(f"[{idx}/{len(pdfs)}] {filename} -> {macro} / {sub}")
        time.sleep(args.sleep)

    # Écriture CSV avec encodage UTF-8-sig pour Excel
    import csv
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Résultats enregistrés dans: {args.output}")
    
    # Génération automatique du fichier Excel et ZIP avec renommage
    try:
        import pandas as pd
        import zipfile
        
        df = pd.DataFrame(results)
        base_path = os.path.dirname(args.output)
        
        # Créer le fichier Excel
        excel_path = os.path.join(base_path, "classification_results.xlsx")
        df.to_excel(excel_path, index=False, sheet_name='CVs Classés', engine='openpyxl')
        print(f"✅ Fichier Excel créé : {excel_path}")
        
        # Créer le fichier ZIP avec renommage
        zip_path = os.path.join(base_path, "CVs_classes.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ajouter le fichier Excel
            zipf.write(excel_path, "classification_results.xlsx")
            
            # Ajouter les CVs avec nouveaux noms
            for row in results:
                original_filename = row["file"]
                candidate_name = row.get("candidate_name", "Candidat_Inconnu")
                macro_category = row["macro_category"]
                sub_category = row["sub_category"]
                
                safe_macro = "".join(c for c in str(macro_category) if c.isalnum() or c in (" ", "_")).rstrip()
                safe_sub = "".join(c for c in str(sub_category) if c.isalnum() or c in (" ", "_")).rstrip()
                
                # Nettoyer le nom du candidat
                safe_candidate_name = "".join(c for c in str(candidate_name) if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                if not safe_candidate_name or safe_candidate_name == "Candidat_Inconnu":
                    safe_candidate_name = os.path.splitext(original_filename)[0]
                
                # Nouveau nom de fichier
                file_extension = os.path.splitext(original_filename)[1]
                new_filename = f"{safe_candidate_name}{file_extension}"
                
                original_file_path = os.path.join(args.input, original_filename)
                if os.path.exists(original_file_path):
                    zip_path_in_archive = os.path.join(safe_macro, safe_sub, new_filename)
                    zipf.write(original_file_path, zip_path_in_archive)
                    print(f"   ✅ {original_filename} -> {new_filename}")
                    
        print(f"✅ Fichier ZIP créé : {zip_path}")
        
    except Exception as e:
        print(f"⚠️ Excel/ZIP : {e}")


if __name__ == "__main__":
    main()
