# CLAUDE.md

Wskazówki dla Claude Code przy pracy w tym repozytorium.

## O projekcie

**DIANA** (*DIagnostyka i ANAliza układów cyfrowych*) – narzędzie edukacyjne (część pracy magisterskiej) do rysowania układów kombinacyjnych i generowania wektorów testowych (ATPG) klasycznym D-Algorytmem dla pojedynczych usterek *stuck-at* (s-a-0 / s-a-1). Wynik to tabela krok po kroku (pobudzenie → propagacja → badanie zgodności) z komentarzami oraz lista punktów decyzyjnych, w których użytkownik może wybrać alternatywną ścieżkę.

Nazwa aplikacji to **DIANA**; „D-Algorytm” oznacza wyłącznie sam algorytm (np. `DAlgorithmEngine`). Repozytorium na GitHubie: `kratagit/diana` (lokalny katalog nadal nazywa się `d-algorytm`).

Kierunek rozwoju (temat pracy): drugi silnik **PODEM** z heurystykami SCOAP – koszty sterowalności `c0`, `c1` i obserwowalności `O` każdej linii – oraz porównanie wydajności D-Algorytmu i PODEM (np. liczba nawrotów w drzewie przeszukiwań) na topologiach ze ścieżkami zbieżnymi i redundancją; do tego zestaw ćwiczeń laboratoryjnych. **Obecnie zajmujemy się wyłącznie D-algorytmem** – PODEM i miary sterowalności/obserwowalności dopiero później.

Język projektu: **polski** (UI, komunikaty silnika, komentarze w kodzie, README).

## Stos i uruchamianie

- Python 3.14 + [Eel](https://github.com/python-eel/Eel) (most WebSocket Python ↔ przeglądarka). Frontend: czysty HTML/CSS/JS + SVG, bez frameworków i bez bundlera.
- Środowisko: `.venv` w katalogu projektu; `requirements.txt` – runtime (Eel), `requirements-dev.txt` – dodatkowo PyInstaller i pytest. Python wołać jako `.venv/Scripts/python`.
- Uruchomienie: `python main.py` – otwiera okno Chrome / Edge (fallback: domyślna przeglądarka), port losowy (`port=0`).
- Testy: `python -m pytest` (konfiguracja w `pyproject.toml`, ~600 testów, ok. 20 s).
- Build: `python build.py` → regeneracja `web/examples.js`, testy, PyInstaller (`--onefile`, ok. 1 min) → `dist/DIANA.exe`. PyInstaller jest tymczasowy – docelowo Electron.
- CI (`.github/workflows/`): `ci.yml` – pytest przy każdym pushu na `main` i pull requeście; `release.yml` – merge PR na `main` z etykietą `patch`/`minor`/`major` → testy, build na `windows-latest` i GitHub Release `vX.Y.Z` z plikiem `diana-X.Y.Z-windows-x64.exe`. Wersja istnieje **tylko jako tag** (ostatni tag podbity wg etykiety, start `v1.0.0`) – w kodzie nie ma pliku z wersją; nie tworzyć tagów ręcznie. PR bez etykiety nie tworzy wydania.
- Podgląd samego frontendu bez backendu: konfiguracja `web-static` w `.claude/launch.json` (serwer statyczny na `web/`; `eel` wtedy nie istnieje).

## Struktura

| Plik | Rola |
|---|---|
| `main.py` | Punkt wejścia: globalny `excepthook` (MessageBox Windows przez `ctypes` – działa tylko na Windows), `eel.init('web')`, eksponuje `run_d_algorithm(components, target_node, fault_type, user_choices)`, wybór przeglądarki. |
| `build.py` | Budowanie `.exe` (PyInstaller). |
| `tests/` | pytest – opis niżej w „Testy”. |
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

- Typy: `IN` (wejście pierwotne, prefiks `X`), `NODE` (węzeł/rozgałęzienie, prefiks `W`, 1 wejście), bramki `AND OR NAND NOR XOR XNOR` (2 wejścia) i `NOT` (1 wejście), prefiks `G`. Interfejs tworzy bramki 2-wejściowe; silnik obsługuje dowolną liczbę wejść (`inputs` o długości n).
- `inputs[i]` to `id` komponentu źródłowego lub `null`. Nie ma jawnych wyjść pierwotnych – kierunek propagacji wynika z tego, kto kogo zasila.
- Plik zapisu: `{ components, counter, target, fault_type }` (+ `choices` w `localStorage`).
- Wartości sygnałów w silniku: `'0'`, `'1'`, `'x'`, `'D'` (zdatny 1 / błędny 0), `'~D'` (zdatny 0 / błędny 1); w `delta` może pojawić się `'ERR'` (UI rysuje ❌).
- Wynik `run()`: `{ cols, steps: [{ s, delta, msg, full }], decision_log: [{ id, title, options: [{label, data}], selected }] }`. `full=True` → wiersz pokazuje cały stan, inaczej tylko `delta`.

## Jak działa silnik (`engine.py`)

Tabela ma być **prosta dla studenta**: każdy wiersz to jeden krok metody (pobudzenie, propagacja przez bramkę, badanie zgodności) i pokazuje wartości ustalone w tym kroku – bez żadnych dodatkowych „implikacji” ani dopisków. Przykłady z materiałów nie muszą być odtwarzane 1:1 (str. 41 ma 3-wejściowy OR, którego interfejs nie ma). Wartości nigdy się nie zmieniają (tylko `x` → wartość). Zgodność sprawdzana jest w D-algebrze (`d_eval`: para układ zdatny / z usterką, `x` = dowolna z 0, 1, D, ~D).

1. **Pobudzenie** – na `target_node` wpisywane `D` (sa0) lub `~D` (sa1); wejścia bramki z `requirement_options` (pierwotne D-sześciany, Tabela 3).
2. **Propagacja** – dopóki błąd nie dotrze do wyjścia, użytkownik wybiera bramkę z D-granicy (bramki z D/~D na wejściu i nieustalonym wyjściem): decyzja `branch_<bramki>` „Propagacja błędu. Wybierz drogę:”, opcje „Przez G3 (NOR)”. Najpierw (domyślnie) bramki zasilane przez ostatnią bramkę, przez którą przeszedł błąd, potem pozostałe wg numerów. Pozostałe wejścia dostają wartość nie-kontrolującą (AND/NAND 1, OR/NOR 0, XOR/XNOR wybór `prop_<bramka>`), wyjście z D-algebry; wejście z D z innej gałęzi zostaje (D AND D = D). Kilka ścieżek naraz (str. 42) = wybieranie kolejnych bramek z D-granicy przed dojściem do wyjścia. Wyjście bez D → „SPRZECZNOŚĆ (Blokada propagacji)”, pusta D-granica → „SPRZECZNOŚĆ … pusta D-granica”. Każda bramka ma wiersz „Propagacja błędu przez …” z wartościami jej pozostałych wejść, a zaraz po pobudzeniu `insert_path_row` wstawia wiersz „Wybór ścieżki propagacji (…)” z wybranymi bramkami po kolei (przy blokadzie także z bramką, na której błąd utknął).
3. **Badanie zgodności** – od wyjść w głąb (DFS po wejściach), potem pozostałe ustalone linie. Wiersz dla każdej bramki z ustaloną wartością 0/1 (także takiej, której wartość już wynika z wejść) oraz dla linii z D/~D, której wartość nie wynika z wejść; wiersz pokazuje wszystkie wejścia bramki, a „Wymagane:” – wejścia, od których zależy wartość (`needed_inputs`). Opcje z `requirement_options` (dla 0/1 = pierwotne sześciany, Tabela 5; linia w zasięgu błędu może dostać D/~D, np. XOR(D, ~D) = 1). Brak opcji → „SPRZECZNOŚĆ … Funkcja logiczna bramki wyklucza taki wynik”.

Ważne szczegóły:
- **Nawracanie wybiera użytkownik.** Każdy wybór z >1 opcją trafia do `decision_log` (`excite_*`, `branch_*`, `prop_*`, `just_*`); wybór pochodzi z `user_choices` (domyślnie 0). Po sprzeczności próba się kończy (bez wiersza podsumowania).
- `resolve_name` przechodzi przez łańcuch `NODE` do źródła – wymaganie na węźle dotyczy źródła; dwa wejścia z tej samej linii dostają tę samą wartość. `assign_state` propaguje wartość w górę i w dół przez węzły.
- `prepare()` ustala kolumny, kolejność topologiczną bramek (`gates`), odbiorców linii (`consumers`), wyjścia (linie, których nic nie czyta) i zasięg błędu (`cone`).
- Kolejność kolumn: `IN` → bramki → `NODE`, w obrębie grupy wg cyfr w nazwie (`sort_key`) – nazwy bez cyfr dostają 0.
- Komunikaty kroków są po polsku i trafiają bezpośrednio do tabeli w UI (renderowane jako HTML).

## Testy

- `tests/oracle.py` – **niezależna wyrocznia** (nie importuje silnika): symulacja 0/1 i w D-algebrze dla bramek o dowolnej liczbie wejść, `Oracle` (wszystkie wektory wejściowe z wartościami linii dla jednej usterki; `realizable(stan)` mówi, czy przypisania z tabeli da się zrealizować).
- `tests/helpers.py` – uruchamianie silnika, `explore` (przejście całego drzewa decyzji; przekroczenie limitu przebiegów to błąd testu, a nie ciche pominięcie), `check_run`/`check_fault` (zasady poprawnej tabeli z kategoriami naruszeń: `struktura`, `test`, `sprzecznosc`, `kompletnosc`, `opcje`).
- `test_examples.py` – przykłady aplikacji, układy z zajęć (`tests/fixtures/tester/*.json`, z `konwertuj_gat.py`) i układ ze str. 41 w wersji 2-wejściowej; pilnuje też, by klucz odpowiedzi w `tests/fixtures/do-sprawdzenia/README.md` zgadzał się z wyrocznią. `test_materials.py` – tabele 2–5 i przykłady z `Materiały.pdf` (`tests/fixtures/materialy/uklad-g1-g9.json` – układ ze str. 33/41 z 3-wejściowym OR). `test_random.py` – 2×150 losowych układów (`random_circuits.py`, 2–5 wejść, 3–10 bramek, rozgałęzienie zawsze przez jeden węzeł). `test_engine.py` – scenariusze i minimalne układy błędów wersji 1.1.0 (`tests/fixtures/do-sprawdzenia/blad-*.json`). `test_gates.py` – funkcje bramek.
- `tests/fixtures/do-sprawdzenia/` – układy do ręcznego sprawdzania w aplikacji (Plik → Wczytaj układ) z kluczem odpowiedzi w `README.md` (wszystkie testy każdej usterki wg wyroczni, zapis wzorcami z x).
- `test_materials.py::test_dalgorytm_str41_znajduje_test_z_materialow` – silnik znajduje test ze str. 41 (bez porównywania tabeli wiersz w wiersz). Błędy wersji 1.1.0 (fałszywe testy i sprzeczności przy rekonwergencji, propagacja jedną ścieżką, wspólne źródło wejść bramki, podsumowanie po sprzeczności) są naprawione.

## Materiały źródłowe (poza repozytorium)

- `../Materiały.pdf` – wykład/instrukcje: D-algebra i Tabela 2 (str. 32–36, **errata**: kolumny f_AND i f_OR zamienione, w wierszu (~D,~D) f_AND = D zamiast ~D), D-algorytm z Tabelami 3–5 i przykładem tabeli (str. 37–41), przykład wymagający propagacji wieloma ścieżkami (str. 42), miary sterowalności/obserwowalności (str. 43–45; uwaga: c¹(x) = 0 dla komplementarnych wejść na str. 44 wygląda na błąd – powinno być „nieosiągalne”), PODEM z wagami WO/WK i przykładem (str. 46–50). Druga wersja tego samego wykładu: str. 61–69.
- `../MiDST/TESTER/` – program TESTER (Turbo Pascal for Windows, 1996) używany na zajęciach, **z kodem źródłowym**: `DALGEBRA.PAS` (D-sześciany), `MYOBJCTS.PAS` (pobudzenie, propagacja wskazaną przez studenta ścieżką, badanie zgodności, tryb testu z punktacją), `TESTER.PAS` (UI). Pliki `.PAS` w CP1250. Bramki max 2-wejściowe, usterki na wejściach elementów. `../MiDST/EDYTOR/` – edytor schematów, `scanedu/` – niezwiązane (boundary scan).

## Konwencje

- **Priorytetem jest czystość kodu i przejrzystość repozytorium.** Wybieraj najprostsze rozwiązanie; nie dodawaj narzędzi, automatyzacji ani warstw, które nie są niezbędne (np. wersja nie jest zapisywana w kodzie ani wyliczana z commitów – decyduje etykieta PR).
- Styl kodu zwarty (wiele instrukcji w jednej linii, krótkie nazwy zmiennych) – zachowywać spójność z otoczeniem.
- Zmiany w strukturze komponentu muszą być zgodne po obu stronach (`index.html`: `add`, `restoreComponents`, `saveWorkspace`, `autoSave`; `engine.py`) oraz ze starymi plikami JSON/`localStorage`.
- Po zmianie przykładów JSON uruchomić `python buduj_przyklady.py`.
- Po zmianach w `engine.py` uruchomić `python -m pytest`. Poprawność tabel rozstrzyga wyrocznia (`tests/oracle.py`), a nie porównanie z poprzednim wynikiem silnika.
- Komunikaty skryptów wypisywane po polsku – `sys.stdout.reconfigure(encoding='utf-8')` jest potrzebne w konsoli Windows (cp1252).
- Commity: Conventional Commits po angielsku (`feat:`, `fix:`, `chore:`, `refactor:`…).
- **Przy tworzeniu PR zawsze zapytaj użytkownika o rodzaj wydania** – `patch` / `minor` / `major` / bez wydania – podając swoją propozycję z krótkim uzasadnieniem, i ustaw wybraną etykietę na PR (`gh pr create --label …` lub `gh pr edit --add-label …`). Bez etykiety PR nie tworzy release'u.
