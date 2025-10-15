from datetime import datetime
import pandas as pd

XLS = 'Recrutement global PBI All  google sheet (3).xlsx'
NAMES = [
"BOUHLAL ABDELOUAHED",
"KHAMRAOUI Mohammed",
"AZNAG Mohamed",
"SAJI Aya",
"HADIK MOHAMED",
"TAIYEB HAMZA",
"EL HAMDOUNI Abderrahim",
"TADOT ZAKARIA",
"LAMAMRA YAMINE Mohamed",
"LAGRICHI AZIZ",
"KATIR AYOUB",
"BOUHMID Abdelhadi",
"AKHALOUI Hamza",
"IDALI AMAL",
"ZAOUI Hadil",
"EL JOUDI ADIL ALAYDI Mohamed"
]


def find_similar_column(df, keywords):
    kws = keywords.lower()
    for c in df.columns:
        if kws in c.lower():
            return c
    return None


def norm_val(x):
    try:
        s = str(x)
        s = s.strip()
        return s
    except Exception:
        return ''


def run():
    df = pd.read_excel(XLS)
    # detect columns
    col_reception = find_similar_column(df, 'réception') or find_similar_column(df, 'reception')
    col_candidat = find_similar_column(df, "nom prénom du candidat") or find_similar_column(df, 'nom prenom')
    col_statut = find_similar_column(df, 'statut')
    col_entite = find_similar_column(df, 'entité') or find_similar_column(df, 'entite')

    print('Cols detected:', col_reception, col_candidat, col_statut, col_entite)

    today = datetime(2025,10,15)

    if col_reception in df.columns:
        df[col_reception] = pd.to_datetime(df[col_reception], errors='coerce')

    # prepare masks
    mask_status_en_cours = pd.Series(False, index=df.index)
    if col_statut and col_statut in df.columns:
        mask_status_en_cours = df[col_statut].fillna('').astype(str).str.lower().apply(lambda s: 'en cours' in s or 'encours' in s)

    mask_has_name = pd.Series(False, index=df.index)
    if col_candidat and col_candidat in df.columns:
        mask_has_name = df[col_candidat].notna() & (df[col_candidat].astype(str).str.strip() != '')

    mask_reception_le_today = pd.Series(True, index=df.index)
    if col_reception and col_reception in df.columns:
        mask_reception_le_today = df[col_reception].notna() & (df[col_reception] <= today)

    mask_en_cours_rule = mask_status_en_cours & (~mask_has_name) & mask_reception_le_today

    # For each name, find rows where candidate column contains the name (case-insensitive substring)
    for name in NAMES:
        hits = df[col_candidat].astype(str).str.strip().fillna('') if col_candidat in df.columns else pd.Series(['']*len(df))
        matches = hits.str.lower().str.contains(name.lower())
        if matches.any():
            print('\nName:', name)
            for idx in df[matches].index:
                ent = df.loc[idx, col_entite] if col_entite in df.columns else ''
                statut = df.loc[idx, col_statut] if col_statut in df.columns else ''
                cand_raw = df.loc[idx, col_candidat] if col_candidat in df.columns else ''
                recv = df.loc[idx, col_reception] if col_reception in df.columns else ''
                counted = mask_en_cours_rule.loc[idx]
                print(f" idx={idx} | Entité={ent} | Statut={statut} | candidat_raw='{cand_raw}' | reception={recv} | counted_as_en_cours={counted}")
        else:
            print('\nName not found in candidate column:', name)

if __name__ == '__main__':
    run()
