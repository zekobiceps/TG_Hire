import fitz
import re
import os

SCAN_LIMIT = 200

# Strict blacklist based on user reports
FORBIDDEN_WORDS = {
    'cv', 'curriculum', 'vitae', 'resume', 'profil', 'profile',
    'expérience', 'experiences', 'experience', 'formation', 'education',
    'compétences', 'skills', 'langues', 'languages', 'projet', 'project',
    'contact', 'téléphone', 'email', 'adresse', 'page', 'date',
    'diplômes', 'diplome', 'formations', 'certifications', 'hobbies', 'loisirs',
    'centres', 'intérêt', 'interets', 'projets', 'réalisés', 'professionnelles',
    'coordonnées', 'management', 'sommaire', 'summary', 'objectif', 'objective',
    'propos', 'about', 'me', 'moi', 'introduction',
    'école', 'ecole', 'school', 'business', 'university', 'université',
    'hec', 'essec', 'esc', 'em', 'master', 'bachelor', 'licence', 'mba',
    'excel', 'vba', 'power', 'bi', 'crm', 'python', 'java', 'sql', 'office',
    'bnp', 'paribas', 'société', 'générale', 'crédit', 'agricole', 'sncf',
    'groupe', 'group', 'bank', 'banque', 'orange', 'capgemini', 'atos',
    'sopra', 'steria', 'accenture', 'deloitte', 'kpmg', 'ey', 'pwc',
    'france', 'paris', 'maroc', 'casablanca', 'rabat', 'lyon', 'marseille',
    'analyste', 'financière', 'gestion', 'ingénieur', 'directeur', 'manager',
    'consultant', 'développeur', 'responsable', 'assistant', 'stagiaire',
    'job', 'étudiant', 'student', 'intern', 'stage', 'engineer', 'developer',
    'analyst', 'specialist', 'coordinator', 'officer', 'executive',
    'ia', 'ai', 'ml', 'machine', 'learning', 'data', 'scientist',
    'weekly', 'meeting', 'decks', 'presentation', 'rapport', 'report',
    'procter', 'gamble', 'loreal', 'carrefour', 'hsbc', 'edf',
    'français', 'anglais', 'arabe', 'espagnol', 'courant', 'bilingue',
    'gpec', 'gepp', 'hdi', 'certification', 'itil', 'diapason', 'ktp',
    'intérêts', 'football', 'sport', 'voyage', 'lecture', 'musique',
    'soft', 'hard', 'linkedin', 'trésorier', 'ingénieure',
    'simulation', 'numérique', 'pensée', 'critique', 'concept', 'partenaire',
    'entreprise', 'charge', 'delivery', 'secteur', 'agro-alimentaire',
    'multi-disciplinary', 'engineering', 'studies', 'parcours', 'professionnel',
    'ivalua', 'prm', 'amf', 'alerting', 'blockchain', 'projects', 'purposes', 'program',
    'permis', 'client', 'missions', 'lecture', 'autocad', 'formateur', 'cuisine',
    'matériel', 'systèmes', 'méthodologie', 'agile-scrum', 'mobilité',
    'ocp', 'sa', 'compétence', 'limitée', 'gestiondeprojet'
}

def clean_text(text):
    # Normalize unicode characters
    text = text.encode('ascii', 'ignore').decode('ascii') # Brutal ascii simplification for debug
    return text

def is_likely_name_line(line):
    line_stripped = line.strip()
    words = line_stripped.lower().split()
    
    # 1. Check for forbidden words
    if any(w in FORBIDDEN_WORDS for w in words):
        return False, "forbidden_word"
        
    # 2. Check structure
    if len(words) < 2 or len(words) > 5:
        return False, "length_mismatch"
        
    # 3. Check characters
    if any(c in line for c in [':', ';', '(', ')', '/', ',', '.', '@', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
        return False, "invalid_chars"
        
    # 4. Check capitalization (Title Case or UPPER CASE)
    if not (line_stripped.isupper() or line_stripped.istitle()):
         # Allow mixed case only if individual words look like names
         if not all(w[0].isupper() for w in line_stripped.split() if w):
             return False, "casing_issue"
             
    return True, "ok"


def analyze_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        text = ""
        # Read specifically first page only for names typically
        page = doc.load_page(0)
        text = page.get_text("text")
        doc.close()
        
        lines = text.split('\n')
        candidates = []
        
        print(f"--- Analyzing {os.path.basename(filepath)} ---")
        
        for i, line in enumerate(lines[:50]): # Only first 50 lines usually relevant for name
            clean_line = line.strip()
            if not clean_line: continue
            
            is_valid, reason = is_likely_name_line(clean_line)
            print(f"L{i}: '{clean_line}' -> {is_valid} ({reason})")
            
            if is_valid:
                candidates.append(clean_line)
        
        print(f"Candidates found: {candidates}")
        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

# Test with specific failing files from user report
failing_files = [
    '68eff7c2729d0.pdf', # 68eff7c2729d0.pdf (fail)
    '68eff58f4fc78.pdf', # FORMATEUR DE CUISINE (fail)
    '68f00c71c9bf2.pdf', # Méthodologie AGILE-SCRUM (fail)
    '68f01b1381cf4.pdf', # Permis B (fail)
    '68f014dc2e24d.pdf', # Mobilité (fail)
    '68f0165bc9cff.pdf', # Matériel et systèmes (fail)
]

base_dir = '/workspaces/TG_Hire/cvs/F1'
for f in failing_files:
    path = os.path.join(base_dir, f)
    if os.path.exists(path):
        analyze_pdf(path)
    else:
        print(f"File not found: {path}")

