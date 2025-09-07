import sys
import os
import importlib.util
import streamlit as st
from datetime import datetime

# -------------------- Import utils --------------------
UTILS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils.py"))
spec = importlib.util.spec_from_file_location("utils", UTILS_PATH)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# -------------------- Init session --------------------
utils.init_session_state()

# Initialiser les variables manquantes
defaults = {
    "conversation_history": [],
    "assistant_responses": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------- Page config --------------------
st.set_page_config(
    page_title="TG-Hire IA - Assistant IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 Assistant IA")

# -------------------- Entrée utilisateur --------------------
user_input = st.text_area("💬 Pose ta question :", key="assistant_input", height=120)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🚀 Envoyer", type="primary", key="assistant_send"):
        if user_input.strip():
            st.session_state.conversation_history.append(
                {"role": "user", "content": user_input, "time": datetime.now().strftime("%H:%M")}
            )
            # Simulation réponse IA
            response = f"Réponse IA simulée à : {user_input}"
            st.session_state.conversation_history.append(
                {"role": "assistant", "content": response, "time": datetime.now().strftime("%H:%M")}
            )
            st.success("✅ Réponse générée")
        else:
            st.warning("⚠️ Veuillez écrire une question avant d’envoyer.")
with col2:
    if st.button("🧹 Réinitialiser", key="assistant_reset"):
        st.session_state.conversation_history = []
        st.success("🗑️ Historique effacé")
        st.rerun()
with col3:
    if st.button("⬇️ Exporter", key="assistant_export"):
        if st.session_state.conversation_history:
            export_text = "\n".join([f"[{c['time']}] {c['role'].capitalize()}: {c['content']}" for c in st.session_state.conversation_history])
            st.download_button(
                "Télécharger conversation",
                data=export_text,
                file_name="conversation_assistant.txt",
                mime="text/plain",
                key="download_assistant"
            )
        else:
            st.info("ℹ️ Pas de conversation à exporter.")

st.divider()

# -------------------- Affichage conversation --------------------
st.subheader("📜 Historique de la conversation")

if not st.session_state.conversation_history:
    st.info("Aucune conversation pour l’instant. Pose une question pour commencer !")
else:
    for i, conv in enumerate(st.session_state.conversation_history[::-1]):  # affichage dernier en premier
        role = "🧑 Toi" if conv["role"] == "user" else "🤖 Assistant"
        with st.expander(f"{role} ({conv['time']})", expanded=False):
            st.write(conv["content"])
            if st.button("🗑️ Supprimer", key=f"delete_msg_{i}"):
                st.session_state.conversation_history.pop(len(st.session_state.conversation_history) - 1 - i)
                st.rerun()
