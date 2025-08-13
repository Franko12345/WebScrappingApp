from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

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

@app.get("/")
def read_root():
    return FileResponse("main.html")

@app.get("/file")
def get_result():
    global Busy
    if get_state():
        Busy = False
        response = FileResponse("./result/result.xlsx",filename="result.xlsx", media_type='application/octet-stream')
        os.remove("result.xlsx")
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

@app.post("/")
def search_news(request: NewsRequest):
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

    return {
        "status": "success",
        "message": "Parâmetros recebidos com sucesso",
        "data": {
            "keyword": request.keyword,
            "fonte": request.fonte,
            "max_news": request.max_news
        }
    }
