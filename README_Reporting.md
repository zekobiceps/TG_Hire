# 📊 Reporting RH Power BI Style

## Description

Ce reporting a été créé pour reproduire les visualisations Power BI partagées, avec deux onglets principaux :

### 🎯 Onglet 1: Recrutements (État Clôture)
Basé sur l'image 1 fournie, cet onglet affiche :
- **KPIs principaux** : Nombre de recrutements, postes demandés, directions concernées
- **Évolution des recrutements** : Graphique en barres par mois
- **Modalités de recrutement** : Répartition en camembert (Cooptation, Candidature spontanée, Sourcing, etc.)
- **Canaux de publication** : Graphique en donut (Site TGCC, Non publié, etc.)
- **Candidats présélectionnés** : Indicateur de performance avec gauge
- **Délai moyen de recrutement** : Affichage en jours

### 📋 Onglet 2: Demandes de Recrutement  
Basé sur l'image 2 fournie, cet onglet affiche :
- **KPI central** : Nombre total de demandes (style grand chiffre)
- **Statut des demandes** : Répartition par statut (Clôture, Dépriorisé, Annulé, En cours)
- **Raison du recrutement** : Comparaison (création, remplacement, restructuration)
- **Évolution des demandes** : Graphique en barres par mois
- **Comparaison par direction** : Top directions demandeuses
- **Comparaison par poste** : Top postes demandés

### 📊 Onglet 3: Intégrations
Onglet supplémentaire pour le suivi des intégrations basé sur le fichier CSV :
- **KPIs d'intégration** : Total, en cours, complets, documents manquants
- **Évolution des intégrations** : Timeline par mois et statut
- **Répartition par affectation** : Graphique en secteurs
- **Données détaillées** : Tableau complet des intégrations

## Sources de données

1. **Excel** : `Recrutement global PBI All google sheet (5).xlsx`
   - 1230 lignes de données de recrutement
   - 35 colonnes avec informations complètes du processus
   
2. **CSV** : `2025-10-09T20-31_export.csv`
   - 65 lignes de données d'intégration
   - 11 colonnes avec suivi des documents et relances

## Fonctionnalités

### Filtres dynamiques
- **Période de recrutement** : Filtrage par année
- **Entité demandeuse** : Sélection par entité (TGCC, TGEM, etc.)
- **Direction concernée** : Tous les niveaux disponibles

### Visualisations interactives
- Graphiques Plotly interactifs
- Couleurs coordonnées selon les standards Power BI
- Responsive design adaptatif
- Export de données disponible

### Navigation
- Interface à onglets pour une navigation claire
- Sidebar avec filtres contextuels
- Métriques en temps réel

## Installation et utilisation

```bash
# Installer les dépendances
pip install streamlit pandas plotly openpyxl

# Lancer l'application
streamlit run pages/Reporting_RH_PowerBI.py --server.port 8503
```

## Structure des fichiers

```
/workspaces/TG_Hire/
├── pages/
│   └── Reporting_RH_PowerBI.py      # Application principal
├── 2025-10-09T20-31_export.csv     # Données d'intégration
├── Recrutement global PBI All...xlsx # Données de recrutement
└── README_Reporting.md              # Cette documentation
```

## Données analysées

### Statuts de demandes
- **Clôture** : 800 demandes (65%)
- **Annulé** : 209 demandes (17%)  
- **Dépriorisé** : 171 demandes (14%)
- **En cours** : 50 demandes (4%)

### Modalités de recrutement (top 5)
1. Cooptation : 260 (25%)
2. Candidature spontanée : 173 (17%)
3. Sourcing : 159 (15%)
4. Ex-stagiaire TGCC : 129 (12%)
5. CVthèque : 70 (7%)

### Directions les plus actives
1. Direction Zone : 342 demandes
2. Direction Qualité et HSE : 193 demandes
3. Direction technique : 85 demandes
4. Direction Décomptes et Métrés : 53 demandes

## Améliorations futures

- [ ] Ajout de filtres par trimestre
- [ ] Export Excel avec formatage
- [ ] Alertes automatiques pour les délais
- [ ] Intégration temps réel avec Google Sheets
- [ ] Dashboard mobile optimisé

---
*Créé le 10 octobre 2025 - Basé sur les maquettes Power BI fournies*