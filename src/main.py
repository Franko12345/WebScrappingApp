import os
import sys
from pathlib import Path
from signal import SIGTERM
from threading import Thread

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from asyncio import sleep, create_task
from uvicorn import run as uvi_run
from webview import settings as webview_settings
from webview import start as webview_start
from webview import create_window

# Handle PyInstaller bundle path
if getattr(sys, 'frozen', False):
    # Running as a bundled executable
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Running as a normal Python script
    BASE_DIR = Path(__file__).parent.parent

app = FastAPI()

# Configurar CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para os dados recebidos
class NewsRequest(BaseModel):
    keyword: str
    fonte: str
    max_news: int

Busy = False

async def result_cleaner():
    await sleep(2)
    result_path = BASE_DIR / "result" / "result.xlsx"
    if result_path.exists():
        os.remove(str(result_path))


def busySetter(value):
    global Busy
    Busy = value

# Mount static files for assets
assets_path = BASE_DIR / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

@app.get("/")
def read_root():
    html_path = BASE_DIR / "main.html"
    return FileResponse(str(html_path))

@app.get("/file")
async def get_result():
    global Busy
    print("Trying to get result")
    if get_state():
        Busy = False
        result_path = BASE_DIR / "result" / "result.xlsx"
        response = FileResponse(str(result_path), filename="result.xlsx", media_type='application/octet-stream')
        create_task(result_cleaner())
        return response
    
@app.get("/finished")
def get_state():
    result_dir = BASE_DIR / "result"
    if result_dir.exists():
        return "result.xlsx" in os.listdir(str(result_dir))
    return False

@app.get("/busy")
def get_busy():
    global Busy
    
    result_dir = BASE_DIR / "result"
    if result_dir.exists() and "result.xlsx" in os.listdir(str(result_dir)) and Busy:
        Busy = False
    
    return Busy

script_table = {
    "G1": "g1",
    "nd+": "NDmais",
    "nsc": "NSC"
}

@app.post("/")
async def search_news(request: NewsRequest):
    global Busy
    if Busy:
        return {
                "status": "fail",
                "message": "Busy",
            }
    print(f"Palavra-chave recebida: {request.keyword}")
    print(f"Fonte recebida: {request.fonte}")
    print(f"Número máximo de notícias: {request.max_news}")
    print()
    Busy = True

    buscadores_path = BASE_DIR / "buscadores" / f"{script_table[request.fonte]}.exe"
    os.system(f'start "{buscadores_path}" 0 {int(request.max_news)} {request.keyword}')

    return {
        "status": "success",
        "message": "Parâmetros recebidos com sucesso",
        "data": {
            "keyword": request.keyword,
            "fonte": request.fonte,
            "max_news": request.max_news
        }
    }


def serve():
    uvi_run(app, port=5555, reload=False)

def open_window():
    webview_settings['ALLOW_DOWNLOADS'] = True
    create_window('Buscador de noticias', 'http://localhost:5555')
    webview_start()

if __name__ == "__main__":
    t1 = Thread(target=serve)
    t1.start()

    open_window()
    
    os.kill(os.getpid(), SIGTERM)

    