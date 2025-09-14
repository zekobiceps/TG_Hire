import streamlit as st
import importlib.util
import os
import requests
import json
import time
from datetime import datetime
import fitz
from PIL import Image

# -------------------- Import utils --------------------
# This assumes utils.py is in the parent directory.
# If not, adjust the path accordingly.
try:
    UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
    spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    utils.init_session_state()
except (FileNotFoundError, AttributeError):
    # Fallback for local testing without utils.py
    st.info("utils.py not found. Initializing session state directly.")
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    # Add other state variables if necessary for your app
    if "current_brief_name" not in st.session_state:
        st.session_state.current_brief_name = None

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Assistant IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- API Configuration --------------------
def get_deepseek_response(prompt):
    """Get a response from the DeepSeek AI model."""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        st.error("❌ Clé API DeepSeek non trouvée dans st.secrets.")
        return "Erreur: Clé API manquante."
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Use a system prompt to align the AI for recruitment
    system_prompt = "Vous êtes un assistant de recrutement IA hautement qualifié. Votre objectif est d'aider les recruteurs à rédiger des fiches de poste, à extraire des compétences clés, à générer des questions d'entretien et à analyser des profils de candidats. Vos réponses doivent être professionnelles, précises, et directement applicables au contexte du recrutement."

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history to maintain context
    for msg in st.session_state.conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the new user prompt
    messages.append({"role": "user", "content": prompt})

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

# -------------------- Main app logic --------------------
selected_page = st.sidebar.selectbox("Sélectionner une page", ['Chat Bot', 'PDF Analysis'])

# -------------------- Chat Bot --------------------
if selected_page == "Chat Bot":
    st.title("🤖 Assistant IA de Recrutement")
    
    st.info("Pose une question à ton assistant IA spécialisé en recrutement.")
    
    # User input
    user_input = st.text_area("💬 Pose ta question :", key="assistant_input", height=120)

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        send_button = st.button("🚀 Envoyer", type="primary", key="assistant_send")
    with col2:
        reset_button = st.button("🧹 Réinitialiser", key="assistant_reset")
    
    if reset_button:
        st.session_state.conversation_history = []
        st.success("🗑️ Historique effacé")
        st.rerun()

    if send_button and user_input.strip():
        # Append user message
        st.session_state.conversation_history.append(
            {"role": "user", "content": user_input, "time": datetime.now().strftime("%H:%M")}
        )
        
        # Get AI response
        with st.spinner('⏳ L\'assistant IA est en train de réfléchir...'):
            ai_response = get_deepseek_response(user_input)

        # Append assistant message
        st.session_state.conversation_history.append(
            {"role": "assistant", "content": ai_response, "time": datetime.now().strftime("%H:%M")}
        )
        st.rerun()
    elif send_button and not user_input.strip():
        st.warning("⚠️ Veuillez écrire une question avant d’envoyer.")

    st.divider()

    # Display chat history
    st.subheader("📜 Historique de la conversation")
    if not st.session_state.conversation_history:
        st.info("Aucune conversation pour l’instant. Pose une question pour commencer !")
    else:
        for i, conv in enumerate(st.session_state.conversation_history):
            role = "🧑 Toi" if conv["role"] == "user" else "🤖 Assistant"
            # Using st.chat_message for a cleaner look
            with st.chat_message(conv["role"]):
                st.write(conv["content"])

# -------------------- PDF Analysis --------------------
elif selected_page == "PDF Analysis":
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
                        
                        st.session_state.analysis_response = full_response
                        
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement du PDF : {e}")