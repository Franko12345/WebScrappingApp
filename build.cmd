pyinstaller --windowed --onefile main.py
pyinstaller --windowed --onefile NSC.py
pyinstaller --windowed --onefile NDmais.py
move ./dist/NDmais/NDmais.exe ./
move ./dist/NSC/NSC.exe ./
move ./dist/main.exe ./