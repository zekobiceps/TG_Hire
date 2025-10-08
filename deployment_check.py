import streamlit as st
import platform
import sys
import subprocess
import pandas as pd
import os
import time

st.set_page_config(
    page_title="Diagnostic de déploiement",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Diagnostic de déploiement Streamlit")

# Afficher les informations système
st.header("Informations système")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Environnement Python")
    st.code(f"""
Python version: {platform.python_version()}
Python implementation: {platform.python_implementation()}
OS: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Streamlit version: {st.__version__}
    """)

with col2:
    st.subheader("Packages installés")
    # Lister les packages les plus importants
    try:
        packages = {
            "pandas": pd.__version__,
            "numpy": pd.np.__version__,
            "streamlit": st.__version__,
            "plotly": "Importable" if "plotly" in sys.modules else "Non importé",
            "pdfplumber": "Importable" if "pdfplumber" in sys.modules else "Non importé",
            "PyPDF2": "Importable" if "PyPDF2" in sys.modules else "Non importé",
            "pypdf": "Importable" if "pypdf" in sys.modules else "Non importé",
        }
        
        package_df = pd.DataFrame(list(packages.items()), columns=["Package", "Version"])
        st.dataframe(package_df)
    except Exception as e:
        st.error(f"Erreur lors de la vérification des packages: {str(e)}")

# Vérifier si c'est un déploiement local ou Cloud
is_cloud = os.environ.get("STREAMLIT_DEPLOYMENT_TYPE") == "cloud"
st.subheader("Type de déploiement")
st.info("☁️ Déploiement Streamlit Cloud" if is_cloud else "🖥️ Déploiement local")

# Vérifier les fichiers existants
st.header("Structure du projet")
try:
    # Liste des fichiers importants à vérifier
    important_files = [
        "Home.py",
        "pages/test_api.py",
        "pages/1_📝_Brief.py",
        "pages/7_🤖_Assistant_IA.py",
        "requirements.txt",
        "utils.py"
    ]
    
    file_status = []
    for file in important_files:
        exists = os.path.exists(file)
        size = os.path.getsize(file) if exists else 0
        timestamp = time.ctime(os.path.getmtime(file)) if exists else "N/A"
        file_status.append({
            "Fichier": file,
            "Existe": "✅" if exists else "❌",
            "Taille": f"{size} octets" if exists else "0",
            "Dernière modification": timestamp
        })
    
    st.dataframe(pd.DataFrame(file_status))
except Exception as e:
    st.error(f"Erreur lors de la vérification des fichiers: {str(e)}")

# Vérifier la présence et la version de git
st.header("Informations Git")
try:
    git_version = subprocess.check_output(["git", "--version"]).decode().strip()
    st.code(git_version)
    
    # Récupérer la version Git
    commit_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    
    st.write(f"**Branche actuelle:** {branch}")
    st.write(f"**Dernier commit:** {commit_hash}")
    
    # Afficher les 5 derniers commits
    st.subheader("5 derniers commits")
    git_log = subprocess.check_output(["git", "log", "-n", "5", "--pretty=format:%h - %s (%ar)"]).decode().strip()
    st.code(git_log)
    
    # Vérifier si des fichiers ont été modifiés
    git_status = subprocess.check_output(["git", "status", "-s"]).decode().strip()
    if git_status:
        st.warning("⚠️ Il y a des fichiers modifiés non commités:")
        st.code(git_status)
    else:
        st.success("✅ Tous les fichiers sont commités")
        
except Exception as e:
    st.error(f"Erreur Git: {str(e)}")

# Vérifier les secrets disponibles
st.header("Secrets")
st.info("""
Cette section ne montre pas les valeurs des secrets pour des raisons de sécurité.
Elle indique uniquement si les clés sont définies dans st.secrets.
""")

try:
    available_secrets = []
    for key in ["DEEPSEEK_API_KEY", "GROQ_API_KEY", "GITHUB_TOKEN"]:
        try:
            exists = key in st.secrets
            value_status = "Défini" if exists else "Non défini"
            available_secrets.append({"Secret": key, "Statut": value_status})
        except:
            available_secrets.append({"Secret": key, "Statut": "Erreur d'accès"})
    
    st.dataframe(pd.DataFrame(available_secrets))
except Exception as e:
    st.error(f"Erreur lors de la vérification des secrets: {str(e)}")

# Section pour vérifier les performances
st.header("Test de performances")
if st.button("Exécuter test de performances"):
    with st.spinner("Test en cours..."):
        start_time = time.time()
        
        # Test pandas
        df = pd.DataFrame({"A": range(10000), "B": range(10000)})
        df_result = df.groupby(df["A"] % 10).sum()
        
        # Test boucle Python
        result = 0
        for i in range(100000):
            result += i
            
        end_time = time.time()
        duration = end_time - start_time
        
        st.success(f"Test complété en {duration:.2f} secondes")
        st.metric("Temps d'exécution", f"{duration:.2f}s")

# Section de notes additionnelles
st.header("Problèmes connus de déploiement")
st.info("""
Si votre application est bloquée sur "Your app is in the oven", voici quelques causes possibles:

1. **Problèmes avec requirements.txt** - Vérifiez s'il y a des versions incompatibles ou des packages problématiques
2. **Erreur de construction silencieuse** - Vérifiez les logs de build dans Streamlit Cloud
3. **Problème de mémoire** - Si l'app charge des fichiers volumineux au démarrage, elle peut dépasser les limites
4. **Timeout** - Si l'initialisation prend trop de temps, le déploiement peut échouer

Solutions possibles:
- Redeployer manuellement depuis l'interface Streamlit Cloud
- Vérifier qu'aucun import ou code au niveau global ne cause de plantage
- Considérer un petit commit de "no-op" pour déclencher un nouveau build
""")

st.divider()
st.caption("Diagnostic de déploiement créé pour aider avec les problèmes Streamlit Cloud")