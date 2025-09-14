import streamlit as st
import fitz
import requests
import json
import io
from docx import Document

# -------------------- API DeepSeek Configuration --------------------
def get_deepseek_response(prompt):
    """Obtient une réponse du modèle DeepSeek AI."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ Clé API DeepSeek non trouvée dans st.secrets.")
        return "Erreur: Clé API manquante."

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Utilisez un prompt de système pour aligner l'IA sur le recrutement
    system_prompt = "Vous êtes un assistant d'analyse de documents RH. Votre objectif est d'analyser le contenu de documents (CV, fiches de poste, etc.), d'en extraire les informations clés, et de fournir une synthèse claire et structurée. Vos réponses doivent être professionnelles, précises et directement applicables au contexte du recrutement."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": "deepseek-coder",
        "messages": messages,
        "stream": False,
        "max_tokens": 2000,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erreur API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erreur lors de l'appel API: {e}"

# -------------------- Logique de la page --------------------
def render_pdf_analysis_page():
    """Affiche l'interface utilisateur pour l'analyse de PDF."""
    
    # Titre et introduction avec une icône
    st.markdown(
        """
        <style>
        .st-emotion-cache-18j2gai {
            text-align: center;
        }
        .main-header {
            font-size: 2.5em;
            font-weight: bold;
            color: #1a1a1a;
            text-align: center;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        .sub-header {
            font-size: 1.2em;
            color: #7f8c8d;
            text-align: center;
            margin-top: 0;
        }
        .upload-container {
            padding: 20px;
            border-radius: 10px;
            border: 2px dashed #bdc3c7;
            text-align: center;
            margin-bottom: 20px;
        }
        .stButton>button {
            color: white;
            background-color: #e74c3c;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 1em;
            border: none;
            cursor: pointer;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #c0392b;
        }
        .st-emotion-cache-1l8943x p {
            font-size: 1.1em;
            text-align: center;
        }
        .st-emotion-cache-1l8943x {
            border: none;
        }
        .st-emotion-cache-e8t53b {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
        }
        .analysis-box {
            padding: 20px;
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            color: black;
        }
        </style>
        <h1 class="main-header">📄 Analyse de Document IA</h1>
        <p class="sub-header">
            Transforme instantanément n'importe quel PDF en un brief de recrutement structuré ou en une analyse de CV.
        </p>
        <hr/>
        """,
        unsafe_allow_html=True
    )
    
    # Utilisation d'un formulaire pour une meilleure gestion des états
    with st.form(key="pdf_analysis_form"):
        st.subheader("1. Uploader votre document")
        uploaded_file = st.file_uploader(
            "Glissez & déposez votre fichier ici ou cliquez pour le parcourir",
            type=["pdf", "docx"],
            accept_multiple_files=False,
            key="uploaded_file"
        )
        
        # Champ pour afficher le texte extrait
        extracted_text_area = st.empty()

        # Bouton pour lancer l'analyse
        submit_button = st.form_submit_button("🚀 Lancer l'analyse du document", type="primary")

    if submit_button:
        if uploaded_file is not None:
            st.success("✅ Fichier chargé avec succès!")
            file_type = uploaded_file.type
            
            # --- Extraction du texte ---
            with st.spinner('⏳ Extraction du texte du document...'):
                text_content = ""
                if file_type == "application/pdf":
                    try:
                        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                            for page in doc:
                                text_content += page.get_text()
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction du PDF : {e}")
                        text_content = ""
                elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    try:
                        doc = Document(uploaded_file)
                        text_content = " ".join([p.text for p in doc.paragraphs])
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction du DOCX : {e}")
                        text_content = ""

            # Affichage du texte extrait
            if text_content.strip():
                extracted_text_area.text_area("Texte extrait:", text_content, height=300, disabled=True)
                
                # --- Appel à l'IA pour l'analyse ---
                with st.spinner('✨ Analyse en cours par l\'IA...'):
                    analysis_prompt = f"Analyse le texte suivant extrait d'un document PDF. Extrait les informations clés pour un brief de recrutement : l'intitulé du poste, les tâches principales, les compétences techniques requises, les soft skills, et l'expérience demandée. Présente les informations dans une liste structurée. Le texte est : {text_content}"
                    full_response = get_deepseek_response(analysis_prompt)
                    
                    st.subheader("💡 Résultat de l'analyse IA")
                    st.markdown(f'<div class="analysis-box">{full_response}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ Le document est vide ou l'extraction a échoué.")
        else:
            st.warning("⚠️ Veuillez uploader un fichier pour lancer l'analyse.")

# Appel de la fonction pour afficher la page si ce fichier est le point d'entrée
if __name__ == "__main__":
    render_pdf_analysis_page()