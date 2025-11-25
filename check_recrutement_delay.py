import pandas as pd

# Charger un extrait du fichier Excel
file_path = '/workspaces/TG_Hire/Recrutement global PBI All  google sheet (11).xlsx'
df = pd.read_excel(file_path)

# Afficher les premières lignes et les types des colonnes de date
print(df[['Date de réception de la demande aprés validation de la DRH', 'Date du 1er retour equipe RH  au demandeur']].head())
print(df[['Date de réception de la demande aprés validation de la DRH', 'Date du 1er retour equipe RH  au demandeur']].dtypes)

# Vérifier l'ordre des dates
mask = df['Date de réception de la demande aprés validation de la DRH'].notna() & df['Date du 1er retour equipe RH  au demandeur'].notna()
df_valid = df[mask].copy()
df_valid['delta'] = (pd.to_datetime(df_valid['Date de réception de la demande aprés validation de la DRH'], errors='coerce') - pd.to_datetime(df_valid['Date du 1er retour equipe RH  au demandeur'], errors='coerce')).dt.days
print(df_valid[['Date de réception de la demande aprés validation de la DRH', 'Date du 1er retour equipe RH  au demandeur', 'delta']].head(20))
print('Moyenne calculée:', df_valid['delta'].mean())
