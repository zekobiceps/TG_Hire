import runpy
import pandas as pd
from datetime import datetime

mod = runpy.run_path('pages/10_📊_Reporting_RH.py')
calculate_weekly_metrics = mod['calculate_weekly_metrics']

# load excel
XLS = 'Recrutement global PBI All  google sheet (3).xlsx'
df = pd.read_excel(XLS)

# set reporting_date in st.session_state via module's st
import streamlit as st
st.session_state['reporting_date'] = datetime(2025,10,15)

metrics = calculate_weekly_metrics(df)

print('TGCC metrics:', metrics.get('TGCC'))
