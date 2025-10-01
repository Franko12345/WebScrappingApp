from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm  import tqdm
import pandas as pd
import time
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

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

driver = webdriver.Chrome(service=driverpath, options=options)

def articleFormatter(article, tag, progress_bar=None): 
    progress_bar.update(1)
    return {
        "title": article.find("a").get_attribute_list("title")[0].strip(),
        "link": article.find("a").get_attribute_list("href")[0],
        "data": article.find("time").get_attribute_list("title")[0].strip(),
        "tag": tag
    }

Verbose = False

def printVerbose(s):
    global Verbose
    if Verbose:
        print(s)

def getNewsByTags(tags):
    global driver
    allNews = []
    for tag in tags:
        acessed = False
        
        while not acessed:
            try:
                driver.get(f"https://ndmais.com.br/?s={tag}")
                acessed = True
            except:
                printVerbose("Erro ao acessar a página, reiniciando navegador...")
                driver.quit()
                driver = webdriver.Chrome(service=driverpath, options=options)

        WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, "title-text")))


        while True:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            news = soup.find_all('div', class_='site-card-content')
            print()
            print(f"max {max_news} len {len(news)}")
            print()

            if len(news) >= max_news:
                print("Max number of new reached")
                break

            try:
                ActionChains(driver).scroll_by_amount(0, 10000).perform()
                
                time.sleep(1)
                
                WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CSS_SELECTOR, "a[title=\"Veja Mais\"]") ) )
                                
                driver.find_element(By.CSS_SELECTOR, "a[title=\"Veja Mais\"]").click()

                WebDriverWait(driver, 10).until_not( EC.visibility_of_element_located( (By.CSS_SELECTOR, "i[class=\"button-icon fas fa-spin fa-sync nd-fa-loaded\"]") ) )

            except Exception as e:
                printVerbose(e)
                printVerbose(f"Page {tag} carregada completamente")
                break            
        
        news = news[:max_news]
        
        printVerbose(f"NEW max {max_news} len {len(news)}")

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

driver.quit()