#!/usr/bin/env python3
"""Test du chargement des logos"""

import os
from PIL import Image

# Chemin comme dans le code
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_folder = os.path.join(current_dir, "LOGO")

print(f"📁 Chemin du dossier LOGO: {logo_folder}")
print(f"✅ Dossier existe: {os.path.exists(logo_folder)}")

if os.path.exists(logo_folder):
    logos = os.listdir(logo_folder)
    print(f"\n✅ {len(logos)} fichiers trouvés:")
    
    for filename in logos:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.jfif')):
            try:
                img_path = os.path.join(logo_folder, filename)
                img = Image.open(img_path)
                print(f"  ✅ {filename}: {img.size} - {img.mode}")
            except Exception as e:
                print(f"  ❌ {filename}: ERREUR - {e}")
else:
    print("❌ Dossier LOGO introuvable!")
