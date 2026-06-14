import json
import os

# Lista plików JSON, które chcesz wbudować w aplikację
pliki = ['1.json', '2.json', '3.json', '4.json', '5.json']

out = "const EXAMPLES = {\n"

for plik in pliki:
    if os.path.exists(plik):
        with open(plik, 'r', encoding='utf-8') as f:
            tresc = f.read()
            numer = plik.replace('.json', '')
            out += f"    {numer}: {tresc},\n"
    else:
        print(f"Pominięto {plik} - plik nie istnieje.")

out += "};\n"

os.makedirs('web', exist_ok=True)
with open('web/examples.js', 'w', encoding='utf-8') as f:
    f.write(out)

print("Gotowe! Zaktualizowano web/examples.js")
