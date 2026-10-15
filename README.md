# D-Algorytm PRO (Silnik Webowy)

D-Algorytm PRO to zaawansowane narzędzie edukacyjno-inżynierskie pozwalające na projektowanie układów logicznych i automatyczne generowanie wektorów testowych (ATPG) dla pojedynczych usterek typu *stuck-at* (s-a-0, s-a-1). Projekt implementuje klasyczny D-Algorytm ze śledzeniem decyzji, nawracaniem (backtrackingiem) oraz szczegółowym, krokowym wyjaśnianiem podejmowanych akcji.

Rozwiązanie to łączy wydajność obliczeniową Pythona z nowoczesnym, w pełni interaktywnym, sprzętowo akcelerowanym interfejsem stworzonym w technologiach webowych (Vanilla JS / SVG).

---

## 🏗️ Architektura Rozwiązania

Aplikacja została zaprojektowana w modelu **Client-Server (lokalnie)**, gdzie backendem jest instancja Pythona sprzęgnięta z przeglądarką Chromium za pomocą biblioteki `Eel`.

### 1. Warstwa Prezentacji (Frontend - Web UI)
Cały interfejs działa w oparciu o silnik przeglądarki, używając natywnego HTML5, Vanilla JavaScript oraz manipulacji DOM i SVG. Zrezygnowano z ciężkich frameworków (np. React) na rzecz surowej wydajności w zarządzaniu setkami wtyczek i kabli.

* **Silnik Renderujący (SVG & DOM):** Bramki logiczne to obiekty DOM nakładane na absolutnie pozycjonowany kontener. Przewody (kable) renderowane są pod spodem jako ścieżki wektorowe w `<svg>`. Dzięki temu kable mogą być swobodnie załamywane (waypoints), "przyklejane" do siatki prostopadle (snapping przy użyciu klawisza SHIFT) oraz chwytane myszą.
* **Zarządzanie Stanem (State Management):** Architektura opiera się na globalnym obiekcie słownikowym `comps`, przechowującym identyfikatory, typy, pozycje X/Y oraz referencje wejść i ścieżek wszystkich komponentów na planszy.
* **Persystencja Danych:** Wszelkie zmiany graficzne na planszy, ustawienia wybranej bramki czy alternatywne decyzje algorytmu są na bieżąco, asynchronicznie (debounce) zapisywane do pamięci przeglądarki (`localStorage`). Pozwala to na kontynuowanie pracy nawet po zamknięciu aplikacji bez konieczności ręcznego zapisu pliku.
* **Responsywność Algorytmu:** Zmiany parametrów (np. awaria `s-a-0` / `s-a-1` lub cel usterki) błyskawicznie emitują zapytanie do środowiska Pythona, które w ułamku sekundy zwraca wygenerowaną tabelę oraz drzewo decyzji do przeglądarki.

### 2. Warstwa Mostu (Bridge - Eel)
* **Asynchroniczna Komunikacja:** `Eel` zapewnia lekkie połączenie WebSocket pomiędzy światem JavaScriptu a światem Pythona.
* Metoda `@eel.expose run_d_algorithm()` przyjmuje "zrzucony" do formatu JSON układ komponentów oraz wybory użytkownika. Python wykonuje swoją ciężką pracę i odsyła sformatowany słownik obiektów, gotowy do wrzucenia prosto w kod HTML (wygenerowanie dynamicznej tabeli w panelu).

### 3. Warstwa Logiki (Backend - Python)
Jądro aplikacji stanowi klasa `DAlgorithmEngine`, odpowiedzialna za trawienie układu i proces decyzyjny.

* **Topologia i Reprezentacja Sieci:** Słownik komponentów przesłany z przeglądarki jest wstępnie filtrowany w celu rozdzielenia fizycznych bramek od węzłów (`NODE`). Węzły (kropki dystrybucyjne) służą jedynie do graficznego przekazywania sygnałów – algorytm wykorzystuje rekursywną funkcję `resolve_name`, która automatycznie "idzie po kablu" przez węzły tak długo, aż odnajdzie fizyczną bramkę, ignorując sztuczne komponenty graficzne przy liczeniu wymagań bramek.
* **Trójfazowy Silnik Decyzyjny:**
  1. **Pobudzenie błędu:** Wymuszenie stanu `1` (dla uszkodzenia `s-a-0`) lub `0` (dla uszkodzenia `s-a-1`) w węźle testowanym i zadeklarowanie wprowadzenia sygnału `D` lub `~D`.
  2. **Propagacja błędu:** Wytyczanie "uczulonych" ścieżek aż do wyjść obserwowalnych. Wszystkie pozostałe wejścia bramek na ścieżce dostają swoje nienegujące wartości absolutne (np. '1' dla AND, '0' dla OR).
  3. **Badanie Zgodności Stanów (Cofanie/Justification):** Wsteczne przepychanie potrzebnych stanów logicznych w stronę wejść fizycznych (X0, X1...). 
* **Drzewo Decyzyjne (Backtracking):** Ze względu na to, że układ logiczny może wymagać kilku wejść, by osiągnąć pożądany stan (np. na wyjściu bramki OR stan '1' można uzyskać na trzy sposoby: `1-0`, `0-1`, `1-1`), silnik używa logiki decyzyjnej. Wykrywa sytuacje wieloznaczne i zatrzymuje się, przerzucając na Front-end obiekt `decision_log`. Następnie czeka na interakcję ze strony użytkownika (wybór z rozwijanej listy).
* **Wykrywanie Sprzeczności:** Gdy wymagany na bramce sygnał łamie jej zasady (fizykę logiczną) dla narzuconego wcześniej punktu pracy układu, algorytm zwraca tzw. błąd, a w tabeli zjawia się stosowny, sformalizowany komentarz (wraz z wstrzykiwanym tagiem `ERR` by UI nałożyło czerwoną ikonę `❌`).

---

## 🚀 Uruchamianie, testy i budowanie

### Środowisko
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt   # samo uruchamianie: requirements.txt
```

### Uruchomienie ze źródeł
```bash
python main.py
```

### Testy
```bash
python -m pytest
```
Testy (`tests/`) obejmują logikę bramek, scenariusze D-Algorytmu na małych układach oraz wszystkie przykładowe układy: dla każdej bramki, typu usterki i każdej ścieżki w drzewie decyzji wygenerowany wektor jest weryfikowany niezależnym symulatorem z wstrzykniętą usterką. Na GitHubie testy uruchamia workflow `CI` przy każdym pushu i pull requeście.

### Budowanie `.exe` (Nuitka)
```bash
python build.py               # przykłady -> testy -> dist/D-Algorytm.exe
python build.py --skip-tests  # bez testów
```
Skrypt regeneruje `web/examples.js`, uruchamia testy i kompiluje `main.py` Nuitką do jednego pliku bez okna konsoli (z wbudowanym folderem `web/` i modułami sieciowymi Eel). Przy pierwszym buildzie Nuitka pobiera do swojego cache Dependency Walker oraz – jeśli nie ma Visual Studio (MSVC) – kompilator C.

### Wydania (GitHub Releases)
Wydanie powstaje po merge'u PR na `main` oznaczonego etykietą `patch`, `minor` lub `major`. Workflow `Release` uruchamia testy, buduje `.exe` na Windows i publikuje release z plikiem `d-algorytm-<wersja>-windows-x64.exe`. Wersja jest wyliczana automatycznie z ostatniego tagu `vX.Y.Z` (pierwsze wydanie: `v1.0.0`) i nie jest zapisana w kodzie:

| Etykieta | Kiedy | Przykład |
|---|---|---|
| `patch` | poprawki błędów | `1.2.3` → `1.2.4` |
| `minor` | nowe funkcje | `1.2.3` → `1.3.0` |
| `major` | zmiany niekompatybilne (np. nowy format pliku układu) | `1.2.3` → `2.0.0` |

PR bez etykiety nie tworzy wydania.

### Dodawanie wbudowanych przykładów (JSON)
1. Zapisz schemat za pomocą „Zapisz układ”.
2. Umieść plik jako `[NUMER].json` (np. `3.json`) w głównym katalogu projektu.
3. Uruchom `python buduj_przyklady.py` (robi to też `build.py`) – wszystkie pliki `[NUMER].json` zostaną zaszyte w `web/examples.js`, a przyciski w menu „Plik” wygenerują się same.

---
