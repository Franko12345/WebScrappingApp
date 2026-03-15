from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from tqdm import tqdm
import pandas as pd
import time
import sys
import os
from pathlib import Path

# Prevent "OSError: [WinError 6] The handle is invalid" when Chrome.__del__ runs after we already quit()
_orig_del = uc.Chrome.__del__
def _chrome_del_safe(self):
    try:
        _orig_del(self)
    except OSError:
        pass
uc.Chrome.__del__ = _chrome_del_safe

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import unquote

# G1 search: loading bar (optional) and "Veja mais" button for infinite scroll
G1_LOADING_CSS = ".MuiLinearProgress-root"
G1_LOAD_MORE_BUTTON_CSS = "button.pagination__load-more, button.fundo-cor-produto.pagination__load-more"
G1_LOAD_MORE_LOADING_CLASS = "loading"  # button has this class + disabled while loading
G1_CARD_CSS = "li.widget.widget--card.widget--info"


def _wait_g1_loading_gone(driver, timeout=45):
    """Wait for G1 loading bar to appear then disappear (if present)."""
    try:
        loading = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, G1_LOADING_CSS))
        )
        WebDriverWait(driver, timeout).until(EC.staleness_of(loading))
    except Exception:
        pass
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"{G1_CARD_CSS}, {G1_LOAD_MORE_BUTTON_CSS}"))
        )
    except Exception:
        pass
    time.sleep(0.5)


def _wait_load_more_ready(driver, timeout=25):
    """Wait for 'Veja mais' button to finish loading (lose 'loading' class and not disabled)."""
    def button_ready(d):
        try:
            btn = d.find_element(By.CSS_SELECTOR, G1_LOAD_MORE_BUTTON_CSS)
            cls = (btn.get_attribute("class") or "")
            disabled = btn.get_attribute("disabled") is not None
            return G1_LOAD_MORE_LOADING_CLASS not in cls and not disabled
        except Exception:
            return False
    try:
        WebDriverWait(driver, timeout).until(button_ready)
    except Exception:
        pass


def _parse_cards_from_page(driver, seen_links, scraped_data, num_items, pbar):
    """Parse current page for result cards; add new ones to scraped_data. Returns number of new items."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    product_blocks = soup.find_all("li", class_=lambda c: c and "widget" in c and "widget--card" in c and "widget--info" in c)
    if not product_blocks:
        product_blocks = soup.select("li.widget.widget--card.widget--info")
    added = 0
    for block in product_blocks:
        if len(scraped_data) >= num_items:
            break
        a = block.find("a")
        if not a or not a.get("href"):
            continue
        try:
            href = (a.get("href") or "").strip()
            if "https" in href:
                link = unquote("https" + href.split("https", 1)[1].split("&syn")[0])
            elif href.startswith("http"):
                link = unquote(href)
            elif href.startswith("/"):
                link = "https://g1.globo.com" + unquote(href)
            else:
                link = unquote(href)
            if link in seen_links:
                continue
            seen_links.add(link)
            title_el = block.find("div", class_="widget--info__title") or block.find("div", class_=lambda c: c and "widget--info__title" in str(c))
            meta_el = block.find("div", class_="widget--info__meta") or block.find("div", class_=lambda c: c and "widget--info__meta" in str(c))
            desc_el = block.find("p", class_="widget--info__description") or block.find("p", class_=lambda c: c and "widget--info__description" in str(c))
            title_from_el = (title_el.get_text(strip=True) if title_el else "") or ""
            title_from_link = (a.get_text(strip=True) if a else "") or ""
            # Prefer link text when title div is missing or is just "G1" (brand)
            if title_from_el and title_from_el.strip().lower() != "g1":
                title_final = title_from_el
            else:
                title_final = title_from_link or title_from_el
            noticia = {
                "title": title_final,
                "link": link,
                "data": meta_el.get_text(strip=True) if meta_el else "",
                "content": desc_el.get_text(strip=True) if desc_el else ""
            }
            scraped_data.append(noticia)
            added += 1
            pbar.update(1)
        except Exception:
            pass
    return added


def scrape_infinite_scroll(url, num_items):
    """Load search page once; scroll and click 'Veja mais' until we have enough or button is gone."""
    print(url)
    driver.get(url)
    time.sleep(2)
    _wait_g1_loading_gone(driver)

    scraped_data = []
    seen_links = set()

    with tqdm(total=num_items, desc="Raspando dados") as pbar:
        while len(scraped_data) < num_items:
            added = _parse_cards_from_page(driver, seen_links, scraped_data, num_items, pbar)
            if len(scraped_data) >= num_items:
                break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            try:
                button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, G1_LOAD_MORE_BUTTON_CSS))
                )
            except Exception:
                print("\nFim dos resultados (botão Veja mais não encontrado).")
                break

            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", button)
                _wait_load_more_ready(driver, timeout=25)
                time.sleep(0.3)
            except Exception:
                print("\nFim da busca (erro ao carregar mais).")
                break

    return scraped_data

if __name__ == '__main__':
    searchReference = sys.argv[3:]
    print(searchReference)
    max_news = int(sys.argv[2])
    # -1 = unlimited: scrape until a high cap so we get as many as available
    num_items = 100000 if max_news == -1 else max_news
    Verbose = int(sys.argv[1])

    # Use undetected-chromedriver to avoid bot detection (e.g. G1/Globo)
    # https://github.com/ultrafunkamsterdam/undetected-chromedriver
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    # Optional: use Brave if BRAVE_PATH is set (same as other scrapers)
    brave_path = os.environ.get("BRAVE_PATH")
    uc_kw = dict(options=options, headless=True, use_subprocess=True)
    if brave_path:
        uc_kw["browser_executable_path"] = brave_path
    # Match ChromeDriver to your Chrome/Brave major version to avoid SessionNotCreatedException.
    # Set UC_VERSION_MAIN=134 (or your browser's major version) if you update the browser.
    version_main = os.environ.get("UC_VERSION_MAIN")
    if version_main:
        uc_kw["version_main"] = int(version_main)
    else:
        uc_kw["version_main"] = 134  # Match current browser; change if you upgrade Chrome/Brave
    driver = uc.Chrome(**uc_kw)

    # Same column names as NSC/NDmais (title, link, data, content) for classification and download
    df = pd.DataFrame(columns=["title", "link", "data", "content"])
    local_appdata = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    result_dir = local_appdata / "Yast" / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    for chave in searchReference:
        url = f"https://g1.globo.com/busca/?q={chave}&order=recent&species=noticias"
        print(f"\nBuscando {chave}")
        scraped_data = scrape_infinite_scroll(url, num_items)

        if scraped_data:
            dfTemp = pd.DataFrame(scraped_data)
            df = pd.concat([df, dfTemp], ignore_index=True)
            df = df.drop_duplicates(subset=["link"])
        else:
            print(f"Nenhum resultado para '{chave}'.")

    # Save once after all keywords so we don't write partial results (e.g. 7) mid-run
    df.to_excel(result_dir / "result.xlsx", index=False)

    try:
        driver.quit()
    except (OSError, Exception):
        pass

    print("Raspagem de dados finalizada")