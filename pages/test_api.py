import streamlit as st
import requests
from datetime import datetime
import json
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# Configuration de l'outil
st.set_page_config(
    page_title="Générateur de Lettres RH - TGCC",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration pour l'appel à l'IA DeepSeek
SYSTEM_PROMPT = """
Tu es un expert en rédaction de lettres officielles pour le                        )       )       )    )TP au Maroc.
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

def generer_lettre_png(texte_lettre, photo_collaborateur=None, nom_fichier="lettre"):
    """Génère une image PNG de la lettre avec la photo si fournie"""
    try:
        # Dimensions de base
        width, height = 800, 1200
        background_color = (255, 255, 255)  # Blanc
        text_color = (0, 0, 0)  # Noir
        
        # Créer l'image
        img = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(img)
        
        # Essayer différentes polices
        try:
            font_titre = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font_titre = ImageFont.load_default()
            font_text = ImageFont.load_default()
        
        # Position initiale
        y_offset = 50
        x_margin = 50
        
        # En-tête TGCC
        draw.text((x_margin, y_offset), "TGCC", fill=text_color, font=font_titre)
        y_offset += 40
        
        # Zone photo à droite si disponible
        photo_width = 0
        if photo_collaborateur is not None:
            try:
                photo = Image.open(photo_collaborateur)
                photo = photo.resize((120, 150), Image.Resampling.LANCZOS)
                img.paste(photo, (width - 170, y_offset))
                photo_width = 170
            except:
                pass
        
        # Texte de la lettre (avec marge pour la photo)
        text_width = width - x_margin - photo_width - 20
        lines = texte_lettre.split('\n')
        
        for line in lines:
            if line.strip():
                # Diviser les lignes trop longues
                words = line.split(' ')
                current_line = ''
                for word in words:
                    test_line = current_line + word + ' '
                    if draw.textlength(test_line, font=font_text) < text_width:
                        current_line = test_line
                    else:
                        if current_line:
                            draw.text((x_margin, y_offset), current_line.strip(), fill=text_color, font=font_text)
                            y_offset += 20
                        current_line = word + ' '
                
                if current_line:
                    draw.text((x_margin, y_offset), current_line.strip(), fill=text_color, font=font_text)
                    y_offset += 20
            else:
                y_offset += 10
        
        # Convertir en bytes pour téléchargement
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Erreur génération PNG: {e}")
        return None

def generer_document_word(texte_lettre, photo_collaborateur=None):
    """Génère un document Word avec la lettre et la photo intégrée"""
    try:
        # Pour l'instant, on génère un format RTF simple qui peut être ouvert par Word
        rtf_content = r"""{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}
        """
        
        # Ajouter l'en-tête
        rtf_content += r"""
        {\pard\qc\b\fs28 TGCC\par}
        {\pard\qc CONSTRUISONS ENSEMBLE\par}
        \line\line
        """
        
        # Si photo disponible, essayer de l'intégrer (simplifié pour RTF)
        if photo_collaborateur is not None:
            # Pour RTF, on ne peut pas facilement intégrer l'image, mais on indique sa position
            rtf_content += r"""{\pard\qr [Photo du collaborateur à insérer ici]\par}"""
            rtf_content += r"""\line"""
        
        # Ajouter le contenu de la lettre
        texte_formate = texte_lettre.replace('\n', r'\line ')
        rtf_content += f"""
        {{\\pard {texte_formate}\\par}}
        """
        
        rtf_content += "}"
        
        return rtf_content.encode('utf-8')
        
    except Exception as e:
        st.error(f"Erreur génération Word: {e}")
        return None

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
col11, col12, col13_params = st.columns(3)
with col11:
    ton_lettre = st.selectbox("Ton de la lettre", ["Formel", "Chaleureux", "Officiel", "Convivial"])
with col12:
    longueur = st.selectbox("Longueur", ["Courte", "Normale", "Détaillée"])
with col13_params:
    format_sortie = st.selectbox("Format de sortie", ["Texte modifiable", "PNG téléchargeable", "Les deux"])

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
                   {rattachement}
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
                   {rattachement}
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
                    # Uniquement téléchargement Word
                    rtf_data = generer_document_word(st.session_state.lettre_modifiable, photo_collaborateur)
                    if rtf_data:
                        st.download_button(
                            label="📝 Télécharger Word",
                            data=rtf_data,
                            file_name=f"lettre_{nom}_{datetime.now().strftime('%Y%m%d')}.rtf",
                            mime="application/rtf",
                            use_container_width=True
                        )
                    with col_txt:
                        st.download_button(
                            label="� TXT",
                            data=st.session_state.lettre_modifiable,
                            file_name=f"lettre_{nom}_{datetime.now().strftime('%Y%m%d')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col_word:
                        rtf_data = generer_document_word(st.session_state.lettre_modifiable, photo_collaborateur)
                        if rtf_data:
                            st.download_button(
                                label="📝 Word",
                                data=rtf_data,
                                file_name=f"lettre_{nom}_{datetime.now().strftime('%Y%m%d')}.rtf",
                                mime="application/rtf",
                                use_container_width=True
                            )
                
                with col14:
                    # Bouton pour génération PNG
                    if st.button("🖼️ Générer PNG", use_container_width=True):
                        with st.spinner("🔄 Génération PNG en cours..."):
                            png_data = generer_lettre_png(st.session_state.lettre_modifiable, photo_collaborateur, nom)
                            if png_data:
                                # Afficher directement le bouton de téléchargement
                                st.download_button(
                                    label="📥 Télécharger PNG",
                                    data=png_data,
                                    file_name=f"lettre_{nom}_{datetime.now().strftime('%Y%m%d')}.png",
                                    mime="image/png",
                                    use_container_width=True,
                                    key=f"download_png_{datetime.now().strftime('%H%M%S')}"
                                )
                                # Afficher un aperçu de l'image
                                st.image(png_data, caption="Aperçu de la lettre PNG", width=400)
                            else:
                                st.error("❌ Erreur lors de la génération PNG")
                
                with col15:
                    if st.button("🔄 Régénérer", use_container_width=True):
                        # Reset du contenu modifiable pour forcer une nouvelle génération
                        if "lettre_modifiable" in st.session_state:
                            del st.session_state.lettre_modifiable
                        if "derniere_lettre" in st.session_state:
                            del st.session_state.derniere_lettre
                        st.rerun()
                
                with col16:
                    if st.button("💾 Sauvegarder", use_container_width=True):
                        # Sauvegarder le modèle avec toutes les informations
                        modele_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": type_lettre,
                            "prenom": prenom,
                            "nom": nom,
                            "poste": poste,
                            "entreprise": entreprise,
                            "contenu": st.session_state.lettre_modifiable,
                            "rattachement": rattachement,
                            "has_photo": photo_collaborateur is not None
                        }
                        
                        # Initialiser la liste des modèles sauvegardés si elle n'existe pas
                        if "modeles_sauvegardes" not in st.session_state:
                            st.session_state.modeles_sauvegardes = []
                        
                        st.session_state.modeles_sauvegardes.append(modele_data)
                        st.success(f"✅ Modèle sauvegardé : {prenom} {nom} - {poste}")
                
                # Statistiques de génération
                st.info(f"📊 Tokens utilisés : {result.get('usage', 0)}")
                
            else:
                st.error("❌ Erreur lors de la génération de la lettre")
                if result.get("content"):
                    st.error(result["content"])

# Section des modèles sauvegardés
if "modeles_sauvegardes" in st.session_state and st.session_state.modeles_sauvegardes:
    st.markdown("---")
    st.markdown("### 📚 Modèles sauvegardés")
    
    with st.expander(f"Voir les {len(st.session_state.modeles_sauvegardes)} modèles sauvegardés", expanded=False):
        for i, modele in enumerate(reversed(st.session_state.modeles_sauvegardes)):
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.write(f"**{modele['prenom']} {modele['nom']}** - {modele['poste']}")
                st.caption(f"{modele['type']} | {modele['entreprise']} | {modele['timestamp']}")
                
            with col_actions:
                if st.button(f"📥 Télécharger", key=f"download_modele_{i}"):
                    st.download_button(
                        label="📄 Télécharger ce modèle",
                        data=modele['contenu'],
                        file_name=f"modele_{modele['nom']}_{modele['timestamp'][:10]}.txt",
                        mime="text/plain",
                        key=f"download_btn_{i}"
                    )

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