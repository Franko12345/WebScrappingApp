import json
import os
import re
import sys
import subprocess
import time
from pathlib import Path
from signal import SIGTERM
from threading import Thread

import pandas as pd
import requests
from fastapi import FastAPI

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from asyncio import sleep, create_task
from uvicorn import run as uvi_run
from webview import settings as webview_settings
from webview import start as webview_start
from webview import create_window
try:
    from src.version_check import check_update_available
except ImportError:
    # Fallback for when running as script
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from version_check import check_update_available

# Handle PyInstaller bundle path
if getattr(sys, 'frozen', False):
    # Running as a bundled executable
    # For assets/HTML, use MEIPASS (temporary extraction directory)
    ASSETS_DIR = Path(sys._MEIPASS)
    # For executables and other files, use the directory where the exe is located
    EXE_DIR = Path(sys.executable).parent
else:
    # Running as a normal Python script
    ASSETS_DIR = Path(__file__).parent.parent
    EXE_DIR = Path(__file__).parent.parent

# BASE_DIR for backward compatibility (used for assets)
BASE_DIR = ASSETS_DIR

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


def _get_config_path() -> Path:
    """Path to persisted app config (classifications + API key). Survives app restart."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    else:
        base = Path(os.path.expanduser("~"))
    config_dir = base / "Yast"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


@app.get("/api/config")
def get_config():
    """Return persisted classifications and Gemini API key from disk."""
    path = _get_config_path()
    if not path.exists():
        return {"classes_groups": {}, "gemini_api_key": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "classes_groups": data.get("classes_groups", {}),
            "gemini_api_key": data.get("gemini_api_key", ""),
        }
    except Exception as e:
        print(f"Error reading config: {e}")
        return {"classes_groups": {}, "gemini_api_key": ""}


class AppConfigPayload(BaseModel):
    classes_groups: dict = {}
    gemini_api_key: str = ""


@app.post("/api/config")
def save_config(payload: AppConfigPayload):
    """Persist classifications and Gemini API key to disk."""
    path = _get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "classes_groups": payload.classes_groups,
                    "gemini_api_key": payload.gemini_api_key or "",
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        return {"status": "ok"}
    except Exception as e:
        print(f"Error writing config: {e}")
        return {"status": "error", "message": str(e)}


# --- News classification with Gemini ---
# Gemini 2.5 Flash: best price-performance for high-volume tasks (gemini_models.md)
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
NAO_SE_ENCAIXA = "Não se encaixa em nenhuma classificação"
# Max items per batch to stay within context and output token limits
CLASSIFY_BATCH_SIZE = 80


def _get_categories_for_group(classes_groups: dict, group_key: str):
    """Return list of (name, description) for the given group."""
    group = classes_groups.get(group_key) or {}
    categories = []
    for key, value in group.items():
        if key == "name":
            continue
        if isinstance(value, dict) and "name" in value:
            name = value.get("name", "").strip()
            desc = (value.get("description") or "").strip()
            if name:
                categories.append((name, desc))
    return categories


def _normalize_label(text: str, valid_names: set) -> str:
    """Map model output to a valid category name or NAO_SE_ENCAIXA."""
    if not text:
        return NAO_SE_ENCAIXA
    # Strip leading numbering (e.g. "1. Previsão", "2) Passado", "3 - Histórico")
    text = re.sub(r"^\s*\d+[\.\)\-]\s*", "", (text or "").strip()).strip()
    if not text:
        return NAO_SE_ENCAIXA
    if text in valid_names:
        return text
    if NAO_SE_ENCAIXA in text:
        return NAO_SE_ENCAIXA
    text_lower = text.lower()
    for name in valid_names:
        if name in text or name.lower() in text_lower:
            return name
    # Model may output "Alerta" when Previsão description says "Alertas e previsão"
    if "alerta" in text_lower or "previsao" in text_lower:
        for name in valid_names:
            if name.lower() in ("previsão", "previsao"):
                return name
    if "passado" in text_lower:
        for name in valid_names:
            if name.lower() == "passado":
                return name
    if "histórico" in text_lower or "historico" in text_lower:
        for name in valid_names:
            if name.lower() in ("histórico", "historico"):
                return name
    return NAO_SE_ENCAIXA


def _classify_news_batch(
    api_key: str,
    items: list[tuple[str, str]],
    categories: list[tuple[str, str]],
) -> list[str]:
    """
    Classify multiple news items in one (or few) API calls.
    Returns one category name (or NAO_SE_ENCAIXA) per item, in order.
    """
    if not api_key or not categories or not items:
        return [NAO_SE_ENCAIXA] * len(items) if items else []

    valid_names = {name for name, _ in categories}
    categories_text = "\n".join(
        f"- **{name}**: {desc}" if desc else f"- **{name}**"
        for name, desc in categories
    )
    system_instruction = f"""Você é um classificador de notícias. Para cada notícia listada, escolha exatamente UMA categoria.

Categorias disponíveis (use APENAS um destes nomes, exatamente como estão):
{categories_text}

Regras:
- Use a categoria de ALERTAS/PREVISÃO (ex.: Previsão) para: (1) previsão do tempo para os próximos dias; (2) alertas em vigor, avisos meteorológicos atuais, situações de risco no momento; (3) notícias sobre o que está ocorrendo AGORA ou em andamento (ex.: "emite alerta", "entra em alerta", "segue em alerta", "coloca em alerta", "em alerta para", risco atual, fenômeno ocorrendo no presente). Tudo isso é alerta/previsão.
- Use a categoria de eventos PASSADOS (ex.: Passado) apenas para relatos de eventos já concluídos (estragos que já aconteceram, cobertura pós-evento, "atingiu", "deixou rastro", "após a chuva").
- Só use "{NAO_SE_ENCAIXA}" se a notícia não se encaixar em nenhuma categoria listada.

IMPORTANTE: Responda com UMA LINHA por notícia, na mesma ordem (notícia 1 = linha 1, notícia 2 = linha 2). Em cada linha escreva APENAS o nome da categoria ou "{NAO_SE_ENCAIXA}". Nada mais."""

    result_labels: list[str] = []
    for start in range(0, len(items), CLASSIFY_BATCH_SIZE):
        batch = items[start : start + CLASSIFY_BATCH_SIZE]
        batch_content_parts = []
        for i, (title, content) in enumerate(batch, start=1):
            snippet = (content[:800] if content else "(sem conteúdo)")
            batch_content_parts.append(f"NOTÍCIA {i}:\nTítulo: {title}\nConteúdo: {snippet}\n")
        user_content = "\n---\n".join(batch_content_parts)
        user_content += f"\n\nResponda com {len(batch)} linhas (uma categoria por linha, na ordem 1 a {len(batch)}):"

        max_tokens = min(8192, 64 + len(batch) * 32)
        text = ""
        last_error = None
        for attempt in range(3):
            try:
                if HAS_GENAI:
                    client = genai.Client(api_key=api_key)
                    config_kw = {
                        "system_instruction": system_instruction,
                        "temperature": 0.1,
                        "max_output_tokens": max_tokens,
                    }
                    # Gemini 2.5 Flash does not support thinking_config; only 3.x models do
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=user_content,
                        config=genai_types.GenerateContentConfig(**config_kw),
                    )
                    text = (response.text or "").strip()
                else:
                    resp = requests.post(
                        GEMINI_URL,
                        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                        json={
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"parts": [{"text": user_content}]}],
                            "generationConfig": {
                                "temperature": 0.1,
                                "maxOutputTokens": max_tokens,
                            },
                        },
                        timeout=120,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = (
                        (data.get("candidates") or [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    text = (text or "").strip()
                break
            except Exception as e:
                last_error = e
                err_str = str(e).upper()
                status = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "status_code", None)
                if status == 429 or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 50 if attempt < 2 else 0
                    if wait:
                        print(f"Gemini rate limit (429), retrying in {wait}s...")
                        time.sleep(wait)
                else:
                    print(f"Gemini classification error: {e}")
                    text = ""
                    break
        if not text:
            if last_error:
                print(f"Gemini classification error: {last_error}")
            result_labels.extend([NAO_SE_ENCAIXA] * len(batch))
            continue

        # Parse one label per line; normalize and pad if we get fewer lines than items
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i in range(len(batch)):
            label = _normalize_label(lines[i], valid_names) if i < len(lines) else NAO_SE_ENCAIXA
            result_labels.append(label)

    return result_labels


class ClassifyPayload(BaseModel):
    class_group: str


@app.post("/classify")
def run_classification(payload: ClassifyPayload):
    """Run Gemini classification on result.xlsx using the selected group. Adds column 'Classificação'."""
    local_appdata = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")))
    result_path = local_appdata / "Yast" / "result" / "result.xlsx"
    if not result_path.exists():
        return {"status": "error", "message": "Arquivo result.xlsx não encontrado."}

    path = _get_config_path()
    if not path.exists():
        return {"status": "error", "message": "Configuração não encontrada."}
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    api_key = (config.get("gemini_api_key") or "").strip()
    classes_groups = config.get("classes_groups") or {}
    categories = _get_categories_for_group(classes_groups, payload.class_group)
    if not categories:
        return {"status": "error", "message": "Nenhuma classificação encontrada para o grupo selecionado."}

    try:
        df = pd.read_excel(result_path, engine="openpyxl")
    except Exception as e:
        return {"status": "error", "message": f"Erro ao ler planilha: {e}"}

    # Detect title and content columns (Portuguese or English)
    title_col = None
    content_col = None
    for c in df.columns:
        c_lower = str(c).lower()
        if c_lower in ("título", "titulo", "title"):
            title_col = c
        if c_lower in ("conteúdo", "conteudo", "content"):
            content_col = c
    if title_col is None:
        title_col = df.columns[0] if len(df.columns) else None
    if content_col is None:
        content_col = ""

    items = []
    for idx, row in df.iterrows():
        title = str(row.get(title_col, "") or "")
        content = str(row.get(content_col, "") or "") if content_col else ""
        items.append((title, content))
    classifications = _classify_news_batch(api_key, items, categories)

    df["Classificação"] = classifications
    try:
        df.to_excel(result_path, index=False, engine="openpyxl")
    except Exception as e:
        return {"status": "error", "message": f"Erro ao salvar planilha: {e}"}
    return {"status": "ok"}


Busy = False

async def result_cleaner():
    await sleep(2)
    local_appdata = Path(os.environ["LOCALAPPDATA"])
    result_path = local_appdata / Path("Yast/result/result.xlsx")
    if result_path.exists():
        os.remove(str(result_path))


def busySetter(value):
    global Busy
    Busy = value

# Mount static files for assets
assets_path = BASE_DIR / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
# Mount static files for assets
scripts_path = BASE_DIR / "scripts"
if scripts_path.exists():
    app.mount("/scripts", StaticFiles(directory=str(scripts_path)), name="scripts")
# Mount static files for assets
styles_path = BASE_DIR / "styles"
if BASE_DIR.exists():
    app.mount("/styles", StaticFiles(directory=str(styles_path)), name="styles")

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
        local_appdata = Path(os.environ["LOCALAPPDATA"])
        result_path = local_appdata / Path("Yast/result/result.xlsx")
        response = FileResponse(str(result_path), filename="result.xlsx", media_type='application/octet-stream')
        create_task(result_cleaner())
        return response
    
@app.get("/finished")
def get_state():
    local_appdata = Path(os.environ["LOCALAPPDATA"])
    result_dir = local_appdata / Path("Yast/result/")
    if result_dir.exists():
        return "result.xlsx" in os.listdir(str(result_dir))
    return False

@app.get("/busy")
def get_busy():
    global Busy
    
    local_appdata = Path(os.environ["LOCALAPPDATA"])
    result_dir = local_appdata / Path("Yast/result/")
    if result_dir.exists() and "result.xlsx" in os.listdir(str(result_dir)) and Busy:
        Busy = False
    
    return Busy

@app.get("/check-update")
def check_update(test: bool = False):
    """Check if an update is available by comparing local and GitHub versions.
    
    Args:
        test: If True, force return update_available=True for testing
    """
    try:
        if test:
            # Test mode - force update available
            result = check_update_available()
            result['update_available'] = True
            result['test_mode'] = True
            print(f"TEST MODE: Forcing update available")
            return result
        
        result = check_update_available()
        print(f"Version check result: {result}")  # Debug logging
        print(f"Local version: {result.get('local_version')}, Remote version: {result.get('remote_version')}")
        print(f"Update available: {result.get('update_available')}")
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'update_available': False,
            'local_version': None,
            'remote_version': None,
            'error': str(e)
        }

@app.post("/run-installer")
def run_installer():
    """Run YastInstaller.exe to update the application."""
    try:
        # Try multiple possible paths for YastInstaller.exe
        possible_paths = [
            EXE_DIR / "YastInstaller.exe",  # Next to main.exe
            Path.cwd() / "YastInstaller.exe",  # Current working directory
        ]
        
        # If not running as executable, also check relative to script location
        if not getattr(sys, 'frozen', False):
            possible_paths.append(Path(__file__).parent.parent / "YastInstaller.exe")
        
        installer_path = None
        for path in possible_paths:
            if path.exists():
                installer_path = path
                print(f"Found installer at: {installer_path}")
                break
        
        if not installer_path or not installer_path.exists():
            return {
                "status": "fail",
                "message": f"YastInstaller.exe not found. Tried: {[str(p) for p in possible_paths]}"
            }
        
        # Run the installer
        if sys.platform == 'win32':
            # On Windows, use CREATE_NEW_CONSOLE to show installer window
            process = subprocess.Popen(
                [str(installer_path)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(installer_path.parent)
            )
            print(f"Installer started with PID: {process.pid}")
        else:
            # On other platforms, run normally
            process = subprocess.Popen(
                [str(installer_path)],
                cwd=str(installer_path.parent)
            )
            print(f"Installer started with PID: {process.pid}")
        
        return {
            "status": "success",
            "message": "Installer started successfully"
        }
    except Exception as e:
        print(f"ERROR starting installer: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "fail",
            "message": f"Error starting installer: {e}"
        }

script_table = {
    "G1": "g1",
    "nd+": "NDmais",
    "nsc": "NSC",
    "terra": "terra"
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

    # Try multiple possible paths for the scraper executable
    possible_paths = [
        EXE_DIR / "buscadores" / f"{script_table[request.fonte]}.exe",  # Next to main.exe
        Path.cwd() / "buscadores" / f"{script_table[request.fonte]}.exe",  # Current working directory
    ]
    
    # If not running as executable, also check relative to script location
    if not getattr(sys, 'frozen', False):
        possible_paths.append(Path(__file__).parent.parent / "buscadores" / f"{script_table[request.fonte]}.exe")
    
    buscadores_path = None
    for path in possible_paths:
        if path.exists():
            buscadores_path = path
            print(f"Found scraper at: {buscadores_path}")
            break
    
    # Check if executable exists
    if not buscadores_path or not buscadores_path.exists():
        print(f"ERROR: Scraper executable not found. Tried:")
        for path in possible_paths:
            exists = path.exists()
            print(f"  - {path} (exists: {exists})")
        Busy = False
        return {
            "status": "fail",
            "message": f"Scraper executable not found: {script_table[request.fonte]}.exe",
        }
    
    # Split keyword into individual terms if it contains spaces
    keywords = request.keyword.split()
    
    # Build command arguments
    # For g1: [verbose, max_news, ...keywords]
    # For others: [placeholder, max_news, ...keywords]
    if request.fonte == "G1":
        args = ["0", str(int(request.max_news))] + keywords
    else:
        args = ["0", str(int(request.max_news))] + keywords
    
    # Build full command
    full_command = [str(buscadores_path)] + args
    print(f"Starting scraper: {full_command}")
    
    # Use subprocess to run in a new console window
    try:
        if sys.platform == 'win32':
            # On Windows, use CREATE_NEW_CONSOLE to show output in separate window
            process = subprocess.Popen(
                full_command,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(buscadores_path.parent)
            )
            print(f"Scraper started with PID: {process.pid}")
        else:
            # On other platforms, run normally
            process = subprocess.Popen(
                full_command,
                cwd=str(buscadores_path.parent)
            )
            print(f"Scraper started with PID: {process.pid}")
    except FileNotFoundError as e:
        print(f"ERROR: Executable not found: {e}")
        print(f"Looking for: {buscadores_path}")
        Busy = False
        return {
            "status": "fail",
            "message": f"Could not find scraper executable: {e}",
        }
    except Exception as e:
        print(f"ERROR starting scraper: {e}")
        import traceback
        traceback.print_exc()
        Busy = False
        return {
            "status": "fail",
            "message": f"Error starting scraper: {e}",
        }

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

    