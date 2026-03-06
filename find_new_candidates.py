import pandas as pd
import sys
import re

# Load the CSV
try:
    df = pd.read_csv('/workspaces/TG_Hire/LOGO/CVS/classification_results.csv')
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)

# Clean up experience column
def clean_experience(x):
    try:
        val = str(x).lower().replace('ans', '').replace('+', '').strip()
        if not val or val == 'nan': return 0.0
        return float(val)
    except:
        return 0.0

df['years_experience_cleaned'] = df['years_experience'].apply(clean_experience)

# List of candidates already discussed (to exclude)
excluded_names = [
    "Yassine MOULY", "Soukaina ROHAINE", "Ghassane El Houasli", "Mounia Aboutaggedine", 
    "Kawtar SOURDOU", "Marwa MOHAMED", "Jihane BEKKAOUI", "Hafsa Tadlaoui", 
    "Hamza ABOUSALHAM", "BOUBGA Hicham", "Salma BENABDELLAH", "Sophia HERRERO", 
    "Chihab Hind", "Adam SOUHAIL", "Ali SERRAT", "Hiba ZARAI", "Najah FIRDAOUS",
    "Rihab HMIMIDI", "AMINE BENABDALLAH"
]

# Regex Patterns
patterns_role = [
    r"responsable comptable", r"chef de mission", r"senior auditor", r"auditeur senior",
    r"finance manager", r"responsable financier", r"contrôleur financier",
    r"daf", r"directeur administratif et financier"
]

patterns_skills = [
    r"comptabilit", r"clôture", r"bilan", r"fiscal", r"social", 
    r"cabinet", r"dscg", r"expert comptable", r"big 4", r"kpmg", r"ey", r"deloitte", r"pwc"
]

patterns_sector = [
    r"immobilier", r"real estate", r"holding", r"family office", r"investissement"
]

def calculate_score(row):
    candidate_name = str(row['candidate_name'])
    
    # Exclude previously discussed candidates (fuzzy matching by name parts if needed, but exact strings for now)
    for excluded in excluded_names:
        if excluded.lower() in candidate_name.lower():
            return -100, []

    summary = str(row['profile_summary']).lower() if pd.notna(row['profile_summary']) else ""
    
    score = 0
    matches = []
    
    # Role Match (High Weight)
    for pat in patterns_role:
        if re.search(pat, summary):
            score += 20
            matches.append(f"ROLE:{pat}")
            break # Count one role max
            
    # Skills Match
    for pat in patterns_skills:
        if re.search(pat, summary):
            score += 5
            matches.append(pat)

    # Sector Match (Bonus)
    for pat in patterns_sector:
        if re.search(pat, summary):
            score += 10
            matches.append(f"SECTOR:{pat}")

    return score, matches

results = df.apply(calculate_score, axis=1)
df['score'] = results.apply(lambda x: x[0])
df['matched_terms'] = results.apply(lambda x: x[1])

# Filter: Experience 4 to 15 years, Score > 20
candidates = df[
    (df['years_experience_cleaned'] >= 3) & 
    (df['score'] >= 15)
].copy()

candidates = candidates.sort_values(by=['score', 'years_experience_cleaned'], ascending=False)

print(f"Found {len(candidates)} new potential candidates.\n")

for idx, row in candidates.head(10).iterrows():
    print(f"--- {row['candidate_name']} ({row['years_experience_cleaned']} ans) ---")
    print(f"File: {row['file']}")
    print(f"Score: {row['score']}")
    print(f"Matches: {', '.join(str(m) for m in row['matched_terms'][:5])}")
    print(f"Summary: {str(row['profile_summary'])[:300]}...")
    print("\n")
