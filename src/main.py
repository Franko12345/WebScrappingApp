import os
import sys
import subprocess
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

    