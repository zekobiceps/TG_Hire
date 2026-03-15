import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def scrape_linkedin_people(url, email, password, max_scrolls=10):
    """
    Scrapes the 'People' page of a LinkedIn company.
    Requires LinkedIn credentials to log in.
    """
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Needs a realistic user agent to avoid immediate blocks sometimes
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    scraped_data = []
    
    try:
        # 1. Login to LinkedIn
        driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        email_field = driver.find_element(By.ID, "username")
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.XPATH, "//*[@type='submit']")
        login_button.click()
        time.sleep(3) # Wait for login to complete
        
        # Check if login failed (e.g. CAPTCHA or wrong credentials)
        if "login" in driver.current_url or "checkpoint" in driver.current_url:
            print("Login failed or requires verification.")
            return {"error": "Échec de connexion ou vérification requise par LinkedIn."}
            
        # 2. Navigate to the target URL
        driver.get(url)
        time.sleep(5) # Wait for initial page load
        
        # Scroll to load profiles
        for _ in range(max_scrolls):
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try to click 'Show more results' if present
            try:
                show_more_button = driver.find_element(By.XPATH, "//button[contains(@class, 'scaffold-finite-scroll__load-button')]")
                show_more_button.click()
                time.sleep(2)
            except:
                pass # Button not found or not clickable yet
                
        # 3. Parse the page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # The typical class for member cards on the people page
        member_cards = soup.find_all("li", class_="org-people-profile-card__profile-card-spacing")
        
        for card in member_cards:
            # Extract Name
            name_element = card.find("div", class_="lt-line-clamp--single-line")
            name = name_element.text.strip() if name_element else "Utilisateur"
            
            # Extract Position
            position_element = card.find("div", class_="lt-line-clamp--multi-line")
            position = position_element.text.strip() if position_element else ""
            
            # Extract URL
            url_element = card.find("a", class_="app-aware-link")
            profile_url = url_element['href'] if url_element and 'href' in url_element.attrs else ""
            
            # Clean up URL (remove tracking parameters)
            if profile_url and "?" in profile_url:
                profile_url = profile_url.split("?")[0]
                
            if profile_url and not profile_url.startswith("http"):
                profile_url = "https://www.linkedin.com" + profile_url
                
            scraped_data.append({
                "name": name,
                "position": position,
                "url": profile_url
            })
            
    except Exception as e:
        return {"error": f"Erreur lors du scraping: {str(e)}"}
    finally:
        driver.quit()
        
    return scraped_data

if __name__ == "__main__":
    # Test script locally
    import sys
    if len(sys.argv) == 4:
        url = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        results = scrape_linkedin_people(url, email, password, max_scrolls=2)
        import json
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python linkedin_scraper.py <url> <email> <password>")
