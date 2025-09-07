import sys
import os
import importlib.util
import streamlit as st

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

st.set_page_config(
    page_title="TG-Hire IA - Assistant IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 Assistant IA")

# -------------------- Historique --------------------
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# -------------------- Entrée utilisateur --------------------
user_input = st.text_area("💬 Posez une question :", key="assistant_input", height=100)

if st.button("🚀 Envoyer", key="assistant_send"):
    if user_input.strip():
        # Ici, on simule une réponse IA
        response = f"Réponse IA simulée pour : {user_input}"
        st.session_state.conversation_history.append({"q": user_input, "a": response})
        st.rerun()
    else:
        st.warning("⚠️ Veuillez saisir une question")

st.divider()
st.subheader("📜 Historique de la conversation")

if st.session_state.conversation_history:
    for i, conv in enumerate(st.session_state.conversation_history[::-1]):
        with st.expander(f"❓ {conv['q']}", expanded=False):
            st.write(f"💡 {conv['a']}")
            if st.button("🗑️ Supprimer", key=f"del_conv_{i}"):
                st.session_state.conversation_history.pop(i)
                st.rerun()
else:
    st.info("ℹ️ Aucune conversation enregistrée")
