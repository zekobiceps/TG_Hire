import pandas as pd
from datetime import datetime
import streamlit as st
import importlib.util
import sys
from pathlib import Path

# Load module by path because filename contains emoji which breaks normal import names
reporting_path = Path(__file__).resolve().parents[1] / 'pages' / '10_📊_Reporting_RH.py'
spec = importlib.util.spec_from_file_location('reporting_rh', str(reporting_path))
reporting_rh = importlib.util.module_from_spec(spec)
sys.modules['reporting_rh'] = reporting_rh
spec.loader.exec_module(reporting_rh)
calculate_weekly_metrics = reporting_rh.calculate_weekly_metrics


def test_weekly_metrics_mon_fri_window():
    # Prepare a small DataFrame with expected columns
    data = {
        'Entité demandeuse': ['E1', 'E1', 'E1'],
        "Date de réception de la demande après validation de la DRH": [
            '01/10/2025',  # before week (should count in 'avant')
            '06/10/2025',  # monday of the week (should count in 'nouveaux')
            '05/10/2025'   # before week but accept date inside week -> pourvu
        ],
        'Statut de la demande': ['Ouvert', 'Ouvert', 'En cours'],
        "Nom Prénom du candidat retenu yant accepté la promesse d'embauche": [None, None, 'Jean Dupont'],
        "Date d'acceptation du candidat": [None, None, '08/10/2025']
    }

    df = pd.DataFrame(data)

    # Ensure dates are parsed similarly to the app
    df["Date de réception de la demande après validation de la DRH"] = pd.to_datetime(df["Date de réception de la demande après validation de la DRH"], dayfirst=True, errors='coerce')
    df["Date d'acceptation du candidat"] = pd.to_datetime(df["Date d'acceptation du candidat"], dayfirst=True, errors='coerce')

    # Set reporting_date to 15/10/2025 (a Wednesday) -> reference Friday = 10/10/2025 -> week 06/10..10/10
    st.session_state['reporting_date'] = datetime(2025, 10, 15)

    metrics = calculate_weekly_metrics(df)

    # Only one entity E1
    assert 'E1' in metrics
    m = metrics['E1']

    # Rows 0 and 2 are before week_start (06/10) -> counted in 'avant'
    assert m['avant'] == 2
    # Row 1 (06/10) is inside week -> nouveaux
    assert m['nouveaux'] == 1
    # Row 2 has accept date 08/10 and statut 'En cours' and candidate name -> pourvus
    assert m['pourvus'] == 1
