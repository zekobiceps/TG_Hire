import streamlit as st
import fitz
import requests
import json
import io

# -------------------- API DeepSeek Configuration --------------------
def get_deepseek_response(prompt):
    """Obtient une réponse du modèle DeepSeek AI."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ Clé API DeepSeek non trouvée dans st.secrets. Assurez-vous d'avoir configuré le fichier secrets.toml.")
        return "Erreur: Clé API manquante."

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Utilisez un prompt de système pour aligner l'IA sur le recrutement
    system_prompt = "Vous êtes un assistant d'analyse de documents RH. Votre objectif est d'analyser le contenu de documents (CV, fiches de poste, etc.), d'en extraire les informations clés et de fournir une synthèse claire et structurée. Vos réponses doivent être professionnelles, précises et directement applicables au contexte du recrutement."

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

    # Conteneur d'upload stylisé
    with st.container():
        st.subheader("1. Uploader votre document")
        st.markdown(
            """
            <div class="upload-container">
                <p>Glissez & déposez votre fichier ici ou cliquez pour le parcourir</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_pdf = st.file_uploader("", accept_multiple_files=False, type=["pdf"])

    # Logique de traitement
    if uploaded_pdf is not None:
        st.success("✅ Fichier PDF chargé avec succès!")
        
        # Bouton d'analyse en rouge vif
        if st.button("🚀 Lancer l'analyse du PDF", type="primary"):
            try:
                # Extraction du texte du PDF
                with st.spinner('⏳ Extraction du texte du document...'):
                    pdf_text = ""
                    with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
                        for page in doc:
                            pdf_text += page.get_text()

                if not pdf_text.strip():
                    st.error("❌ Le document est vide ou l'extraction a échoué.")
                else:
                    # Affichage du texte extrait (facultatif)
                    with st.expander("👁️ Voir le texte extrait du PDF"):
                        st.text_area("Texte extrait:", pdf_text, height=300)

                    # Appel à l'IA pour l'analyse
                    with st.spinner('✨ Analyse en cours par l\'IA...'):
                        analysis_prompt = f"Analyse le texte suivant extrait d'un document PDF. Extrait les informations clés pour un brief de recrutement : l'intitulé du poste, les tâches principales, les compétences techniques requises, les soft skills, et l'expérience demandée. Présente les informations dans une liste structurée. Le texte est : {pdf_text}"
                        full_response = get_deepseek_response(analysis_prompt)
                        
                        st.subheader("💡 Résultat de l'analyse IA")
                        st.markdown(f'<div class="analysis-box">{full_response}</div>', unsafe_allow_html=True)
                        
            except Exception as e:
                st.error(f"❌ Erreur lors du traitement du PDF : {e}")

# Appel de la fonction pour afficher la page si ce fichier est le point d'entrée
if __name__ == "__main__":
    render_pdf_analysis_page()