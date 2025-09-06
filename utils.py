import streamlit as st
import requests
import json
import time
from datetime import datetime
import pandas as pd
import os
import pickle
import re
import io
import webbrowser
from urllib.parse import quote

# Imports optionnels pour l'export PDF/Word
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    from docx.shared import Inches
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# Configuration de l'API DeepSeek
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception as e:
    st.error("Clé API non configurée.")
    st.stop()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Modèle simplifié basé sur LEDR
SIMPLIFIED_CHECKLIST = {
    "Contexte du Poste et Environnement": [
        "Pourquoi ce poste est-il ouvert?",
        "Fourchette budgétaire (entre X et Y)",
        "Date de prise de poste souhaitée",
        "Équipe (taille, composition)",
        "Manager (poste, expertise, style)",
        "Collaborations internes/externes",
        "Lieux de travail et déplacements"
    ],
    "Missions et Responsabilités": [
        "Mission principale du poste",
        "Objectifs à atteindre (3-5 maximum)",
        "Sur quoi la performance sera évaluée?",
        "3-5 Principales tâches quotidiennes",
        "2 Tâches les plus importantes/critiques",
        "Outils informatiques à maitriser"
    ],
    "Compétences - Modèle KSA": [],  # Sera rempli dynamiquement
    "Profil et Formation": [
        "Expérience minimum requise",
        "Formation/diplôme nécessaire"
    ],
    "Stratégie de Recrutement": [
        "Pourquoi recruter maintenant?",
        "Difficultés anticipées",
        "Mot-clés cruciaux (CV screening)",
        "Canaux de sourcing prioritaires",
        "Plans B : Autres postes, Revoir certains critères...",
        "Exemple d'un profil cible sur LinkedIn",
        "Processus de sélection étape par étape"
    ]
}

# Modèle KSA dynamique
KSA_MODEL = {
    "Knowledge (Connaissances)": [
        "Ex. Connaissance du droit du travail",
        "Ex. Connaissance des outils ATS"
    ],
    "Skills (Savoir-faire)": [
        "Ex. Conduite d'entretien structuré",
        "Ex. Rédaction d'annonces attractives",
        "Ex. Négociation avec candidats"
    ],
    "Abilities (Aptitudes)": [
        "Ex. Analyse et synthèse",
        "Ex. Résilience face aux refus",
        "Ex. Gestion du stress"
    ]
}

# Templates prédéfinis
BRIEF_TEMPLATES = {
    "Template Vide": {category: {item: {"valeur": "", "importance": 3} for item in items} for category, items in SIMPLIFIED_CHECKLIST.items()},
    "Développeur Fullstack": {
        "Contexte du Poste et Environnement": {
            "Pourquoi ce poste est-il ouvert?": {"valeur": "Expansion de l'équipe technique", "importance": 3},
            "Fourchette budgétaire (entre X et Y)": {"valeur": "entre 15 000 et 20 000 DH", "importance": 3},
            "Date de prise de poste souhaitée": {"valeur": "Dès que possible", "importance": 3},
            "Équipe (taille, composition)": {"valeur": "5 développeurs, 1 PO, 1 UX", "importance": 3},
            "Manager (poste, expertise, style)": {"valeur": "Head of Engineering - management participatif", "importance": 3},
            "Collaborations internes/externes": {"valeur": "Équipe produit, marketing, support", "importance": 3},
            "Lieux de travail et déplacements": {"valeur": "Casablanca avec déplacements occasionnels", "importance": 3}
        },
        "Missions et Responsabilités": {
            "Mission principale du poste": {"valeur": "Développement et maintenance des applications web", "importance": 3},
            "Objectifs à atteindre (3-5 maximum)": {"valeur": "Livraison des features, qualité du code, performance", "importance": 3},
            "Sur quoi la performance sera évaluée?": {"valeur": "Velocity, qualité du code, satisfaction utilisateur", "importance": 3},
            "3-5 Principales tâches quotidiennes": {"valeur": "Code review, développement, debugging", "importance": 3},
            "2 Tâches les plus importantes/critiques": {"valeur": "Déploiements en production, résolution d'incidents", "importance": 3},
            "Outils informatiques à maitriser": {"valeur": "React, Node.js, MongoDB, AWS, Git", "importance": 3}
        },
        "Compétences - Modèle KSA": {},
        "Profil et Formation": {
            "Expérience minimum requise": {"valeur": "3+ ans en développement fullstack", "importance": 4},
            "Formation/diplôme nécessaire": {"valeur": "Bac+3 minimum en informatique", "importance": 3}
        },
        "Stratégie de Recrutement": {
            "Pourquoi recruter maintenant?": {"valeur": "Besoin pour lancement nouvelle feature", "importance": 3},
            "Difficultés anticipées": {"valeur": "Concurrence sur profils seniors", "importance": 3},
            "Mot-clés cruciaux (CV screening)": {"valeur": "React, Node.js, MongoDB, AWS", "importance": 4},
            "Canaux de sourcing prioritaires": {"valeur": "LinkedIn, Rekrute, cooptation", "importance": 3},
            "Plans B : Autres postes, Revoir certains critères...": {"valeur": "", "importance": 3},
            "Exemple d'un profil cible sur LinkedIn": {"valeur": "", "importance": 3},
            "Processus de sélection étape par étape": {"valeur": "Entretien technique + culture fit", "importance": 3}
        }
    }
}

# Données pour la cartographie de sourcing
SOURCING_MATRIX_DATA = {
    "Postes non vitaux / Marché abondant": {
        "exemples": ["Agent d'accueil", "Assistant administratif", "Téléconseiller", "Caissier"],
        "canaux": ["Annonces en ligne (Rekrute, Emploi.ma)", "Job boards locaux", "Réseaux sociaux", "ATS"],
        "objectif": "Volume, rapidité, coût réduit"
    },
    "Postes non vitaux / Marché pénurique": {
        "exemples": ["Technicien spécialisé", "Chauffeur poids lourd", "Ouvrier qualifié"],
        "canaux": ["Job boards spécialisés", "Partenariats écoles", "Cooptation renforcée"],
        "objectif": "Volume modéré, qualité acceptable, délai moyen"
    },
    "Postes vitaux / Marché abondant": {
        "exemples": ["Développeur web", "Commercial B2B", "Chef de projet junior"],
        "canaux": ["LinkedIn", "Réseau professionnel", "Événements métier", "Cooptation"],
        "objectif": "Qualité, adéquation culturelle, délai contrôlé"
    },
    "Postes vitaux / Marché pénurique": {
        "exemples": ["Data Scientist senior", "Expert cybersécurité", "Directeur financier"],
        "canaux": ["Chasse de tête", "Réseau personnel étendu", "Salons spécialisés", "Cabinets de recrutement"],
        "objectif": "Qualité exceptionnelle, patience, branding employeur"
    }
}

def load_saved_briefs():
    """Charge les briefs sauvegardés depuis un fichier"""
    try:
        if os.path.exists("saved_briefs.pkl"):
            with open("saved_briefs.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return {}

def load_sourcing_history():
    """Charge l'historique de sourcing"""
    try:
        if os.path.exists("sourcing_history.pkl"):
            with open("sourcing_history.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return []

def save_sourcing_history():
    """Sauvegarde l'historique de sourcing"""
    try:
        with open("sourcing_history.pkl", "wb") as f:
            pickle.dump(st.session_state.sourcing_history, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde historique: {e}")

def load_library_entries():
    """Charge les entrées de la bibliothèque interne"""
    try:
        if os.path.exists("library_entries.pkl"):
            with open("library_entries.pkl", "rb") as f:
                return pickle.load(f)
    except:
        pass
    return []

def save_library_entries():
    """Sauvegarde les entrées de la bibliothèque interne"""
    try:
        with open("library_entries.pkl", "wb") as f:
            pickle.dump(st.session_state.library_entries, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde bibliothèque: {e}")

def generate_automatic_brief_name():
    """Génère un nom de brief automatique selon le format jj/mm/aa-poste-manager-recruteur-affectation"""
    now = datetime.now()
    date_str = f"{now.strftime('%d')}/{now.strftime('%m')}/{now.strftime('%y')}"
    poste = st.session_state.get('poste_intitule', '').replace(' ', '-').lower()
    manager = st.session_state.get('manager_nom', '').replace(' ', '-').lower()
    recruteur = st.session_state.get('recruteur', '').lower()
    affectation = st.session_state.get('affectation_nom', '').replace(' ', '-').lower()
    return f"{date_str}-{poste}-{manager}-{recruteur}-{affectation}"

def init_session_state():
    """Initialise tous les états de session nécessaires"""
    saved_briefs = load_saved_briefs()
    sourcing_history = load_sourcing_history()
    library_entries = load_library_entries()
    
    defaults = {
        'brief_data': {category: {item: {"valeur": "", "importance": 3} for item in items} for category, items in SIMPLIFIED_CHECKLIST.items()},
        'ksa_data': {},
        'current_brief_name': "",
        'poste_intitule': "",
        'manager_nom': "",
        'recruteur': "Zakaria",
        'affectation_type': "Chantier",
        'affectation_nom': "",
        'saved_briefs': saved_briefs,
        'sourcing_history': sourcing_history,
        'library_entries': library_entries,
        'api_usage': {
            "total_tokens": 800000,
            "used_tokens": 0,
            "current_session_tokens": 0
        },
        'current_messages': [
            {"role": "system", "content": "Tu es un expert en recrutement qui aide à préparer des briefs managers. Tes réponses doivent être concises et pratiques."}
        ],
        'response_format': "tableau",
        'detail_level': "Concis",
        'max_tokens': 500,
        'brief_phase': "Gestion",
        'advice_visibility': {},
        'current_advice': None,
        'current_category': None,
        'current_item': None,
        'conversation_history': [],
        'show_advice_buttons': True,
        'brief_counter': 1,
        'ksa_competences': [],
        'comment_libre': "",
        'filtered_briefs': {},
        'show_filtered_results': False,
        'selected_question': "",
        'sourcing_matrix_data': SOURCING_MATRIX_DATA
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_briefs():
    """Sauvegarde les briefs dans un fichier"""
    try:
        with open("saved_briefs.pkl", "wb") as f:
            pickle.dump(st.session_state.saved_briefs, f)
    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")
        
def ask_deepseek(messages, max_tokens=500, response_format="text"):
    """Fonction pour interroger l'API DeepSeek"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    if response_format == "tableau" and messages:
        messages[-1]["content"] += "\n\nRéponds OBLIGATOIREMENT sous forme de tableau markdown avec des colonnes appropriées."
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            
            # 🔥 Mise à jour des compteurs
            st.session_state.api_usage["used_tokens"] += total_tokens
            st.session_state.api_usage["current_session_tokens"] += total_tokens
            if "token_counter" not in st.session_state:
                st.session_state["token_counter"] = 0
            st.session_state["token_counter"] += total_tokens
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "total_tokens": total_tokens
            }
        else:
            return {"content": f"❌ Erreur {response.status_code}", "total_tokens": 0}
            
    except Exception as e:
        return {"content": f"❌ Erreur: {str(e)}", "total_tokens": 0}
    
def ask_deepseek(messages, max_tokens=500, response_format="text"):
    """Fonction pour interroger l'API DeepSeek"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Modifier le prompt selon le format demandé
    if response_format == "tableau" and messages:
        messages[-1]["content"] += "\n\nRéponds OBLIGATOIREMENT sous forme de tableau markdown avec des colonnes appropriées."
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            
            st.session_state.api_usage["used_tokens"] += total_tokens
            st.session_state.api_usage["current_session_tokens"] += total_tokens
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "total_tokens": total_tokens
            }
        else:
            return {"content": f"❌ Erreur {response.status_code}", "total_tokens": 0}
            
    except Exception as e:
        return {"content": f"❌ Erreur: {str(e)}", "total_tokens": 0}

def generate_checklist_advice(category, item):
    """Génère des conseils pour remplir un item de la checklist"""
    format_instruction = " - RÉPONDS OBLIGATOIREMENT SOUS FORME DE LISTE À PUCES AVEC CHAQUE POINT SUR UNE NOUVELLE LIGNE"
    
    prompt = f"""
    En tant qu'expert en recrutement, donne des conseils PRATIQUES pour bien remplir cette partie du brief:
    Catégorie: {category}
    Question: {item}
    
    Fournis des conseils concrets sous forme de liste à puces:
    - Premier conseil pratique
    - Deuxième conseil avec exemple
    - Troisième conseil avec piège à éviter
    - etc.
    
    Réponds en français avec des conseils actionnables.{format_instruction}
    
    IMPORTANT: Utilise exclusivement le format liste à puces avec chaque point sur une nouvelle ligne.
    """
    
    messages = [
        {"role": "system", "content": "Tu es un coach en recrutement expérimenté. Réponds toujours avec des listes à puces bien formatées, chaque point sur une nouvelle ligne. Ne jamais utiliser de balises HTML."},
        {"role": "user", "content": prompt}
    ]
    
    response = ask_deepseek(messages, max_tokens=st.session_state.max_tokens)
    if "content" in response:
        cleaned_content = re.sub(r'<[^>]*>', '', response["content"])
        cleaned_content = re.sub(r'^(\s*)[•\-]\s*', r'\1- ', cleaned_content, flags=re.MULTILINE)
        return cleaned_content
    return "Erreur de génération"

def format_advice_response(text):
    """Formate spécifiquement les conseils pour un meilleur affichage"""
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        if re.match(r'^[\s]*[-•]\s', line):
            formatted_line = re.sub(r'^[\s]*[-•]\s*', '- ', line.strip())
            formatted_lines.append(formatted_line)
        elif line.strip():
            formatted_lines.append(line.strip())
    
    return '\n'.join(formatted_lines)

def render_ksa_section():
    """Affiche la section KSA avec possibilité d'ajouter/supprimer des compétences"""
    st.subheader("📊 Modèle KSA (Knowledge-Skills-Abilities)")
    
    # Hint pour expliquer la méthode KSA
    with st.expander("💡 Comment utiliser le modèle KSA"):
        st.markdown("""
        **Knowledge (Connaissances)** : Informations théoriques nécessaires
        - Ex: Connaissance du droit du travail, maîtrise d'Excel, connaissance des normes ISO
        
        **Skills (Savoir-faire)** : Compétences pratiques et techniques
        - Ex: Conduite d'entretien, négociation commerciale, programmation Python
        
        **Abilities (Aptitudes)** : Capacités comportementales et cognitives
        - Ex: Gestion du stress, leadership, capacité d'adaptation
        
        **Niveau requis** : 
        - Débutant : Notions de base, formation récente
        - Intermédiaire : Expérience pratique de 1-3 ans
        - Expert : Maîtrise avancée, plus de 3 ans d'expérience
        
        **Priorité** : 
        - Indispensable : Sans cette compétence, le candidat ne peut pas faire le poste
        - Souhaitable : Compétence qui serait un plus mais pas obligatoire
        
        **Évaluateur** : Qui évalue cette compétence 
        - Manager : Le futur manager évalue
        - Recruteur : Le recruteur évalue
        - Les deux : Évaluation partagée
        """)
    
    for category, examples in KSA_MODEL.items():
        st.markdown(f"**{category}**")
        
        # Ajouter de nouvelles compétences
        col1, col2 = st.columns([3, 1])
        with col1:
            new_comp = st.text_input(f"Ajouter compétence {category}", key=f"new_{category}")
        with col2:
            if st.button("➕ Ajouter", key=f"add_{category}") and new_comp:
                if category not in st.session_state.ksa_data:
                    st.session_state.ksa_data[category] = {}
                
                # Générer une clé unique si la compétence existe déjà
                comp_key = new_comp
                counter = 1
                while comp_key in st.session_state.ksa_data[category]:
                    comp_key = f"{new_comp}_{counter}"
                    counter += 1
                
                st.session_state.ksa_data[category][comp_key] = {
                    "niveau": "Intermédiaire",
                    "priorite": "Indispensable",
                    "evaluateur": "Manager"
                }
                st.rerun()
        
        # Afficher les compétences existantes
        if category in st.session_state.ksa_data:
            for comp_name, comp_data in st.session_state.ksa_data[category].items():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    st.write(comp_name)
                
                with col2:
                    niveau = st.selectbox(
                        "Niveau",
                        ["Débutant", "Intermédiaire", "Expert"],
                        index=["Débutant", "Intermédiaire", "Expert"].index(comp_data.get("niveau", "Intermédiaire")),
                        key=f"niveau_{category}_{comp_name}"
                    )
                    st.session_state.ksa_data[category][comp_name]["niveau"] = niveau
                
                with col3:
                    priorite = st.selectbox(
                        "Priorité",
                        ["Indispensable", "Souhaitable"],
                        index=["Indispensable", "Souhaitable"].index(comp_data.get("priorite", "Indispensable")),
                        key=f"priorite_{category}_{comp_name}"
                    )
                    st.session_state.ksa_data[category][comp_name]["priorite"] = priorite
                
                with col4:
                    evaluateur = st.selectbox(
                        "Évaluateur",
                        ["Manager", "Recruteur", "Les deux"],
                        index=["Manager", "Recruteur", "Les deux"].index(comp_data.get("evaluateur", "Manager")),
                        key=f"eval_{category}_{comp_name}"
                    )
                    st.session_state.ksa_data[category][comp_name]["evaluateur"] = evaluateur
                
                with col5:
                    if st.button("🗑️", key=f"del_{category}_{comp_name}"):
                        del st.session_state.ksa_data[category][comp_name]
                        st.rerun()

def filter_briefs(saved_briefs, filter_month=None, filter_recruteur=None, filter_poste=None, filter_manager=None):
    """Filtre les briefs selon les critères sélectionnés"""
    filtered = {}
    
    for name, data in saved_briefs.items():
        # Extraction du mois depuis le nom du brief (format jj/mm/aa-...)
        try:
            month = name.split('-')[0].split('/')[1] if '-' in name and '/' in name.split('-')[0] else None
        except:
            month = None
            
        # Application des filtres
        if filter_month and month != filter_month:
            continue
        if filter_recruteur and data.get('recruteur', '').lower() != filter_recruteur.lower():
            continue
        if filter_poste and filter_poste.lower() not in data.get('poste_intitule', '').lower():
            continue
        if filter_manager and filter_manager.lower() not in data.get('manager_nom', '').lower():
            continue
            
        filtered[name] = data
    
    return filtered

def generate_boolean_query(poste, synonymes, competences_obligatoires, competences_optionnelles, exclusions, localisation, secteur):
    """Génère une requête Boolean"""
    query_parts = []
    
    # Poste et synonymes
    if poste:
        poste_part = f'("{poste}"'
        if synonymes:
            for syn in synonymes.split(','):
                poste_part += f' OR "{syn.strip()}"'
        poste_part += ")"
        query_parts.append(poste_part)
    
    # Compétences obligatoires
    if competences_obligatoires:
        for comp in competences_obligatoires.split(','):
            query_parts.append(f'"{comp.strip()}"')
    
    # Compétences optionnelles
    if competences_optionnelles:
        opt_part = "("
        for comp in competences_optionnelles.split(','):
            opt_part += f'"{comp.strip()}" OR '
        opt_part = opt_part.rstrip(' OR ') + ")"
        query_parts.append(opt_part)
    
    # Localisation
    if localisation:
        query_parts.append(f'"{localisation}"')
    
    # Secteur
    if secteur:
        query_parts.append(f'"{secteur}"')
    
    # Assemblage de la requête
    query = " AND ".join(query_parts)
    
    # Exclusions
    if exclusions:
        for excl in exclusions.split(','):
            query += f' NOT "{excl.strip()}"'
    
    return query

def generate_xray_query(site, poste, mots_cles, localisation):
    """Génère une requête X-Ray Google"""
    site_urls = {
        "LinkedIn": "site:linkedin.com/in/",
        "GitHub": "site:github.com",
        "Indeed": "site:indeed.com"
    }
    
    query = f"{site_urls.get(site, 'site:linkedin.com/in/')} "
    
    if poste:
        query += f'"{poste}" '
    
    if mots_cles:
        for mot in mots_cles.split(','):
            query += f'"{mot.strip()}" '
    
    if localisation:
        query += f'"{localisation}" '
    
    return query.strip()

def generate_annonce(poste, competences):
    """Génère une annonce optimisée avec l'IA"""
    prompt = f"""
    Crée une annonce d'emploi attractive et concise pour le poste de {poste}.
    
    Compétences clés: {competences}
    
    Structure:
    1. Accroche percutante (1 phrase)
    2. Missions principales (3-4 points max)
    3. Profil recherché (compétences techniques et soft skills)
    4. Avantages et conditions (salaire, localisation, télétravail, etc.)
    
    Format: Texte concis, phrases courtes, ton dynamique.
    Public cible: Professionnels marocains.
    Localisation: Maroc.
    Salaire: En dirhams marocains (DH).
    """
    
    messages = [
        {"role": "system", "content": "Tu es un expert en rédaction d'annonces d'emploi. Tes réponses doivent être concises, attractives et adaptées au marché marocain."},
        {"role": "user", "content": prompt}
    ]
    
    response = ask_deepseek(messages, max_tokens=600)
    return response["content"] if "content" in response else "Erreur de génération"

def generate_accroche_inmail(url_linkedin, poste):
    """Génère une accroche InMail personnalisée"""
    prompt = f"""
    Crée une accroche InMail percutante pour contacter un candidat sur LinkedIn.
    
    Poste à pourvoir: {poste}
    Profil LinkedIn: {url_linkedin}
    
    L'accroche doit:
    - Être personnalisée et pertinente
    - Mentionner le poste et l'entreprise brièvement
    - Proposer un appel ou échange
    - Être courte (4-5 lignes max)
    - Ton professionnel mais chaleureux
    
    Format: Message direct, sans formules trop formelles.
    """
    
    messages = [
        {"role": "system", "content": "Tu es un expert en recrutement et communication professionnelle. Crée des messages courts, personnalisés et engageants."},
        {"role": "user", "content": prompt}
    ]
    
    response = ask_deepseek(messages, max_tokens=300)
    return response["content"] if "content" in response else "Erreur de génération"

def export_brief_pdf():
    """Exporte le brief en PDF"""
    if not PDF_AVAILABLE:
        st.error("Module reportlab non installé. Utilisez : pip install reportlab")
        return None
    
    try:
        # Créer un buffer
        buffer = io.BytesIO()
        
        # Créer le document PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.darkblue)
        story.append(Paragraph(f"Brief Recrutement - {st.session_state.poste_intitule}", title_style))
        story.append(Spacer(1, 20))
        
        # Informations générales
        story.append(Paragraph("Informations Générales", styles['Heading2']))
        general_info = [
            ["Poste", st.session_state.poste_intitule],
            ["Manager", st.session_state.manager_nom],
            ["Recruteur", st.session_state.recruteur],
            ["Affectation", f"{st.session_state.affectation_type} - {st.session_state.affectation_nom}"]
        ]
        
        table = Table(general_info, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Sections du brief
        for category, items in st.session_state.brief_data.items():
            if category != "Compétences - Modèle KSA":
                story.append(Paragraph(category, styles['Heading2']))
                
                for item, data in items.items():
                    if data['valeur']:
                        story.append(Paragraph(f"<b>{item}:</b>", styles['Normal']))
                        story.append(Paragraph(data['valeur'], styles['Normal']))
                        story.append(Spacer(1, 10))
                
                story.append(Spacer(1, 15))
        
        # Section KSA
        if st.session_state.ksa_data:
            story.append(Paragraph("Modèle KSA", styles['Heading2']))
            
            for category, competences in st.session_state.ksa_data.items():
                story.append(Paragraph(category, styles['Heading3']))
                
                ksa_data = [["Compétence", "Niveau", "Priorité", "Évaluateur"]]
                for comp, details in competences.items():
                    ksa_data.append([comp, details['niveau'], details['priorite'], details['evaluateur']])
                
                if len(ksa_data) > 1:
                    ksa_table = Table(ksa_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
                    ksa_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(ksa_table)
                    story.append(Spacer(1, 15))
        
        # Commentaire libre
        if st.session_state.comment_libre:
            story.append(Paragraph("Commentaires", styles['Heading2']))
            story.append(Paragraph(st.session_state.comment_libre, styles['Normal']))
        
        # Construire le PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer
    
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {e}")
        return None

def export_brief_word():
    """Exporte le brief en Word"""
    if not WORD_AVAILABLE:
        st.error("Module python-docx non installé. Utilisez : pip install python-docx")
        return None
    
    try:
        doc = Document()
        
        # Titre
        title = doc.add_heading(f"Brief Recrutement - {st.session_state.poste_intitule}", 0)
        
        # Informations générales
        doc.add_heading("Informations Générales", level=1)
        
        table = doc.add_table(rows=4, cols=2)
        table.style = 'Light Shading Accent 1'
        
        cells = [
            ("Poste", st.session_state.poste_intitule),
            ("Manager", st.session_state.manager_nom),
            ("Recruteur", st.session_state.recruteur),
            ("Affectation", f"{st.session_state.affectation_type} - {st.session_state.affectation_nom}")
        ]
        
        for i, (key, value) in enumerate(cells):
            table.cell(i, 0).text = key
            table.cell(i, 1).text = value
        
        # Sections du brief
        for category, items in st.session_state.brief_data.items():
            if category != "Compétences - Modèle KSA":
                doc.add_heading(category, level=1)
                
                for item, data in items.items():
                    if data['valeur']:
                        doc.add_heading(item, level=2)
                        doc.add_paragraph(data['valeur'])
        
        # Section KSA
        if st.session_state.ksa_data:
            doc.add_heading("Modèle KSA", level=1)
            
            for category, competences in st.session_state.ksa_data.items():
                doc.add_heading(category, level=2)
                
                if competences:
                    ksa_table = doc.add_table(rows=len(competences)+1, cols=4)
                    ksa_table.style = 'Light Shading Accent 1'
                    
                    # En-têtes
                    headers = ["Compétence", "Niveau", "Priorité", "Évaluateur"]
                    for i, header in enumerate(headers):
                        ksa_table.cell(0, i).text = header
                    
                    # Données
                    for i, (comp, details) in enumerate(competences.items(), 1):
                        ksa_table.cell(i, 0).text = comp
                        ksa_table.cell(i, 1).text = details['niveau']
                        ksa_table.cell(i, 2).text = details['priorite']
                        ksa_table.cell(i, 3).text = details['evaluateur']
        
        # Commentaire libre
        if st.session_state.comment_libre:
            doc.add_heading("Commentaires", level=1)
            doc.add_paragraph(st.session_state.comment_libre)
        
        # Sauvegarder dans un buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    
    except Exception as e:
        st.error(f"Erreur lors de la génération du Word: {e}")
        return None

