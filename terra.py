from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm  import tqdm
import pandas as pd
import time
import sys
# from fake_useragent import UserAgent

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

options = webdriver.ChromeOptions()

options.binary_location = "./brave/brave.exe"

driverpath = Service("./chromedriver/chromedriver-win64/chromedriver.exe")

# options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  # Evita problemas de memória compartilhada
options.add_argument('--disable-web-security')
options.add_argument('--disable-site-isolation-trials')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument('--disable-notifications')

options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

options.page_load_strategy = 'eager'

# options.add_argument(f'user-agent={UserAgent().random}')

driver = webdriver.Chrome(service=driverpath, options=options)

def articleFormatter(article, tag, progress_bar=None): 
    progress_bar.update(1)
    return {
        "title": article.find("a", class_="gs-title", recursive=True).text,
        "link": article.find("a", class_="gs-title", recursive=True).get_attribute_list("href")[0],
        "description": article.find("div", class_="gs-bidi-start-align gs-snippet", recursive=True).text,
        "tag": tag
    }

def remove_duplicates(news):
    normalized_articles = {}
    for article in news:
        normalized_articles[article["link"]] = article
    return normalized_articles.values()

Verbose = False

def printVerbose(s):
    global Verbose
    if Verbose:
        print(s)

def getNewsByTags(tags):
    global driver
    allNews = []
    news = []
    for tag in tags:
        page = 1
        while True:
            acessed = False
            
            while not acessed:
                try:
                    driver.get(f"https://www.terra.com.br/busca/?q={tag}#gsc.tab=1&gsc.q={tag}&gsc.page={page}")
                    acessed = True
                except:
                    printVerbose("Erro ao acessar a página, reiniciando navegador...")
                    driver.quit()
                    driver = webdriver.Chrome(service=driverpath, options=options)

                #Handle of captchas

            WebDriverWait(driver, 20).until_not( EC.presence_of_element_located((By.CLASS_NAME, "gsc-loading-resultsRoot")))
            WebDriverWait(driver, 20).until( EC.presence_of_element_located( (By.CLASS_NAME, "gs-webResult")))
            print("Page loaded!")

            #Parse current page results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            news += soup.find_all('div', class_='gsc-webResult gsc-result')

            news = list(set(news))

            print()
            print(f"max {max_news} len {len(news)}")
            print()

            if len(news) >= max_news:
                print("Max number of new reached")
                break

            page += 1
        
        news = news[:max_news]

        progress_bar = tqdm(total=len(news), desc=f"Formatando notícias com a tag {tag}", unit="notícias")
        parsedNews = [articleFormatter(article, tag, progress_bar) for article in news]
        
        printVerbose("Notícias formatadas!")

        allNews += parsedNews
        
        printVerbose(f"\nPlanilha salva com {len(allNews)} notícias para backup...")
        storeAsExcel(allNews)
        printVerbose("Salvo\n")
            
        printVerbose(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nTotal: {len(allNews)}\n")
        
            
    return allNews

def storeAsExcel(data):
    rows = list(map(lambda article: article.values(), data))
    df = pd.DataFrame(rows, columns=["title", "link", "data", "tag"])
    
    printVerbose(f"Número de noticias com duplicados: {len(df)}")
    
    df = df.drop("tag", axis=1)
    df = df.drop_duplicates()
    
    printVerbose(f"Número de noticias sem duplicados: {len(df)}")
    
    df.to_excel("./result/result.xlsx", index=False)
    

searchReference = sys.argv[3:]
max_news =  int(sys.argv[2])
Verbose =  int(sys.argv[1])

if Verbose in [1,0]:
    Verbose = bool(Verbose)
else:
    raise TypeError("Verbose Must be 1 or 0")

searchReference = list(map(lambda x: x.replace(" ", "+"), searchReference))

data = getNewsByTags(searchReference)

printVerbose(data)

storeAsExcel(data)