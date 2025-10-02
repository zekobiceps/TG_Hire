#!/usr/bin/env python3
"""
Test simple de la fonction get_email_from_charika améliorée
"""

import sys
import time
sys.path.append('pages')

# Importer uniquement les fonctions nécessaires sans Streamlit
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

def get_email_from_charika_test(entreprise):
    """Version de test de la fonction get_email_from_charika"""
    try:
        # Rechercher sur Charika.ma
        search_url = f"https://www.charika.ma/search?q={quote(entreprise)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"🔍 Recherche pour '{entreprise}' sur Charika.ma...")
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Approche améliorée pour trouver les liens d'entreprise
        company_links = soup.find_all('a', href=True)
        company_url = None
        
        # 1. Chercher d'abord les liens avec "entreprise" ou "fiche" dans l'URL
        for link in company_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            if ('entreprise' in href or 'fiche' in href or 'company' in href) and any(word in text for word in entreprise.lower().split()):
                company_url = "https://www.charika.ma" + href if href.startswith('/') else href
                print(f"✅ URL trouvée (méthode 1): {company_url}")
                break
        
        # 2. Si pas trouvé, chercher plus largement
        if not company_url:
            for link in company_links:
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                # Recherche plus souple dans le texte du lien
                if href and href.startswith('/') and len(href) > 5:  # URLs relatives significatives
                    # Vérifier si le nom de l'entreprise est dans le texte
                    if (entreprise.lower() in text or 
                        any(word.lower() in text for word in entreprise.split() if len(word) > 2)):
                        company_url = "https://www.charika.ma" + href
                        print(f"✅ URL trouvée (méthode 2): {company_url}")
                        break
        
        # 3. Essayer des URLs construites directement (fallback)
        if not company_url:
            print("⚠️ Aucun lien trouvé dans les résultats, tentative d'URLs directes...")
            # Essayer différents formats d'URL possibles
            possible_urls = [
                f"https://www.charika.ma/entreprise/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/fiche/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/company/{entreprise.lower().replace(' ', '-')}",
                f"https://www.charika.ma/entreprise/{entreprise.lower().replace(' ', '')}",
            ]
            
            for test_url in possible_urls:
                try:
                    test_response = requests.head(test_url, headers=headers, timeout=5)
                    if test_response.status_code == 200:
                        company_url = test_url
                        print(f"✅ URL directe valide: {company_url}")
                        break
                except:
                    continue
        
        if not company_url:
            print("❌ Aucune URL d'entreprise trouvée")
            return None
        
        # Accéder à la page de l'entreprise
        print(f"🌐 Accès à la page: {company_url}")
        company_response = requests.get(company_url, headers=headers, timeout=10)
        company_soup = BeautifulSoup(company_response.content, 'html.parser')
        
        # Sauvegarder pour debug
        with open(f'debug_page_{entreprise.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
            f.write(company_soup.prettify())
        
        # Méthode améliorée basée sur l'inspection de la structure HTML de Charika.ma
        # Structure identifiée: <span class="dropdown"> avec <span class="mrg-fiche3"> contenant "E-mail" et lien mailto
        
        # Méthode 1: Chercher spécifiquement dans les spans dropdown (structure observée)
        print("🔍 Méthode 1: Recherche dans spans dropdown...")
        dropdown_spans = company_soup.find_all('span', class_='dropdown')
        print(f"  Trouvé {len(dropdown_spans)} spans dropdown")
        
        for dropdown in dropdown_spans:
            # Vérifier si ce dropdown contient "E-mail" dans un span avec class "mrg-fiche3"
            mrg_spans = dropdown.find_all('span', class_='mrg-fiche3')
            for mrg_span in mrg_spans:
                if 'E-mail' in mrg_span.get_text():
                    print(f"  ✅ Span E-mail trouvé: {mrg_span.get_text()}")
                    # Chercher les liens mailto dans ce dropdown
                    mailto_links = dropdown.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                    for link in mailto_links:
                        email = link.get('href').replace('mailto:', '').strip()
                        if '@' in email and '.' in email.split('@')[1]:
                            # Vérifier que ce n'est pas l'email de Charika
                            if 'charika.ma' not in email.lower():
                                print(f"  ✅ Email trouvé via dropdown: {email}")
                                return email
        
        # Méthode 2: Chercher tous les liens mailto dans la page (en excluant Charika)
        print("🔍 Méthode 2: Recherche de tous les liens mailto...")
        mailto_links = company_soup.find_all('a', href=lambda x: x and x.startswith('mailto:'))
        print(f"  Trouvé {len(mailto_links)} liens mailto")
        
        for link in mailto_links:
            email = link.get('href').replace('mailto:', '').strip()
            print(f"  Lien: {email}")
            if '@' in email and '.' in email.split('@')[1]:
                # Filtrer les emails génériques et celui de Charika
                excluded = ['noreply', 'no-reply', 'donotreply', 'example', 'test', 'charika.ma', 'contact@charika']
                if not any(generic in email.lower() for generic in excluded):
                    print(f"  ✅ Email retenu: {email}")
                    return email
        
        # Méthode 3: Recherche par regex dans tout le texte
        print("🔍 Méthode 3: Recherche par regex...")
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        all_text = company_soup.get_text()
        emails = re.findall(email_pattern, all_text)
        print(f"  Emails trouvés: {emails}")
        
        if emails:
            # Filtrer les emails génériques et celui de Charika
            excluded = ['noreply', 'no-reply', 'donotreply', 'example', 'test', 'charika.ma']
            for email in emails:
                if not any(generic in email.lower() for generic in excluded):
                    print(f"  ✅ Email retenu: {email}")
                    return email
        
        print("❌ Aucun email d'entreprise trouvé")
        return None
        
    except Exception as e:
        print(f"❌ Erreur lors de la recherche sur Charika: {e}")
        return None

if __name__ == "__main__":
    # Test avec différentes entreprises
    test_companies = ["TGCC", "OCP", "Attijariwafa Bank"]
    
    for company in test_companies:
        print(f"\n{'='*60}")
        print(f"TEST: {company}")
        print(f"{'='*60}")
        
        result = get_email_from_charika_test(company)
        
        if result:
            print(f"✅ SUCCÈS: Email trouvé pour '{company}': {result}")
        else:
            print(f"❌ ÉCHEC: Aucun email trouvé pour '{company}'")
        
        # Pause entre les tests pour éviter de surcharger le serveur
        if company != test_companies[-1]:
            print("⏳ Pause de 2 secondes...")
            time.sleep(2)