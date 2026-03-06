import fitz  # PyMuPDF
import re
import os

candidate_files = {
    "Soukaina ROHAINE": "68e610662042c.pdf",
    "BOUBGA Hicham": "68ef911880c2f.pdf",
    "Jihane BEKKAOUI": "68ed36b68a573.pdf", # Nice Profile for corporate accounting
    "Ghassane El Houasli": "68efc607b1303.pdf", # Back in the list, fit nicely in experience range
    "Hafsa Tadlaoui": "68dbeb65de96b.pdf" # Audit background
}

base_path = "/workspaces/TG_Hire/LOGO/CVS/"

jd_data = {
    "1. Admin & Gestion (Family Office)": {
        "keywords": [
            r"gestion administrative", r"facturation", r"encaissement", r"paiement", 
            r"trésorerie", r"procédure", r"family office", r"holding", r"multi-entité"
        ],
        "weight": 3.0
    },
    "2. Comptabilité & Technique": {
        "keywords": [
            r"comptabilit", r"clôture", r"fiscal", r"audit", 
            r"déclaration", r"bilan", r"dscg", r"expert-comptable"
        ],
        "weight": 2.5
    },
    "3. Investissement & Juridique": {
        "keywords": [
            r"juridique", r"contrat", r"corporate", 
            r"immobilier", r"private equity", r"investissement"
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

print("# Analyse Ciblée (Profils Intermédiaires 4-10 ans)\n")

for name, filename in candidate_files.items():
    filepath = os.path.join(base_path, filename)
    content = extract_text(filepath)
    
    print(f"## 👤 {name}")
    print(f"*Fichier: {filename}*\n")
    
    total = 0
    max_pts = sum(d["weight"] for d in jd_data.values())
    
    print("| Axe | Évaluation | Détails |")
    print("|---|---|---|")
    
    for mission, data in jd_data.items():
        found = set()
        for kw in data["keywords"]:
            if re.search(kw, content):
                found.add(kw.replace("\\", ""))
        
        count = len(found)
        score = 0
        status = "🔴"
        
        if count >= 3:
            score = 1.0
            status = "🟢 Fort"
        elif count >= 1:
            score = 0.5
            status = "🟡 Moyen"
        
        total += score * data["weight"]
        
        found_str = ", ".join(list(found)[:4])
        print(f"| {mission} | {status} | {found_str} |")

    final = (total / max_pts) * 10
    print(f"\n**Note: {final:.1f}/10**\n")
    print("---\n")
