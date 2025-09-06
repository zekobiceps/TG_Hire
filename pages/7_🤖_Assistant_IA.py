import streamlit as st
from utils import *
init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant Recrutement",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 Assistant IA - Questions Réponses")

st.title("🤖 Assistant IA - Questions Réponses")
st.write("Posez des questions spécifiques à l'assistant IA pour vous aider dans votre processus de recrutement.")

# Configuration des réponses dans le contenu principal
st.header("⚙️ Configuration Réponses")
config_col1, config_col2, config_col3 = st.columns(3)

with config_col1:
    st.session_state.response_format = st.selectbox(
        "Format de réponse:",
        ["texte", "tableau", "liste"],
        index=0
    )

with config_col2:
    st.session_state.detail_level = st.selectbox(
        "Niveau de détail:",
        ["Concis", "Détaillé"],
        index=0
    )

with config_col3:
    st.session_state.max_tokens = st.slider(
        "Longueur max réponse:",
        100, 1000, 500
    )

# Zone de question
st.header("💬 Poser une question")
question = st.text_area(
    "Votre question:",
    placeholder="Ex: Comment évaluer la compétence 'autonomie' en entretien?",
    height=100,
    key="assistant_question"
)

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🪄 Poser la question", type="primary", use_container_width=True) and question:
        if st.session_state.api_usage['current_session_tokens'] < 800000:
            messages = st.session_state.current_messages + [{"role": "user", "content": question}]
            result = ask_deepseek(messages, max_tokens=st.session_state.max_tokens, response_format=st.session_state.response_format)
            
            if "content" in result:
                assistant_response = result['content']
                st.session_state.current_messages.append({"role": "user", "content": question})
                st.session_state.current_messages.append({"role": "assistant", "content": assistant_response})
                st.session_state.conversation_history.append({"question": question, "answer": assistant_response})
                st.success("Réponse générée!")
        else:
            st.warning("Tokens insuffisants!")

with col2:
    if st.button("🗑️ Effacer l'historique", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.current_messages = [
            {"role": "system", "content": "Tu es un expert en recrutement qui aide à préparer des briefs managers. Tes réponses doivent être concises et pratiques."}
        ]
        st.rerun()

# Historique de conversation
if st.session_state.conversation_history:
    st.header("📜 Historique des conversations")
    for i, conv in enumerate(st.session_state.conversation_history):
        with st.expander(f"Conversation {i+1} - {conv['question'][:50]}..."):
            st.markdown(f"**🧑‍💼 Vous:** {conv['question']}")
            st.markdown(f"**🤖 Assistant:**")
            
            # Affichage selon le format
            if st.session_state.response_format == "tableau" and ('|' in conv['answer'] or 'tableau' in conv['answer'].lower()):
                st.markdown(conv['answer'])
            else:
                st.markdown(conv['answer'])
            
            if st.button("🗑️ Supprimer", key=f"delete_{i}"):
                st.session_state.conversation_history.pop(i)
                st.rerun()