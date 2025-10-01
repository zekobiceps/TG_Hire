import streamlit as st
import sys
import os
import importlib.util
from datetime import datetime
try:
    import pypdf  # Alternative moderne à PyPDF2
except ImportError:
    st.error("Veuillez installer pypdf : pip install pypdf")
    st.stop()
from io import BytesIO
# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

if "annonces" not in st.session_state or not st.session_state.annonces:
    try:
        records = utils.load_annonces_from_gsheet()
        st.session_state.annonces = []
        for r in records:
            st.session_state.annonces.append({
                "date": r.get("timestamp", ""),
                "poste": r.get("poste", ""),
                "entreprise": r.get("entreprise", ""),
                "localisation": r.get("localisation", ""),
                "contenu": r.get("contenu", ""),
                "plateforme": r.get("plateforme", r.get("format_type", ""))
            })
    except Exception as e:
        st.session_state.annonces = []
        st.warning(f"Erreur lors du chargement initial des annonces : {e}")

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Annonces",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📢  Gestion des annonces")

# Bloc Informations générales déplacé ici pour être en haut
with st.container():
    st.subheader("Informations générales")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        poste_final = st.text_input("Poste*", help="Ex: Directeur des Projets BTP")
    with col_info2:
        localisation_finale = st.text_input("Localisation*", help="Ex: Casablanca, Rabat, Tanger")
    entreprise = "TGCC"  # constante

# --- Debug: test de connexion Google Sheets (visible si st.secrets['DEBUG']==True ou param ?debug=true)
debug_mode = False
try:
    debug_mode = bool(st.secrets.get("DEBUG", False))
except Exception:
    debug_mode = False
if not debug_mode:
    # allow quick URL override: ?debug=true
    params = st.query_params
    if params.get("debug", ["false"])[0].lower() == "true":
        debug_mode = True

if debug_mode:
    st.warning("DEBUG MODE: Bouton de test Google Sheets activé")
    cold1, cold2 = st.columns([1, 3])
    with cold2:
        if st.button("🔎 Tester connexion Annonces → Google Sheets", key="debug_test_sheets"):
            try:
                gc = utils.get_annonces_gsheet_client()
                if not gc:
                    st.error("Client gspread non initialisé (vérifiez GSPREAD_AVAILABLE et st.secrets)")
                else:
                    st.success("Client gspread initialisé")
                    try:
                        records = utils.load_annonces_from_gsheet()
                        st.success(f"Chargé {len(records)} enregistrements depuis la feuille Annonces")
                        if len(records) > 0:
                            st.json(records[0])
                    except Exception as e:
                        st.error(f"Erreur lors du chargement des annonces: {e}")
            except Exception as e:
                st.error(f"Erreur lors du test Google Sheets: {e}")

# -------------------- Styles CSS --------------------
st.markdown("""
    <style>
    .red-button button {
        background-color: #ff4444 !important;
        color: white !important;
        border: 1px solid #ff4444 !important;
        font-weight: bold !important;
    }
    .red-button button:hover {
        background-color: #cc0000 !important;
        border: 1px solid #cc0000 !important;
    }
    .red-generate-button button {
        background-color: #ff4444 !important;
        color: white !important;
        border: 1px solid #ff4444 !important;
        font-weight: bold !important;
    }
    .red-generate-button button:hover {
        background-color: #cc0000 !important;
        border: 1px solid #cc0000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- Formulaire principal --------------------
# Choix de la plateforme
plateforme = st.selectbox("Plateforme cible", ["JOBZYN", "TGCC", "LinkedIn"], key="annonce_plateforme")

# Afficher la saisie manuelle uniquement pour TGCC
if plateforme == "TGCC":
    input_mode = st.radio("Mode d'entrée des infos du poste", ["Upload PDF fiche de poste", "Saisie manuelle"], key="input_mode")
else:
    input_mode = "Upload PDF fiche de poste"

fiche_text = ""

if input_mode == "Upload PDF fiche de poste":
    uploaded_file = st.file_uploader("Téléchargez la fiche de poste (PDF)", type="pdf", key="pdf_upload")
    if uploaded_file:
        try:
            pdf_reader = pypdf.PdfReader(BytesIO(uploaded_file.read()))
            fiche_text = ""
            for page in pdf_reader.pages:
                fiche_text += page.extract_text() + "\n"
            # note: removed success toast to reduce noisy messages
        except Exception as e:
            st.error(f"Erreur lors de l'extraction du PDF : {e}")
else:
    # Saisie manuelle avec 4 colonnes (uniquement pour TGCC)
    st.subheader("Informations du poste")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        type_contrat = st.selectbox("Type de contrat*", 
            ["CDI", "CDD", "Contrat de chantier", "Stage"],
            help="Sélectionnez le type de contrat")
        niveau_experience = st.selectbox("Niveau d'expérience*",
            ["0-2 ans", "3-5 ans", "5-10 ans", "10+ ans"],
            help="Nombre d'années d'expérience requis")
        formation_requise = st.selectbox("Formation requise*",
            ["Bac", "Bac+2", "Bac+3", "Bac+5"],
            help="Niveau de formation minimum")
        
    with col2:
        affectation = st.text_input("Affectation*", help="Ex: Chantier Mohammed VI, Direction Technique, Projet Autoroute")
        date_demarrage = st.text_input("Date de démarrage", help="Ex: Dès que possible, Septembre 2024")
        salaire = st.text_input("Salaire indicatif", help="Ex: Selon profil et expérience")
        
    with col3:
        competences_techniques = st.text_area("Compétences techniques*", 
            help="Ex: Maîtrise d'AutoCAD, gestion de projet, normes BTP, lecture de plans")
        langues = st.multiselect("Langues requises",
            ["Arabe", "Français", "Anglais", "Espagnol"],
            help="Langues nécessaires pour le poste")
        
    with col4:
        missions_principales = st.text_area("Missions principales*", 
            help="Ex: Gestion de chantier, coordination d'équipe, suivi budget, contrôle qualité")
        soft_skills = st.text_area("Soft skills*",
            help="Ex: Leadership, rigueur, autonomie, gestion du stress")
        deplacement = st.selectbox("Déplacements requis",
            ["Non", "Occasionnels", "Fréquents", "Permanent"],
            help="Fréquence des déplacements")

    # Section contexte et entreprise intégrée
    st.subheader("Informations complémentaires")
    col_ctx1, col_ctx2 = st.columns(2)
    
    with col_ctx1:
        contexte_recrutement = st.text_area("Contexte du recrutement*",
            help="Ex: Expansion de l'entreprise sur de nouveaux marchés, nouveau chantier")
        description_equipe = st.text_area("Description de l'équipe",
            help="Ex: Équipe de 15 ingénieurs expérimentés")
        
    with col_ctx2:
        valeurs_entreprise = st.text_area("Valeurs de TGCC*", 
            value="Qualité, Intégrité, Excellence, Ambition",
            help="Valeurs fondamentales de l'entreprise")
        avantages = st.text_area("Avantages proposés",
            help="Ex: Mutuelle, transport, formation, évolution de carrière")

    fiche_text = f"""
    Type de contrat: {type_contrat}
    Niveau d'expérience: {niveau_experience}
    Formation requise: {formation_requise}
    Affectation: {affectation}
    Date de démarrage: {date_demarrage}
    Salaire: {salaire}
    Compétences techniques: {competences_techniques}
    Langues: {', '.join(langues)}
    Missions principales: {missions_principales}
    Soft skills: {soft_skills}
    Déplacements: {deplacement}
    Contexte du recrutement: {contexte_recrutement}
    Description de l'équipe: {description_equipe}
    Valeurs de TGCC: {valeurs_entreprise}
    Avantages: {avantages}
    """

## (Section Informations générales déplacée en haut)

# (Bloc formulaire principal dupliqué supprimé - on conserve la première instance définie plus haut)

# Bouton pour générer via IA (pleine largeur)
generate_button = st.button("💡 Générer l'annonce via IA", type="primary", use_container_width=True, key="btn_generer_annonce")

# Génération IA avec spinner
if generate_button:
    if fiche_text and poste_final and entreprise and localisation_finale:
        # Prompt base
        prompt_base = f"Basé sur cette fiche de poste : {fiche_text}\n\nGénère une annonce complète pour le poste {poste_final} chez {entreprise} à {localisation_finale}."

        if plateforme == "JOBZYN":
            prompt = prompt_base + """
            Structure obligatoire (sans titres en gras, directement le contenu):
            
            Introduction au poste:
            [Description concise du poste et son importance]
            
            Votre rôle:
            [Liste à puces des missions principales, sans sous-titres]
            
            Votre équipe:
            [Description de l'environnement de travail et de l'équipe]
            
            Vos qualifications:
            [Liste à puces des compétences et expériences requises]
            
            Avantages:
            • Une formation continue adaptée grâce à TGCC Academy qui vous accompagne par des formations physiques et digitales.
            • Un environnement de travail dynamique Vous êtes entouré(e) d'une équipe jeune et passionnée.
            • Vous êtes au cœur de la réussite de nos projets.
            • Une culture d'excellence Environnement stimulant et bienveillant favorisant le dépassement de soi.
            
            Processus de recrutement:
            • Analyse préalable de votre candidature
            • Entretien de préqualification téléphonique  
            • Entretien technique
            • Entretien RH
            
            Rends-la attractive et concise.
            """
        elif plateforme == "LinkedIn":
            prompt = prompt_base + """
            STRUCTURE OBLIGATOIRE POUR LINKEDIN:

            Format LinkedIn court et percutant avec hashtags:

            #TGCCrecrute

            En tant que [Titre du poste], vous [brève description des missions principales, en une phrase concise et variée selon le poste].

            Offre complète disponible ici : [lien vers l'offre détaillée]

            L'équipe Développement RH reste à votre écoute.

            #Recrutement #BTP #Carrière #Construction #RH #capitalhumain #developpementRH #recruter 
            #OpportunitéProfessionnelle #cv #candidature #maroc #Innovation #rejoigneznous #joinus 
            #ConstruisonsEnsemble #Bâtiment #TGCC #Building #afrique #RecrutementBTP #géniecivil 
            #Emploigéniecivil #Depuisplusde30ans #annonces #bâtiment #ingénierie #ProjetsAmbitieux #recrute

            [Ajouter 4 hashtags spécifiques au poste en relation avec le métier]

            RÈGLES STRICTES:
            - Format court et percutant pour LinkedIn
            - Varier les formulations pour ne pas être répétitif
            - Phrases courtes et impactantes
            - Hashtags optimisés pour le recrutement BTP
            - Ton professionnel mais engageant
            - Ajouter 4 hashtags spécifiques au poste
            """
        else:  # TGCC
            prompt = prompt_base + """
            STRUCTURE OBLIGATOIRE (sans titres en gras, directement le contenu):

            [Phrase d'accroche directe et engageante sans mentionner "Accroche engageante", adaptée au secteur BTP]

            Pourquoi TGCC a besoin de vous:
            [Contexte business adapté au secteur BTP marocain]

            Ce que vous ferez:
            [Liste à puces des missions quotidiennes, sans sous-titres]

            Votre environnement:
            [Description de l'équipe et de la culture d'entreprise basée sur: Qualité, Intégrité, Excellence, Ambition]

            Ce que nous recherchons:
            [Liste à puces des compétences clés]

            Ce poste n'est pas pour vous si...
            [Filtre naturel adapté au profil]

            Avantages:
            • Une formation continue adaptée grâce à TGCC Academy qui vous accompagne par des formations physiques et digitales.
            • Un environnement de travail dynamique Vous êtes entouré(e) d'une équipe jeune et passionnée.
            • Vous êtes au cœur de la réussite des projets de TGCC.
            • Une culture d'excellence et d'intrapreneuriat Environnement stimulant et bienveillant favorisant le dépassement de soi.

            Processus de recrutement:
            • Analyse préalable de votre candidature
            • Entretien de préqualification téléphonique  
            • Entretien technique
            • Entretien RH

            RÈGLES STRICTES:
            - Pas de titres de sections visibles
            - Pas de mention du salaire dans les avantages
            - Utiliser toujours "TGCC" pour parler de l'entreprise
            - Phrases directes et naturelles
            - Formatage propre avec des listes à puces
            - Ton authentique et transparent
            - Pas de mots anglais, tout en français
            - Phrase d'accroche directe sans être une question
            """

        # Appel à l'IA avec spinner
        with st.spinner("🔄 Génération en cours par l'IA... Veuillez patienter."):
            try:
                generated_contenu = utils.deepseek_generate(prompt)
                # Nettoyer le contenu généré
                generated_contenu = generated_contenu.replace('**', '')  # Enlever les **
                generated_contenu = generated_contenu.replace('* ', '• ')  # Uniformiser les puces
                generated_contenu = generated_contenu.replace('challenging', 'stimulant')  # Traduction français
                generated_contenu = generated_contenu.replace('Challenging', 'Stimulant')  # Traduction français
                
                # Nettoyer les sections spécifiques
                if plateforme == "TGCC":
                    # Enlever "Informations clés:" et le bloc qui suit
                    lines = generated_contenu.split('\n')
                    cleaned_lines = []
                    skip_next_lines = False
                    for line in lines:
                        if 'Informations clés:' in line or 'Accroche engageante:' in line:
                            skip_next_lines = True
                            continue
                        if skip_next_lines and line.strip() == '':
                            skip_next_lines = False
                            continue
                        if not skip_next_lines:
                            cleaned_lines.append(line)
                    generated_contenu = '\n'.join(cleaned_lines)
                
                # Corriger les retours à la ligne dans les avantages
                lines = generated_contenu.split('\n')
                cleaned_lines = []
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith('•') and i+1 < len(lines) and not lines[i+1].strip().startswith('•'):
                        # Fusionner avec la ligne suivante si ce n'est pas une nouvelle puce
                        next_line = lines[i+1].strip()
                        if next_line and not next_line.startswith('•'):
                            line += ' ' + next_line
                            i += 1
                    cleaned_lines.append(line)
                    i += 1
                generated_contenu = '\n'.join(cleaned_lines)
                
                st.session_state["annonce_contenu"] = generated_contenu
                st.success("✅ Annonce générée avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de la génération IA : {e}")
    else:
        st.warning("⚠️ Merci de remplir tous les champs obligatoires (marqués d'un *)")

# Textarea pour le contenu
st.session_state.setdefault("annonce_contenu", "")
contenu = st.text_area("Contenu de l'annonce (généré ou manuel)", 
                       key="annonce_contenu", 
                       height=300, 
                       help="Contenu de l'annonce généré par l'IA ou saisi manuellement")

if st.button("💾 Sauvegarder l'annonce", type="primary", use_container_width=True, key="btn_sauvegarder_annonce"):
        if poste_final and entreprise and contenu and localisation_finale:
            # Préparer les données pour Google Sheets
            annonce_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "poste": poste_final,
                "entreprise": entreprise,
                "localisation": localisation_finale,
                "plateforme": plateforme,
                "format_type": plateforme,
                "contenu": contenu
            }
            
            # Sauvegarder dans Google Sheets (obligatoire)
            success = utils.save_annonce_to_gsheet(annonce_data)
            if success:
                st.success("✅ Annonce sauvegardée dans Google Sheets avec succès !")
                # Recharger la liste des annonces depuis Google Sheets pour affichage
                try:
                    records = utils.load_annonces_from_gsheet()
                    # Convertir les records (dicts) vers le format local attendu pour l'affichage
                    st.session_state.annonces = []
                    for r in records:
                        st.session_state.annonces.append({
                            "date": r.get("timestamp", ""),
                            "poste": r.get("poste", ""),
                            "entreprise": r.get("entreprise", ""),
                            "localisation": r.get("localisation", ""),
                            "contenu": r.get("contenu", ""),
                            "plateforme": r.get("plateforme", r.get("format_type", ""))
                        })
                except Exception as e:
                    st.warning(f"⚠️ Annonce sauvegardée mais impossible de recharger la liste depuis Sheets: {e}")

                # Reset pour nouvelle saisie (protection contre erreurs Streamlit API)
                try:
                    st.session_state["annonce_contenu"] = ""
                except Exception:
                    pass
            else:
                st.error("❌ Erreur lors de la sauvegarde dans Google Sheets — l'annonce n'a PAS été enregistrée.")
        else:
            st.warning("⚠️ Merci de remplir tous les champs obligatoires")

st.divider()



# -------------------- Sidebar Statistiques --------------------
with st.sidebar:
    # Titre réduit de ~20%
    st.markdown("<h2 style='font-size:1.6rem;margin-bottom:0.4rem;'>📊 Annonces créées</h2>", unsafe_allow_html=True)
    nb_annonces = len(st.session_state.annonces)
    # Nombre centré en rouge vif
    st.markdown(f"<div style='text-align:center;margin:0.3rem 0 0.6rem;'>" \
                f"<span style='font-size:2.4rem;font-weight:800;color:#C40000;'>{nb_annonces}</span>" \
                f"</div>", unsafe_allow_html=True)
    st.divider()

# -------------------- Liste des annonces --------------------
st.subheader("📋 Annonces sauvegardées")


# Barre de recherche
search_term = st.text_input("🔎 Rechercher une annonce par poste, entreprise ou affectation", key="search_annonce")

filtered_annonces = [a for a in st.session_state.annonces[::-1] if not search_term or search_term.lower() in a['poste'].lower() or search_term.lower() in a['entreprise'].lower() or search_term.lower() in a['localisation'].lower()]

if not filtered_annonces:
    st.info("Aucune annonce sauvegardée pour le moment.")
else:
    for i, annonce in enumerate(filtered_annonces):
        with st.expander(f"{annonce['date']} - {annonce['poste']} - {annonce['plateforme']}", expanded=False):
            st.write(f"**Entreprise :** {annonce['entreprise']}")
            st.write(f"**Affectation (Nom de la direction/chantier) :** {annonce['localisation'] or 'Non spécifiée'}")
            st.write("**Contenu :**")
            st.text_area("Contenu", annonce["contenu"], height=120, key=f"annonce_contenu_{i}", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"delete_annonce_{i}"):
                    # Suppression réelle dans Google Sheets
                    try:
                        utils.delete_annonce_from_gsheet(annonce)
                        st.success("Annonce supprimée de la base de données.")
                    except Exception as e:
                        st.error(f"Erreur lors de la suppression dans Google Sheets : {e}")
                    # Suppression locale
                    st.session_state.annonces.pop(len(filtered_annonces) - 1 - i)
                    st.rerun()
            with col2:
                st.download_button(
                    "⬇️ Exporter",
                    data=f"Poste: {annonce['poste']}\nEntreprise: {annonce['entreprise']}\nAffectation: {annonce['localisation']}\nPlateforme: {annonce['plateforme']}\n\n{annonce['contenu']}",
                    file_name=f"annonce_{annonce['poste']}_{i}.txt",
                    mime="text/plain",
                    key=f"download_annonce_{i}"
                )

# -------------------- Nouvelle section : Création d'annonce --------------------