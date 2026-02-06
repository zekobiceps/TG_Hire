import pandas as pd
import json

def find_security_profiles(file_path):
    df = pd.read_excel(file_path)
    
    keywords = [
        'sécurité', 'cyber', 'rssi', 'iso 27001', 'iso 27002', 'nist', 'ebios', 
        'cissp', 'cism', 'siem', 'soc', 'edr', 'pam', 'iam', 'firewall', 
        'pentest', 'vulnérabilité'
    ]
    
    # Remplacer les NaN par des chaînes vides pour éviter les erreurs
    df['profile_summary'] = df['profile_summary'].fillna('')
    
    # Filtrer les profils
    security_profiles = df[df['profile_summary'].str.lower().str.contains('|'.join(keywords))]
    
    # Sélectionner les colonnes pertinentes pour l'affichage
    result = security_profiles[['candidate_name', 'years_experience', 'profile_summary']]
    
    print(result.to_json(orient='records'))

find_security_profiles('/workspaces/TG_Hire/LOGO/CVS/classification_results.xlsx')
