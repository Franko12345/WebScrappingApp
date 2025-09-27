try:
    import sys
    from bs4 import BeautifulSoup
    from selenium import webdriver

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.action_chains import ActionChains

    import pandas as pd
    import time

    from tqdm import tqdm

    if input("Deseja rodar preparação de ambiente (RECOMENDADO PARA PRIMEIRA VEZ): [sim/não]") in ["sim", "Sim", "S", "s"]:
        raise Exception("Preparação de ambiente solicitada")
except:
    print("Configurando ambiente")
    
    import os
    import subprocess
    
    print("Checking for not installed packages...")
    
    result = subprocess.run(["pip", "list"], stdout=subprocess.PIPE, text=True)

    if not all([lib in result.stdout for lib in ["selenium","wget","pandas","openpyxl", "beautifulsoup4"]]):
        print("Installing packages...")
        os.system("pip install --upgrade selenium wget pandas openpyxl beautifulsoup4")
    
    print("All packages are installed!")
    
    
    print("Checking for outdated packages...")
    result = subprocess.run(["pip", "list", "--outdated"], stdout=subprocess.PIPE, text=True)
    
    if any([lib in result.stdout for lib in ["selenium","wget","pandas","openpyxl", "beautifulsoup4"]]):
        print("Updating packages...")
        os.system("pip install --upgrade selenium wget pandas openpyxl beautifulsoup4")

    print("All packages are updated!")
    
    import wget
    import zipfile
    
    if "chromedriver" not in os.listdir():
        print("Downloading chromedriver")
        filename = wget.download("https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.165/win64/chromedriver-win64.zip")
        with zipfile.ZipFile(f"./{filename}", 'r') as zip_ref:
            zip_ref.extractall("./chromedriver")
    else:
        print("Chromedriver found!")
    
    if "brave" not in os.listdir():
        print("Downloading brave")
        filename = wget.download("https://github.com/brave/brave-browser/releases/download/v1.76.82/brave-v1.76.82-win32-x64.zip")
        with zipfile.ZipFile(f"./{filename}", 'r') as zip_ref:
            zip_ref.extractall("./brave")
    else:
        print("Brave found!")

    from tqdm import tqdm
    from selenium import webdriver
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service

    import pandas as pd

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

def SCfilter(article):
    cidades_sc1 = pd.read_excel('./planilhas/cidade_sc1.xlsx')
    
    for key in [" sc ", "santa catarina", " sc", "sc "]:
        if key in article["title"].lower():
            return True
        
        
    for key in ["-sc-", "santa-catarina", "-sc", "sc-"]:
        if key in article["link"].split("/")[-1].lower():
            return True

    for cidade in cidades_sc1["MUNICIPIO"]:
        if cidade.lower() in article["title"].lower() or cidade.lower() in article["link"].split("/")[-1].lower():
            return True

    return False

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
                print("Erro ao acessar a página, reiniciando navegador...")
                driver.quit()
                driver = webdriver.Chrome(service=driverpath, options=options)

        WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, "title-text")))


        while True:
            try:
                ActionChains(driver).scroll_by_amount(0, 10000).perform()
                
                time.sleep(1)
                
                WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CSS_SELECTOR, "a[title=\"Veja Mais\"]") ) )
                                
                driver.find_element(By.CSS_SELECTOR, "a[title=\"Veja Mais\"]").click()

                WebDriverWait(driver, 10).until_not( EC.visibility_of_element_located( (By.CSS_SELECTOR, "i[class=\"button-icon fas fa-spin fa-sync nd-fa-loaded\"]") ) )

            except Exception as e:
                print(e)
                print(f"Page {tag} carregada completamente")
                break            
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        news = soup.find_all('div', class_='site-card-content')

        
        progress_bar = tqdm(total=len(news), desc=f"Formatando notícias com a tag {tag}", unit="notícias")
        parsedNews = [articleFormatter(article, tag, progress_bar) for article in news]

        print("Notícias formatadas!")

        print(f"Filtrando notícias com a tag {tag}...")
        parsedNews = list(filter(SCfilter, parsedNews))
                
        print("Notícias Filtradas!")
        
        allNews += parsedNews


        print(f"\nPlanilha salva com {len(allNews)} notícias para backup...")
        storeAsExcel(allNews)
        print("Salvo\n")
            
        print(f"\nNoticias coletadas: {len(parsedNews)}\nTag: {tag}\nTotal: {len(allNews)}\n")
        
            
    return allNews

def storeAsExcel(data):
    rows = list(map(lambda article: article.values(), data))
    df = pd.DataFrame(rows, columns=["title", "link", "data", "tag"])
    
    print(f"Número de noticias com duplicados: {len(df)}")
    
    df = df.drop("tag", axis=1)
    df = df.drop_duplicates()
    
    print(f"Número de noticias sem duplicados: {len(df)}")
    
    df.to_excel("./planilhas/noticias_ndmais.xlsx", index=False)
    


searchReference = sys.argv[2:]
max_news = sys.argv[1]

searchReference = list(map(lambda x: x.replace(" ", "+"), searchReference))

data = getNewsByTags(searchReference)

print(data)

storeAsExcel(data)