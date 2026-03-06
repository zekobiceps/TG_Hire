import fitz  # PyMuPDF
import re
import os

candidate_files = {
    "Yassine MOULY": "68e4123fc251c.pdf",
    "Soukaina ROHAINE": "68e610662042c.pdf",
    "Ghassane El Houasli": "68efc607b1303.pdf",
    "Mounia Aboutaggedine": "68d6d2e5dfe91.pdf"
}

base_path = "/workspaces/TG_Hire/LOGO/CVS/"

jd_data = {
    "1. Gestion Administrative & Financière": {
        "keywords": [
            r"gestion administrative", r"administrative management", r"administrator", 
            r"gestion financière", r"financial management", 
            r"facturation", r"billing", r"invoicing",
            r"encaissement", r"collection", r"recouvrement",
            r"paiement", r"payment", 
            r"trésorerie", r"treasury", r"cash management", r"cash flow",
            r"procédure", r"process", r"procedure"
        ],
        "weight": 2.0
    },
    "2. Comptabilité & Fiscalité": {
        "keywords": [
            r"comptabilit", r"accounting", r"accountancy",
            r"clôture", r"closing", 
            r"fiscal", r"tax", r"taxation",
            r"audit", 
            r"déclaration", r"declaration", r"return",
            r"bilan", r"balance sheet", 
            r"liasse fiscale", 
            r"tva", r"vat",
            r"social", r"payroll", r"paie"
        ],
        "weight": 2.0 
    },
    "3. Contrôle & Reporting": {
        "keywords": [
            r"contrôle de gestion", r"controlling", r"financial control",
            r"reporting", r"report", 
            r"indicateur", r"indicator", r"kpi", 
            r"budget", r"p&l", 
            r"analyse financière", r"financial analysis",
            r"performance"
        ],
        "weight": 2.0
    },
    "4. Juridique & Corporate": {
        "keywords": [
            r"juridique", r"legal", 
            r"contrat", r"contract", 
            r"kyc", r"aml", 
            r"assemblée générale", r"general assembly", r"ag",
            r"conseil d'administration", r"board", 
            r"corporate", r"secrétariat juridique", r"company secretary"
        ],
        "weight": 1.0
    },
    "5. Relations Tiers & Audit": {
        "keywords": [
            r"banque", r"bank", 
            r"commissaire aux comptes", r"cac", r"auditor", r"auditeur", 
            r"expert-comptable", r"chartered accountant", r"cpa", 
            r"cabinet", r"firm", r"big4", r"big 4", r"ey", r"deloitte", r"pwc", r"kpmg"
        ],
        "weight": 1.0
    },
    "6. Spécifique Family Office": {
        "keywords": [
            r"family office", r"holding", 
            r"multi-entité", r"multi-entity", r"filiale", r"subsidiary",
            r"spv", r"vehicle",
            r"participation", r"equity", 
            r"immobilier", r"real estate", 
            r"private equity", r"pe", 
            r"investissement", r"investment"
        ],
        "weight": 3.0
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

print("# Analyse Comparative Détaillée\n")

for name, filename in candidate_files.items():
    filepath = os.path.join(base_path, filename)
    content = extract_text(filepath)
    
    print(f"## 👤 {name}")
    print(f"*Fichier: {filename}*\n")
    
    total_weighted_points = 0
    max_possible_points = sum(d["weight"] for d in jd_data.values()) # Assuming max 1.0 score per category
    
    print("| Domaine | Statut | Mots-clés trouvés |")
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
            status = "🟢 Excellent"
        elif count >= 1:
            score = 0.5
            status = "🟡 Partiel"
        
        total_weighted_points += score * data["weight"]
        
        found_str = ", ".join(list(found)[:4])
        print(f"| {mission} | {status} | {found_str} |")

    final_score = (total_weighted_points / max_possible_points) * 10
    print(f"\n**Note Globale d'Adéquation : {final_score:.1f}/10**\n")
    print("---\n")
