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
        val = str(x).lower().replace('ans', '').strip()
        if not val or val == 'nan': return 0.0
        return float(val) 
    except:
        return 0.0

df['years_experience_cleaned'] = df['years_experience'].apply(clean_experience)

# Define regex patterns for scoring
patterns_raf = [
    r"responsable administratif et financier",
    r"raf",
]

patterns_finance_mid = [
    r"comptabilit", r"finance", r"contrôle de gestion", r"audit", 
    r"expert comptable", r"cabinet", r"dscg"
]

patterns_family_office_light = [
    r"family office", r"holding", r"immobilier", r"investissement"
]

patterns_negative = [
    r"java", r"python", r"devops", r"fullstack", r"react", r"angular", 
    r"ingénieur", r"technicien", r"commercial", r"marketing", 
    r"data scientist", r"développeur", r"consultant si"
]

def calculate_score(row):
    summary = str(row['profile_summary']).lower() if pd.notna(row['profile_summary']) else ""
    sub_category = str(row['sub_category']).lower() if pd.notna(row['sub_category']) else ""
    
    # Force check for "Non classé" candidates
    is_unclassified = "non classé" in sub_category or "divers" in sub_category

    score = 0
    matched_terms = []

    # Strict negative filter to remove IT/Engineering profiles
    for pat in patterns_negative:
        if re.search(pat, summary):
            return -100, ["NEGATIVE_MATCH"]

    # Title Match
    for pat in patterns_raf:
        if re.search(pat, summary):
            score += 20
            matched_terms.append(f"TITLE:{pat}")
            
    # Mid-Senior Finance Match
    for pat in patterns_finance_mid:
        if re.search(pat, summary):
            score += 10
            matched_terms.append(f"FINANCE:{pat}")

    # Sector Match
    for pat in patterns_family_office_light:
        if re.search(pat, summary):
            score += 15
            matched_terms.append(f"SECTOR:{pat}")

    return score, matched_terms

# Apply scoring
results = df.apply(calculate_score, axis=1)
df['score'] = results.apply(lambda x: x[0])
df['matched_terms'] = results.apply(lambda x: x[1])

# Filter based on score and experience
# Target Audience: 4 to 10 years experience (Mid-Senior, not Overqualified)
candidates = df[
    (df['years_experience_cleaned'] >= 4) & 
    (df['years_experience_cleaned'] <= 10) & 
    (df['score'] >= 20) 
].copy()

# Sort by score desc
candidates = candidates.sort_values(by=['score', 'years_experience_cleaned'], ascending=False)

print(f"Found {len(candidates)} mid-level candidates (4-10 years) matching criteria.\n")

if not candidates.empty:
    for idx, row in candidates.head(10).iterrows():
        print(f"--- CANDIDATE: {row['candidate_name']} ({row['years_experience_cleaned']} ans) ---")
        print(f"File: {row['file']}")
        print(f"Category: {row['sub_category']}")
        print(f"Score: {row['score']}")
        print(f"Matched terms: {', '.join(str(x) for x in row['matched_terms'])}")
        print(f"Summary: {str(row['profile_summary'])[:300]}...")
        print("-" * 50)
else:
    print("No strong matches found.")
