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

st.title("📢 Gestion des annonces")

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
    </style>
""", unsafe_allow_html=True)

# -------------------- Formulaire principal --------------------
with st.form(key='annonce_form'):
    
    # Choix de la plateforme
    plateforme = st.selectbox("Plateforme cible", ["JOBZYN", "TGCC", "LinkedIn"], key="annonce_plateforme")
    
    # Mode d'entrée : PDF ou manuel (uniquement pour TGCC)
    if plateforme == "TGCC":
        input_mode = st.radio("Mode d'entrée des infos du poste", ["Upload PDF fiche de poste", "Saisie manuelle"], key="input_mode")
    else:
        input_mode = "Upload PDF fiche de poste"  # Pour JOBZYN et LinkedIn, uniquement PDF

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
        # Saisie manuelle avec 4 colonnes
        st.subheader("Informations du poste")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            poste = st.text_input("Poste concerné*", help="Ex: Directeur Projets, Ingénieur BTP, Chef de Chantier")
            type_contrat = st.selectbox("Type de contrat*", 
                ["CDI", "CDD", "Contrat de chantier", "Stage", "Alternance", "Freelance"],
                help="Sélectionnez le type de contrat")
            niveau_experience = st.selectbox("Niveau d'expérience*",
                ["Débutant (0-2 ans)", "Intermédiaire (3-5 ans)", "Confirmé (5-10 ans)", "Expert (10+ ans)"],
                help="Niveau d'expérience requis")
            formation_requise = st.selectbox("Formation requise*",
                ["Bac", "Bac+2", "Bac+3", "Bac+5", "Doctorat", "Spécialisation BTP"],
                help="Niveau de formation minimum")
            
        with col2:
            localisation = st.text_input("Localisation*", help="Ex: Casablanca, Rabat, Tanger, Marrakech")
            affectation = st.text_input("Affectation*", help="Ex: Chantier Mohammed VI, Direction Technique, Projet Autoroute")
            date_demarrage = st.text_input("Date de démarrage", help="Ex: Dès que possible, Septembre 2024")
            salaire = st.text_input("Salaire indicatif", help="Ex: Selon profil et expérience")
            
        with col3:
            competences_techniques = st.text_area("Compétences techniques*", 
                help="Ex: Maîtrise d'AutoCAD, gestion de projet, normes BTP, lecture de plans")
            langues = st.multiselect("Langues requises",
                ["Arabe", "Français", "Anglais", "Espagnol"],
                help="Langues nécessaires pour le poste")
            permis = st.multiselect("Permis requis",
                ["Permis B", "Permis C", "Permis D", "CACES", "Habilitation électrique"],
                help="Permis et habilitations nécessaires")
            
        with col4:
            missions_principales = st.text_area("Missions principales*", 
                help="Ex: Gestion de chantier, coordination d'équipe, suivi budget, contrôle qualité")
            soft_skills = st.text_area("Soft skills*",
                help="Ex: Leadership, rigueur, autonomie, gestion du stress")
            deplacement = st.selectbox("Déplacements requis",
                ["Non", "Occasionnels", "Fréquents", "Permanent"],
                help="Fréquence des déplacements")

        # Section contexte et entreprise
        st.subheader("Contexte et entreprise")
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
        Poste: {poste}
        Type de contrat: {type_contrat}
        Niveau d'expérience: {niveau_experience}
        Formation requise: {formation_requise}
        Localisation: {localisation}
        Affectation: {affectation}
        Date de démarrage: {date_demarrage}
        Salaire: {salaire}
        Compétences techniques: {competences_techniques}
        Langues: {', '.join(langues)}
        Permis: {', '.join(permis)}
        Missions principales: {missions_principales}
        Soft skills: {soft_skills}
        Déplacements: {deplacement}
        Contexte du recrutement: {contexte_recrutement}
        Description de l'équipe: {description_equipe}
        Valeurs de TGCC: {valeurs_entreprise}
        Avantages: {avantages}
        """

    # Informations de base
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        poste_final = st.text_input("Poste*", value=poste if 'poste' in locals() else "", 
                                  help="Ex: Directeur des Projets BTP")
    with col_info2:
        localisation_finale = st.text_input("Localisation*", value=localisation if 'localisation' in locals() else "", 
                                          help="Ex: Casablanca, Rabat, Tanger")
        entreprise = st.text_input("Entreprise*", value="TGCC", disabled=True)

    # Bouton pour générer via IA
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        generate_button = st.form_submit_button("💡 Générer l'annonce via IA", 
                                              use_container_width=True,
                                              type="secondary")

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
                • Une formation continue adaptée Chez TGCC, vous montez en compétences selon vos besoins.
                • Un environnement de travail dynamique Vous êtes entouré(e) d'une équipe jeune et passionnée.
                • Des responsabilités significatives Vous êtes au cœur de la réussite de nos projets.
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

                En tant que [Poste en gras avec emoji si pertinent], vous [mission principale en une phrase concise et impactante].

                📍 Localisation: [Ville]
                🏢 Type de contrat: [Type de contrat]
                🎯 Profil recherché: [2-3 caractéristiques clés du profil]

                Principales missions:
                • [Mission 1 concise]
                • [Mission 2 concise] 
                • [Mission 3 concise]

                Le poste est fait pour vous si:
                ✅ [Critère 1]
                ✅ [Critère 2]
                ✅ [Critère 3]

                Chez TGCC, nous vous offrons:
                ✨ [Avantage 1]
                ✨ [Avantage 2] 
                ✨ [Avantage 3]

                📞 L'équipe Développement RH est à votre écoute.

                hashtag#[PosteSansEspace] hashtag#Recrutement hashtag#BTP hashtag#Carrière hashtag#Construction 
                hashtag#RH hashtag#capitalhumain hashtag#developpementRH hashtag#OpportunitéProfessionnelle 
                hashtag#maroc hashtag#Innovation hashtag#rejoigneznous hashtag#ConstruisonsEnsemble 
                hashtag#TGCC hashtag#Building hashtag#afrique hashtag#RecrutementBTP hashtag#géniecivil 
                hashtag#Emploigéniecivil hashtag#Depuisplusde30ans hashtag#annonces hashtag#bâtiment 
                hashtag#ingénierie hashtag#ProjetsAmbitieux hashtag#recrute

                RÈGLES STRICTES:
                - Format court et percutant pour LinkedIn
                - Utiliser des emojis pertinents
                - Phrases courtes et impactantes
                - Hashtags optimisés pour le recrutement BTP
                - Ton professionnel mais engageant
                - Mettre le poste en gras au début
                """
            else:  # TGCC
                prompt = prompt_base + """
                STRUCTURE OBLIGATOIRE (sans titres en gras, directement le contenu):

                Informations clés:
                Entreprise: TGCC
                Localisation: [localisation] 
                Type de contrat: [type]
                Poste: [poste]

                Accroche engageante:
                [2-3 questions rhétoriques adaptées au BTP]

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
                • Une formation continue adaptée Chez TGCC, vous montez en compétences selon vos besoins.
                • Un environnement de travail dynamique Vous êtes entouré(e) d'une équipe jeune et passionnée.
                • Des responsabilités significatives Vous êtes au cœur de la réussite des projets de TGCC.
                • Une culture d'excellence et d'intrapreneuriat Environnement stimulant et bienveillant favorisant le dépassement de soi.

                Processus de recrutement:
                • Analyse préalable de votre candidature
                • Entretien de préqualification téléphonique  
                • Entretien technique
                • Entretien RH

                RÈGLES STRICTES:
                - Pas de titres en gras
                - Pas de mention du salaire dans les avantages
                - Utiliser toujours "TGCC" pour parler de l'entreprise
                - Phrases directes et naturelles
                - Formatage propre avec des listes à puces
                - Ton authentique et transparent
                - Pas de mots anglais, tout en français
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
if st.button("💾 Sauvegarder l'annonce", type="primary", use_container_width=True, key="btn_sauvegarder_annonce"):
    if poste_final and entreprise and contenu and localisation_finale:
        annonce = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "poste": poste_final,
            "entreprise": entreprise,
            "localisation": localisation_finale,
            "contenu": contenu,
            "plateforme": plateforme,
        }
        st.session_state.annonces.append(annonce)
        st.success("✅ Annonce sauvegardée avec succès !")
        # Reset pour nouvelle saisie
        st.session_state["annonce_contenu"] = ""
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