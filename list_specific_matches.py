import pandas as pd
import sys

# Load CSV
try:
    df = pd.read_csv('LOGO/CVS/classification_results.csv')
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)

# Specific files list provided by user
user_files = [
    "68d6cea0ac1e1.pdf", "68d6d2849eef4.pdf", "68d6d28e08681.pdf", "68d6e4c7d64ba.pdf",
    "68d6e50032f3c.pdf", "68d6e5733f2e7.pdf", "68d6eccb2db17.pdf", "68d70c1d56a8f.pdf",
    "68d7a09ed40b0.pdf", "68d7ae0472ea9.pdf", "68d7c2e121252.pdf", "68d7cc547ce68.pdf",
    "68d7d319d7b03.pdf", "68d7d783b3500.pdf", "68d7e5145fe24.pdf", "68d80a84f3439.pdf",
    "68d82cd44fbea.pdf", "68d8820501795.pdf", "68d8f7b29cdde.pdf", "68d9035d32a9b.pdf",
    "68d909c1cdd10.pdf", "68d90b5084598.pdf", "68d916f513059.pdf", "68d9312053c25.pdf",
    "68d95ed45015e.pdf", "68da0473655b5.pdf", "68da60b1d5dde.pdf", "68da6d9044df0.pdf",
    "68da6fb7389dd.pdf", "68da734def150.pdf", "68da7a08ae709.pdf", "68da83af9b753.pdf",
    "68da83f131509.pdf", "68da856b71d43.pdf", "68da87d9785a3.pdf", "68da9922a4e2f.pdf",
    "68dabec068406.pdf", "68dba290408d1.pdf", "68dbc4c23bca4.pdf", "68dbc8686f073.pdf",
    "68dbc8ea93480.pdf", "68dbcbadc15d1.pdf", "68dbcc1a22d04.pdf", "68dbcd4bb53c0.pdf",
    "68dbce281953e.pdf", "68dbcfb06e81d.pdf", "68dbd5280dccc.pdf", "68dbe10c5465a.pdf",
    "68dbf9dc1877f.pdf", "68dc2831b9692.pdf", "68dc29360b588.pdf", "68dc342193bdb.pdf",
    "68dce2a1b6166.pdf", "68dd2b2fee6ed.pdf", "68dd47dd21b28.pdf", "68dd4e2b89bdb.pdf",
    "68dd99eba445f.pdf", "68de467fbd519.pdf", "68de7fadedbe3.pdf", "68de877b2a577.pdf",
    "68de8a95bd4e9.pdf", "68df468ad7bdf.pdf", "68df9fa92a980.pdf", "68e0076e8f402.pdf",
    "68e04509a7d26.pdf", "68e10f0b1c4cf.pdf", "68e27248c1926.pdf", "68e2a80aa2136.pdf",
    "68e36dc5e33ff.pdf", "68e3a8477a8e1.pdf", "68e3c7d56f5f6.pdf", "68e3d6624af4d.pdf",
    "68e3e2baa16da.pdf", "68e3e98859366.pdf", "68e425fd9c496.pdf", "68e44840ab1a4.pdf",
    "68e4cef4558ae.pdf", "68e50dcb9e712.pdf", "68e61fa612050.pdf", "68e62a466c128.pdf",
    "68e66aba13f6e.pdf", "68e689bf5c30f.pdf", "68e6b72cd5255.pdf", "68e6ca61f2714.pdf",
    "68e6ca6f97575.pdf", "68e6d75de8bfc.pdf", "68e6f7cc17127.pdf", "68e760edce5f8.pdf",
    "68e76c0689e9b.pdf", "68e772f057a77.pdf", "68e7c4d9e870d.pdf", "68e7d34534181.pdf",
    "68e7e00a3c956.pdf", "68e7fde00e3af.pdf", "68e801cf23aa1.pdf", "68e8e367d2b83.pdf",
    "68ebc2f819e12.pdf", "68ecc26c8a8f1.pdf", "68ecf4df6a13c.pdf", "68ecf8cc9521b.pdf",
    "68ecfcb65887d.pdf", "68ed184dcea07.pdf", "68ed19b0a20a5.pdf", "68ed2eea0f6e0.pdf",
    "68ed3b9c96fad.pdf", "68ed72eb52de5.pdf", "68edf0e03a97c.pdf", "68ee581451107.pdf",
    "68ee9e07d7a04.pdf", "68eeb41ae6dd5.pdf", "68eeb7c7e4e2b.pdf", "68ef4f7e96ff8.pdf",
    "68ef5b8b38406.pdf", "68ef71b43717f.pdf", "68ef8b7638c7a.pdf", "68efa053bf7c5.pdf",
    "68efa1fe0cb9c.pdf", "68efaea7bf78d.pdf", "68efbc8177293.pdf", "68efd52740613.pdf",
    "68efda8408cbd.pdf", "68efe529cc41b.pdf", "68efe554922b2.pdf", "68efe8af98d40.pdf",
    "68f005f87bcae.pdf", "68f012dc68164.pdf"
]

# Helper function
def safe_exp(x):
    try:
        if pd.isna(x): return 0.0
        return float(str(x).replace('ans', '').strip())
    except:
        return 0.0

df['years_experience_clean'] = df['years_experience'].apply(safe_exp)

# Scoring (Same as before)
keywords = {
    "raf": 5, "responsable administratif et financier": 5, "finance": 2, "financier": 2,
    "comptab": 3, "contrôle de gestion": 3, "controle de gestion": 3, "trésorerie": 2,
    "audit": 2, "administratif": 1, "gestion": 1
}

def calculate_score(row):
    text = f"{row['candidate_name']} {row['sub_category']} {row['profile_summary']}".lower()
    score = 0
    for kw, points in keywords.items():
        if kw in text: score += points
    return score

df['score'] = df.apply(calculate_score, axis=1)

# Filter for matches in specific list
matches = df[
    (df['file'].isin(user_files)) & 
    (df['years_experience_clean'] >= 4) & 
    (df['years_experience_clean'] <= 12) & 
    (df['score'] > 0)
].sort_values(by='score', ascending=False)

print(f"Liste actualisée des {len(matches)} profils retenus (Liste Spécifique) :\n")

for i, (_, row) in enumerate(matches.iterrows(), 1):
    print(f"{i}. {row['candidate_name']} ({row['years_experience']} ans) - Score: {row['score']}")
    print(f"   Fichier: {row['file']}")
    print(f"   Profil: {row['sub_category']}")
    print(f"   Résumé: {row['profile_summary'][:200]}...")
    print("")
