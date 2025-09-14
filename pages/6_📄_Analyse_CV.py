import streamlit as st
import fitz
import requests
import json
from PIL import Image

# -------------------- API Configuration --------------------
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
    system_prompt = "Vous êtes un assistant d'analyse de documents RH. Votre objectif est d'analyser le contenu de CV ou de fiches de poste, d'en extraire les informations clés, et de fournir une synthèse claire et structurée. Vos réponses doivent être professionnelles, précises et directement applicables au contexte du recrutement."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": "deepseek-coder",
        "messages": messages,
        "stream": False,
        "max_tokens": 1500,
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
def pdf_analysis_page():
    """Affiche l'interface utilisateur pour l'analyse de PDF."""
    st.header("Upload a PDF and Get Insights :page_facing_up:")
    
    uploaded_pdf = st.file_uploader("Choose a PDF file", accept_multiple_files=False, type=["pdf"])

    if uploaded_pdf is not None:
        try:
            pdf_text = ""
            with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
                for page in doc:
                    pdf_text += page.get_text()

            st.text_area("Extracted Text from PDF:", pdf_text, height=300, disabled=True)

            if st.button(":orange[Analyze PDF]"):
                if not pdf_text.strip():
                    st.error("❌ Le document est vide ou l'extraction a échoué.")
                else:
                    with st.spinner('Analyzing PDF...'):
                        analysis_prompt = f"Analyse le texte suivant extrait d'un PDF et fournissez une synthèse structurée des points clés. Le texte est : {pdf_text}"
                        full_response = get_deepseek_response(analysis_prompt)
                        
                        st.subheader(":blue[PDF Analysis Response]")
                        st.write(full_response)
                        
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement du PDF : {e}")

# Appel de la fonction pour afficher la page si ce fichier est le point d'entrée
if __name__ == "__main__":
    pdf_analysis_page()