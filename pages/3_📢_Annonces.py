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
# Vérification de la connexion
if not st.session_state.get("logged_in", False):
    st.stop()
# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# Initialiser les variables manquantes
defaults = {
    "annonces": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Annonces",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📢  Gestion des annonces")

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
            st.success("PDF extrait avec succès !")
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

# Informations de base
st.subheader("Informations générales")
col_info1, col_info2 = st.columns(2)
with col_info1:
    poste_final = st.text_input("Poste*", help="Ex: Directeur des Projets BTP")
with col_info2:
    localisation_finale = st.text_input("Localisation*", help="Ex: Casablanca, Rabat, Tanger")

# Entreprise par défaut (TGCC)
entreprise = "TGCC"

# Bouton pour générer via IA
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    st.markdown('<div class="red-generate-button">', unsafe_allow_html=True)
    generate_button = st.button("💡 Générer l'annonce via IA", 
                              width="stretch",
                              key="btn_generer_annonce")
    st.markdown('</div>', unsafe_allow_html=True)

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
if "annonce_contenu" not in st.session_state:
    st.session_state["annonce_contenu"] = ""

contenu = st.text_area("Contenu de l'annonce (généré ou manuel)", 
                       key="annonce_contenu", 
                       height=300, 
                       value=st.session_state.get("annonce_contenu", ""),
                       help="Contenu de l'annonce généré par l'IA ou saisi manuellement")

# Bouton de sauvegarde
col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
with col_save2:
    if st.button("💾 Sauvegarder l'annonce", type="primary", width="stretch", key="btn_sauvegarder_annonce"):
        if poste_final and entreprise and contenu and localisation_finale:
            # Préparer les données pour Google Sheets
            annonce_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "poste": poste_final,
                "entreprise": entreprise,
                "localisation": localisation_finale,
                "plateforme": plateforme,
                "format_type": plateforme,
                "contenu": contenu,
                "fiche_text": fiche_text if fiche_text else "",
                "type_contrat": locals().get('type_contrat', '') if input_mode == "Saisie manuelle" else "",
                "niveau_experience": locals().get('niveau_experience', '') if input_mode == "Saisie manuelle" else "",
                "formation_requise": locals().get('formation_requise', '') if input_mode == "Saisie manuelle" else "",
                "affectation": locals().get('affectation', '') if input_mode == "Saisie manuelle" else "",
                "competences_techniques": locals().get('competences_techniques', '') if input_mode == "Saisie manuelle" else "",
                "missions_principales": locals().get('missions_principales', '') if input_mode == "Saisie manuelle" else "",
                "soft_skills": locals().get('soft_skills', '') if input_mode == "Saisie manuelle" else "",
                "date_creation": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Sauvegarder dans Google Sheets
            if utils.save_annonce_to_gsheet(annonce_data):
                st.success("✅ Annonce sauvegardée dans Google Sheets avec succès !")
            else:
                st.warning("⚠️ Erreur lors de la sauvegarde dans Google Sheets, sauvegarde locale uniquement.")
            
            # Sauvegarder aussi localement
            annonce = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "poste": poste_final,
                "entreprise": entreprise,
                "localisation": localisation_finale,
                "contenu": contenu,
                "plateforme": plateforme,
            }
            st.session_state.annonces.append(annonce)
            
            # Reset pour nouvelle saisie (protection contre erreurs Streamlit API)
            try:
                st.session_state["annonce_contenu"] = ""
            except Exception:
                # Si Streamlit refuse la modification (ex: contexte restreint), on ignore pour éviter le plantage
                pass
        else:
            st.warning("⚠️ Merci de remplir tous les champs obligatoires")

st.divider()

# -------------------- Liste des annonces --------------------
st.subheader("📋 Annonces sauvegardées")

if not st.session_state.annonces:
    st.info("Aucune annonce sauvegardée pour le moment.")
else:
    for i, annonce in enumerate(st.session_state.annonces[::-1]):  # affichage dernière en premier
        with st.expander(f"{annonce['date']} - {annonce['poste']} - {annonce['plateforme']}", expanded=False):
            st.write(f"**Entreprise :** {annonce['entreprise']}")
            st.write(f"**Localisation :** {annonce['localisation'] or 'Non spécifiée'}")
            st.write("**Contenu :**")
            st.text_area("Contenu", annonce["contenu"], height=120, key=f"annonce_contenu_{i}", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer", key=f"delete_annonce_{i}"):
                    st.session_state.annonces.pop(len(st.session_state.annonces) - 1 - i)
                    st.success("Annonce supprimée.")
                    st.rerun()
            with col2:
                st.download_button(
                    "⬇️ Exporter",
                    data=f"Poste: {annonce['poste']}\nEntreprise: {annonce['entreprise']}\nLocalisation: {annonce['localisation']}\nPlateforme: {annonce['plateforme']}\n\n{annonce['contenu']}",
                    file_name=f"annonce_{annonce['poste']}_{i}.txt",
                    mime="text/plain",
                    key=f"download_annonce_{i}"
                )