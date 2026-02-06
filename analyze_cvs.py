import pandas as pd

def analyze_cvs(file_path):
    df = pd.read_excel(file_path)
    print(df.head(2).to_json(orient='records'))

analyze_cvs('/workspaces/TG_Hire/LOGO/CVS/classification_results.xlsx')
