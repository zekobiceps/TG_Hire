import fitz  # PyMuPDF
import re
import os

candidate_files = {
    "Kawtar SOURDOU": "68dc09195bb8b.pdf",
    "Marwa MOHAMED": "68e0076e8f402.pdf",
    # Including key comparison candidates to show why they were preferred
    "Yassine MOULY": "68e4123fc251c.pdf", 
    "Ghassane El Houasli": "68efc607b1303.pdf"
}

base_path = "/workspaces/TG_Hire/LOGO/CVS/"

jd_criteria = {
    "1. Comptabilité & Audit (Technique)": {
        "keywords": [
            r"audit", r"comptabilit", r"fiscal", r"expert-comptable", r"dscg", 
            r"commissaire aux comptes", r"clôture", r"bilan", r"consolidation"
        ],
        "weight": 2.5
    },
    "2. Family Office / Investissement (Métier)": {
        "keywords": [
            r"family office", r"holding", r"immobilier", r"real estate", 
            r"private equity", r"pe ", r"investissement", r"participation"
        ],
        "weight": 3.0
    },
    "3. Gestion & Contrôle (Opérationnel)": {
        "keywords": [
            r"contrôle de gestion", r"reporting", r"trésorerie", r"cash", 
            r"procédure", r"budget", r"kpi", r"performance"
        ],
        "weight": 2.0
    }
}

def extract_text(filepath):
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.lower()
    except Exception as e:
        return ""

print("# Analyse Comparative : Kawtar S. & Marwa M. vs Sélection Actuelle\n")

results = []

for name, filename in candidate_files.items():
    filepath = os.path.join(base_path, filename)
    content = extract_text(filepath)
    
    candidate_scores = {"name": name, "total": 0, "details": {}}
    
    for criteria, data in jd_criteria.items():
        matches = []
        for kw in data["keywords"]:
            if re.search(kw, content):
                matches.append(kw.replace("\\", ""))
        
        score = 0
        if len(matches) >= 3: score = 1.0
        elif len(matches) >= 1: score = 0.5
        
        weighted_score = score * data["weight"]
        candidate_scores["total"] += weighted_score
        candidate_scores["details"][criteria] = {
            "score": score,
            "matches": matches[:3] # Show top 3 matches
        }
    
    results.append(candidate_scores)

# Sort by total score
results.sort(key=lambda x: x["total"], reverse=True)

for res in results:
    print(f"## {res['name']} (Score: {res['total']:.1f})")
    for criteria, details in res['details'].items():
        status = "✅" if details['score'] == 1.0 else "⚠️" if details['score'] == 0.5 else "❌"
        matches_str = ", ".join(details['matches']) if details['matches'] else "Aucun"
        print(f"- {criteria} : {status} ({matches_str})")
    print("\n")

print("\n### Pourquoi Kawtar et Marwa n'étaient pas dans le Top 3 ?\n")
print("Analyse en cours...")
