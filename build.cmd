set PYTHONOPTIMIZE=2 && pyinstaller --windowed --onefile --distpath=./ --workpath=./build ./src/main.py
set PYTHONOPTIMIZE=2 && pyinstaller --onefile --distpath=./buscadores --workpath=./build ./src/NSC.py
set PYTHONOPTIMIZE=2 && pyinstaller --onefile --distpath=./buscadores --workpath=./build ./src/NDmais.py
set PYTHONOPTIMIZE=2 && pyinstaller --onefile --distpath=./buscadores --workpath=./build ./src/g1.py