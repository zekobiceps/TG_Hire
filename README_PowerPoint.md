# Guide de Génération PowerPoint - Reporting RH

## 📝 Fonctionnalité

La page **Reporting RH** permet désormais de générer automatiquement un fichier PowerPoint à partir d'un template prédéfini.

## 🎯 Comment utiliser

### 1. Préparer le template PowerPoint

Créez un fichier PowerPoint (.pptx) avec les placeholders suivants:

- `{{TABLEAU_BESOINS_ENTITES}}` - Sera remplacé par le tableau des besoins par entité avec les métriques
- `{{METRIC_TOTAL_POSTES}}` - Sera remplacé par le tableau Kanban des postes en cours

### 2. Dans Streamlit

1. Allez sur la page **📊 Reporting RH**
2. Uploadez votre fichier Excel avec les données de recrutement
3. Cliquez sur "Actualiser les Graphiques"
4. Dans la section "Génération PowerPoint":
   - Uploadez votre template PowerPoint
   - Cliquez sur "Générer le PowerPoint"
5. Téléchargez le fichier généré

## 🖼️ Ce qui est généré

### Tableau des Besoins par Entité
- Colonnes: Entité, Postes avant, Nouveaux postes, Postes pourvus, Postes en cours
- Ligne TOTAL en bas avec fond rouge (#9C182F)
- Format: Image PNG (1400x640px)

### Tableau Kanban
- 5 colonnes: Sourcing, Shortlisté, Signature DRH, Clôture, Désistement
- Cartes avec: Titre du poste, Entité-Lieu, Demandeur, Recruteur
- Format: Image PNG (1340x800px)

## ⚙️ Technique

Les visualisations sont générées avec PIL (Python Imaging Library) pour éviter les dépendances à Chrome/Chromium.

### Dépendances
- python-pptx
- pillow (PIL)
- pandas
- streamlit

### Fonctions principales
- `generate_table_image_simple(weekly_metrics)` - Génère l'image du tableau
- `generate_kanban_image_simple(df_recrutement)` - Génère l'image du Kanban
- `generate_powerpoint_report(df, template_path)` - Génère le PowerPoint complet

## 🎨 Personnalisation

Pour modifier les couleurs, ajustez dans le code:
- Couleur principale: `#9C182F` (rouge TGCC)
- Backgrounds: `#f9f9f9` (gris clair)
- Bordures: `#ddd` (gris moyen)

## 📊 Exemple de template

```
Slide 1: Page de garde
Slide 2: {{TABLEAU_BESOINS_ENTITES}} ← Tableau des entités
Slide 3: {{METRIC_TOTAL_POSTES}} ← Kanban des postes
Slide 4: Autres slides...
```

## 🔧 Limitations

- Les images sont générées avec des polices système (DejaVu Sans)
- Maximum 5 postes affichés par colonne du Kanban
- Les logos des entités ne sont pas inclus dans la version simplifée (limitation PIL vs HTML)
- Les noms d'entités sont tronqués à 20 caractères dans le tableau

## 💡 Conseils

- Gardez votre template simple et propre
- Les placeholders doivent être dans des zones de texte PowerPoint
- Les images générées remplacent complètement les placeholders
- Utilisez des placeholders suffisamment grands (minimum 10cm x 7cm)
