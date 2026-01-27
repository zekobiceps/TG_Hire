import pandas as pd
import glob
import os

# Find the latest Excel file
excel_files = glob.glob('Recrutement global PBI All*.xlsx')
if not excel_files:
    print("No Excel files found.")
    exit()

excel_files.sort(key=os.path.getmtime)
latest_excel = excel_files[-1]
print(f"Loading: {latest_excel}")

try:
    df = pd.read_excel(latest_excel, sheet_name=0)
    
    # Logic from calculate_weekly_metrics to find the column
    entite_col = None
    available_cols = df.columns.tolist()
    for col in available_cols:
        if col.lower() == "entité demandeuse" or col.lower() == "entite demandeuse":
            entite_col = col
            break
    
    if not entite_col:
        for col in available_cols:
            if "entité" in col.lower() or "entite" in col.lower():
                entite_col = col
                break
    
    if entite_col:
        print(f"Found entity column: '{entite_col}'")
        unique_entities = df[entite_col].dropna().unique()
        print("\nUnique values in entity column:")
        for entity in sorted(unique_entities):
            print(f"- {entity}")
    else:
        print("Entity column not found.")
        print("Available columns:", available_cols)
        
except Exception as e:
    print(f"Error: {e}")
