import sys
from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

options = webdriver.ChromeOptions()

import os

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

def articleFormatter(article, tag): 
    return {
        "title": article.find("h3").text.strip(),
        "link": article.find("a").get_attribute_list("href")[0],
        "data": article.find("div", class_="date").text.strip(),
        "tag": tag
    }

def getNewsByTags(tags):
    global driver
    global max_news
    allNews = []

    pageCounter = 0
    for tag in tags.keys():
        currentNewsNum = len(allNews)

        for page in range(tags[tag]):
            if pageCounter % 10 == 0:
                print(f"\nPlanilha salva com {len(allNews)} notícias para backup...")
                storeAsExcel(allNews)
                print("Salvo\n")
            
            acessed = False
            
            while not acessed:
                try:
                    driver.get(f"https://www.nsctotal.com.br/tag/{tag}?page={page}")
                    acessed = True
                except:
                    print("Erro ao acessar a página, reiniciando navegador...")
                    driver.quit()
                    driver = webdriver.Chrome(service=driverpath, options=options)
    
            try:
                WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, "date") ) )
                driver.implicitly_wait(5)
            except:
                continue            
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            news = soup.find_all('div', class_='featured-news-thumb')
            
            parsedNews = [articleFormatter(article, tag) for article in news]
            
            allNews += parsedNews
            
            print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nPágina:{page}\nTotal: {len(allNews)}\n")
            
            pageCounter += 1
            
            
            if len(allNews)-currentNewsNum > max_news:
                allNews = allNews[:currentNewsNum+max_news]
                break
            
    return allNews

def storeAsExcel(data, final=False):
    rows = list(map(lambda article: article.values(), data))
    df = pd.DataFrame(rows, columns=["title", "link", "data", "tag"])
    
    print(f"Número de noticias com duplicados: {len(df)}")
    
    df = df.drop("tag", axis=1)
    df = df.drop_duplicates()
    
    print(f"Número de noticias sem duplicados: {len(df)}")
    
    if not final:
        df.to_excel("./backup/result.xlsx", index=False)
    else:
        df.to_excel("./result/result.xlsx", index=False)
            

searchReference = sys.argv[3:]
max_news = int(sys.argv[2])

searchReference = {x:int(round((max_news/10)+0.5)) for x in list(map(lambda x: x.replace(" ", "+"), searchReference))}

data = getNewsByTags(searchReference)

storeAsExcel(data, True)

driver.quit()