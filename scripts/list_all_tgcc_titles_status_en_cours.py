import pandas as pd
from datetime import datetime

XLS = 'Recrutement global PBI All  google sheet (3).xlsx'

def _norm(s):
    import unicodedata
    if pd.isna(s):
        return ''
    ss = str(s)
    ss = unicodedata.normalize('NFKD', ss)
    ss = ''.join(ch for ch in ss if not unicodedata.combining(ch))
    return ss.lower().strip()


def run():
    df = pd.read_excel(XLS)
    # detect columns
    col_statut = None
    col_entite = None
    col_poste = None
    for c in df.columns:
        lc = c.lower()
        if 'statut' in lc or 'status' in lc:
            col_statut = c
        if 'entite' in lc or 'entité' in lc:
            col_entite = c
        if 'poste' in lc or 'post' in lc:
            col_poste = c

    print('detected:', col_statut, col_entite, col_poste)
    # mask for TGCC & statut en cours
    mask = (df[col_entite].fillna('').astype(str).str.strip().str.upper()=='TGCC') & df[col_statut].fillna('').astype(str).apply(lambda s: 'en cours' in s.lower() or 'encours' in s.lower())
    titles = df.loc[mask, col_poste].fillna('').astype(str)
    norm = titles.apply(_norm)
    counts = norm.value_counts()
    for t,c in counts.items():
        print(c,':',t)

if __name__ == '__main__':
    run()
