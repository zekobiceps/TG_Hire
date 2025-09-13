# test_api.py
import os
from openai import OpenAI

# Récupérer la clé API (adaptez selon votre configuration)
api_key = os.getenv("DEEPSEEK_API_KEY") or "your-test-key"

try:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    # Test simple sans consommer de crédits
    models = client.models.list()
    print("✅ Connexion API réussie")
    print(f"Modèles disponibles: {len(models.data)}")
    
except Exception as e:
    print(f"❌ Erreur API: {e}")