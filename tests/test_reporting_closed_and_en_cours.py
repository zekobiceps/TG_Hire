import pandas as pd
import streamlit as st
from datetime import datetime

# The test will import calculate_weekly_metrics by executing the reporting module
import runpy
mod = runpy.run_path('pages/10_📊_Reporting_RH.py', run_name='__main__')
calculate_weekly_metrics = mod['calculate_weekly_metrics']


def make_df(rows):
    return pd.DataFrame(rows)


def test_exclude_closed_from_avant():
    # Prepare rows: one closed before previous_monday, one open before previous_monday
    rows = [
        {'Entité demandeuse': 'E1', 'Date de réception de la demande aprés validation de la DRH': '01/10/2025', 'Statut de la demande': 'Clôture'},
        {'Entité demandeuse': 'E1', 'Date de réception de la demande aprés validation de la DRH': '01/10/2025', 'Statut de la demande': 'Ouvert'},
    ]
    df = make_df(rows)
    # set reporting date
    st.session_state['reporting_date'] = datetime(2025,10,15)
    # closed requests are excluded by default and permanently
    metrics = calculate_weekly_metrics(df)
    assert 'E1' in metrics
    assert metrics['E1']['avant'] == 1


def test_en_cours_without_candidate_counts_as_sourcing():
    rows = [
        {'Entité demandeuse': 'E2', 'Date de réception de la demande aprés validation de la DRH': '01/10/2025', 'Statut de la demande': 'En cours', "Nom Prénom du candidat retenu yant accepté la promesse d'embauche": None},
        {'Entité demandeuse': 'E2', 'Date de réception de la demande aprés validation de la DRH': '01/10/2025', 'Statut de la demande': 'En cours', "Nom Prénom du candidat retenu yant accepté la promesse d'embauche": 'Jean'},
    ]
    df = make_df(rows)
    st.session_state['reporting_date'] = datetime(2025,10,15)
    # closed exclusion is permanent
    metrics = calculate_weekly_metrics(df)
    assert metrics['E2']['en_cours'] == 1
