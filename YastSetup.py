import os
import sys
import shutil
import subprocess
import ctypes
import urllib.request
from pathlib import Path
import pythoncom
import win32com.client
from win32com.shell import shell, shellcon
import zipfile
import urllib.request

REPO_URL = "https://github.com/Franko12345/WebScrappingApp.git"
INSTALL_DIR = Path(os.environ["ProgramFiles"]) / "Yast"
GIT_INSTALLER_URL = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe"
GIT_INSTALLER_PATH = Path(os.environ["TEMP"]) / "git-installer.exe"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe"
PYTHON_INSTALLER_PATH = Path(os.environ["TEMP"]) / "python-installer.exe"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    print("🔒 Requesting admin privileges...")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def get_special_folder(folder_id):
    """Retorna o caminho da pasta especial (Desktop, Start Menu, etc) independente do idioma."""
    return Path(shell.SHGetFolderPath(0, folder_id, None, 0))
DESKTOP = get_special_folder(shellcon.CSIDL_DESKTOPDIRECTORY)
START_MENU = get_special_folder(shellcon.CSIDL_PROGRAMS) / "Yast"
def ensure_git():
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        print("✅ Git is already installed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Git not found. Downloading Git for Windows...")

        urllib.request.urlretrieve(GIT_INSTALLER_URL, GIT_INSTALLER_PATH)
        print(f"⬇️ Downloaded Git installer to {GIT_INSTALLER_PATH}")

        print("⚙️ Installing Git silently...")
        subprocess.run([str(GIT_INSTALLER_PATH), "/VERYSILENT", "/NORESTART"], check=True)

        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            print("✅ Git installed successfully.")
            return True
        except Exception as e:
            print(f"❌ Failed to verify Git installation: {e}")
            return False

def ensure_python():
    try:
        result = subprocess.run(
            ["python", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Python found: {result.stdout.strip()}")
        return True
    except Exception:
        print("❌ Python not found. Downloading installer...")

        urllib.request.urlretrieve(PYTHON_INSTALLER_URL, PYTHON_INSTALLER_PATH)
        print(f"⬇️ Downloaded Python installer to {PYTHON_INSTALLER_PATH}")

        print("⚙️ Installing Python silently...")
        try:
            subprocess.run([
                str(PYTHON_INSTALLER_PATH),
                "/quiet",
                "InstallAllUsers=1",
                "PrependPath=1",
                "Include_test=0"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Python installation failed: {e}")
            return False

        # Re-check installation
        try:
            result = subprocess.run(
                ["python", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ Python installed successfully: {result.stdout.strip()}")
            return True
        except Exception:
            print("❌ Python installation completed but not detected in PATH.")
            return False

def install_requirements():
    req_file = INSTALL_DIR / "requirements.txt"
    if req_file.exists():
        print("📦 Installing Python packages from requirements.txt...")
        try:
            subprocess.run(
                ["python", "-m", "pip", "install", "-r", str(req_file)],
                check=True
            )
            print("✅ All requirements installed.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install requirements: {e}")
            input("👉 Press any key to exit...")
            sys.exit(1)
    else:
        print("⚠️ No requirements.txt found. Skipping package installation.")

BRAVE_DIR = INSTALL_DIR / "brave"
BRAVE_ZIP_URL = "https://github.com/brave/brave-browser/releases/download/v1.76.82/brave-v1.76.82-win32-x64.zip"
BRAVE_ZIP_PATH = BRAVE_DIR / "brave.zip"

def download_and_extract_brave():
    if BRAVE_DIR.exists():
        print(f"✅ Brave already installed at {BRAVE_DIR}")
        return
    
    brave_folder = Path(BRAVE_DIR)
    brave_folder.mkdir(parents=True, exist_ok=True)

    print("⬇️ Downloading Brave browser...")
    urllib.request.urlretrieve(BRAVE_ZIP_URL, BRAVE_ZIP_PATH)
    print(f"📥 Downloaded to {BRAVE_ZIP_PATH}")

    print("⚙️ Extracting Brave...")
    with zipfile.ZipFile(BRAVE_ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(BRAVE_DIR)

    # Remove the zip
    BRAVE_ZIP_PATH.unlink()

    # The zip may extract a folder with version name, rename it to 'brave'
    # Find first folder that starts with "brave"
    extracted_folders = [f for f in INSTALL_DIR.iterdir() if f.is_dir() and f.name.lower().startswith("brave")]
    if extracted_folders:
        extracted_folder = extracted_folders[0]
        extracted_folder.rename(BRAVE_DIR)
        print(f"✅ Brave installed at {BRAVE_DIR}")
    else:
        print("❌ Could not find extracted Brave folder")

def clone_repo():
    if INSTALL_DIR.exists():
        print("♻️ Removing old installation...")

        # Try normal removal first
        try:
            shutil.rmtree(INSTALL_DIR)
        except Exception as e:
            print(f"⚠️ Python removal failed: {e}, trying system removal...")
            # Force remove via Windows command
            subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(INSTALL_DIR)], shell=True)

    if INSTALL_DIR.exists():
        print("❌ Could not remove old installation, aborting.")
        sys.exit(1)

    os.makedirs(INSTALL_DIR.parent, exist_ok=True)
    print("⬇️ Cloning repo...")
    subprocess.run(["git", "clone", REPO_URL, str(INSTALL_DIR)], check=True)


def create_shortcut(shortcut_path, exe_path):
    try:
        pythoncom.CoInitialize()  # inicializa o COM
        shell_obj = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell_obj.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(exe_path)
        shortcut.WorkingDirectory = str(exe_path.parent)
        shortcut.IconLocation = str(exe_path)
        shortcut.save()
        print(f"✅ Atalho criado em {shortcut_path}")
    except Exception as e:
        print(f"⚠️ Falha ao criar atalho: {e}")


def main():
    if not is_admin():
        run_as_admin()

    if not ensure_git():
        sys.exit(1)

    if not ensure_python():
        sys.exit(1)

    clone_repo()
    install_requirements()

    download_and_extract_brave()

    brave_path = INSTALL_DIR / "brave/brave.exe"

    print(brave_path) 

    # Set environment variable permanently (user-level)
    os.system(f'setx BRAVE_PATH "{brave_path}"')

    driver_path = INSTALL_DIR / "chromedriver/chromedriver-win64/chromedriver.exe"

    print(driver_path)

    # Set environment variable permanently (user-level)
    os.system(f'setx CHROMEDRIVER_PATH "{driver_path}"')

    exe_path = INSTALL_DIR / "main.exe"
    if not exe_path.exists():
        print("❌ main.exe not found in repository!")
        input("👉 Press any key to exit...")
        sys.exit(1)

    choice = input("📌 Do you want to create a Desktop shortcut? (y/n): ").strip().lower()
    if choice == "y":
        create_shortcut(DESKTOP / "Yast.lnk", exe_path)

    START_MENU.mkdir(parents=True, exist_ok=True)
    create_shortcut(START_MENU / "Yast.lnk", exe_path)

    print("\n🎉 Installation complete.")
    input("👉 Press any key to finish...")




if __name__ == "__main__":
    main()
