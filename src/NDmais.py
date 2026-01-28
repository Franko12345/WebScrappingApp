import sys
from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from pathlib import Path

options = webdriver.ChromeOptions()

import os

brave_path = os.environ.get("BRAVE_PATH")
options.binary_location = str(brave_path)

driver_path = os.environ.get("CHROMEDRIVER_PATH")
driverpath = Service(driver_path)

options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  # Evita problemas de memória compartilhada
options.add_argument('--disable-web-security')
options.add_argument('--disable-site-isolation-trials')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument('--disable-notifications')

options.page_load_strategy = 'eager'

driver = webdriver.Chrome(options=options)

def articleFormatter(article, tag):
    return {
        "title": article.find("a").get_attribute_list("title")[0].strip(),
        "link": article.find("a").get_attribute_list("href")[0],
        "data": article.find("time").get_attribute_list("title")[0].strip(),
        "tag": tag
    }

def getNewsByTags(tags):
    global driver
    global max_news
    allNews = []
    seen_links = set()

    pageCounter = 0
    for tag in tags.keys():
        currentNewsNum = len(allNews)

        acessed = False
        while not acessed:
            try:
                driver.get(f"https://ndmais.com.br/?s={tag}")
                acessed = True
            except:
                print("Erro ao acessar a página, reiniciando navegador...")
                driver.quit()
                driver = webdriver.Chrome(service=driverpath, options=options)

        try:
            WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, "title-text")))
            driver.implicitly_wait(5)
        except:
            continue

        for page in range(tags[tag]):
            if pageCounter % 10 == 0:
                print(f"\nPlanilha salva com {len(allNews)} notícias para backup...")
                storeAsExcel(allNews)
                print("Salvo\n")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            news = soup.find_all('div', class_='site-card-content')

            # Filter out duplicates by link
            new_articles = []
            for article in news:
                try:
                    link = article.find("a").get_attribute_list("href")[0]
                    if link not in seen_links:
                        seen_links.add(link)
                        new_articles.append(article)
                except:
                    continue

            parsedNews = [articleFormatter(article, tag) for article in new_articles]

            allNews += parsedNews

            print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page+1}\nTotal: {len(allNews)}\n")

            pageCounter += 1

            if len(allNews)-currentNewsNum > max_news:
                allNews = allNews[:currentNewsNum+max_news]
                break

            # Try to load more content for next iteration
            if page < tags[tag] - 1:
                try:
                    ActionChains(driver).scroll_by_amount(0, 10000).perform()
                    
                    import time
                    time.sleep(1)
                    
                    WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CSS_SELECTOR, "a[title=\"Veja Mais\"]") ) )
                                    
                    driver.find_element(By.CSS_SELECTOR, "a[title=\"Veja Mais\"]").click()

                    WebDriverWait(driver, 10).until_not( EC.visibility_of_element_located( (By.CSS_SELECTOR, "i[class=\"button-icon fas fa-spin fa-sync nd-fa-loaded\"]") ) )
                except Exception as e:
                    print(f"Page {tag} carregada completamente")
                    break

    return allNews

def storeAsExcel(data, final=False):
    rows = list(map(lambda article: article.values(), data))
    df = pd.DataFrame(rows, columns=["title", "link", "data", "tag"])

    print(f"Número de noticias com duplicados: {len(df)}")

    df = df.drop("tag", axis=1)
    df = df.drop_duplicates()

    print(f"Número de noticias sem duplicados: {len(df)}")

    local_appdata = Path(os.environ["LOCALAPPDATA"])

    folder = local_appdata / Path("Yast/backup/") if not final else local_appdata / Path("Yast/result/")

    # Create the folder if it doesn't exist
    folder.mkdir(parents=True, exist_ok=True)

    # Save the Excel file
    file_path = folder / ("result.xlsx")
    df.to_excel(file_path, index=False)


searchReference = sys.argv[3:]
max_news = int(sys.argv[2])

searchReference = {x:int(round((max_news/10)+0.5)) for x in list(map(lambda x: x.replace(" ", "+"), searchReference))}

data = getNewsByTags(searchReference)

storeAsExcel(data, True)

driver.quit()
