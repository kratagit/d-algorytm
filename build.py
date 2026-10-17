# build.py
# Budowanie aplikacji DIANA do jednego pliku .exe (PyInstaller).
#
#   python build.py                -> przykłady + testy + dist/DIANA.exe
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

    print("[3/3] Budowanie .exe (PyInstaller)")
    run([
        sys.executable, '-m', 'PyInstaller',
        '--onefile', '--name', 'DIANA',
        '--noconsole',                                                  # błędy pokazuje excepthook z main.py
        '--add-data', os.path.join(BASE_DIR, 'web') + os.pathsep + 'web',  # cały interfejs webowy wewnątrz .exe
        '--distpath', DIST_DIR, '--workpath', BUILD_DIR, '--specpath', BUILD_DIR,
        '--noconfirm', '--clean',
        'main.py',
    ])
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    print(f"Gotowe: {os.path.join(DIST_DIR, 'DIANA.exe')}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # polskie znaki w konsoli Windows (cp1252)
    parser = argparse.ArgumentParser(description="Budowanie DIANA do pliku .exe")
    parser.add_argument('--skip-tests', action='store_true', help="nie uruchamiaj testów przed budowaniem")
    build(parser.parse_args().skip_tests)
