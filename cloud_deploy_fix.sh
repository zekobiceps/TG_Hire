#!/bin/bash

# Script de diagnostic et correction pour le déploiement Streamlit Cloud
# Ce script aide à identifier et corriger les problèmes courants de déploiement

echo "🔍 Démarrage du diagnostic pour Streamlit Cloud..."
echo "=================================================="

# Vérifier que nous sommes dans le répertoire du projet
if [ ! -f "Home.py" ] && [ ! -f "minimal_test.py" ]; then
    echo "❌ ERREUR: Ce script doit être exécuté depuis le répertoire racine du projet"
    exit 1
fi

# Vérifier requirements.txt
echo "📋 Vérification de requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERREUR: requirements.txt introuvable"
    exit 1
else
    echo "✅ requirements.txt trouvé"
    echo "Contenu:"
    cat requirements.txt
fi

# Vérifier les bibliothèques problématiques dans requirements.txt
echo -e "\n🔎 Recherche de bibliothèques potentiellement problématiques..."
PROBLEMATIC_LIBS=("tensorflow-gpu" "torch" "opencv-python" "psycopg2" "mysqlclient")
for lib in "${PROBLEMATIC_LIBS[@]}"; do
    if grep -q "$lib" requirements.txt; then
        echo "⚠️ Bibliothèque potentiellement problématique trouvée: $lib"
        echo "   → Considérez utiliser une alternative plus légère ou un import conditionnel"
    fi
done

# Créer une sauvegarde des fichiers importants
echo -e "\n💾 Création de sauvegardes..."
mkdir -p backup
cp Home.py backup/Home.py.bak 2>/dev/null || echo "Home.py non trouvé"
cp requirements.txt backup/requirements.txt.bak
echo "✅ Sauvegardes créées dans le dossier 'backup'"

# Vérifier la structure des dossiers
echo -e "\n📁 Vérification de la structure des dossiers..."
if [ ! -d "pages" ]; then
    echo "⚠️ Dossier 'pages' non trouvé. Vérifiez la structure de votre projet"
else
    echo "✅ Dossier 'pages' trouvé"
    echo "Contenu du dossier pages:"
    ls -la pages/
fi

# Vérifier si .streamlit existe
if [ ! -d ".streamlit" ]; then
    echo "⚠️ Dossier '.streamlit' non trouvé. Création..."
    mkdir -p .streamlit
    echo "✅ Dossier '.streamlit' créé"
else
    echo "✅ Dossier '.streamlit' trouvé"
fi

# Vérifier la configuration
if [ ! -f ".streamlit/config.toml" ]; then
    echo "⚠️ Fichier config.toml non trouvé. La configuration par défaut sera utilisée."
else
    echo "✅ Fichier config.toml trouvé"
fi

# Vérifier la présence de secrets.toml (ne pas afficher le contenu pour des raisons de sécurité)
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️ Fichier secrets.toml local non trouvé. Assurez-vous de configurer les secrets sur Streamlit Cloud"
else
    echo "✅ Fichier secrets.toml local trouvé (ne pas l'inclure dans Git!)"
fi

# Vérifier les fichiers Python problématiques
echo -e "\n🔍 Recherche d'imports problématiques..."
python_files=$(find . -name "*.py")
for file in $python_files; do
    if grep -q "^import torch" "$file" || grep -q "^from torch" "$file"; then
        echo "⚠️ Import torch trouvé dans $file"
        echo "   → Considérez un import conditionnel: 'try: import torch; except ImportError: torch = None'"
    fi
    if grep -q "^import tensorflow" "$file" || grep -q "^from tensorflow" "$file"; then
        echo "⚠️ Import tensorflow trouvé dans $file"
        echo "   → Considérez un import conditionnel: 'try: import tensorflow; except ImportError: tensorflow = None'"
    fi
done

# Vérifier l'état Git
echo -e "\n🔄 Vérification de l'état Git..."
if [ -d ".git" ]; then
    echo "✅ Dépôt Git trouvé"
    echo "Derniers commits:"
    git log -n 5 --oneline
    echo -e "\nBranche courante:"
    git branch --show-current
    echo -e "\nFichiers modifiés:"
    git status -s
else
    echo "❌ Dépôt Git non trouvé"
fi

# Créer un fichier minimal pour le déploiement si nécessaire
if [ ! -f "minimal_test.py" ]; then
    echo -e "\n📝 Création d'un fichier minimal_test.py pour tester le déploiement..."
    echo 'import streamlit as st
st.title("Test minimal Streamlit")
st.success("Si vous voyez cette page, le déploiement minimal fonctionne!")
st.write("Vérifiez les logs de déploiement pour plus de détails.")' > minimal_test.py
    echo "✅ Fichier minimal_test.py créé"
fi

# Proposer des solutions
echo -e "\n🛠️ Solutions recommandées:"
echo "1. Redéployer l'application sur Streamlit Cloud"
echo "2. Vérifier les secrets configurés sur Streamlit Cloud (sans les copier-coller dans le chat!)"
echo "3. Tester avec minimal_test.py comme page d'entrée sur Streamlit Cloud"
echo "4. Vérifier les logs de déploiement sur Streamlit Cloud"
echo "5. Ajouter progressivement les fonctionnalités pour identifier le problème exact"

echo -e "\n✅ Diagnostic terminé!"
echo "Exécutez 'streamlit run minimal_test.py' pour tester localement le fichier minimal"
echo "=================================================="