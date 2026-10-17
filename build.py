# build.py
# Budowanie aplikacji DIANA do jednego pliku .exe (Nuitka).
#
#   python build.py                -> przykłady + testy + kompilacja do dist/DIANA.exe
#   python build.py --skip-tests   -> jak wyżej, bez uruchamiania testów
import argparse
import os
import shutil
import subprocess
import sys

import buduj_przyklady

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, 'build')
DIST_DIR = os.path.join(BASE_DIR, 'dist')
EXE_NAME = 'DIANA.exe'


def run(cmd):
    print('>', ' '.join(cmd), flush=True)
    if subprocess.call(cmd, cwd=BASE_DIR) != 0:
        sys.exit("Polecenie zakończyło się błędem - przerwano budowanie.")


def build(skip_tests=False):
    print("[1/3] Generowanie web/examples.js")
    buduj_przyklady.buduj()

    if skip_tests:
        print("[2/3] Testy pominięte (--skip-tests)")
    else:
        print("[2/3] Testy")
        run([sys.executable, '-m', 'pytest', '-q'])

    print("[3/3] Kompilacja (Nuitka)")
    run([
        sys.executable, '-m', 'nuitka',
        '--onefile',
        '--assume-yes-for-downloads',                 # bez pytań o pobranie kompilatora / Dependency Walker
        '--windows-console-mode=disable',             # bez okna konsoli; błędy pokazuje excepthook z main.py
        '--include-data-dir=web=web',                 # cały interfejs webowy wewnątrz .exe
        '--include-module=bottle_websocket',          # moduły sieciowe Eel, które Nuitka potrafi pominąć
        '--include-module=geventwebsocket',
        f'--output-dir={BUILD_DIR}',                  # pliki pośrednie; bez --remove-output, bo antywirus potrafi
        f'--output-filename={EXE_NAME}',              # zablokować ich usuwanie i Nuitka przerywa wtedy build
        'main.py',
    ])
    os.makedirs(DIST_DIR, exist_ok=True)
    shutil.copy2(os.path.join(BUILD_DIR, EXE_NAME), os.path.join(DIST_DIR, EXE_NAME))
    shutil.rmtree(BUILD_DIR, ignore_errors=True)    # co zablokowane, zostanie (build/ jest w .gitignore)
    print(f"Gotowe: {os.path.join(DIST_DIR, EXE_NAME)}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # polskie znaki w konsoli Windows (cp1252)
    parser = argparse.ArgumentParser(description="Budowanie DIANA do pliku .exe")
    parser.add_argument('--skip-tests', action='store_true', help="nie uruchamiaj testów przed kompilacją")
    build(parser.parse_args().skip_tests)
