import pandas as pd
import os
import zipfile
import io
import sys

def to_excel(df):
    """Convertit un DataFrame en un objet bytes Excel avec des styles."""
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="CVs Classés")
            
            workbook = writer.book
            worksheet = writer.sheets["CVs Classés"]
            
            # Type ignore pour éviter l'erreur Pylance sur add_format
            header_format = workbook.add_format({  # type: ignore
                "bold": True,
                "text_wrap": True,
                "valign": "top",
                "fg_color": "#D7E4BC",
                "border": 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            for i, col in enumerate(df.columns):
                if df[col].dropna().empty:
                    column_len = len(col) + 2
                else:
                    column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_len, 60))

        return output.getvalue()
    except Exception as e:
        print(f"Erreur critique lors de la création du fichier Excel. Assurez-vous que 'xlsxwriter' est installé (`pip install xlsxwriter`). Erreur: {e}", file=sys.stderr)
        return None

def main():
    """Script principal pour générer le rapport Excel et l'archive ZIP."""
    base_path = "/workspaces/TG_Hire/LOGO/CVS"
    results_csv_path = os.path.join(base_path, "classification_results.csv")
    output_excel_path = os.path.join(base_path, "classification_results.xlsx")
    output_zip_path = os.path.join(base_path, "CVs_classes.zip")

    print("--- Début de la génération du rapport ---")

    if not os.path.exists(results_csv_path):
        print(f"ERREUR : Le fichier d'entrée '{results_csv_path}' est introuvable.", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(results_csv_path)
        print(f"'{results_csv_path}' lu avec succès. {len(df)} lignes trouvées.")

        excel_data = to_excel(df)
        if excel_data:
            with open(output_excel_path, "wb") as f:
                f.write(excel_data)
            print(f"✅ Fichier Excel créé : {output_excel_path}")

            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr("classification_results.xlsx", excel_data)
                print("   - Fichier Excel ajouté à l'archive.")

                for index, row in df.iterrows():
                    original_filename = row.get("file")
                    candidate_name = row.get("candidate_name", "Candidat_Inconnu")
                    macro_category = row.get("macro_category", "Inconnu")
                    sub_category = row.get("sub_category", "Inconnu")
                    
                    if not original_filename:
                        continue

                    safe_macro = "".join(c for c in str(macro_category) if c.isalnum() or c in (" ", "_")).rstrip()
                    safe_sub = "".join(c for c in str(sub_category) if c.isalnum() or c in (" ", "_")).rstrip()
                    
                    # Nettoyer le nom du candidat pour créer un nom de fichier valide
                    safe_candidate_name = "".join(c for c in str(candidate_name) if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                    if not safe_candidate_name or safe_candidate_name == "Candidat_Inconnu":
                        safe_candidate_name = os.path.splitext(original_filename)[0]
                    
                    # Nouveau nom de fichier avec le nom du candidat
                    file_extension = os.path.splitext(original_filename)[1]
                    new_filename = f"{safe_candidate_name}{file_extension}"

                    original_file_path = os.path.join(base_path, original_filename)

                    if os.path.exists(original_file_path):
                        zip_path = os.path.join(safe_macro, safe_sub, new_filename)
                        zipf.write(original_file_path, zip_path)
                        print(f"   ✅ {original_filename} -> {new_filename}")
                    else:
                        print(f"   ⚠️ Fichier CV non trouvé, ignoré : {original_file_path}")
            
            print(f"✅ Fichier ZIP créé : {output_zip_path}")
        else:
            print("ERREUR : La création du fichier Excel a échoué. Le ZIP n'a pas été créé.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}", file=sys.stderr)
        sys.exit(1)

    print("--- Génération du rapport terminée ---")

if __name__ == "__main__":
    main()
