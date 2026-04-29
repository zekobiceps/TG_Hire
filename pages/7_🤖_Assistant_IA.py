import streamlit as st
from utils import require_login
import importlib.util
import os
import requests
import json
import time
from datetime import datetime
import random

# --- IMPORTS POUR LES MODÈLES IA ---
try:
    import groq
    import google.generativeai as genai
    import anthropic
    from google.oauth2 import service_account 
except ImportError:
    st.error("❌ Bibliothèques manquantes. Exécutez : pip install groq google-generativeai google-auth anthropic")
    st.stop()
    
# --- INITIALISATION DU SESSION STATE ---
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "Groq" 
if "response_length" not in st.session_state:
    st.session_state.response_length = "Courte"
if "last_token_usage" not in st.session_state:
    st.session_state.last_token_usage = 0
if "placeholder" not in st.session_state:
    # --- NOUVEAUTÉ : "Ex: " ajouté aux placeholders ---
    placeholders = [
        "Ex: Quelles sont les missions clés d'un conducteur de travaux au Maroc ?",
        "Ex: Rédige une offre d'emploi pour un chef de projet à Casablanca.",
        "Ex: Propose 5 questions techniques pour un entretien avec un ingénieur."
    ]
    st.session_state.placeholder = random.choice(placeholders)

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vérification de la connexion
require_login()

# -------------------- CONFIGURATION DES APIS --------------------
SYSTEM_PROMPT = """
Tu es 'TG-Hire Assistant', un expert IA spécialisé dans le recrutement pour le secteur du BTP (Bâtiment et Travaux Publics) au Maroc.
Ton rôle est d'aider un recruteur humain à optimiser ses tâches quotidiennes.
Tes réponses doivent être :
1.  **Contextualisées** : Toujours adaptées au marché de l'emploi marocain et aux spécificités du secteur du BTP.
2.  **Professionnelles et Précises** : Fournis des informations concrètes et structurées.
3.  **Orientées Action** : Propose des listes, des questions, des modèles de texte, etc.
4.  **Adaptables** : Tu dois ajuster la longueur de ta réponse (courte, normale, détaillée) selon la demande.
"""

def get_google_credentials():
    """Crée les identifiants du compte de service à partir des secrets Streamlit."""
    try:
        creds_json = {
            "type": st.secrets["GCP_TYPE"],
            "project_id": st.secrets["GCP_PROJECT_ID"],
            "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'),
            "client_email": st.secrets["GCP_CLIENT_EMAIL"],
            "client_id": st.secrets["GCP_CLIENT_ID"],
            "auth_uri": st.secrets["GCP_AUTH_URI"],
            "token_uri": st.secrets["GCP_TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_CERT_URL"],
            "client_x509_cert_url": st.secrets["GCP_CLIENT_CERT_URL"]
        }
        return service_account.Credentials.from_service_account_info(creds_json)
    except Exception as e:
        st.error(f"❌ Erreur de chargement des identifiants Google: {e}")
        return None

def get_deepseek_response(prompt, history, length):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: return {"content": "Erreur: Clé API DeepSeek manquante.", "usage": 0}
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": final_prompt}]
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages, "max_tokens": 2048}
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {}).get("total_tokens", 0)
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API DeepSeek: {e}", "usage": 0}

def get_groq_response(prompt, history, length):
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return {"content": "Erreur: Clé API Groq manquante.", "usage": 0}
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": final_prompt}]
    
    try:
        client = groq.Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
        )
        content = chat_completion.choices[0].message.content or ""
        usage = chat_completion.usage.total_tokens if chat_completion.usage else 0
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API Groq: {e}", "usage":0}

def get_gemini_response(prompt, history, length):
    creds = get_google_credentials() 
    if not creds:
        return {"content": "Erreur: Impossible de charger les identifiants du compte de service Google.", "usage": 0}

    final_prompt = f"{SYSTEM_PROMPT}\n\nHistorique:\n{json.dumps(history)}\n\nQuestion:\n{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    
    try:
        genai.configure(credentials=creds) 
        # Update to gemini-2.5-flash-lite as it is confirmed available
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(final_prompt)
        content = response.text
        usage = model.count_tokens(final_prompt).total_tokens
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API Gemini: {e}", "usage": 0}

def get_claude_response(prompt, history, length):
    api_key = None
    if "Claude_API_KEY" in st.session_state:
        api_key = st.session_state.Claude_API_KEY
    elif "Claude_API_KEY" in st.secrets:
        api_key = st.secrets["Claude_API_KEY"]
    elif "ANTHROPIC_API_KEY" in st.secrets:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    
    if not api_key:
        return {"content": "❌ Clé API Claude manquante.", "usage": 0}

    final_prompt = f"{SYSTEM_PROMPT}\n\nHistorique:\n{json.dumps(history)}\n\nQuestion:\n{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            messages=[{"role": "user", "content": final_prompt}]
        )
        content = ""
        if message.content:
            for block in message.content:
                if block.type == "text":
                    content += block.text
        
        usage = 0
        if message.usage:
            usage = message.usage.input_tokens + message.usage.output_tokens
            
        return {"content": content, "usage": usage}
    except Exception as e:
        return {"content": f"❌ Erreur API Claude: {e}", "usage": 0}

# --- ROUTEUR DE MODÈLE ---
def get_ai_response(prompt, history, model, length):
    if model == "Groq":
        return get_groq_response(prompt, history, length)
    elif model == "DeepSeek":
        return get_deepseek_response(prompt, history, length)
    elif model == "Gemini":
        return get_gemini_response(prompt, history, length)
    elif model == "Claude":
        return get_claude_response(prompt, history, length)
    else:
        return {"content": "Erreur: Modèle non reconnu.", "usage": 0}

# -------------------- INTERFACE PRINCIPALE --------------------
# --- NOUVEAUTÉ : Titre mis à jour ---
st.title("🤖 Assistant IA pour le Recrutement")
# Affichage du commit
try:
    from utils import display_commit_info
    display_commit_info()
except Exception:
    pass
# --- SÉLECTEURS DANS LA BARRE LATÉRALE ---
with st.sidebar:
    st.subheader("⚙️ Paramètres")
    st.session_state.selected_model = st.selectbox(
        "🧠 Choisir le modèle IA :",
        ("Groq", "DeepSeek", "Gemini", "Claude") # CoGenAI retiré
    )
    
    st.session_state.response_length = st.selectbox(
        "📄 Longueur de la réponse :",
        ("Courte", "Normale", "Détaillée"),
        index=0 # --- NOUVEAUTÉ : "Courte" par défaut ---
    )

    st.divider()

    st.subheader("📊 Utilisation")
    st.metric("Tokens de la dernière réponse", f"{st.session_state.last_token_usage}")
    st.caption("Le nombre de tokens mesure la 'quantité de travail' de l'IA.")

# --- ZONE DE SAISIE ET BOUTONS ---
user_input = st.text_area(
    "💬 Posez votre question ici :",
    key="assistant_input",
    height=120,
    placeholder=st.session_state.placeholder
)

col1, col2 = st.columns([3, 1])
with col1:
    send_button = st.button("💡 Générer par l'IA", type="primary", width="stretch")
with col2:
    reset_button = st.button("🧹 Effacer", width="stretch")

if reset_button:
    st.session_state.conversation_history = []
    st.session_state.last_token_usage = 0
    st.success("🗑️ Historique effacé !")
    time.sleep(1)
    st.rerun()

if send_button and user_input.strip():
    api_history = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.conversation_history]
    
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    
    with st.spinner("⏳ Génération d'une réponse par l'IA en cours..."):
        response_dict = get_ai_response(
            user_input, 
            api_history, 
            st.session_state.selected_model,
            st.session_state.response_length
        )

    ai_response = response_dict["content"]
    token_usage = response_dict["usage"]

    st.session_state.conversation_history.append({"role": "assistant", "content": ai_response})
    st.session_state.last_token_usage = token_usage
    
    placeholders = [
        "Ex: Quelles sont les missions clés d'un conducteur de travaux au Maroc ?",
        "Ex: Rédige une offre d'emploi pour un chef de projet à Casablanca.",
        "Ex: Propose 5 questions techniques pour un entretien avec un ingénieur."
    ]
    st.session_state.placeholder = random.choice(placeholders)
    
    st.rerun()

elif send_button and not user_input.strip():
    st.warning("⚠️ Veuillez écrire une question avant de générer une réponse.")

# --- AFFICHAGE DE L'HISTORIQUE ---
st.subheader("📜 Historique de la conversation")
if not st.session_state.conversation_history:
    st.info("La conversation n'a pas encore commencé.")
else:
    for conv in reversed(st.session_state.conversation_history):
        with st.chat_message(conv["role"]):
            st.markdown(conv["content"])