# CLAUDE.md

Wskazówki dla Claude Code przy pracy w tym repozytorium.

## O projekcie

**D-Algorytm** – narzędzie edukacyjne (część pracy magisterskiej) do rysowania układów kombinacyjnych i generowania wektorów testowych (ATPG) klasycznym D-Algorytmem dla pojedynczych usterek *stuck-at* (s-a-0 / s-a-1). Wynik to tabela krok po kroku (pobudzenie → propagacja → badanie zgodności) z komentarzami oraz lista punktów decyzyjnych, w których użytkownik może wybrać alternatywną ścieżkę.

Język projektu: **polski** (UI, komunikaty silnika, komentarze w kodzie, README).

## Stos i uruchamianie

- Python 3.14 + [Eel](https://github.com/python-eel/Eel) (most WebSocket Python ↔ przeglądarka). Frontend: czysty HTML/CSS/JS + SVG, bez frameworków i bez bundlera.
- Środowisko: `.venv` w katalogu projektu; `requirements.txt` – runtime (Eel), `requirements-dev.txt` – dodatkowo Nuitka i pytest. Python wołać jako `.venv/Scripts/python`.
- Uruchomienie: `python main.py` – otwiera okno Chrome / Edge (fallback: domyślna przeglądarka), port losowy (`port=0`).
- Testy: `python -m pytest` (konfiguracja w `pyproject.toml`, ~170 testów, kilka sekund).
- Build: `python build.py` → regeneracja `web/examples.js`, testy, Nuitka → `dist/D-Algorytm.exe`. Flagi Nuitki opisane w `build.py`.
- CI (`.github/workflows/ci.yml`): pytest przy każdym pushu na `main` i pull requeście.
- Podgląd samego frontendu bez backendu: konfiguracja `web-static` w `.claude/launch.json` (serwer statyczny na `web/`; `eel` wtedy nie istnieje).

## Struktura

| Plik | Rola |
|---|---|
| `main.py` | Punkt wejścia: globalny `excepthook` (MessageBox Windows przez `ctypes` – działa tylko na Windows), `eel.init('web')`, eksponuje `run_d_algorithm(components, target_node, fault_type, user_choices)`, wybór przeglądarki. |
| `build.py` | Budowanie `.exe` (Nuitka). |
| `tests/` | pytest. `conftest.py` zawiera helper `circuit(...)`, niezależny symulator (`simulate`, `detects`) i `explore` (przejście całego drzewa decyzji). `test_examples.py` weryfikuje każdy wygenerowany test na przykładach symulacją z usterką. |
| `engine.py` | Klasa `DAlgorithmEngine` – cała logika algorytmu. Bez zależności zewnętrznych, można ją testować w izolacji. |
| `web/index.html` | Cały frontend w jednym pliku (CSS + JS inline, ~940 linii): edytor schematów, zoom/pan, kable z załamaniami, tabela wyników, panel alternatywnych decyzji, autosave do `localStorage` (`d_algo_save`). |
| `web/examples.js` | **Generowany** – `const EXAMPLES = {...}`. Nie edytować ręcznie. |
| `buduj_przyklady.py` | Generuje `web/examples.js` ze wszystkich plików `[NUMER].json` w katalogu głównym. Przyciski w menu „Plik” tworzą się w JS z kluczy `EXAMPLES`. Test pilnuje, by `examples.js` był aktualny. |
| `1.json`, `2.json`, `4.json`, `5.json` | Przykładowe układy (format zapisu z UI). |

## Model danych (kontrakt JS ↔ Python)

Układ to słownik `comps` (`id → komponent`):

```json
{ "id": "G3", "type": "AND", "x": 120, "y": 80,
  "inputs": ["X1", "W2"], "waypoints": [[{"x":..,"y":..}], []] }
```

- Typy: `IN` (wejście pierwotne, prefiks `X`), `NODE` (węzeł/rozgałęzienie, prefiks `W`, 1 wejście), bramki `AND OR NAND NOR XOR XNOR` (2 wejścia) i `NOT` (1 wejście), prefiks `G`. Bramki są **maksymalnie dwuwejściowe** – silnik zakłada piny `0` i `1`.
- `inputs[i]` to `id` komponentu źródłowego lub `null`. Nie ma jawnych wyjść pierwotnych – kierunek propagacji wynika z tego, kto kogo zasila.
- Plik zapisu: `{ components, counter, target, fault_type }` (+ `choices` w `localStorage`).
- Wartości sygnałów w silniku: `'0'`, `'1'`, `'x'`, `'D'`, `'~D'`; w `delta` może pojawić się `'ERR'` (UI rysuje ❌).
- Wynik `run()`: `{ cols, steps: [{ s, delta, msg, full }], decision_log: [{ id, title, options: [{label, data}], selected }] }`. `full=True` → wiersz pokazuje cały stan, inaczej tylko `delta`.

## Jak działa silnik (`engine.py`)

1. **Pobudzenie** – na `target_node` wpisywane `D` (sa0) lub `~D` (sa1); wejścia bramki dobierane z `get_justifications` tak, by wyjście bezbłędnie wynosiło `1`/`0`.
2. **Propagacja** – pętla po bramkach zasilanych z bieżącego węzła (`NODE` są przechodzone rekurencyjnie); dla drugiego wejścia szukana wartość nie-kontrolująca; blokada → wiersz „SPRZECZNOŚĆ”.
3. **Badanie zgodności (justification)** – wsteczne przejście po `cols` (od końca) aż do ustalenia wartości; brak spójnej kombinacji → „SPRZECZNOŚĆ”.

Ważne szczegóły:
- **Nawracanie nie jest automatyczne.** Każde rozgałęzienie z >1 opcją trafia do `decision_log` z kluczem (`excite_*`, `branch_*`, `prop_*`, `just_*`); wybór pochodzi z `user_choices` (domyślnie 0). Zmiana w UI → ponowne wywołanie silnika z nowymi wyborami.
- `resolve_name` przechodzi przez łańcuch `NODE` do fizycznego źródła; `assign_state` propaguje wartość w górę i w dół przez węzły i zwraca `True` przy konflikcie.
- Kolejność kolumn: `IN` → bramki → `NODE`, w obrębie grupy wg cyfr w nazwie (`sort_key`) – nazwy bez cyfr dostają 0.
- Komunikaty kroków są po polsku i trafiają bezpośrednio do tabeli w UI (renderowane jako HTML).

## Konwencje

- **Priorytetem jest czystość kodu i przejrzystość repozytorium.** Wybieraj najprostsze rozwiązanie; nie dodawaj narzędzi, automatyzacji ani warstw, które nie są niezbędne (np. świadomie zrezygnowano z wersjonowania i automatycznych release'ów).
- Styl kodu zwarty (wiele instrukcji w jednej linii, krótkie nazwy zmiennych) – zachowywać spójność z otoczeniem.
- Zmiany w strukturze komponentu muszą być zgodne po obu stronach (`index.html`: `add`, `restoreComponents`, `saveWorkspace`, `autoSave`; `engine.py`) oraz ze starymi plikami JSON/`localStorage`.
- Po zmianie przykładów JSON uruchomić `python buduj_przyklady.py`.
- Po zmianach w `engine.py` uruchomić `python -m pytest`. `test_examples.py` wymaga, by każdy wektor kończący się wierszem „TEST” faktycznie wykrywał usterkę i by każda testowalna usterka miała co najmniej jedną ścieżkę decyzji prowadzącą do testu.
- Komunikaty skryptów wypisywane po polsku – `sys.stdout.reconfigure(encoding='utf-8')` jest potrzebne w konsoli Windows (cp1252).
- Commity: Conventional Commits po angielsku (`feat:`, `fix:`, `chore:`, `refactor:`…).
