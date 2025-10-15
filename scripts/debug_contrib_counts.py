from datetime import datetime, timedelta
import pandas as pd

# This script computes per-entity en_cours and contrib_en_cours using the same
# logic as in pages/10_📊_Reporting_RH.py for quick diagnostics.

XLS = 'Recrutement global PBI All  google sheet (3).xlsx'

def _parse_mixed_dates(series):
    s = series.copy()
    if pd.api.types.is_numeric_dtype(s):
        origin = pd.Timestamp('1899-12-30')
        return pd.to_timedelta(s.fillna(0).astype(float), unit='D') + origin
    try:
        coerced = pd.to_numeric(s.dropna().unique(), errors='coerce')
        if len(coerced) > 0 and not pd.isna(coerced).all():
            def _maybe_excel(x):
                try:
                    xf = float(x)
                    return pd.Timestamp('1899-12-30') + pd.Timedelta(days=xf)
                except Exception:
                    return pd.NaT
            return s.apply(lambda v: _maybe_excel(v) if pd.notna(v) and str(v).strip().replace('.','',1).isdigit() else pd.NaT).combine_first(pd.to_datetime(s, dayfirst=True, errors='coerce'))
    except Exception:
        pass
    parsed = pd.to_datetime(s, dayfirst=True, errors='coerce')
    if parsed.isna().sum() > len(parsed) * 0.25:
        parsed_alt = pd.to_datetime(s, errors='coerce')
        parsed = parsed.combine_first(parsed_alt)
    return parsed


def diagnose():
    df = pd.read_excel(XLS)
    # Normalize column names to simpler keys
    cols = {c:c for c in df.columns}
    def find_similar_column(target):
        t = target.lower()
        for c in df.columns:
            if c.lower() == t:
                return c
        if 'date' in t and 'réception' in t:
            for c in df.columns:
                if 'date' in c.lower() and ('réception' in c.lower() or 'reception' in c.lower() or 'demande' in c.lower()):
                    return c
        if 'statut' in t:
            for c in df.columns:
                if 'statut' in c.lower() or 'status' in c.lower():
                    return c
        if 'entité' in t or 'entite' in t:
            for c in df.columns:
                if 'entit' in c.lower() or 'entite' in c.lower():
                    return c
        return None

    real_date_reception_col = find_similar_column('Date de réception de la demande aprés validation de la DRH')
    real_date_integration_col = find_similar_column("Date d'entrée prévisionnelle")
    real_accept_col = find_similar_column("Date d'acceptation du candidat") or find_similar_column("Date d'acceptation")
    real_candidat_col = find_similar_column("Nom Prénom du candidat retenu yant accepté la promesse d'embauche")
    real_statut_col = find_similar_column('Statut de la demande')
    real_entite_col = find_similar_column('Entité demandeuse')

    print('detected cols:', real_date_reception_col, real_accept_col, real_date_integration_col, real_candidat_col, real_statut_col, real_entite_col)

    today = datetime(2025,10,15)
    start_of_week = datetime(year=today.year, month=today.month, day=today.day) - timedelta(days=today.weekday())
    previous_monday = start_of_week - timedelta(days=7)
    previous_friday = start_of_week - timedelta(days=3)
    previous_friday_exclusive = previous_friday + timedelta(days=1)

    if real_date_reception_col:
        df[real_date_reception_col] = pd.to_datetime(df[real_date_reception_col], errors='coerce')
    if real_accept_col:
        try:
            df[real_accept_col] = _parse_mixed_dates(df[real_accept_col])
        except Exception:
            df[real_accept_col] = pd.to_datetime(df[real_accept_col], errors='coerce')
    if real_date_integration_col:
        df[real_date_integration_col] = pd.to_datetime(df[real_date_integration_col], errors='coerce')

    import unicodedata
    def _norm(s):
        if pd.isna(s):
            return ''
        ss = str(s)
        ss = unicodedata.normalize('NFKD', ss)
        ss = ''.join(ch for ch in ss if not unicodedata.combining(ch))
        return ss.lower()
    closed_keywords = ['cloture', 'clôture', 'annule', 'annulé', 'depriorise', 'dépriorisé', 'desistement', 'désistement', 'annul', 'reject', 'rejett']

    mask_status_en_cours = df[real_statut_col].fillna('').astype(str).apply(lambda s: 'en cours' in _norm(s) or 'encours' in _norm(s))
    mask_has_name = None
    if real_candidat_col:
        mask_has_name = df[real_candidat_col].notna() & (df[real_candidat_col].astype(str).str.strip() != '')

    mask_reception_le_today = df[real_date_reception_col].notna() & (df[real_date_reception_col] <= today)

    # contrib mask (debug): should match pages logic after our fix
    contrib_en_cours = mask_status_en_cours & (~mask_has_name.fillna(False) if mask_has_name is not None else True) & mask_reception_le_today

    # SPECIAL_TITLE_FILTERS (same as in reporting file)
    SPECIAL_TITLE_FILTERS = {
        'TGCC': [
            'CHEF DE PROJETS', 'INGENIEUR TRAVAUX', 'CONDUCTEUR TRAVAUX SENIOR', 'CONDUCTEUR TRAVAUX',
            'INGENIEUR TRAVAUX JUNIOR', 'RESPONSABLE QUALITE', 'CHEF DE CHANTIER', 'METREUR',
            'RESPONSABLE HSE', 'SUPERVISEUR HSE', 'ANIMATEUR HSE', 'DIRECTEUR PROJETS',
            'RESPONSABLE ADMINISTRATIF ET FINANCIER', 'RESPONSABLE MAINTENANCE', 'RESPONSABLE ENERGIE INDUSTRIELLE',
            'RESPONSABLE CYBER SECURITE', 'RESPONSABLE VRD', 'RESPONSABLE ACCEUIL', 'RESPONSABLE ETUDES',
            'TECHNICIEN SI', 'RESPONSABLE GED & ARCHIVAGE', 'ARCHIVISTE SENIOR', 'ARCHIVISTE JUNIOR', 'TOPOGRAPHE'
        ]
    }

    # compute per-entity
    entites = df[real_entite_col].dropna().unique()
    # detect poste col
    real_poste_col = None
    for c in df.columns:
        if 'poste' in c.lower() or 'post' in c.lower():
            real_poste_col = c
            break
    rows = []

    for e in entites:
        dfe = df[df[real_entite_col] == e]
        base_mask = mask_status_en_cours.loc[dfe.index] & (~mask_has_name.fillna(False).loc[dfe.index] if mask_has_name is not None else True) & mask_reception_le_today.loc[dfe.index]
        en_cours_status = int(base_mask.sum())
        # apply special title filter if present
        if real_poste_col and real_poste_col in df.columns and e in SPECIAL_TITLE_FILTERS:
            tokens = set()
            for t in SPECIAL_TITLE_FILTERS.get(e, []):
                for part in __import__('re').split(r"[^\w]+", t):
                    p = _norm(part)
                    if p and len(p) > 2:
                        tokens.add(p)
            def _title_matches_tokens(title):
                ns = _norm(title)
                return any(tok in ns for tok in tokens)
            mask_title = df[real_poste_col].fillna('').astype(str).apply(lambda s: _title_matches_tokens(s))
            en_cours_status = int((base_mask & mask_title.loc[dfe.index]).sum())

        contrib_count = int(contrib_en_cours.loc[dfe.index].sum())
        rows.append((e, en_cours_status, contrib_count))

    for r in sorted(rows, key=lambda x: x[0]):
        print(r)

if __name__ == '__main__':
    diagnose()
