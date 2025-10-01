from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm  import tqdm
import pandas as pd
import time
import sys
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import unquote



def scrape_infinite_scroll(url, num_items):
    start_time = time.time()  

    driver.get(url)

    scraped_data = []
    noticia = {""}

    page_counter = 1

    with tqdm(total=num_items, desc="Raspando dados") as pbar:
        
        while len(scraped_data) < num_items:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_blocks = soup.find_all('li', {'class': 'widget widget--card widget--info'})
            
            for block in product_blocks:    
                if not block.find('a').get('href'):
                    continue
                try:
                    if len(scraped_data) >= num_items:
                        pbar.update(1)
                        break
                    noticia = {"Produto": block.find('div', class_='widget--info__header').text.strip(),
                               "Link": unquote("https" + block.find('a').get('href').split("https")[1]).split("&syn")[0],
                               "Título": block.find('div', 'widget--info__title').text.strip(),
                               "Data": block.find('div', 'widget--info__meta').text.strip(),
                               "Conteúdo": block.find('p', class_='widget--info__description').text.strip()
                              }
                    
                    scraped_data.append(noticia)
                except:
                    pass
                pbar.update(1)


            # Avança para a próxima página
            page_counter += 1
            driver.get(url + f"&page={page_counter}")

    return scraped_data

if __name__ == '__main__':
    searchReference = sys.argv[3:]
    max_news =  int(sys.argv[2])
    Verbose =  int(sys.argv[1])

    options = webdriver.ChromeOptions()


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
    options.add_argument('--disable-blink-features=AutomationControlled')

    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')

    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    
    # options.page_load_strategy = 'eager'

    driver = webdriver.Chrome(service=driverpath, options=options)

    df = pd.DataFrame(columns=["Produto", "Link", "Título","Data","Conteúdo"])
    
    scraped_data = []
    for chave in searchReference:
        # url = f"https://g1.globo.com/busca/?q={chave}&order=recent&from={2020}-01-01T00%3A00%3A00-0200&to={2020}-12-30T23%3A59%3A59-0200"
        url = f"https://g1.globo.com/busca/?q={chave}&order=recent"
        print(f"\nBuscando {chave}")
        scraped_data = scrape_infinite_scroll(url, max_news)

        dfTemp = pd.DataFrame(list(map(lambda x: x.values(), scraped_data)) ,columns=scraped_data[0].keys())
        df = pd.concat([df, dfTemp])
        df = df.drop_duplicates()
    
        df.to_excel('./result/result.xlsx', index=False)
    
    driver.quit()

    # Convertendo os dados para um DataFrame do pandas
    
    # Salvando o DataFrame em um arquivo Excel
    print("Raspagem de dados finalizada")
