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

# Mode d'entrée : PDF ou manuel
input_mode = st.radio("Mode d'entrée des infos du poste", ["Upload PDF fiche de poste", "Saisie manuelle"], key="input_mode")

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
    # Saisie manuelle : formulaire simple basé sur la check-list (sélection des indispensables + essentiels)
    st.subheader("Remplissez les infos clés (basé sur la check-list LEDR)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        salaire = st.text_input("Salaire")
        localisation = st.text_input("Localisation")
        type_contrat = st.text_input("Type de contrat + durée")
        date_demarrage = st.text_input("Date de démarrage")
        objectif_poste = st.text_area("Objectif du poste")
        missions = st.text_area("Missions")
        competences = st.text_area("Compétences")
        infos_entreprise = st.text_area("Infos sur l'entreprise")
        comment_postuler = st.text_input("Comment postuler")
        culture_valeurs = st.text_area("Culture, valeurs de l'entreprise")
        competences_hierarchisees = st.text_area("Compétences hiérarchisées")
        
    with col2:
        contexte_recrutement = st.text_area("Contexte du recrutement")
        description_equipe = st.text_area("Description de l'équipe")
        presentation_manager = st.text_area("Présentation du manager")
        position_hierarchique = st.text_input("Position hiérarchique")
        responsabilites_autonomie = st.text_area("Les responsabilités / l'autonomie")
        contact_recruteur = st.text_input("Le contact direct de la personne en charge du recrutement")
        processus_recrutement = st.text_area("Processus de recrutement")
        conditions_reussite = st.text_area("Conditions de réussite")
        criteres_recrutement = st.text_area("Expliquer ses critères de recrutement")
        evolution_missions = st.text_area("Évolution à court/moyen terme sur les missions du poste")
        parcours_carriere = st.text_area("Parcours de carrière et de formation de l'entreprise")

    fiche_text = f"""
    Salaire: {salaire}
    Localisation: {localisation}
    Type de contrat + durée: {type_contrat}
    Date de démarrage: {date_demarrage}
    L'objectif du poste: {objectif_poste}
    Missions: {missions}
    Compétences: {competences}
    Infos sur l'entreprise: {infos_entreprise}
    Comment postuler: {comment_postuler}
    Culture, valeurs de l'entreprise: {culture_valeurs}
    Compétences hiérarchisées: {competences_hierarchisees}
    Contexte du recrutement: {contexte_recrutement}
    Description de l'équipe: {description_equipe}
    Présentation du manager: {presentation_manager}
    Position hiérarchique: {position_hierarchique}
    Les responsabilités / l'autonomie: {responsabilites_autonomie}
    Le contact direct de la personne en charge du recrutement: {contact_recruteur}
    Processus de recrutement: {processus_recrutement}
    Conditions de réussite: {conditions_reussite}
    Expliquer ses critères de recrutement: {criteres_recrutement}
    Évolution à court/moyen terme sur les missions du poste: {evolution_missions}
    Parcours de carrière et de formation de l'entreprise: {parcours_carriere}
    """

# Check-list du PDF/screenshot (hardcodée pour l'intégrer au prompt)
check_list = """
L'indispensable: Salaire, Localisation, Type de Contrat + durée, Date de démarrage, L'objectif du poste, Missions, Compétences, infos sur l'entreprise, Comment postuler
L'essentiel: Culture, valeurs de l'entreprise, Compétences hiérarchisées, Contexte du recrutement, Description de l'équipe, Présentation du manager, Position hiérarchique, Les responsabilités / l'autonomie, Le contact direct de la personne en charge du recrutement, Processus de recrutement
L'exceptionnel: Conditions de réussite, Expliquer ses critères de recrutement, Évolution à court/ moyen terme sur les missions du poste, Parcours de carrière et de formation de l'entreprise, Infos sur la carrière ou la formation des personnes AVANT ce poste, Infos sur les projets à moyen, où long terme de l'équipe, L'accompagnement à la prise de poste : pré-boarding et d'onboarding
"""

col1, col2 = st.columns(2)
with col1:
    titre = st.text_input("Titre de l'annonce", key="annonce_titre")
    poste = st.text_input("Poste concerné", key="annonce_poste")
with col2:
    entreprise = st.text_input("Entreprise", key="annonce_entreprise")
    localisation_input = st.text_input("Localisation", key="annonce_loc")  # Peut être overwrite par PDF/manuel

# Bouton pour générer via IA
if st.button("🤖 Générer l'annonce via IA", type="secondary", use_container_width=True, key="btn_generer_annonce"):
    if fiche_text:
        # Prompt base
        prompt_base = f"Utilise cette check-list pour inclure un maximum d'infos pertinentes dans l'annonce : {check_list}\n\nBasé sur cette fiche de poste : {fiche_text}\n\nGénère une annonce complète pour le poste {poste} chez {entreprise} à {localisation_input}."

        if plateforme == "JOBZYN":
            prompt = prompt_base + "\nRestrict-toi strictement à ces blocs : Introduction au poste, Votre rôle, Votre équipe, Vos qualifications, Avantages, Processus de recrutement. Rends-la attractive et concise."
        else:  # TGCC
            prompt = prompt_base + """
CONTEXTE ET OBJECTIF
Tu es un expert en rédaction d'annonces d'emploi qui doit créer des annonces hautement attractives et efficaces basées sur les meilleures pratiques du secteur. Ton objectif est de générer des annonces qui convertissent les lecteurs en candidats qualifiés.

RÈGLES FONDAMENTALES À APPLIQUER
✅ CE QU'IL FAUT FAIRE (Inspiré de la bonne annonce) :

STRUCTURE OPTIMALE :

Titre accrocheur avec emoji → "Exemple 2024 → [Poste] – [Entreprise] – [Type de contrat] – [Lieu]"

Informations clés en haut : Entreprise, Localisation, Contrat, Date, Salaire

Accroche qui interpelle par des questions rhétoriques sur les frustrations du métier

Section "Pourquoi nous avons besoin de vous" avec contexte business

Section "Ce que vous ferez" avec missions détaillées

Section "Ce que l'on recherche" avec compétences clés et bonus

Section "Ce poste n'est pas pour vous si..." pour filtrer naturellement

Processus de recrutement transparent

TON ET STYLE :

Direct et authentique, comme une conversation

Utiliser "vous" pour s'adresser directement au candidat

Ton franc et transparent sur les défis et avantages

Mise en valeur de l'autonomie et de la culture d'entreprise

CONTENU ENGAGEANT :

Expliquer la différence entre travailler ici et ailleurs

Décrire l'environnement et l'équipe actuelle

Précision sur le management et les perspectives

❌ CE QU'IL FAUT ABSOLUMENT ÉVITER (Erreurs courantes) :

NE PAS FAIRE UN SIMPLE DESCRIPTIF DE POSTE

Une annonce est une PUBLICITÉ, pas un document administratif

Éviter le jargon RH et les formulations bureaucratiques

NE PAS TROP RACCOURCIR

Une annonce courte perd son pouvoir de conviction

Le candidat a besoin d'informations concrètes pour décider

NE PAS CHERCHER À PLAIRE À TOUT LE MONDE

Attirer, c'est accepter de repousser certaines personnes

Mentionner clairement les inconvénients et défis

ÉVITER LA LANGUE DE BOIS

Supprimer les termes à géométrie variable : "taille humaine", "innovant", "responsable"

Éliminer les adjectifs vides de sens

Appliquer le test du "blab bla" : si on peut remplacer par "blab bla", supprimer

FAIRE ATTENTION À LA FORME

Éviter les blocs de texte denses

Utiliser une hiérarchie claire : titres, listes, phrases courtes

Vérifier que la plateforme conserve la mise en forme

STRUCTURE OBLIGATOIRE DE L'ANNONCE
TITRE ACCROCHEUR [Format standardisé]

INFORMATIONS CLÉS [En haut, très visible]

ACCROCHE ENGAGEANTE [2-3 questions rhétoriques]

POURQUOI NOUS AVONS BESOIN DE VOUS [Contexte business]

PRÉSENTATION DE L'ENTREPRISE [Culture, valeurs, spécificités]

CE QUE VOUS FEREZ [Missions quotidiennes + ponctuelles]

VOTRE ENVIRONNEMENT [Équipe, management, culture]

CE QUE NOUS RECHERCHONS [Compétences clés + bonus]

CE POSTE N'EST PAS POUR VOUS SI... [Filtre naturel]

PROCESSUS DE RECRUTEMENT [Étapes transparentes]

APPEL À L'ACTION [Comment postuler]

EXEMPLE DE BONNE PRATIQUE À REPRODUIRE
« Fatigué·e de devoir vous battre pour convaincre d'adopter des méthodes de recrutement efficaces ? Marre de ne pas avoir les outils nécessaires pour réussir dans votre métier ? »

« Chez nous, vous n'aurez plus à vous soucier de ces problèmes. »

« Ce poste n'est pas pour vous si... vous aimez recruter au feeling »

DEMANDE SPÉCIFIQUE
Quand je te fournirai les informations sur un poste à pourvoir, génère une annonce complète qui respecte scrupuleusement ces règles. L'annonce doit être prête à être publiée et optimisée pour attirer les candidats idéaux tout en filtrant naturellement les non-correspondants.

Ton expertise doit se concentrer sur :

La conversion des lecteurs en candidats qualifiés

L'authenticité et la transparence

La différenciation par rapport aux annonces traditionnelles

L'optimisation pour les plateformes de recrutement. Rends-la authentique, transparente, avec accroche rhétorique, filtre naturel, etc."""

        # Appel à l'IA (assumez que utils.deepseek_generate existe)
        try:
            generated_contenu = utils.deepseek_generate(prompt)  # Remplacez par votre fonction réelle
            st.session_state["annonce_contenu"] = generated_contenu
            st.success("Annonce générée avec succès !")
        except Exception as e:
            st.error(f"Erreur lors de la génération IA : {e}")
    else:
        st.warning("Fournissez une fiche de poste via PDF ou saisie manuelle.")

contenu = st.text_area("Contenu de l'annonce (généré ou manuel)", key="annonce_contenu", height=300, value=st.session_state.get("annonce_contenu", ""))

if st.button("💾 Publier l'annonce", type="primary", use_container_width=True, key="btn_publier_annonce"):
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
        st.success("✅ Annonce publiée avec succès !")
        # Reset pour nouvelle saisie
        st.session_state["annonce_contenu"] = ""
    else:
        st.warning("⚠️ Merci de remplir tous les champs obligatoires")

st.divider()

# -------------------- Liste des annonces --------------------
st.subheader("📋 Annonces publiées")

if not st.session_state.annonces:
    st.info("Aucune annonce publiée pour le moment.")
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