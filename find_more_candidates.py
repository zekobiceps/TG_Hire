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
excluded_candidates = [
    # Top Tier
    "Yassine MOULY", "Soukaina ROHAINE", "Ghassane El Houasli", "Mounia Aboutaggedine", 
    # Mid Tier
    "Jihane BEKKAOUI", "Hafsa Tadlaoui", "BOUBGA Hicham", "Hamza ABOUSALHAM",
    # Specifics discussed
    "Kawtar SOURDOU", "Marwa MOHAMED", 
    # Last batch
    "Naima Rhoubal", "Yassine Idaras", "ALAMI HOUSSAM", 
    # Others previously filtered out but seen
    "Salma BENABDELLAH", "Sophia HERRERO", "Chihab Hind", "Adam SOUHAIL", "Ali SERRAT", "Hiba ZARAI", "Najah FIRDAOUS"
]

patterns_potential = {
    "Real Estate Finance": [r"immobilier", r"real estate", r"asset management", r"gestion locative"],
    "Audit & Rigueur": [r"cabinet", r"audit", r"interne", r"contrôle", r"big 4"],
    "Investissement": [r"private equity", r"fonds", r"valorisation", r"middle office"]
}

patterns_role_junior_lead = [
    r"responsable", r"manager", r"chargé de mission finance", r"analyste senior"
]

def calculate_score(row):
    candidate_name = str(row['candidate_name'])
    for excluded in excluded_candidates:
        if excluded.lower() in candidate_name.lower():
            return -100, [] # Exclude

    summary = str(row['profile_summary']).lower()
    
    # Filter out heavy IT profiles that often pollute results
    if re.search(r"java|python|devops|fullstack|data engineer", summary):
        return -100, []

    score = 0
    matches = []
    
    # Check for sector relevance
    for category, keywords in patterns_potential.items():
        for kw in keywords:
            if re.search(kw, summary):
                score += 10
                matches.append(f"{category}:{kw}")
                break
    
    # Check for title/potential
    for kw in patterns_role_junior_lead:
        if re.search(kw, summary):
            score += 5
            matches.append(f"ROLE:{kw}")
            break

    # Bonus for "Finance" core skills to ensure we don't get property managers
    if re.search(r"comptabilit|finance|gestion|reporting", summary):
        score += 5
    else:
        score = 0 # Reset if no finance core

    return score, matches

results = df.apply(calculate_score, axis=1)
df['score'] = results.apply(lambda x: x[0])
df['matched_terms'] = results.apply(lambda x: x[1])

# Filter: Broader experience range to find hidden fits
candidates = df[
    (df['years_experience_cleaned'] >= 3) & 
    (df['years_experience_cleaned'] <= 12) & 
    (df['score'] >= 15)
].copy()

candidates = candidates.sort_values(by=['score', 'years_experience_cleaned'], ascending=False)

print(f"Found {len(candidates)} additional candidates.\n")

for idx, row in candidates.head(15).iterrows():
    print(f"--- {row['candidate_name']} ({row['years_experience_cleaned']} ans) ---")
    print(f"File: {row['file']}")
    print(f"Matches: {', '.join(str(m) for m in row['matched_terms'])}")
    print(f"Summary: {str(row['profile_summary'])[:300]}...")
    print("\n")
