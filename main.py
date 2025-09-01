import time
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import subprocess
import asyncio

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
    await asyncio.sleep(2)
    os.remove("./result/result.xlsx")


def busySetter(value):
    global Busy
    Busy = value

@app.get("/")
def read_root():
    return FileResponse("main.html")

@app.get("/file")
async def get_result():
    global Busy
    print("Trying to get result")
    if get_state():
        Busy = False
        response = FileResponse("./result/result.xlsx",filename="result.xlsx", media_type='application/octet-stream')
        asyncio.create_task(result_cleaner())
        return response
    
@app.get("/finished")
def get_state():
    return "result.xlsx" in os.listdir("./result")

@app.get("/busy")
def get_busy():
    global Busy
    
    if "result.xlsx" in os.listdir("./result") and Busy:
        Busy = False
    
    return Busy

script_table = {
    "G1": "G1.py",
    "nd+": "NDmais2.py",
    "nsc": "NSC.py"
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

    Busy = True

    os.system(f"start ./{script_table[request.fonte]} 0 {int(request.max_news)} {request.keyword}")

    return {
        "status": "success",
        "message": "Parâmetros recebidos com sucesso",
        "data": {
            "keyword": request.keyword,
            "fonte": request.fonte,
            "max_news": request.max_news
        }
    }
