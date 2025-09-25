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

# -------------------- Ajout d'une annonce --------------------
st.subheader("➕ Ajouter une annonce")

# Choix de la plateforme
plateforme = st.selectbox("Plateforme cible", ["JOBZYN", "TGCC"], key="annonce_plateforme")

# Mode d'entrée : PDF ou manuel (uniquement pour TGCC)
if plateforme == "TGCC":
    input_mode = st.radio("Mode d'entrée des infos du poste", ["Upload PDF fiche de poste", "Saisie manuelle"], key="input_mode")
else:
    input_mode = "Upload PDF fiche de poste"  # Pour JOBZYN, uniquement PDF

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
    # Saisie manuelle : formulaire simple basé sur la check-list (uniquement pour TGCC)
    st.subheader("Remplissez les infos clés (basé sur la check-list LEDR)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        salaire = st.text_input("Salaire", help="Ex: 15 000 - 20 000 MAD, selon expérience")
        localisation = st.text_input("Localisation", help="Ex: Casablanca, Rabat, Tanger, Marrakech")
        type_contrat = st.text_input("Type de contrat", help="Ex: CDI, CDD, Stage, Alternance")
        date_demarrage = st.text_input("Date de démarrage", help="Ex: Dès que possible, Septembre 2024")
        objectif_poste = st.text_area("Objectif du poste", help="Ex: Assurer la gestion complète des projets BTP de l'entreprise")
        missions = st.text_area("Missions principales", help="Ex: Gestion de chantier, coordination d'équipe, suivi budget")
        competences = st.text_area("Compétences techniques", help="Ex: Maîtrise d'AutoCAD, gestion de projet, normes BTP")
        infos_entreprise = st.text_area("Infos sur l'entreprise", help="Ex: Entreprise leader dans le BTP au Maroc depuis 20 ans")
        
    with col2:
        culture_valeurs = st.text_area("Culture et valeurs", help="Ex: Qualité, Intégrité, Excellence, Ambition")
        contexte_recrutement = st.text_area("Contexte du recrutement", help="Ex: Expansion de l'entreprise sur de nouveaux marchés")
        description_equipe = st.text_area("Description de l'équipe", help="Ex: Équipe de 15 ingénieurs expérimentés")
        position_hierarchique = st.text_input("Position hiérarchique", help="Ex: N+1, rattachement à la Direction")
        responsabilites_autonomie = st.text_area("Responsabilités et autonomie", help="Ex: Autonomie complète sur les décisions techniques")
        processus_recrutement = st.text_area("Processus de recrutement", help="Ex: 1. Analyse CV, 2. Entretien téléphonique, 3. Entretien technique, 4. Entretien RH")
        evolution_missions = st.text_area("Évolution possible", help="Ex: Possibilité d'évolution vers un poste de direction")
        parcours_carriere = st.text_area("Parcours de carrière", help="Ex: Formation continue, programmes de développement")

    fiche_text = f"""
    Salaire: {salaire}
    Localisation: {localisation}
    Type de contrat: {type_contrat}
    Date de démarrage: {date_demarrage}
    Objectif du poste: {objectif_poste}
    Missions principales: {missions}
    Compétences techniques: {competences}
    Infos sur l'entreprise: {infos_entreprise}
    Culture et valeurs: {culture_valeurs}
    Contexte du recrutement: {contexte_recrutement}
    Description de l'équipe: {description_equipe}
    Position hiérarchique: {position_hierarchique}
    Responsabilités et autonomie: {responsabilites_autonomie}
    Processus de recrutement: {processus_recrutement}
    Évolution possible: {evolution_missions}
    Parcours de carrière: {parcours_carriere}
    """

# Check-list simplifiée
check_list = """
Informations essentielles: Salaire, Localisation, Type de contrat, Date de démarrage, Objectif du poste, Missions, Compétences
Informations complémentaires: Culture entreprise, Contexte recrutement, Équipe, Processus
"""

col1, col2 = st.columns(2)
with col1:
    titre = st.text_input("Titre de l'annonce", key="annonce_titre", help="Ex: Directeur des Projets BTP - Casablanca")
    poste = st.text_input("Poste concerné", key="annonce_poste", help="Ex: Directeur Projets, Ingénieur BTP, Chef de Chantier")
with col2:
    entreprise = st.text_input("Entreprise", key="annonce_entreprise", help="Ex: TGCC, Vinci Maroc, Groupe Addoha")
    localisation_input = st.text_input("Localisation", key="annonce_loc", help="Ex: Casablanca, Rabat, région de Souss-Massa")

# Bouton pour générer via IA avec style rouge
st.markdown("""
    <style>
    .red-button button {
        background-color: #ff4444 !important;
        color: white !important;
        border: 1px solid #ff4444 !important;
    }
    .red-button button:hover {
        background-color: #cc0000 !important;
        border: 1px solid #cc0000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Génération IA avec spinner
if st.button("💡 Générer l'annonce via IA", type="secondary", use_container_width=True, 
             key="btn_generer_annonce", help="Génération automatique par intelligence artificielle"):
    if fiche_text:
        # Prompt base
        prompt_base = f"Utilise cette check-list pour inclure un maximum d'infos pertinentes dans l'annonce : {check_list}\n\nBasé sur cette fiche de poste : {fiche_text}\n\nGénère une annonce complète pour le poste {poste} chez {entreprise} à {localisation_input}."

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
            • Une formation continue adaptée
            Chez nous, vous montez en compétences selon vos besoins.
            
            • Un environnement de travail dynamique
            Vous êtes entouré(e) d'une équipe jeune et passionnée.
            
            • Des responsabilités significatives
            Vous êtes au cœur de la réussite de nos projets.
            
            • Une culture d'excellence
            Environnement challenging et bienveillant favorisant le dépassement de soi.
            
            Processus de recrutement:
            • Analyse préalable de votre candidature
            • Entretien de préqualification téléphonique  
            • Entretien technique
            • Entretien RH
            
            Rends-la attractive et concise.
            """
        else:  # TGCC
            prompt = prompt_base + """
            CONTEXTE ET OBJECTIF
            Tu es un expert en rédaction d'annonces d'emploi qui doit créer des annonces hautement attractives et efficaces basées sur les meilleures pratiques du secteur. Ton objectif est de générer des annonces qui convertissent les lecteurs en candidats qualifiés.

            STRUCTURE OBLIGATOIRE (sans titres en gras, directement le contenu):

            Informations clés:
            Entreprise: {entreprise}
            Localisation: {localisation_input} 
            Type de contrat: [type]
            Poste: {poste}

            Accroche engageante:
            [2-3 questions rhétoriques adaptées au BTP]

            Pourquoi nous avons besoin de vous:
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
            • Une formation continue adaptée
            Chez nous, vous montez en compétences en termes de hard skills ou soft skills selon vos besoins.

            • Un environnement de travail dynamique
            Vous êtes entouré(e) d'une équipe jeune et passionnée : c'est une réelle aventure professionnelle qui commence !

            • Des responsabilités significatives
            Vous êtes au cœur de la réussite des projets de nos clients.

            • Une culture d'excellence et d'intrapreneuriat
            Environnement challenging et bienveillant favorisant le dépassement de soi, où les idées innovantes peuvent se développer.

            Processus de recrutement:
            • Analyse préalable de votre candidature
            • Entretien de préqualification téléphonique  
            • Entretien technique
            • Entretien RH

            RÈGLES STRICTES:
            - Pas de titres en gras (**texte**)
            - Pas de mention du salaire dans les avantages
            - Pas de durée pour le type de contrat
            - Phrases directes et naturelles
            - Formatage propre avec des listes à puces
            - Ton authentique et transparent
            """

        # Appel à l'IA avec spinner
        with st.spinner("🔄 Génération en cours par l'IA... Veuillez patienter."):
            try:
                generated_contenu = utils.deepseek_generate(prompt)
                # Nettoyer le contenu généré
                generated_contenu = generated_contenu.replace('**', '')  # Enlever les **
                generated_contenu = generated_contenu.replace('* ', '• ')  # Uniformiser les puces
                st.session_state["annonce_contenu"] = generated_contenu
                st.success("✅ Annonce générée avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de la génération IA : {e}")
    else:
        st.warning("Fournissez une fiche de poste via PDF ou saisie manuelle.")

# Textarea pour le contenu avec gestion de la valeur par défaut
if "annonce_contenu" not in st.session_state:
    st.session_state["annonce_contenu"] = ""

contenu = st.text_area("Contenu de l'annonce (généré ou manuel)", 
                       key="annonce_contenu", 
                       height=300, 
                       value=st.session_state.get("annonce_contenu", ""),
                       help="Contenu de l'annonce généré par l'IA ou saisi manuellement")

if st.button("💾 Sauvegarder l'annonce", type="primary", use_container_width=True, key="btn_publier_annonce"):
    if titre and poste and entreprise and contenu:
        annonce = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "titre": titre,
            "poste": poste,
            "entreprise": entreprise,
            "localisation": localisation_input,
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
        with st.expander(f"{annonce['date']} - {annonce['titre']} ({annonce['poste']}) - {annonce['plateforme']}", expanded=False):
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
                    data=f"Titre: {annonce['titre']}\nPoste: {annonce['poste']}\nEntreprise: {annonce['entreprise']}\nLocalisation: {annonce['localisation']}\nPlateforme: {annonce['plateforme']}\n\n{annonce['contenu']}",
                    file_name=f"annonce_{annonce['poste']}_{i}.txt",
                    mime="text/plain",
                    key=f"download_annonce_{i}"
                )