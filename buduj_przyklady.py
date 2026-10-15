import json
import os
import re
import sys

# Wbudowuje przykładowe układy ([NUMER].json z katalogu głównego) w web/examples.js
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE_DIR, 'web', 'examples.js')


def znajdz_przyklady(katalog=BASE_DIR):
    pliki = [p for p in os.listdir(katalog) if re.fullmatch(r'\d+\.json', p)]
    return sorted(pliki, key=lambda p: int(p[:-5]))


def generuj_examples_js(katalog=BASE_DIR):
    out = "const EXAMPLES = {\n"
    for plik in znajdz_przyklady(katalog):
        with open(os.path.join(katalog, plik), 'r', encoding='utf-8') as f:
            tresc = f.read()
        json.loads(tresc)  # walidacja - przerwij, jeśli plik jest uszkodzony
        out += f"    {plik[:-5]}: {tresc.strip()},\n"
    out += "};\n"
    return out


def buduj(katalog=BASE_DIR, out_file=OUT_FILE):
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(generuj_examples_js(katalog))
    return znajdz_przyklady(katalog)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    pliki = buduj()
    print(f"Gotowe! Zaktualizowano web/examples.js ({', '.join(pliki)})")
