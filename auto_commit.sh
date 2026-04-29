#!/bin/bash

# Script pour automatiser l'ajout, le commit et le push des changements
# Usage: ./auto_commit.sh "Votre message de commit ici"

# Vérification qu'un message de commit a été fourni
if [ -z "$1" ]
then
    echo "Erreur: Veuillez fournir un message de commit"
    echo "Usage: ./auto_commit.sh \"Votre message de commit ici\""
    exit 1
fi

# Ajouter tous les fichiers modifiés
echo "Ajout des fichiers modifiés..."
git add .

# Vérifier s'il y a des changements à commiter
if git diff-index --quiet HEAD --; then
    echo "Aucune modification détectée. Rien à commiter."
    exit 0
fi

# Créer le commit avec le message fourni
echo "Création du commit..."
git commit -m "$1"

# Pousser les changements vers le dépôt distant
echo "Push vers le dépôt distant..."
git push origin main

echo "✅ Terminé!"