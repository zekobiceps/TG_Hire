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
        # Essayer les autres formats de clé
        api_key = st.secrets.get("deepseek_api_key") or st.secrets.get("DEEPSEEK_KEY")
        if not api_key:
            return {"content": "Erreur: Clé API DeepSeek manquante dans les secrets Streamlit.", "usage": 0}
    
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

# Formulaire d'informations organisé en 4 colonnes
col1, col2, col3, col4 = st.columns(4)

with col1:
    prenom = st.text_input("Prénom", placeholder="Mohamed")
    nom = st.text_input("Nom", placeholder="ALAMI")
    
with col2:
    genre = st.selectbox("Genre", ["Monsieur", "Madame"])
    poste = st.text_input("Poste/Fonction", placeholder="Directeur Technique")
    
with col3:
    entreprise = st.selectbox(
        "Entreprise/Filiale", 
        ["TGCC", "TG ALU", "TG COVER", "TG WOOD", "TG STEEL", "TG STONE", "TGEM", "TGCC Immobilier"]
    )
    date_prise_fonction = st.date_input("Date de prise de fonction", datetime.now())
    
with col4:
    rattachement = st.text_input("Rattachement", placeholder="Direction Générale")
    poste_precedent = st.text_input("Poste précédent (optionnel)", placeholder="Chef de projet")

# Ligne supplémentaire pour les derniers champs
col5, col6, col7, col8 = st.columns(4)

with col5:
    lieu_travail = st.text_input("Lieu de travail", placeholder="Casablanca - Siège social")
    
with col6:
    superviseur = st.text_input("Supérieur hiérarchique", placeholder="Directeur Général")
    
with col7:
    # Upload photo du collaborateur
    photo_collaborateur = st.file_uploader(
        "Photo du collaborateur", 
        type=['jpg', 'jpeg', 'png'],
        help="Photo qui apparaîtra à droite de la lettre"
    )
    
with col8:
    # Espace réservé pour équilibrer
    st.write("")

# Informations complémentaires selon le type de lettre (simplifiées)
st.markdown("### 📄 Détails complémentaires")

if type_lettre == "Lettre de nomination":
    col9, col10 = st.columns(2)
    with col9:
        salaire = st.text_input("Salaire (optionnel)", placeholder="À définir selon grille")
        departement = st.text_input("Département/Service", placeholder="Direction Technique")
    with col10:
        avantages = st.text_area("Avantages (optionnel)", placeholder="Véhicule de fonction, frais de mission...")

elif type_lettre == "Annonce de nouvelle recrue":
    col9, col10 = st.columns(2)
    with col9:
        experience = st.text_input("Expérience professionnelle", placeholder="5 ans d'expérience en BTP")
        formation = st.text_input("Formation", placeholder="Ingénieur Civil - EHTP")
        competences = st.text_area("Compétences clés", placeholder="Gestion de projet, AutoCAD, Management d'équipe")
    with col10:
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
col11, col12 = st.columns(2)
with col11:
    ton_lettre = st.selectbox("Ton de la lettre", ["Formel", "Chaleureux", "Officiel", "Convivial"])
    longueur = st.selectbox("Longueur", ["Courte", "Normale", "Détaillée"])
with col12:
    format_sortie = st.selectbox("Format de sortie", ["Texte modifiable", "PNG téléchargeable", "Les deux"])
    st.info("ℹ️ En-tête TGCC et signature 'Direction + TGCC CONSTRUISONS ENSEMBLE' inclus automatiquement")

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
                
                STRUCTURE OBLIGATOIRE :
                1. En-tête avec coordonnées TGCC
                2. Contenu de la lettre 
                3. Zone de signature avec :
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
                
                STRUCTURE OBLIGATOIRE :
                1. En-tête avec coordonnées TGCC
                2. Contenu de l'annonce
                3. Zone de signature avec :
                   Direction
                   TGCC CONSTRUISONS ENSEMBLE
                """
            
            # Appel à l'IA
            result = get_deepseek_response(prompt, longueur.lower())
            
            if result.get("content") and "Erreur:" not in result["content"]:
                st.markdown("### 📝 Lettre générée")
                st.markdown("---")
                
                # Zone de texte modifiable
                lettre_content = result["content"]
                
                # Initialiser le contenu modifiable dans session state
                if "lettre_modifiable" not in st.session_state:
                    st.session_state.lettre_modifiable = lettre_content
                else:
                    # Mettre à jour seulement si c'est une nouvelle génération
                    if st.session_state.get("derniere_lettre") != lettre_content:
                        st.session_state.lettre_modifiable = lettre_content
                        st.session_state.derniere_lettre = lettre_content
                
                # Affichage avec photo à droite si disponible
                if photo_collaborateur is not None:
                    col_lettre, col_photo = st.columns([3, 1])
                    with col_lettre:
                        lettre_modifiee = st.text_area(
                            "Lettre modifiable (vous pouvez éditer le texte) :",
                            value=st.session_state.lettre_modifiable,
                            height=400,
                            key="texte_lettre_modifiable",
                            help="Modifiez le texte selon vos besoins avant téléchargement"
                        )
                        # Mettre à jour le session state
                        st.session_state.lettre_modifiable = lettre_modifiee
                        
                    with col_photo:
                        st.image(photo_collaborateur, caption=f"{prenom} {nom}", width=150)
                        st.markdown("**Position sur le document final :**")
                        st.info("📍 Cette photo sera positionnée à droite de la lettre dans le document final")
                else:
                    # Affichage normal sans photo
                    lettre_modifiee = st.text_area(
                        "Lettre modifiable (vous pouvez éditer le texte) :",
                        value=st.session_state.lettre_modifiable,
                        height=400,
                        key="texte_lettre_modifiable_simple",
                        help="Modifiez le texte selon vos besoins avant téléchargement"
                    )
                    # Mettre à jour le session state
                    st.session_state.lettre_modifiable = lettre_modifiee
                    st.info("💡 Ajoutez une photo du collaborateur pour un rendu plus professionnel")
                
                # Boutons d'action
                col13, col14, col15, col16 = st.columns(4)
                
                with col13:
                    st.download_button(
                        label="📥 Télécharger (.txt)",
                        data=st.session_state.lettre_modifiable,
                        file_name=f"lettre_{type_lettre.lower().replace(' ', '_')}_{nom}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col14:
                    # Bouton pour génération PNG (simulation pour l'instant)
                    if st.button("🖼️ Générer PNG", use_container_width=True):
                        st.info("🔄 Génération PNG en cours de développement. Pour l'instant, copiez le texte dans Word avec l'en-tête TGCC.")
                        # TODO: Implémenter génération PNG avec PIL/reportlab
                
                with col15:
                    if st.button("🔄 Régénérer", use_container_width=True):
                        # Reset du contenu modifiable pour forcer une nouvelle génération
                        if "lettre_modifiable" in st.session_state:
                            del st.session_state.lettre_modifiable
                        if "derniere_lettre" in st.session_state:
                            del st.session_state.derniere_lettre
                        st.rerun()
                
                with col16:
                    if st.button("💾 Sauvegarder modèle", use_container_width=True):
                        # Sauvegarder le modèle modifié
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
    
    ### 🎨 Canevas PDF (en développement)
    **Question posée :** Faut-il créer un canevas PDF avec en-tête ?
    
    **Réponse :** Oui, c'est une excellente idée ! Un canevas PDF avec :
    - En-tête officiel TGCC avec logo
    - Zone de contenu pour le texte généré par l'IA
    - Zone photo à droite (comme dans vos exemples)
    - Pied de page avec "TGCC CONSTRUISONS ENSEMBLE"
    
    Cela donnerait un rendu plus professionnel et cohérent. 
    Pour l'instant, copiez le texte dans Word avec votre modèle d'en-tête.
    """)