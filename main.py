from flask import Flask, render_template, request
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import re
import ssl

from flask import Response
import json

# Initialiser Flask
app = Flask(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

def filter_results(results):
    unique_results = []
    seen_urls = set()
    valid_emails = []

    for result in results:
        # Vérifier si l'URL est unique
        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)

        # Vérifier le format de l'adresse e-mail
        if re.match(r'[^@]+@[^@]+\.[^@]+', result["email"]):
            valid_emails.append(result["email"])

    return unique_results, valid_emails

@app.route('/')
def index():
    return render_template('index.html')

# Ajouter une nouvelle route pour gérer le scrolling et le scraping progressif
@app.route('/scrape_progressive')
def scrape_progressive():
    search_query = request.args.get('search_query')
    link = f"https://www.google.com/maps/search/{search_query}" 
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    # Initialiser le webdriver Chrome
    browser = webdriver.Chrome(options=chrome_options)

    results = []

    # Fonction pour extraire les données de manière progressive
    def progressive_extraction():
        nonlocal results
        action = ActionChains(browser)
        prev_len = None  
        same_len_count = 0 
        processed_urls = {}  
        
        while True:
            a = browser.find_elements(By.CLASS_NAME, "hfpxzc")
            if len(a) == prev_len:
                same_len_count += 1
            else:
                prev_len = len(a)
                same_len_count = 0
            if same_len_count >= 3:
                break
            
            var = len(a)
            scroll_origin = ScrollOrigin.from_element(a[len(a)-1])
            action.scroll_from_origin(scroll_origin, 0, 30).perform()
            time.sleep(2)
        
        max_results = 1000
        results_count = 0
        
        for i in range(len(a)):
            try:
                scroll_origin = ScrollOrigin.from_element(a[i])
                action.scroll_from_origin(scroll_origin, 0, 10).perform()
                action.move_to_element(a[i]).perform()
                WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "hfpxzc")))
                browser.execute_script("arguments[0].click();", a[i])
                time.sleep(2)
                source = browser.page_source
                soup = BeautifulSoup(source, 'html.parser')
                links = soup.find_all('a', class_="lcr4fd S9kvJb")
                
                for link in links:
                    href = link.get('href')
                    
                    if href in processed_urls:
                        print("URL déjà traitée:", href)
                        continue
                    
                    browser.get(href)
                    time.sleep(2)
                    page_content = browser.page_source
                    mentions_legales = re.findall(r'Mentions\s+l[ée]gales', page_content, re.IGNORECASE)
                    
                    if mentions_legales:
                        print("Mentions légales trouvées pour:", href)
                        emails_found = set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_content))
                        phone_numbers_found = re.findall(r'(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]?\d{2}){4}', page_content)

                        for email in emails_found:
                            phone_number = None
                            if email not in processed_urls:  
                                for phone_number in phone_numbers_found:
                                    if phone_number not in processed_urls.values():  
                                        processed_urls[href] = phone_number  
                                        break
                                else:
                                    phone_number = None
                                
                                if phone_number:  
                                    results.append({"url": href, "phone_number": phone_number, "email": email})
                                    results_count += 1
                                
                                if results_count >= max_results:
                                    return
                    else:
                        print("Aucune mention légale trouvée pour:", href)
                        processed_urls[href] = None  
            except StaleElementReferenceException as e:
                print("Erreur de référence d'élément obsolète. Récupération des éléments à nouveau.")
                continue
            except Exception as e:
                print("Erreur inattendue:", e)
                continue

    # Ouvrir l'URL dans le navigateur
    browser.get(link)
    time.sleep(10)
    try:
        accept_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.VfPpkd-LgbsSe")))
        accept_button.click()
    except Exception as e:
        print("Erreur lors du clic sur Tout accepter:", e)

    # Appeler la fonction d'extraction progressive
    progressive_extraction()
    browser.quit()

    results, valid_emails = filter_results(results)
    results_json = json.dumps(results)  
    print(results_json)
    return render_template('index.html', results=results, valid_emails=valid_emails, results_json=results_json, download=True)

# Ajoutez une route pour télécharger les résultats au format CSV
@app.route('/download_csv')
def download_csv():
    # Récupérer la chaîne JSON des résultats passés en tant qu'argument
    results_json = request.args.get('results')

    # Vérifier si des résultats sont disponibles
    if results_json:
        # Convertir la chaîne JSON en une liste de dictionnaires
        results = json.loads(results_json)

        # Créez une chaîne CSV à partir des résultats
        csv_data = "URL,Email,Numero de telephone\n"
        for result in results:
            csv_data += f"{result['url']},{result['email']},{result['phone_number']}\n"

        # Créez une réponse Flask avec le contenu CSV
        response = Response(csv_data, mimetype='text/csv')
        response.headers.set("Content-Disposition", "attachment", filename="results.csv")
        return response
    else:
        return "Aucun résultat à télécharger"


if __name__ == '__main__':
    app.run(debug=True)