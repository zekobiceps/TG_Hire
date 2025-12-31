# Installation de Chromium pour génération PowerPoint

## 🎯 Pourquoi Chromium?

La génération PowerPoint utilise `html2image` pour capturer les visualisations Streamlit exactes (avec logos et formatage) et les convertir en images PNG.

## 📦 Installation

### En développement (Codespaces/Local)

```bash
sudo apt-get update
sudo apt-get install -y chromium chromium-driver
```

### En production (Streamlit Cloud / serveur)

Créez un fichier `.aptfile` à la racine du projet avec:
```
chromium
chromium-driver
```

Streamlit Cloud installera automatiquement ces packages au déploiement.

## 🔄 Fallback automatique

Si Chromium n'est pas disponible, le système basculera automatiquement sur **PIL** pour générer des images simplifiées (sans logos mais fonctionnelles).

Messages dans Streamlit:
- ⚠️ "html2image non disponible, utilisation de PIL à la place"
- 📊 "Tentative avec PIL..."

## 🐛 Résolution de problèmes

### Erreur: "Failed to find a seemingly valid chrome executable"

**Solution 1**: Vérifier que Chromium est installé
```bash
which chromium
# Devrait retourner: /usr/bin/chromium
```

**Solution 2**: Si Chromium n'est pas disponible, le fallback PIL sera utilisé automatiquement

### Erreur: "No module named 'html2image'"

```bash
pip install html2image
```

Ou ajoutez `html2image` dans `requirements.txt` (déjà fait).

## 📊 Différences entre les modes

### Mode html2image + Chromium (Préféré)
✅ Logos des entités affichés
✅ Formatage exact de Streamlit
✅ Couleurs et styles identiques
✅ Layout Kanban exact

### Mode PIL (Fallback)
⚠️ Pas de logos (limitation PIL)
✅ Tableaux basiques fonctionnels
✅ Couleurs principales (#9C182F)
✅ Génération rapide et fiable

## 🚀 Test

Pour vérifier si html2image fonctionne:

```python
from html2image import Html2Image
import tempfile

hti = Html2Image(
    output_path=tempfile.gettempdir(),
    browser_executable='/usr/bin/chromium',
    custom_flags=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--headless']
)
print("✅ html2image fonctionne!")
```

## 📝 Configuration actuelle

Le code détecte automatiquement la disponibilité de Chromium:

```python
try:
    # Essayer html2image avec Chromium
    hti = Html2Image(...)
    image = hti.screenshot(...)
except Exception as e:
    # Fallback vers PIL
    image = generate_image_simple(...)
```

Aucune configuration manuelle nécessaire! 🎉
