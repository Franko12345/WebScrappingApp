import os
import sys
import time
from contextlib import contextmanager

try:
    from PyInstaller.__main__ import run as pyinstaller_run
except Exception as e:
    pyinstaller_run = None
    # se for importado numa máquina sem PyInstaller, vamos avisar ao usuário quando rodar

@contextmanager
def set_env_var(key: str, value: str | None):
    """Context manager para setar temporariamente uma variável de ambiente."""
    old = os.environ.get(key)
    if value is None:
        if key in os.environ:
            del os.environ[key]
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old

def get_output_executable(script_path: str, dist_path: str) -> str:
    """Estimativa do arquivo de saída produzido pelo --onefile.
    Usa o nome base do script sem .py e adiciona extensão .exe no Windows.
    """
    base = os.path.splitext(os.path.basename(script_path))[0]
    ext = ".exe" if sys.platform.startswith("win") else ""
    # se dist_path for ".", transforma em path absoluto relativo ao cwd
    return os.path.join(dist_path, base + ext)

def build_if_newer(
    script_path: str,
    dist_path: str,
    work_path: str,
    icon: str,
    windowed: bool = False,
    optimize: int = 2,
    extra_args: list[str] | None = None,
    datas: list[tuple[str, str]] | None = None,
):
    if pyinstaller_run is None:
        raise RuntimeError("PyInstaller não está disponível neste ambiente. Instale com: pip install pyinstaller")

    script_path = os.path.normpath(script_path)
    dist_path = os.path.normpath(dist_path)
    work_path = os.path.normpath(work_path)

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script não encontrado: {script_path}")

    script_mod_time = os.path.getmtime(script_path)
    output_file = get_output_executable(script_path, dist_path)

    if os.path.exists(output_file):
        output_mod_time = os.path.getmtime(output_file)
    else:
        output_mod_time = 0  # força build se não existe

    if script_mod_time <= output_mod_time:
        print(f"[OK] {script_path} está atualizado (saida: {output_file}).")
        return

    # garante que a pasta de dist exista (PyInstaller normalmente cria)
    os.makedirs(dist_path, exist_ok=True)
    os.makedirs(work_path, exist_ok=True)

    args = [
        "--onefile",
        f"--distpath={dist_path}",
        f"--workpath={work_path}",
        "--noconfirm",  # sobrescrever sem pedir confirmação
        f"--icon={icon}"
    ]
    if windowed:
        args.append("--windowed")
    # Add data files (assets, HTML, etc.)
    if datas:
        # On Windows, use semicolon; on Unix, use colon
        separator = ";" if sys.platform.startswith("win") else ":"
        for source, dest in datas:
            args.append(f"--add-data={source}{separator}{dest}")
    if extra_args:
        args.extend(extra_args)

    # adiciona script no final
    args.append(script_path)

    print(f"[BUILD] Compilando {script_path} -> {output_file}")
    # setamos a variável de ambiente PYTHONOPTIMIZE temporariamente
    with set_env_var("PYTHONOPTIMIZE", str(optimize)):
        # PyInstaller escreve logs na saída padrão; chamamos a API diretamente.
        try:
            pyinstaller_run(args)
        except SystemExit as se:
            # PyInstaller às vezes chama sys.exit; capturamos para poder continuar.
            if getattr(se, "code", 0) != 0:
                raise
        except Exception:
            print("Erro ao executar PyInstaller (detalhes abaixo).")
            raise

    # espera um pequeno intervalo para garantir que o arquivo tenha sido escrito e timestamp atualizado
    time.sleep(0.1)

    if os.path.exists(output_file):
        print(f"[SUCESSO] Gerado: {output_file}")
    else:
        print(f"[ERRO] PyInstaller não gerou o arquivo esperado em: {output_file}")

if __name__ == "__main__":
    relative_path = "./brave/brave.exe"
    absolute_path = os.path.abspath(relative_path)

    print(absolute_path)  # e.g., C:\Users\Davi\project\brave\brave.exe

    # Set environment variable permanently (user-level)
    os.system(f'setx BRAVE_PATH "{absolute_path}"')

    relative_path = "./chromedriver/chromedriver-win64/chromedriver.exe"
    absolute_path = os.path.abspath(relative_path)

    print(absolute_path)  # e.g., C:\Users\Davi\project\brave\brave.exe

    # Set environment variable permanently (user-level)
    os.system(f'setx CHROMEDRIVER_PATH "{absolute_path}"')
    
    # Lista de builds baseada nos comandos que você forneceu
    builds = [
        {
            "script": "./src/main.py",
            "dist": "./",
            "work": "./build",
            "windowed": True,
            "extra": None,
            "icon": "./assets/app_ico.ico",
            "datas": [
                ("assets", "assets"),
                ("main.html", "."),
                ("style.css", "."),
                ("scripts", "scripts"),
            ]
        },
        {
            "script": "./src/NSC.py",
            "dist": "./buscadores",
            "work": "./build",
            "windowed": False,
            "extra": None,
            "binaries": [("./brave/brave.exe", ".")],
            "icon": "./assets/buscador.ico"
        },
        {
            "script": "./src/NDmais.py",
            "dist": "./buscadores",
            "work": "./build",
            "windowed": False,
            "extra": None,
            "icon": "./assets/buscador.ico"
        },
        {
            "script": "./src/g1.py",
            "dist": "./buscadores",
            "work": "./build",
            "windowed": False,
            "extra": None,
            "icon": "./assets/buscador.ico"
        },
    ]

    # executa cada build
    for b in builds:
        try:
            build_if_newer(
                script_path=b["script"],
                dist_path=b["dist"],
                work_path=b["work"],
                windowed=b["windowed"],
                optimize=2,
                extra_args=b.get("extra"),
                icon=b["icon"],
                datas=b.get("datas"),
            )
        except Exception as e:
            print(f"[ERRO] Falha ao construir {b['script']}: {e}")
