#!/usr/bin/env python3
"""
Test direct avec une URL d'entreprise Charika pour tester l'extraction d'email
"""

import requests
from bs4 import BeautifulSoup
import re

def test_email_extraction_direct(url):
    """Test l'extraction d'email sur une page d'entreprise directe"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"🌐 Accès direct à: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"📄 Page chargée, taille: {len(response.content)} bytes")
        
        # Sauvegarder le HTML pour inspection
        with open('charika_page.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        print("💾 HTML sauvegardé dans charika_page.html")
        
        # Méthode 1: Chercher spécifiquement dans les spans dropdown
        print("\n🔍 Méthode 1: Recherche dans les spans dropdown...")
        dropdown_spans = soup.find_all('span', class_='dropdown')
        print(f"📋 Trouvé {len(dropdown_spans)} spans dropdown")
        
        for i, dropdown in enumerate(dropdown_spans):
            dropdown_text = dropdown.get_text()
            print(f"  Dropdown {i+1}: {dropdown_text[:100]}...")
            
            # Vérifier si ce dropdown contient "E-mail"
            if 'E-mail' in dropdown_text or 'Email' in dropdown_text:
                print(f"  ✅ Dropdown {i+1} contient 'E-mail'")
                print(f"  HTML: {str(dropdown)[:300]}...")
                # Chercher les liens mailto dans ce dropdown
                mailto_links = dropdown.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                print(f"  📧 Trouvé {len(mailto_links)} liens mailto")
                
                for link in mailto_links:
                    email = link.get('href').replace('mailto:', '').strip()
                    print(f"  ✅ Email trouvé via dropdown: {email}")
                    return email
        
        # Méthode 2: Chercher tous les liens mailto
        print("\n🔍 Méthode 2: Recherche de tous les liens mailto...")
        mailto_links = soup.find_all('a', href=lambda x: x and x.startswith('mailto:'))
        print(f"📧 Trouvé {len(mailto_links)} liens mailto au total")
        
        for i, link in enumerate(mailto_links):
            href = link.get('href', '')
            email = href.replace('mailto:', '').strip()
            print(f"  {i+1}. {email}")
            if '@' in email and '.' in email.split('@')[1]:
                if not any(spam in email.lower() for spam in ['noreply', 'no-reply', 'example', 'test']):
                    print(f"  ✅ Email retenu: {email}")
                    return email
        
        # Méthode 3: Recherche par pattern dans tout le texte
        print("\n🔍 Méthode 3: Recherche par regex...")
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = soup.get_text()
        emails = re.findall(email_pattern, page_text)
        print(f"📧 Emails trouvés par regex: {emails}")
        
        if emails:
            for email in emails:
                if not any(spam in email.lower() for spam in ['noreply', 'no-reply', 'example', 'test']):
                    print(f"  ✅ Email retenu: {email}")
                    return email
        
        # Méthode 4: Chercher les spans contenant "E-mail"
        print("\n🔍 Méthode 4: Recherche dans spans avec 'E-mail'...")
        
        # Chercher tous les éléments contenant "E-mail"
        email_elements = soup.find_all(text=re.compile(r'E-?mail', re.IGNORECASE))
        print(f"📋 Trouvé {len(email_elements)} éléments avec 'E-mail'")
        
        for i, element in enumerate(email_elements):
            print(f"  Element {i+1}: '{element.strip()}'")
            parent = element.parent
            if parent:
                print(f"  Parent: {parent.name} - {str(parent)[:200]}...")
                # Chercher dans le parent et ses voisins
                for sibling in [parent] + list(parent.next_siblings):
                    if hasattr(sibling, 'find_all'):
                        links = sibling.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                        for link in links:
                            email = link.get('href').replace('mailto:', '').strip()
                            print(f"  ✅ Email trouvé via sibling: {email}")
                            return email
        
        print("❌ Aucun email trouvé")
        return None
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

if __name__ == "__main__":
    # Utilisons une URL d'exemple ou essayons de construire une URL plausible
    test_urls = [
        "https://www.charika.ma/entreprise/jetalu",
        "https://www.charika.ma/fiche/jetalu",
        "https://www.charika.ma/company/jetalu"
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"TEST URL: {url}")
        print(f"{'='*60}")
        
        result = test_email_extraction_direct(url)
        
        if result:
            print(f"✅ SUCCÈS: Email trouvé: {result}")
            break
        else:
            print(f"❌ ÉCHEC avec cette URL")
    
    print("\n📄 Vérifiez le fichier charika_page.html pour voir le contenu de la page")