import sys
from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from pathlib import Path

options = webdriver.ChromeOptions()

import os
from pathlib import Path

brave_path = os.environ.get("BRAVE_PATH")
options.binary_location = str(brave_path)

driver_path = os.environ.get("CHROMEDRIVER_PATH")
driverpath = Service(driver_path)
# driverpath = Service()


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
# Timeout so we don't hang forever on a page that never loads (e.g. past last page)
driver.set_page_load_timeout(25)

def articleFormatter(article, tag):
    # Article is a BeautifulSoup Tag; use .get() and .get_text(), not .get_attribute_list()
    a = article.find("a", href=True)
    link = (a.get("href") or "").strip() if a else ""
    h3 = article.find("h3")
    title_from_h3 = (h3.get_text(strip=True) if h3 else "") or ""
    title_from_link = (a.get("title") or (a.get_text(strip=True) if a else "") or "").strip() if a else ""
    # Prefer headline that is not just the tag name (e.g. "nsc") or too short
    if title_from_h3 and title_from_h3.lower() != tag.lower() and len(title_from_h3) > 3:
        title = title_from_h3
    elif title_from_link and title_from_link.lower() != tag.lower() and len(title_from_link) > 3:
        title = title_from_link
    else:
        title = title_from_h3 or title_from_link
    date_el = article.find("div", class_="date")
    data = (date_el.get_text(strip=True) if date_el else "") or ""
    return {
        "title": title,
        "link": link,
        "data": data,
        "tag": tag
    }

def getNewsByTags(tags):
    global driver
    global max_news
    allNews = []
    resetCounter = 0
    lastNewsNumber = 0

    pageCounter = 0
    for tag in tags.keys():
        currentNewsNum = len(allNews)

        page = 0
        while(True):
            page += 1
            max_page = tags[tag]
            if pageCounter % 10 == 0:
                print(f"\nPlanilha salva com {len(allNews)} notícias para backup...")
                storeAsExcel(allNews)
                print("Salvo\n")

            acessed = False

            while not acessed:
                try:
                    driver.get(f"https://www.nsctotal.com.br/tag/{tag}?page={page}")
                    acessed = True
                except Exception as e:
                    print(f"Erro ao acessar a página {page} ({e}), assumindo fim dos resultados.")
                    return allNews

            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "date")))
                driver.implicitly_wait(5)
            except Exception:
                # Page loaded but no content or took too long; treat as end of results
                print(f"\nPágina {page} sem conteúdo ou timeout. Total: {len(allNews)}\n")
                return allNews

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            news = soup.find_all('div', class_='featured-news-thumb')

            parsedNews = [articleFormatter(article, tag) for article in news]

            # No articles on this page = end of results, stop immediately
            if len(parsedNews) == 0:
                print(f"\nFim dos resultados (página {page} vazia). Total: {len(allNews)}\n")
                return allNews

            # Partial page (e.g. 7 instead of 10) = last page; stop so we never request the next page (which can hang)
            if len(parsedNews) < 10:
                allNews += parsedNews
                print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page}\nTotal: {len(allNews)}\n")
                print(f"\nÚltima página parcial ({len(parsedNews)} itens), encerrando. Total: {len(allNews)}\n")
                return allNews

            allNews += parsedNews

            print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page}\nTotal: {len(allNews)}\n")

            pageCounter += 1

            if max_news != -1:
                if len(allNews)-currentNewsNum > max_news:
                    allNews = allNews[:currentNewsNum+max_news]
                    break
            
            if lastNewsNumber != len(allNews):
                lastNewsNumber = len(allNews)
                resetCounter = 0
            else:
                resetCounter += 1
            
            # Stop when no new items for 3 pages in a row or reached max_page
            if resetCounter >= 3 or page == max_page:
                print(f"\nParando (sem novos resultados ou limite de páginas). Total: {len(allNews)}\n")
                return allNews   

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
# -1 = unlimited: use a large page limit so we keep fetching until no more results
effective_max = 10000 if max_news == -1 else max_news
searchReference = {x: int(round((effective_max / 10) + 0.5)) for x in list(map(lambda x: x.replace(" ", "+"), searchReference))}

data = getNewsByTags(searchReference)

storeAsExcel(data, True)

driver.quit()
