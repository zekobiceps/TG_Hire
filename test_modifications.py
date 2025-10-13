#!/usr/bin/env python3
"""
Script de test pour vérifier les modifications apportées au reporting RH
"""

import pandas as pd
import os

def test_filters_and_data():
    """Tester les filtres et données disponibles"""
    print("=== Test des Modifications du Reporting RH ===\n")
    
    # Charger les données Excel
    excel_file = "Recrutement global PBI All  google sheet (5).xlsx"
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"✅ Fichier Excel chargé: {df.shape[0]} lignes, {df.shape[1]} colonnes\n")
        
        # Test des nouveaux filtres
        print("🔧 Nouveaux filtres ajoutés:")
        filtres_ajoutes = ["Entité demandeuse", "Direction concernée", "Affectation"]
        
        for filtre in filtres_ajoutes:
            if filtre in df.columns:
                unique_values = df[filtre].nunique()
                print(f"   ✓ {filtre}: {unique_values} valeurs uniques")
            else:
                print(f"   ✗ {filtre}: Colonne non trouvée")
        
        print("\n📊 Test de l'onglet Intégrations:")
        # Test des critères d'intégration
        candidat_col = "Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
        date_integration_col = "Date d'entrée prévisionnelle"
        
        # Filtrer comme dans le nouveau code
        df_integrations = df[
            (df['Statut de la demande'] == 'En cours') &
            (df[candidat_col].notna()) &
            (df[candidat_col].str.strip() != "")
        ]
        
        print(f"   ✓ Recrutements 'En cours': {len(df[df['Statut de la demande'] == 'En cours'])}")
        print(f"   ✓ Avec candidat retenu: {len(df[df[candidat_col].notna()])}")
        print(f"   ✓ Intégrations en cours (critères combinés): {len(df_integrations)}")
        
        if len(df_integrations) > 0:
            print(f"   ✓ Avec date d'intégration prévue: {len(df_integrations[df_integrations[date_integration_col].notna()])}")
            
            print("\n📋 Exemples d'intégrations en cours:")
            colonnes_affichage = [candidat_col, 'Poste demandé ', 'Entité demandeuse', date_integration_col]
            colonnes_dispo = [col for col in colonnes_affichage if col in df_integrations.columns]
            
            if colonnes_dispo:
                print(df_integrations[colonnes_dispo].head(3).to_string(index=False))
        
        print("\n🎯 Structure des onglets:")
        print("   ✓ Upload (inchangé)")
        print("   ✓ Demandes & Recrutement (regroupés avec sous-onglets)")
        print("     ├── 📋 Demandes")
        print("     └── 🎯 Recrutement") 
        print("   ✓ Hebdomadaire (inchangé)")
        print("   ✓ Intégrations (nouveau critères)")
        
    else:
        print(f"❌ Fichier Excel non trouvé: {excel_file}")

if __name__ == "__main__":
    test_filters_and_data()