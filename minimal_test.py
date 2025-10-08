import streamlit as st
import sys
import platform
import pandas as pd
import os

st.set_page_config(
    page_title="TG Hire - Minimal Test",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 TG Hire - Version Minimale")
st.info("Cette page est une version minimale pour tester le déploiement Streamlit Cloud")

# Afficher les informations système
st.header("Informations système")
st.write(f"Python version: {platform.python_version()}")
st.write(f"Streamlit version: {st.__version__}")

# Vérifier si dans le Cloud ou en local
is_cloud = os.environ.get("STREAMLIT_DEPLOYMENT_TYPE") == "cloud"
st.success(f"Environnement: {'☁️ Streamlit Cloud' if is_cloud else '🖥️ Local'}")

# Vérifier les imports basiques
imports_to_check = ["pandas", "numpy", "plotly", "requests", "json", "io"]
import_status = {}

for module_name in imports_to_check:
    try:
        __import__(module_name)
        import_status[module_name] = "✅ OK"
    except ImportError:
        import_status[module_name] = "❌ Non installé"

st.subheader("Vérification des imports")
st.table(pd.DataFrame(list(import_status.items()), columns=["Module", "Statut"]))

# Afficher les variables d'environnement (non sensibles)
st.subheader("Variables d'environnement (non sensibles)")
env_vars = {
    "PATH": os.environ.get("PATH", "")[-20:] + "...",  # Juste la fin pour éviter de tout afficher
    "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
    "USER": os.environ.get("USER", ""),
    "STREAMLIT_SERVER_PORT": os.environ.get("STREAMLIT_SERVER_PORT", ""),
    "STREAMLIT_SERVER_HEADLESS": os.environ.get("STREAMLIT_SERVER_HEADLESS", ""),
}
st.json(env_vars)

# Vérifier la présence de secrets
st.subheader("Vérification des secrets")
secrets_to_check = ["DEEPSEEK_API_KEY", "GROQ_API_KEY", "GITHUB_TOKEN"]
secret_status = {}

for secret_name in secrets_to_check:
    try:
        has_secret = secret_name in st.secrets
        secret_status[secret_name] = "✅ Présent" if has_secret else "❌ Manquant"
    except Exception:
        secret_status[secret_name] = "⚠️ Erreur de vérification"

st.table(pd.DataFrame(list(secret_status.items()), columns=["Secret", "Statut"]))

st.header("Prochaines étapes")
st.markdown("""
1. Si cette page s'affiche correctement sur Streamlit Cloud, le problème vient probablement du fichier `Home.py` ou d'un autre module.
2. Essayez de mettre à jour `requirements.txt` pour assurer que toutes les dépendances sont correctement installées.
3. Vérifiez les logs de build sur Streamlit Cloud pour identifier des erreurs éventuelles.
4. Considérez l'utilisation d'imports conditionnels pour les bibliothèques qui pourraient causer des problèmes.
""")