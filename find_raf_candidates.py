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
    r"\braf\b",
]

patterns_finance_strong = [
    r"comptabilit", r"finance", r"contrôle de gestion", r"audit", 
    r"trésorerie", r"consolidation", r"expert comptable", r"dscg", r"daf"
]

patterns_bonus = [
    r"family office", r"holding", r"multi-entit", r"immobilier", 
    r"investissements", r"spv", r"private equity", 
]

patterns_negative = [
    r"java", r"python", r"devops", r"fullstack", r"react", r"angular", 
    r"administrateur syst", r"technicien support", r"helpdesk", r"développeur"
]

def calculate_score(row):
    summary = str(row['profile_summary']).lower() if pd.notna(row['profile_summary']) else ""
    sub_category = str(row['sub_category']).lower() if pd.notna(row['sub_category']) else ""
    
    score = 0
    matched_terms = []

    # Check for RAF titles (High value)
    for pat in patterns_raf:
        if re.search(pat, summary):
            score += 30
            matched_terms.append(f"TITLE:{pat}")
            
    # Check for Strong Finance keywords
    for pat in patterns_finance_strong:
        if re.search(pat, summary):
            score += 10
            matched_terms.append(f"STRONG:{pat}")

    # Check for Bonus keywords
    for pat in patterns_bonus:
        if re.search(pat, summary):
            score += 15
            matched_terms.append(f"BONUS:{pat}")
            
    # IMPORTANT: Apply negative penalty AFTER positive matches calculation
    # Only verify negative patterns if the score is somewhat relevant, or just always apply.
    for pat in patterns_negative:
        if re.search(pat, summary):
            # If it's a strong IT profile, nuke the score
            score = -100
            matched_terms.append("NEGATIVE_MATCH")
            break

    return score, matched_terms

# Apply scoring
results = df.apply(calculate_score, axis=1)
df['score'] = results.apply(lambda x: x[0])
df['matched_terms'] = results.apply(lambda x: x[1])

# Filter based on score and experience
# Needs reasonable experience (3+) and decent match score
candidates = df[
    (df['years_experience_cleaned'] >= 3) & 
    (df['score'] >= 20)  # Must have some finance relevance
].copy()

# Sort by score desc
candidates = candidates.sort_values(by=['score', 'years_experience_cleaned'], ascending=False)

print(f"Found {len(candidates)} candidates matching criteria out of {len(df)} total files.\n")

if not candidates.empty:
    for idx, row in candidates.head(10).iterrows():
        print(f"--- CANDIDATE: {row['candidate_name']} ({row['years_experience_cleaned']} ans) ---")
        print(f"File: {row['file']}")
        print(f"Score: {row['score']}")
        print(f"Matched terms: {', '.join(str(x) for x in row['matched_terms'])}")
        print(f"Summary: {str(row['profile_summary'])[:400]}...")
        print("-" * 50)
else:
    print("No strong matches found. Check keywords or criteria.")
