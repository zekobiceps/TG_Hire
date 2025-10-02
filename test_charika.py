#!/usr/bin/env python3
"""
Test standalone pour la fonction get_email_from_charika améliorée
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

def get_email_from_charika(entreprise):
    """Recherche d'email d'entreprise depuis Charika.ma avec amélioration ciblée"""
    try:
        # Rechercher sur Charika.ma
        search_url = f"https://www.charika.ma/search?q={quote(entreprise)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"🔍 Recherche pour '{entreprise}' sur Charika.ma...")
        print(f"URL: {search_url}")
        
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher le lien vers la page de l'entreprise - approche améliorée
        company_links = soup.find_all('a', href=True)
        company_url = None
        
        print(f"📋 Trouvé {len(company_links)} liens sur la page de recherche")
        
        # Debug: afficher quelques liens pour comprendre la structure
        print("🔍 Premiers liens trouvés:")
        for i, link in enumerate(company_links[:10]):
            href = link.get('href', '')
            text = link.get_text().strip()
            print(f"  {i+1}. href='{href}' | text='{text[:50]}...'")
        
        # Chercher d'abord les liens contenant "entreprise"
        for link in company_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            if 'entreprise' in href and any(word in text for word in entreprise.lower().split()):
                company_url = "https://www.charika.ma" + href if not href.startswith('http') else href
                print(f"✅ Lien entreprise trouvé: {company_url}")
                break
        
        # Si pas trouvé, chercher dans tous les liens
        if not company_url:
            print("🔍 Recherche dans tous les liens...")
            for link in company_links:
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                # Assouplir la recherche
                if href and (entreprise.lower() in text or any(word in text for word in entreprise.lower().split())):
                    if 'entreprise' in href or 'company' in href or '/fiche/' in href:
                        company_url = "https://www.charika.ma" + href if not href.startswith('http') else href
                        print(f"✅ Lien général trouvé: {company_url}")
                        break
        
        if not company_url:
            print("❌ Aucun lien vers la page de l'entreprise trouvé")
            return None
            
        if company_url:
            print(f"🌐 Accès à la page de l'entreprise: {company_url}")
            
            # Accéder à la page de l'entreprise
            company_response = requests.get(company_url, headers=headers, timeout=10)
            company_soup = BeautifulSoup(company_response.content, 'html.parser')
            
            # Méthode 1: Chercher spécifiquement dans les spans dropdown (structure identifiée)
            print("🔍 Méthode 1: Recherche dans les spans dropdown...")
            dropdown_spans = company_soup.find_all('span', class_='dropdown')
            print(f"📋 Trouvé {len(dropdown_spans)} spans dropdown")
            
            for i, dropdown in enumerate(dropdown_spans):
                dropdown_text = dropdown.get_text()
                print(f"  Dropdown {i+1}: {dropdown_text[:100]}...")
                
                # Vérifier si ce dropdown contient "E-mail"
                if 'E-mail' in dropdown_text or 'Email' in dropdown_text:
                    print(f"  ✅ Dropdown {i+1} contient 'E-mail'")
                    # Chercher les liens mailto dans ce dropdown
                    mailto_links = dropdown.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                    print(f"  📧 Trouvé {len(mailto_links)} liens mailto")
                    
                    for link in mailto_links:
                        email = link.get('href').replace('mailto:', '').strip()
                        if '@' in email and '.' in email.split('@')[1]:
                            print(f"  ✅ Email trouvé via dropdown: {email}")
                            return email
            
            # Méthode 2: Chercher tous les liens mailto avec différents sélecteurs
            print("🔍 Méthode 2: Recherche de tous les liens mailto...")
            email_selectors = [
                'a[href^="mailto:"]',
                'span.dropdown a[href^="mailto:"]',
                '.contact-info a[href^="mailto:"]',
                '.email a[href^="mailto:"]',
                '.contact a[href^="mailto:"]'
            ]
            
            for selector in email_selectors:
                email_elements = company_soup.select(selector)
                print(f"  Sélecteur '{selector}': {len(email_elements)} éléments")
                
                for element in email_elements:
                    href = element.get('href', '')
                    if href.startswith('mailto:'):
                        email = href.replace('mailto:', '').strip()
                        # Vérifier que c'est un email valide
                        if '@' in email and '.' in email.split('@')[1]:
                            print(f"  ✅ Email trouvé via sélecteur: {email}")
                            return email
            
            # Méthode 3: Recherche par pattern dans les spans contenant "E-mail"
            print("🔍 Méthode 3: Recherche dans spans contenant 'E-mail'...")
            email_spans = company_soup.find_all('span', string=lambda text: text and 'E-mail' in text)
            print(f"📋 Trouvé {len(email_spans)} spans avec 'E-mail'")
            
            for span in email_spans:
                # Chercher dans le parent ou les éléments suivants
                parent = span.parent
                if parent:
                    print(f"  Parent HTML: {str(parent)[:200]}...")
                    mailto_links = parent.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                    for link in mailto_links:
                        email = link.get('href').replace('mailto:', '').strip()
                        if '@' in email and '.' in email.split('@')[1]:
                            print(f"  ✅ Email trouvé via span parent: {email}")
                            return email
            
            # Méthode 4: Chercher dans le texte avec regex comme fallback
            print("🔍 Méthode 4: Recherche par regex dans tout le texte...")
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            page_text = company_soup.get_text()
            emails = re.findall(email_pattern, page_text)
            print(f"📧 Emails trouvés par regex: {emails}")
            
            if emails:
                # Filtrer les emails qui semblent pertinents
                for email in emails:
                    if not any(spam in email.lower() for spam in ['noreply', 'no-reply', 'example', 'test']):
                        print(f"  ✅ Email retenu: {email}")
                        return email
        
        print("❌ Aucun email trouvé")
        return None
        
    except Exception as e:
        print(f"❌ Erreur lors de la recherche sur Charika: {e}")
        return None

if __name__ == "__main__":
    # Test avec différentes entreprises
    test_companies = ["jetalu", "TGCC", "OCP"]
    
    for company in test_companies:
        print(f"\n{'='*50}")
        print(f"TEST: {company}")
        print(f"{'='*50}")
        
        result = get_email_from_charika(company)
        
        if result:
            print(f"✅ SUCCÈS: Email trouvé pour '{company}': {result}")
        else:
            print(f"❌ ÉCHEC: Aucun email trouvé pour '{company}'")
        
        print("\n" + "-"*50)