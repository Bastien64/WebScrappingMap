from flask import Flask, render_template, request, send_file, Response
from flask_dependencies import *

app = Flask(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

def filter_results(results):
    unique_results = []
    seen_urls = set()
    valid_emails = []

    for result in results:

        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)

        if re.match(r'[^@]+@[^@]+\.[^@]+', result["email"]):
            valid_emails.append(result["email"])

    return unique_results, valid_emails

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scrape_progressive')
def scrape_progressive():
    search_query = request.args.get('search_query')
    link = f"https://www.google.com/maps/search/{search_query}" 
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")

    browser = webdriver.Chrome(options=chrome_options)

    results = []


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
        
        max_results = 10000
        results_count = 0
        
        for i in range(len(a)):
            try:
                scroll_origin = ScrollOrigin.from_element(a[i])
                action.scroll_from_origin(scroll_origin, 0, 10).perform()
                action.move_to_element(a[i]).perform()
                WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "hfpxzc")))
                browser.execute_script("arguments[0].click();", a[i])
                time.sleep(5)
                source = browser.page_source
                soup = BeautifulSoup(source, 'html.parser')
                links = soup.find_all('a', class_="lcr4fd S9kvJb")
                print(links)
                print("Nombre de liens trouvés:", len(links))
                
                for link in links:
                    href = link.get('href')
                    parsed_url = urlparse(href)


                    if parsed_url.scheme not in ['http', 'https']:
                        print("URL invalide:", href)
                        continue

                    print("Lien trouvé:", href)

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
                        print("Emails trouvés:", emails_found)
                        phone_numbers_found = re.findall(r'0\d\s\d{2}\s\d{2}\s\d{2}\s\d{2}', page_content)
                        print ("Numéros de téléphone trouvés:", phone_numbers_found)

                        for email in emails_found:
                            phone_number = "Téléphone non trouvé"  # 
                            if email not in processed_urls:  
                                for phone_number in phone_numbers_found:
                                    if phone_number not in processed_urls.values():  
                                        processed_urls[href] = phone_number  
                                        print("Email trouvé:", email)
                                        break
                                else:
                                     phone_number = "Téléphone non trouvé"  # 
                                
                                if phone_number:  
                                    results.append({"url": href, "phone_number": phone_number, "email": email})
                                    results_count += 1
                                    print("Résultats trouvés:", results_count)
                            
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


    browser.get(link)
    time.sleep(10)
    try:
        accept_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.VfPpkd-LgbsSe")))
        accept_button.click()
    except Exception as e:
        print("Erreur lors du clic sur Tout accepter:", e)


    progressive_extraction()
    browser.quit()

    results, valid_emails = filter_results(results)
    results_json = json.dumps(results)  
    print(results_json)
    return render_template('index.html', results=results, valid_emails=valid_emails, results_json=results_json, download=True)



@app.route('/download_csv')
def download_csv():

    results_json = request.args.get('results')


    if results_json:
        results = json.loads(results_json)
        csv_data = "URL,Email,Numero de telephone\n"
        for result in results:
            csv_data += f"{result['url']},{result['email']},{result['phone_number']}\n"
        response = Response(csv_data, mimetype='text/csv')
        response.headers.set("Content-Disposition", "attachment", filename="results.csv")
        return response
    else:
        return "Aucun résultat à télécharger"

@app.route('/merge', methods=['POST'])
def merge():
    if request.method == 'POST':
        file1 = request.files['file1']
        file2 = request.files['file2']

        file1.save(file1.filename)
        file2.save(file2.filename)

        merged_file = merge_csv(file1.filename, file2.filename)
        os.remove(file1.filename)
        os.remove(file2.filename)

        return send_file(merged_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)