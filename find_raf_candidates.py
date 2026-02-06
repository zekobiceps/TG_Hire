import pandas as pd
import sys

try:
    df = pd.read_csv('LOGO/CVS/classification_results.csv')
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)

# Clean and filter experience
def safe_exp(x):
    try:
        return float(str(x).replace('ans', '').strip())
    except:
        return 0.0

df['years_experience_clean'] = df['years_experience'].apply(safe_exp)

# Strict criteria: 4 <= exp <= 12
df_filtered = df[
    (df['years_experience_clean'] >= 4) & 
    (df['years_experience_clean'] <= 12)
].copy()

# Scoring keywords based on Job Description
# "Responsable Administratif et Financier", "RAF", "Finance", "Comptabilité", "Contrôle de gestion"
keywords = {
    "raf": 5,
    "responsable administratif et financier": 5,
    "finance": 2,
    "financier": 2,
    "comptab": 3,
    "contrôle de gestion": 3,
    "controle de gestion": 3,
    "trésorerie": 2,
    "audit": 2,
    "administratif": 1,
    "gestion": 1
}

def calculate_score(row):
    text = f"{row['candidate_name']} {row['sub_category']} {row['profile_summary']}".lower()
    score = 0
    matches = []
    
    for kw, points in keywords.items():
        if kw in text:
            score += points
            matches.append(kw)
            
    return score

df_filtered['score'] = df_filtered.apply(calculate_score, axis=1)

# Sort by score
results = df_filtered[df_filtered['score'] > 0].sort_values(by='score', ascending=False)

print(f"Analyse terminée. {len(results)} profils trouvés correspondant aux critères (4-12 ans d'expérience + mots-clés).")

if len(results) == 0:
    print("Aucun candidat trouvé.")
else:
    print("Top candidats :\n")
    for i, (_, row) in enumerate(results.head(10).iterrows(), 1):
        print(f"#{i} NOM: {row['candidate_name']}")
        print(f"   FICHIER: {row['file']}")
        print(f"   EXPÉRIENCE: {row['years_experience']} ans")
        print(f"   SCORE: {row['score']}")
        print(f"   CATÉGORIE: {row['macro_category']} > {row['sub_category']}")
        print(f"   RÉSUMÉ: {row['profile_summary']}")
        print("-" * 50)
