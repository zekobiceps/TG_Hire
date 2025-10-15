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
    # detect cols
    col_reception = None
    col_candidat = None
    col_statut = None
    col_entite = None
    col_poste = None
    for c in df.columns:
        lc = c.lower()
        if 'reception' in lc or 'réception' in lc or 'demande' in lc:
            col_reception = c
        if 'nom' in lc and 'candidat' in lc:
            col_candidat = c
        if 'statut' in lc or 'status' in lc:
            col_statut = c
        if 'entite' in lc or 'entité' in lc:
            col_entite = c
        if 'poste' in lc or 'post' in lc:
            col_poste = c

    print('detected:', col_reception, col_candidat, col_statut, col_entite, col_poste)
    today = datetime(2025,10,15)
    if col_reception:
        df[col_reception] = pd.to_datetime(df[col_reception], errors='coerce')

    mask_status = df[col_statut].fillna('').astype(str).str.lower().apply(lambda s: 'en cours' in s or 'encours' in s)
    mask_has_name = df[col_candidat].notna() & (df[col_candidat].astype(str).str.strip() != '')
    mask_recep = df[col_reception].notna() & (df[col_reception] <= today)

    overall_mask = mask_status & (~mask_has_name) & mask_recep
    print('Overall en_cours without candidate count:', int(overall_mask.sum()))
    if col_entite:
        print('Unique entities sample:', df[col_entite].dropna().unique()[:10])
    tgcc_mask = overall_mask & (df[col_entite].fillna('').str.strip().str.upper() == 'TGCC')
    print('TGCC matched rows:', int(tgcc_mask.sum()))
    if int(tgcc_mask.sum()) > 0:
        titles = df.loc[tgcc_mask, col_poste].fillna('').astype(str)
        norm_titles = titles.apply(_norm)
        counts = norm_titles.value_counts()
        for t, c in counts.items():
            print(c, ' : ', t)
    else:
        # show sample rows that are en_cours without candidate
        sample_idx = df[overall_mask].index[:20]
        print('Sample en_cours without candidate rows (idx, entite, poste):')
        for i in sample_idx:
            print(i, df.loc[i, col_entite], df.loc[i, col_poste])

if __name__ == '__main__':
    run()
