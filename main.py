from flask import Flask, render_template, request
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import re

# Initialiser Flask
app = Flask(__name__)

# Définir la route pour la page d'accueil
@app.route('/')
def index():
    return render_template('index.html')

# Définir la route pour le scraping
@app.route('/scrape')
def scrape():
    # Récupérer la valeur du champ texte
    search_query = request.args.get('search_query')
    # Construire l'URL de recherche Google Maps
    link = f"https://www.google.com/maps/search/{search_query}" if search_query else "https://www.google.com/maps/search/agence+web+biarritz"

    # Initialiser le webdriver Chrome
    browser = webdriver.Chrome()
    # Liste pour stocker les résultats
    results = []

    # Fonction pour extraire les données avec Selenium
    def Selenium_extractor():
        nonlocal results
        le = 0  # Initialise le compteur
        action = ActionChains(browser)
        while True:
            a = browser.find_elements(By.CLASS_NAME, "hfpxzc")
            print(len(a))
            if len(a) >= 20 or le > 20:
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
                        emails_found = re.findall(r'[\w\.-]+@[\w\.-]+', page_content)
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
    # Appeler la fonction pour extraire les données
    Selenium_extractor()
    # Fermer le navigateur
    browser.quit()

    # Retourner les résultats à afficher dans le template HTML
    print(results)
    return render_template('index.html', results=results)

# Exécuter l'application Flask
if __name__ == '__main__':
    app.run(debug=True)
