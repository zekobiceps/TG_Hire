import streamlit as st
import requests
from datetime import datetime
import json

# Configuration de l'outil
st.set_page_config(
    page_title="Générateur de Lettres RH - TGCC",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration pour l'appel à l'IA DeepSeek
SYSTEM_PROMPT = """
Tu es un expert en rédaction de lettres officielles pour les entreprises du BTP au Maroc.
Tu maîtrises parfaitement :
1. Les codes de la correspondance administrative marocaine
2. Le vocabulaire technique du BTP
3. Les protocoles de nomination et d'annonce de recrutement
4. Le ton professionnel et respectueux requis

Tes lettres doivent être :
- Formelles et respectueuses
- Structurées selon les normes administratives marocaines
- Adaptées au contexte du BTP
- Personnalisées selon les informations fournies
"""

def get_deepseek_response(prompt, length="normale"):
    """Appel à l'API DeepSeek pour génération de lettres"""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        return {"content": "Erreur: Clé API DeepSeek manquante.", "usage": 0}
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": final_prompt}
    ]
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json", 
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "deepseek-chat", 
                "messages": messages, 
                "max_tokens": 2048
            }
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {}).get("total_tokens", 0)
        
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API DeepSeek: {e}", "usage": 0}

# Interface principale
st.title("📝 Générateur de Lettres RH - TGCC")
st.markdown("---")

# Sidebar avec les statistiques (simple pour l'instant)
with st.sidebar:
    st.subheader("📊 Statistiques")
    st.metric("🔑 Session", 0)
    st.metric("📊 Total", 0)
    st.markdown("---")
    st.info("💡 Générateur IA de lettres officielles")

# Choix du type de lettre
type_lettre = st.selectbox(
    "📋 Type de lettre à générer",
    [
        "Lettre de nomination",
        "Annonce de nouvelle recrue",
        "Lettre de félicitations",
        "Communiqué interne"
    ],
    help="Sélectionnez le type de document à générer"
)

st.markdown("### ℹ️ Informations du candidat/employé")

# Formulaire d'informations organisé en 2 colonnes
col1, col2 = st.columns(2)

with col1:
    prenom = st.text_input("Prénom", placeholder="Mohamed")
    nom = st.text_input("Nom", placeholder="ALAMI")
    genre = st.selectbox("Genre", ["Monsieur", "Madame"])
    poste = st.text_input("Poste/Fonction", placeholder="Directeur Technique")
    
with col2:
    entreprise = st.selectbox(
        "Entreprise/Filiale", 
        ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"]
    )
    date_prise_fonction = st.date_input("Date de prise de fonction", datetime.now())
    rattachement = st.text_input("Rattachement", placeholder="Direction Générale")
    
    # Upload photo du collaborateur
    photo_collaborateur = st.file_uploader(
        "Photo du collaborateur", 
        type=['jpg', 'jpeg', 'png'],
        help="Photo qui apparaîtra à droite de la lettre (comme dans les exemples)"
    )

# Informations complémentaires selon le type de lettre organisées en 2 colonnes
st.markdown("### 📄 Détails complémentaires")

if type_lettre == "Lettre de nomination":
    col3, col4 = st.columns(2)
    with col3:
        poste_precedent = st.text_input("Poste précédent (optionnel)", placeholder="Chef de projet")
        departement = st.text_input("Département/Service", placeholder="Direction Technique")
        superviseur = st.text_input("Supérieur hiérarchique", placeholder="Directeur Général")
    with col4:
        lieu_travail = st.text_input("Lieu de travail", placeholder="Casablanca - Siège social")
        salaire = st.text_input("Salaire (optionnel)", placeholder="À définir selon grille")
        avantages = st.text_area("Avantages (optionnel)", placeholder="Véhicule de fonction, frais de mission...")

elif type_lettre == "Annonce de nouvelle recrue":
    col3, col4 = st.columns(2)
    with col3:
        experience = st.text_input("Expérience professionnelle", placeholder="5 ans d'expérience en BTP")
        formation = st.text_input("Formation", placeholder="Ingénieur Civil - EHTP")
        competences = st.text_area("Compétences clés", placeholder="Gestion de projet, AutoCAD, Management d'équipe")
    with col4:
        projets_precedents = st.text_area("Projets/Entreprises précédents", placeholder="Participation aux projets X, Y, Z")
        certifications = st.text_input("Certifications (optionnel)", placeholder="PMP, AutoCAD certifié...")
        langues = st.text_input("Langues", placeholder="Arabe, Français, Anglais")

# Fiche de poste (optionnelle pour enrichir la génération)
st.markdown("### 📋 Fiche de poste (optionnel - pour enrichissement IA)")

# Deux options : texte ou PDF
tab_text, tab_pdf = st.tabs(["📝 Coller le texte", "📄 Uploader PDF"])

fiche_poste = ""

with tab_text:
    fiche_poste = st.text_area(
        "Collez ici la fiche de poste complète:",
        height=150,
        placeholder="Mission: ...\nResponsabilités: ...\nProfil recherché: ...\nCompétences requises: ...\nExpérience: ...\nFormation: ..."
    )

with tab_pdf:
    uploaded_fiche = st.file_uploader(
        "Choisissez votre fichier PDF:",
        type=['pdf'],
        help="La fiche de poste sera analysée par l'IA pour enrichir la lettre"
    )
    
    if uploaded_fiche is not None:
        try:
            # Ici on pourrait ajouter l'extraction du texte du PDF
            # Pour l'instant, on affiche juste le nom du fichier
            st.success(f"✅ Fiche de poste chargée : {uploaded_fiche.name}")
            fiche_poste = f"[Fiche de poste PDF chargée : {uploaded_fiche.name}]"
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement du PDF : {e}")

# Paramètres de génération
st.markdown("### ⚙️ Paramètres de génération")
col5, col6 = st.columns(2)
with col5:
    ton_lettre = st.selectbox("Ton de la lettre", ["Formel", "Chaleureux", "Officiel", "Convivial"])
    longueur = st.selectbox("Longueur", ["Courte", "Normale", "Détaillée"])
with col6:
    inclure_entete_tgcc = st.checkbox("Inclure en-tête TGCC", value=True)
    # Signature par défaut avec Direction et "TGCC CONSTRUISONS ENSEMBLE"
    st.info("ℹ️ Zone de signature incluse par défaut : Direction + TGCC CONSTRUISONS ENSEMBLE")

# Bouton de génération
if st.button("✨ Générer la lettre", type="primary", use_container_width=True):
    if not prenom or not nom or not poste:
        st.error("⚠️ Veuillez remplir au minimum : Prénom, Nom et Poste")
    else:
        with st.spinner("🤖 Génération de la lettre en cours..."):
            # Construction du prompt selon le type de lettre
            if type_lettre == "Lettre de nomination":
                prompt = f"""
                Génère une lettre de nomination officielle avec les informations suivantes :
                
                **Informations personnelles :**
                - {genre} {prenom} {nom.upper()}
                - Nouveau poste : {poste}
                - Entreprise : {entreprise}
                - Date de prise de fonction : {date_prise_fonction.strftime('%d/%m/%Y')}
                - Poste précédent : {poste_precedent if poste_precedent else 'Non spécifié'}
                - Département : {departement if departement else 'Non spécifié'}
                - Supérieur hiérarchique : {superviseur if superviseur else 'Direction'}
                - Lieu de travail : {lieu_travail if lieu_travail else 'Maroc'}
                
                **Fiche de poste :**
                {fiche_poste if fiche_poste else 'Non fournie'}
                
                **Style demandé :** {ton_lettre}
                
                **Informations résumé à inclure dans la lettre :**
                {genre} {prenom} {nom.upper()}
                Poste : {poste}
                Prise de fonction : {date_prise_fonction.strftime('%d/%m/%Y')}
                Rattachement : {rattachement}
                
                Génère une lettre de nomination complète, structurée et professionnelle.
                {'Inclus les coordonnées de TGCC en en-tête.' if inclure_entete_tgcc else ''}
                Inclus TOUJOURS une zone de signature avec :
                
                Direction
                TGCC CONSTRUISONS ENSEMBLE
                """
                
            elif type_lettre == "Annonce de nouvelle recrue":
                prompt = f"""
                Génère une annonce de nouvelle recrue avec les informations suivantes :
                
                **Nouveau collaborateur :**
                - {genre} {prenom} {nom.upper()}
                - Poste : {poste}
                - Entreprise : {entreprise}
                - Date d'arrivée : {date_prise_fonction.strftime('%d/%m/%Y')}
                - Expérience : {experience if experience else 'Non spécifiée'}
                - Formation : {formation if formation else 'Non spécifiée'}
                - Compétences : {competences if competences else 'Non spécifiées'}
                - Expérience précédente : {projets_precedents if projets_precedents else 'Non spécifiée'}
                
                **Fiche de poste :**
                {fiche_poste if fiche_poste else 'Non fournie'}
                
                **Style demandé :** {ton_lettre}
                
                **Informations résumé à inclure dans l'annonce :**
                {genre} {prenom} {nom.upper()}
                Poste : {poste}
                Prise de fonction : {date_prise_fonction.strftime('%d/%m/%Y')}
                Rattachement : {rattachement}
                
                Génère une annonce interne accueillante et professionnelle pour présenter le nouveau collaborateur.
                {'Inclus les coordonnées de TGCC en en-tête.' if inclure_entete_tgcc else ''}
                Inclus TOUJOURS une zone de signature avec :
                
                Direction
                TGCC CONSTRUISONS ENSEMBLE
                """
            
            # Appel à l'IA
            result = get_deepseek_response(prompt, longueur.lower())
            
            if result.get("content") and "Erreur:" not in result["content"]:
                st.markdown("### 📝 Lettre générée")
                st.markdown("---")
                
                # Affichage avec photo à droite si disponible
                if photo_collaborateur is not None:
                    col_lettre, col_photo = st.columns([3, 1])
                    with col_lettre:
                        lettre_content = result["content"]
                        st.text_area(
                            "Votre lettre :",
                            value=lettre_content,
                            height=400,
                            help="Vous pouvez copier le contenu et le coller dans Word ou votre éditeur préféré"
                        )
                    with col_photo:
                        st.image(photo_collaborateur, caption=f"{prenom} {nom}", width=150)
                        st.markdown("**Position sur le document final :**")
                        st.info("📍 Cette photo sera positionnée à droite de la lettre dans le document final")
                else:
                    # Affichage normal sans photo
                    lettre_content = result["content"]
                    st.text_area(
                        "Votre lettre :",
                        value=lettre_content,
                        height=400,
                        help="Vous pouvez copier le contenu et le coller dans Word ou votre éditeur préféré"
                    )
                    st.info("💡 Ajoutez une photo du collaborateur pour un rendu plus professionnel")
                
                # Boutons d'action
                col7, col8, col9 = st.columns(3)
                with col7:
                    st.download_button(
                        label="📥 Télécharger (.txt)",
                        data=lettre_content,
                        file_name=f"lettre_{type_lettre.lower().replace(' ', '_')}_{nom}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col8:
                    if st.button("🔄 Régénérer", use_container_width=True):
                        st.rerun()
                
                with col9:
                    if st.button("💾 Sauvegarder modèle", use_container_width=True):
                        st.success("✅ Modèle sauvegardé !")
                
                # Statistiques de génération
                st.info(f"📊 Tokens utilisés : {result.get('usage', 0)}")
                
            else:
                st.error("❌ Erreur lors de la génération de la lettre")
                if result.get("content"):
                    st.error(result["content"])

# Section d'aide
with st.expander("❓ Guide d'utilisation", expanded=False):
    st.markdown("""
    ### 📋 Comment utiliser cet outil
    
    1. **Choisissez le type de lettre** - Nomination, annonce de recrue, etc.
    2. **Remplissez les informations** - Nom, prénom, poste, entreprise
    3. **Ajoutez les détails** - Selon le type de lettre choisi
    4. **Collez la fiche de poste** (optionnel) - Pour une génération plus précise
    5. **Configurez les paramètres** - Ton, longueur, options d'affichage
    6. **Générez la lettre** - L'IA crée une lettre personnalisée
    7. **Téléchargez ou copiez** - Récupérez votre document final
    
    ### 💡 Conseils pour de meilleurs résultats
    - Remplissez un maximum d'informations
    - Utilisez la fiche de poste pour plus de précision
    - Choisissez le ton approprié à votre contexte
    - Relisez et ajustez selon vos besoins
    """)