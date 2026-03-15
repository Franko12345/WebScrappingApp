import sys
import re
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

def _extract_date_from_snippet(snippet):
    """Extract leading date part from Terra/Google snippet (e.g. 'há 2 dias ...' or '13/12/2025 ...')."""
    if not snippet or not isinstance(snippet, str):
        return "", snippet or ""
    snippet = snippet.strip()
    # Match "há N dias/horas/minutos" or "DD/MM/YYYY" or "DD/MM/YYYY ..."
    m = re.match(r"(há\s+\d+\s+(?:dias?|horas?|minutos?)(?:\s+\.\.\.)?\s*)", snippet, re.I)
    if m:
        date_part = m.group(1).strip().rstrip("...").strip()
        rest = snippet[len(m.group(0)):].strip()
        return date_part, rest
    m = re.match(r"(\d{1,2}/\d{1,2}/\d{4}(?:\s+\.\.\.)?\s*)", snippet)
    if m:
        date_part = m.group(1).strip().rstrip("...").strip()
        rest = snippet[len(m.group(0)):].strip()
        return date_part, rest
    return "", snippet


def articleFormatter(article, tag):
    # Prefer the article link (href to terra content), not logo. Article is BeautifulSoup Tag.
    link_el = article.find("a", class_="gs-title", recursive=True)
    if not link_el:
        link_el = article.find("a", href=re.compile(r"terra\.com\.br/"), recursive=True)
    href = (link_el.get("href") or "").strip() if link_el else ""
    title_text = (link_el.get_text(strip=True) if link_el else "") or ""
    snippet_div = article.find("div", class_="gs-bidi-start-align gs-snippet", recursive=True)
    description = (snippet_div.get_text(strip=True) if snippet_div else "") or ""
    data_part, description_rest = _extract_date_from_snippet(description)
    if not title_text or title_text.lower() == "terra" or len(title_text) < 3:
        title_text = (description_rest[:200] + "..." if len(description_rest) > 200 else description_rest) or title_text
    return {
        "title": title_text,
        "link": href,
        "data": data_part,
        "description": description_rest,
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
        news = []

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
                    driver.get(f"https://www.terra.com.br/busca/?q={tag}#gsc.tab=1&gsc.q={tag}&gsc.page={page}")
                    acessed = True
                except:
                    print("Erro ao acessar a página, reiniciando navegador...")
                    driver.quit()
                    driver = webdriver.Chrome(service=driverpath, options=options)

            try:
                WebDriverWait(driver, 20).until_not( EC.presence_of_element_located((By.CLASS_NAME, "gsc-loading-resultsRoot")))
                WebDriverWait(driver, 20).until( EC.presence_of_element_located( (By.CLASS_NAME, "gs-webResult")))
                driver.implicitly_wait(5)
            except:
                continue

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pageNews = soup.find_all('div', class_='gsc-webResult gsc-result')
            news += pageNews

            news = list(set(news))

            parsedNews = [articleFormatter(article, tag) for article in pageNews]

            allNews += parsedNews

            print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page+1}\nTotal: {len(allNews)}\n")

            pageCounter += 1

            if max_news != -1:
                if len(allNews)-currentNewsNum > max_news:
                    allNews = allNews[:currentNewsNum+max_news]
                    break

            if(lastNewsNumber != len(allNews)):
                lastNewsNumber = len(allNews)
                resetCounter = 0
            else:
                resetCounter += 1
            
            if resetCounter == 5 or page == max_page:
                return allNews            

    return allNews

def storeAsExcel(data, final=False):
    rows = list(map(lambda article: article.values(), data))
    df = pd.DataFrame(rows, columns=["title", "link", "data", "description", "tag"])

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