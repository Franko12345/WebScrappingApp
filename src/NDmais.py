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
    # Prefer the main article link (href to ndmais with path), not logo/category. Use BeautifulSoup API.
    links = article.find_all("a", href=True)
    article_link = None
    for a in links:
        href = a.get("href") or ""
        if "ndmais.com.br" in href and len(href) > 30:
            article_link = a
            break
    if not article_link and links:
        article_link = links[0]
    title = ""
    link = ""
    if article_link:
        title = (article_link.get("title") or article_link.get_text(strip=True) or "").strip()
        link = article_link.get("href") or ""
    if not title or title.lower() == "nd+":
        title_el = article.find("div", class_="title-text")
        title = (title_el.get_text(strip=True) if title_el else "") or title
    time_el = article.find("time")
    data = (time_el.get("title") or "").strip() if time_el else ""
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

        page = 0
        while(True):
            page += 1
            max_page = tags[tag]
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
                    a = article.find("a", href=True)
                    link = a.get("href") if a else None
                    if link and link not in seen_links:
                        seen_links.add(link)
                        new_articles.append(article)
                except Exception:
                    continue

            parsedNews = [articleFormatter(article, tag) for article in new_articles]

            allNews += parsedNews

            print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page}\nTotal: {len(allNews)}\n")

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

            # Try to load more content: scroll and look for "Veja mais" button
            import time
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # Check if "Veja mais" button exists (no more results = button is gone)
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.ajax-pagination-button, button[title='Veja mais']"))
                )
            except Exception:
                # Button not found = no more news, finish cleanly
                print(f"\nFim dos resultados (botão Veja mais não encontrado). Total: {len(allNews)}\n")
                return allNews

            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(1)
                time.sleep(0.5)
                current_article_count = len(driver.find_elements(By.CSS_SELECTOR, "div.site-card-content"))
                driver.execute_script("arguments[0].click();", button)
                try:
                    WebDriverWait(driver, 15).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.site-card-content")) > current_article_count
                    )
                except Exception:
                    try:
                        driver.find_element(By.CSS_SELECTOR, "button.ajax-pagination-button")
                        time.sleep(2)
                    except Exception:
                        pass
                time.sleep(1)
            except Exception:
                # Click or load failed; we already have current results, finish cleanly
                print(f"\nFim da busca para tag '{tag}'. Total: {len(allNews)}\n")
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
