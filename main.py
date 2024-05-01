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


@app.route('/scrape')
def scrape():
    search_query = request.args.get('search_query')
    link = f"https://www.google.com/maps/search/{search_query}" 
    chrome_options = Options()
    chrome_options.add_argument('--ignore-ssl-errors=true')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(options=chrome_options)

# Liste pour stocker les résultats
    results = []

    def extract_emails(page_content):
        emails_found = re.findall(r'[\w\.-]+@[\w\.-]+', page_content)
        return set(emails_found)

    def extract_links(page_content):
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all('a', class_="lFl0Oc")
        return [link.get('href') for link in links]
    

# Modifier votre fonction process_page() pour capturer les exceptions SSL
    def process_page(href):
        try:
            browser.get(href)
            time.sleep(2)
            page_content = browser.page_source
            mentions_legales = re.findall(r'Mentions\s+l[ée]gales', page_content, re.IGNORECASE)
            if mentions_legales:
                print("Mentions légales trouvées pour:", href)
                # Utiliser une expression régulière améliorée pour trouver les adresses e-mail
                emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_content)
                for email in emails:
                    results.append({"url": href, "email": email})
            else:
                print("Aucune mention légale trouvée pour:", href)
                # Si aucune mention légale trouvée, ajouter un résultat avec une indication
                results.append({"url": href, "email": "Aucune mention légale trouvée"})
        except Exception as e:
            print("Erreur lors de l'accès à la page:", e)


    def Selenium_extractor():
        nonlocal results
        le = 0  # Initialise le compteur
        action = ActionChains(browser)
        prev_len = None  # Variable pour stocker la longueur précédente de a
        same_len_count = 0  # Compteur pour suivre le nombre de fois que la longueur de a reste la même
        while True:
            a = browser.find_elements(By.CLASS_NAME, "hfpxzc")
            print(len(a))
            # Vérifier si la longueur de a est égale à la longueur précédente
            if len(a) == prev_len:
                same_len_count += 1
            else:
                prev_len = len(a)
                same_len_count = 0
            
            # Si la longueur de a reste la même pendant trois itérations consécutives
            if same_len_count >= 3:
                break
            
            var = len(a)
            scroll_origin = ScrollOrigin.from_element(a[len(a)-1])
            action.scroll_from_origin(scroll_origin, 0, 30).perform()
            time.sleep(2)
            le += 1


        max_results = 20
        results_count = 0
        # Créer un ensemble pour stocker les adresses e-mail uniques
        unique_emails = set()
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
                    browser.get(href)
                    time.sleep(2)
                    page_content = browser.page_source
                    mentions_legales = re.findall(r'Mentions\s+l[ée]gales', page_content, re.IGNORECASE)
                    if mentions_legales:
                        print("Mentions légales trouvées pour:", href)
                        emails_found = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_content)
                        for email in emails_found:
                            # Vérifier si l'e-mail est déjà dans l'ensemble unique_emails
                            if email not in unique_emails:
                                unique_emails.add(email)
                                print("Adresse e-mail trouvée:", email)
                                # Ajouter l'URL et l'e-mail à la liste des résultats
                                results.append({"url": href, "email": email})
                                results_count += 1
                                if results_count >= max_results:
                                    return
                    else:
                        print("Aucune mention légale trouvée pour:", href)
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

    Selenium_extractor()
    browser.quit()
    results, valid_emails = filter_results(results)
    results_json = json.dumps(results)  
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
        csv_data = "URL,Email\n"
        for result in results:
            csv_data += f"{result['url']},{result['email']}\n"

        # Créez une réponse Flask avec le contenu CSV
        response = Response(csv_data, mimetype='text/csv')
        response.headers.set("Content-Disposition", "attachment", filename="results.csv")
        return response
    else:
        return "Aucun résultat à télécharger"


if __name__ == '__main__':
    app.run(debug=True)
