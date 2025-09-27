import streamlit as st
import importlib.util
import os
import requests
import json
import time
from datetime import datetime
import random

# --- NOUVEAUX IMPORTS POUR LES MODÈLES IA ---
try:
    import groq
    import google.generativeai as genai
except ImportError:
    st.error("❌ Bibliothèques Groq ou Gemini manquantes. Exécutez : pip install groq google-generativeai")
    st.stop()

# --- VÉRIFICATION DE CONNEXION (si nécessaire) ---
# if not st.session_state.get("logged_in", False):
#     st.error("🛑 Veuillez vous connecter pour accéder à cette page.")
#     st.stop()
    
# --- INITIALISATION DU SESSION STATE ---
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "Groq" # Modèle par défaut
if "response_length" not in st.session_state:
    st.session_state.response_length = "Normale" # Longueur par défaut
if "placeholder" not in st.session_state:
    # Liste de 10 placeholders aléatoires
    placeholders = [
        "Quelles sont les missions clés d'un conducteur de travaux dans le BTP au Maroc ?",
        "Rédige une offre d'emploi pour un chef de projet BTP à Casablanca.",
        "Propose 5 questions techniques pour un entretien avec un ingénieur en génie civil.",
        "Comment évaluer les soft skills d'un chargé d'affaires BTP ?",
        "Quels sont les salaires moyens pour un dessinateur-projeteur à Rabat ?",
        "Liste les compétences indispensables pour un responsable QSE dans la construction.",
        "Comment attirer des profils pénuriques comme les grutiers au Maroc ?",
        "Analyse ce profil : 'Ingénieur d'état, 5 ans d'expérience en suivi de chantiers routiers'.",
        "Donne-moi des arguments pour convaincre un candidat de rejoindre notre entreprise de BTP.",
        "Quelles sont les réglementations marocaines importantes à connaître pour un poste RH dans le BTP ?"
    ]
    st.session_state.placeholder = random.choice(placeholders)

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- CONFIGURATION DES APIS --------------------

# --- PROMPT SYSTÈME COMMUN ---
# Contexte précis pour guider tous les modèles IA
SYSTEM_PROMPT = """
Tu es 'TG-Hire Assistant', un expert IA spécialisé dans le recrutement pour le secteur du BTP (Bâtiment et Travaux Publics) au Maroc.
Ton rôle est d'aider un recruteur humain à optimiser ses tâches quotidiennes.
Tes réponses doivent être :
1.  **Contextualisées** : Toujours adaptées au marché de l'emploi marocain et aux spécificités du secteur du BTP (terminologie, types de postes, réglementations locales).
2.  **Professionnelles et Précises** : Fournis des informations concrètes, structurées et directement utilisables.
3.  **Orientées Action** : Propose des listes, des questions, des modèles de texte, etc.
4.  **Adaptables** : Tu dois ajuster la longueur et le niveau de détail de ta réponse (courte, normale, détaillée) selon la demande de l'utilisateur.
"""

def get_deepseek_response(prompt, history, length):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: return "Erreur: Clé API DeepSeek manquante."
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": final_prompt}]
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages, "max_tokens": 2048}
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Erreur API DeepSeek: {e}"

def get_groq_response(prompt, history, length):
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return "Erreur: Clé API Groq manquante."
    
    final_prompt = f"{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": final_prompt}]
    
    try:
        client = groq.Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Erreur API Groq: {e}"

def get_gemini_response(prompt, history, length):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "Erreur: Clé API Gemini manquante."
    
    final_prompt = f"{SYSTEM_PROMPT}\n\nHistorique de la conversation:\n{json.dumps(history)}\n\nNouvelle question:\n{prompt}\n\n(Instruction: Fournir une réponse de longueur '{length}')"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(final_prompt)
        return response.text
    except Exception as e:
        return f"❌ Erreur API Gemini: {e}"

# --- ROUTEUR DE MODÈLE ---
def get_ai_response(prompt, history, model, length):
    if model == "Groq":
        return get_groq_response(prompt, history, length)
    elif model == "DeepSeek":
        return get_deepseek_response(prompt, history, length)
    elif model == "Gemini":
        return get_gemini_response(prompt, history, length)
    else:
        return "Erreur: Modèle non reconnu."

# -------------------- INTERFACE PRINCIPALE --------------------
st.title("🤖 Assistant IA pour le Recrutement BTP")
st.info("Posez une question à votre assistant spécialisé pour le marché marocain du BTP.")

# --- SÉLECTEURS DANS LA BARRE LATÉRALE ---
with st.sidebar:
    st.subheader("⚙️ Paramètres")
    st.session_state.selected_model = st.radio(
        "🧠 Choisir le modèle IA :",
        ("Groq", "DeepSeek", "Gemini"),
        horizontal=True,
    )
    st.session_state.response_length = st.radio(
        "📄 Longueur de la réponse :",
        ("Courte", "Normale", "Détaillée"),
        horizontal=True,
    )

# --- ZONE DE SAISIE ET BOUTONS ---
user_input = st.text_area(
    "💬 Posez votre question ici :",
    key="assistant_input",
    height=120,
    placeholder=st.session_state.placeholder # Placeholder aléatoire
)

col1, col2 = st.columns([3, 1]) # Donne plus de place au bouton principal
with col1:
    send_button = st.button("💡 Générer par l'IA", type="primary", use_container_width=True)
with col2:
    reset_button = st.button("🧹 Effacer", use_container_width=True)

if reset_button:
    st.session_state.conversation_history = []
    st.success("🗑️ Historique de la conversation effacé !")
    time.sleep(1) # Petit délai pour voir le message
    st.rerun()

if send_button and user_input.strip():
    # Extrait uniquement le rôle et le contenu pour l'historique de l'API
    api_history = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.conversation_history]
    
    # Ajoute le message de l'utilisateur à l'historique d'affichage
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    
    # Récupère la réponse de l'IA
    with st.spinner(f"⏳ L'assistant {st.session_state.selected_model} réfléchit..."):
        ai_response = get_ai_response(
            user_input, 
            api_history, 
            st.session_state.selected_model,
            st.session_state.response_length
        )

    # Ajoute la réponse de l'IA à l'historique d'affichage
    st.session_state.conversation_history.append({"role": "assistant", "content": ai_response})
    
    # Change le placeholder pour la prochaine question
    st.session_state.placeholder = random.choice([
        "Quelles sont les missions clés d'un conducteur de travaux dans le BTP au Maroc ?",
        "Rédige une offre d'emploi pour un chef de projet BTP à Casablanca.",
        "Propose 5 questions techniques pour un entretien avec un ingénieur en génie civil.",
        "Comment évaluer les soft skills d'un chargé d'affaires BTP ?",
        "Quels sont les salaires moyens pour un dessinateur-projeteur à Rabat ?",
        "Liste les compétences indispensables pour un responsable QSE dans la construction.",
        "Comment attirer des profils pénuriques comme les grutiers au Maroc ?",
        "Analyse ce profil : 'Ingénieur d'état, 5 ans d'expérience en suivi de chantiers routiers'.",
        "Donne-moi des arguments pour convaincre un candidat de rejoindre notre entreprise de BTP.",
        "Quelles sont les réglementations marocaines importantes à connaître pour un poste RH dans le BTP ?"
    ])
    st.rerun()

elif send_button and not user_input.strip():
    st.warning("⚠️ Veuillez écrire une question avant de générer une réponse.")

st.divider()

# --- AFFICHAGE DE L'HISTORIQUE DE CONVERSATION (INVERSÉ) ---
st.subheader("📜 Historique de la conversation")
if not st.session_state.conversation_history:
    st.info("La conversation n'a pas encore commencé. Posez une question pour démarrer !")
else:
    # Itère sur la liste inversée pour afficher le plus récent en premier
    for conv in reversed(st.session_state.conversation_history):
        # Utilise st.chat_message pour une interface de chat moderne
        with st.chat_message(conv["role"]):
            st.markdown(conv["content"])