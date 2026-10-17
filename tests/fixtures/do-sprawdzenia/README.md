# Układy do ręcznego sprawdzania

Każdy plik wczytasz w aplikacji: **Plik → Wczytaj układ**. Wybierz bramkę i typ usterki, kliknij **Oblicz Test**, a wynik porównaj z kluczem poniżej. Klucz wyznaczyła wyrocznia testów (`tests/oracle.py`) – sprawdzenie wszystkich kombinacji wejść w układzie zdatnym i z usterką.

Jak czytać klucz: test z aplikacji jest poprawny, jeśli **każde** jego uzupełnienie (każde `x` zamienione na 0 i na 1) jest na liście testów danej usterki. Opisy „teraz” dotyczą naprawionego silnika (po wersji 1.1.0).

## 1. Błędy wersji 1.1.0 – najmniejsze możliwe układy (naprawione)

### `blad-1-zbiezne-galezie.json`

Błąd dochodzi do G3 dwiema gałęziami (bezpośrednio z W1 i przez G2).

- **Wersja 1.1.0 pokazywała:** G1 s-a-0, domyślne wybory: aplikacja zgłasza „SPRZECZNOŚĆ (Blokada propagacji) na G3! Drugie wejście ma stan D”.
- **Prawda (do policzenia na kartce):** Dla X1=1, X2=1, X3=0: zdatny G1=1, G2=1, G3=1; z usterką G1=0, G2=0, G3=0 – wyjście się różni, więc błąd przez G3 przechodzi (D AND D = D). Blokady nie ma.
- **Teraz (domyślne wybory):** propagacja przez G2 (X3=0), potem przez G3 – „Wymagane: Brak”, bo oba wejścia G3 mają już D (D AND D = D) – TEST X1=1, X2=1, X3=0.

### `blad-2-to-samo-zrodlo.json`

Oba wejścia G2 = AND są podłączone do tego samego węzła W1 (bramka działa jak bufor).

- **Wersja 1.1.0 pokazywała:** G2 s-a-1, domyślne wybory: aplikacja pokazuje TEST bez żadnych wymagań na wejściach (X1, X2 = x).
- **Prawda (do policzenia na kartce):** G2 = G1 = X1 OR X2. Usterkę s-a-1 wykrywa tylko X1=0, X2=0 (zdatny G2=0, z usterką 1). Np. X1=1 niczego nie wykrywa – to nie jest test.
- **Teraz (domyślne wybory):** pobudzenie wymaga G1=0, badanie zgodności daje X1=0, X2=0 – TEST 00, jedyny poprawny.

### `blad-3-falszywy-test.json`

G4 = XOR(XNOR(X1, G1), NOT(G1)) = X1 – wyjście nie zależy od G1, więc usterek G1 nie da się wykryć.

- **Wersja 1.1.0 pokazywała:** G1 s-a-0, wybory „Propagacja błędu z G1. Wybierz drogę” → „Przez G3 (NOT)” oraz „Propagacja błędu przez G4” → „G2=1”: aplikacja pokazuje TEST X1=0, X2=0.
- **Prawda (do policzenia na kartce):** Dla X1=0, X2=0: zdatny G1=1, G2=0, G3=0, G4=0; z usterką G1=0, G2=1, G3=1, G4=XOR(1,1)=0 – wyjście takie samo, to nie jest test. Tabela podaje G2=1, a naprawdę G2 = ~D.
- **Teraz (domyślne wybory):** propagacja przez G2 i G4, a badanie zgodności kończy się SPRZECZNOŚCIĄ na G3=0 (G3 = NOT G1, a G1 ma D). Przy żadnym wyborze nie ma testu, bo usterki nie da się wykryć.

### `blad-4-falszywa-sprzecznosc.json`

G3 = XOR(G1, NOT(G1)) = 1 zawsze.

- **Wersja 1.1.0 pokazywała:** G1 s-a-0, wybór „Propagacja błędu z G1. Wybierz drogę” → „Przez G4 (AND)”: aplikacja zgłasza sprzeczność na G3=1; w pozostałych drogach też nie znajduje testu.
- **Prawda (do policzenia na kartce):** Dla X1=1, X2=1: zdatny G1=1, G3=1, G4=1; z usterką G1=0, G3=1, G4=0 – to jest test. G3=1 da się uzyskać (D XOR ~D = 1), więc sprzeczności nie ma.
- **Teraz (domyślne wybory):** domyślnie błąd idzie przez G2 i utyka na G3 (docierają do niej D i ~D, które się znoszą) – to prawdziwa sprzeczność tej drogi. „Przez G4 (AND)” w pierwszym „Wybierz drogę” daje TEST X1=1, X2=1 (badanie zgodności G3=1: G1=D, G2=~D).

### `blad-5-wiersz-po-sprzecznosci.json`

Pobudzenie G1 s-a-0 wymaga X1=0, a ten sam sygnał blokuje propagację przez G2.

- **Wersja 1.1.0 pokazywała:** G1 s-a-0: sprzeczność jest prawdziwa (usterki nie da się wykryć), ale po niej tabela pokazuje jeszcze wiersz „Stan po propagacji (Podsumowanie)”.
- **Prawda (do policzenia na kartce):** Po sprzeczności próba powinna się kończyć (materiały, str. 37: „Odrzuć błędny test. Cofnij się do najbliższego punktu decyzyjnego”).
- **Teraz (domyślne wybory):** SPRZECZNOŚĆ (Blokada propagacji) na G2 kończy próbę, bez wiersza podsumowania.

## 2. Przykład z materiałów (str. 41)

### `materialy-str41.json`

Układ z tabeli „Działanie D-algorytmu” (str. 41). Aplikacja ma tylko bramki 2-wejściowe, więc 3-wejściowy OR G7 jest tu zbudowany z dwóch: G10 = OR(G4, G5) i G7 = OR(G10, G6). Dla **G2 s-a-1** materiały wyznaczają test x1..x6 = x,1,1,1,0,x (ścieżka G3, G5, G7 – tutaj G3, G5, G10, G7).

Wejścia w kolejności X1X2X3X4X5X6, wyjścia: G7, G9. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G1 s-a-0 | `0011xx`, `1001xx`, `10x00x`, `x0x0x0` |
| G1 s-a-1 | `0111xx`, `1101xx`, `11x00x`, `x1x0x0` |
| G10 s-a-0 | `10x1xx`, `10xx0x`, `x111xx` |
| G10 s-a-1 | `00x1xx`, `0xx00x`, `x101xx`, `x1x00x` |
| G2 s-a-0 | `00x01x`, `x0x0x0`, `x1001x`, `x1100x` |
| G2 s-a-1 | `00x11x`, `x0x1x0`, `x1011x`, `x1110x` |
| G3 s-a-0 | `x111xx` |
| G3 s-a-1 | `0011xx`, `0x100x`, `x1100x` |
| G4 s-a-0 | `10x1xx`, `10xx0x` |
| G4 s-a-1 | `00x1xx`, `0xx00x`, `x101xx`, `x1x00x` |
| G5 s-a-0 | `x111xx` |
| G5 s-a-1 | `00x1xx`, `0xx00x`, `x101xx`, `x1x00x` |
| G6 s-a-0 | `0xx01x`, `x1x01x` |
| G6 s-a-1 | `00x1xx`, `0xx00x`, `x101xx`, `x1x00x` |
| G7 s-a-0 | `10xxxx`, `x111xx`, `xxx01x` |
| G7 s-a-1 | `00x1xx`, `0xx00x`, `x101xx`, `x1x00x` |
| G8 s-a-0 | `x0x0x0` |
| G8 s-a-1 | `x1xxx0`, `xxx1x0` |
| G9 s-a-0 | `x0x0xx`, `xxxxx1` |
| G9 s-a-1 | `x1xxx0`, `xxx1x0` |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

## 3. Losowe układy bez rekonwergencji (aplikacja powinna być bezbłędna)

### `losowy-prosty-1.json`

Wejścia w kolejności X1X2X3, wyjścia: G7, G9. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G4 s-a-0 | `0xx`, `x0x` |
| G4 s-a-1 | `11x` |
| G5 s-a-0 | `110` |
| G5 s-a-1 | `111` |
| G6 s-a-0 | `0xx`, `x0x`, `xx0` |
| G6 s-a-1 | `111` |
| G7 s-a-0 | `111` |
| G7 s-a-1 | `0xx`, `x0x`, `xx0` |
| G9 s-a-0 | `11x` |
| G9 s-a-1 | `0xx`, `x0x` |

### `losowy-prosty-2.json`

Wejścia w kolejności X1X2X3X4, wyjścia: G11, G13, G14, G15, G5, G9. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G11 s-a-0 | `xx00`, `xx11` |
| G11 s-a-1 | `xx01`, `xx10` |
| G13 s-a-0 | `xx0x` |
| G13 s-a-1 | `xx1x` |
| G14 s-a-0 | `xx0x` |
| G14 s-a-1 | `xx1x` |
| G15 s-a-0 | `0x00`, `0x11`, `1x01`, `1x10` |
| G15 s-a-1 | `0x01`, `0x10`, `1x00`, `1x11` |
| G5 s-a-0 | `0xxx` |
| G5 s-a-1 | `1xxx` |
| G6 s-a-0 | `xx0x` |
| G6 s-a-1 | `xx1x` |
| G8 s-a-0 | `0xx0`, `1xx1` |
| G8 s-a-1 | `0xx1`, `1xx0` |
| G9 s-a-0 | `x0xx` |
| G9 s-a-1 | `x1xx` |

### `losowy-prosty-3.json`

Wejścia w kolejności X1X2X3X4, wyjścia: G11, G12, G14. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G11 s-a-0 | `00xx`, `11xx`, `xx1x` |
| G11 s-a-1 | `010x`, `100x` |
| G12 s-a-0 | `1xx1` |
| G12 s-a-1 | `0xxx`, `xxx0` |
| G14 s-a-0 | `0001`, `1101` |
| G14 s-a-1 | `01xx`, `10xx`, `xx1x`, `xxx0` |
| G5 s-a-0 | `000x`, `110x` |
| G5 s-a-1 | `010x`, `100x` |
| G7 s-a-0 | `0xxx`, `xxx0` |
| G7 s-a-1 | `1xx1` |
| G9 s-a-0 | `010x`, `100x`, `xx00` |
| G9 s-a-1 | `0001`, `1101` |

### `losowy-prosty-4.json`

Wejścia w kolejności X1X2X3X4, wyjścia: G11, G13, G6. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G10 s-a-0 | `x010` |
| G10 s-a-1 | `x1x0`, `xx00` |
| G11 s-a-0 | `x1x0`, `xx00` |
| G11 s-a-1 | `x01x`, `xxx1` |
| G13 s-a-0 | `0xx0`, `x1xx` |
| G13 s-a-1 | `10xx`, `x0x1` |
| G5 s-a-0 | `10xx`, `x01x`, `x0x1` |
| G5 s-a-1 | `11xx`, `x11x`, `x1x1` |
| G6 s-a-0 | `xx01`, `xx10` |
| G6 s-a-1 | `xx00`, `xx11` |
| G8 s-a-0 | `10xx`, `x0x1` |
| G8 s-a-1 | `00x0` |

### `losowy-prosty-5.json`

Wejścia w kolejności X1X2X3X4, wyjścia: G12, G14, G9. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G12 s-a-0 | `0x00`, `0x11`, `1x01`, `1x10` |
| G12 s-a-1 | `0x01`, `0x10`, `1x00`, `1x11` |
| G13 s-a-0 | `xx01`, `xx10` |
| G13 s-a-1 | `xx00`, `xx11` |
| G14 s-a-0 | `xx00`, `xx11` |
| G14 s-a-1 | `xx01`, `xx10` |
| G5 s-a-0 | `xx01`, `xx10` |
| G5 s-a-1 | `xx00`, `xx11` |
| G6 s-a-0 | `xx00`, `xx11` |
| G6 s-a-1 | `xx01`, `xx10` |
| G7 s-a-0 | `011x`, `101x` |
| G7 s-a-1 | `001x`, `111x` |
| G9 s-a-0 | `011x`, `101x` |
| G9 s-a-1 | `00xx`, `11xx`, `xx0x` |

## 4. Losowe układy z rekonwergencją (tu myliła się wersja 1.1.0)

### `losowy-zbiezny-1.json`

Wejścia w kolejności X1X2X3, wyjścia: G10. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G10 s-a-0 | `0x0`, `x0x` |
| G10 s-a-1 | `11x`, `x11` |
| G4 s-a-0 | `11x`, `x11` |
| G4 s-a-1 | `010` |
| G5 s-a-0 | `11x`, `x11` |
| G5 s-a-1 | `10x`, `x01` |
| G7 s-a-0 | `010` |
| G7 s-a-1 | `000` |
| G8 s-a-0 | `000` |
| G8 s-a-1 | `1xx`, `x1x`, `xx1` |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

### `losowy-zbiezny-2.json`

Wejścia w kolejności X1X2X3, wyjścia: G12, G6. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G10 s-a-0 | `1xx`, `xx1` |
| G10 s-a-1 | `0x0` |
| G12 s-a-0 | **brak – usterki nie da się wykryć** |
| G12 s-a-1 | `xxx` |
| G4 s-a-0 | `00x` |
| G4 s-a-1 | `1xx`, `x1x` |
| G5 s-a-0 | `xx0` |
| G5 s-a-1 | `xx1` |
| G6 s-a-0 | `000`, `1x1`, `x11` |
| G6 s-a-1 | `001`, `1x0`, `x10` |
| G9 s-a-0 | `xx1` |
| G9 s-a-1 | **brak – usterki nie da się wykryć** |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

### `losowy-zbiezny-3.json`

Wejścia w kolejności X1X2X3, wyjścia: G12, G14. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G10 s-a-0 | **brak – usterki nie da się wykryć** |
| G10 s-a-1 | `0x1`, `x01` |
| G11 s-a-0 | `0xx`, `x0x` |
| G11 s-a-1 | **brak – usterki nie da się wykryć** |
| G12 s-a-0 | `0x1`, `100`, `x11` |
| G12 s-a-1 | `0x0`, `101`, `x10` |
| G14 s-a-0 | `xxx` |
| G14 s-a-1 | **brak – usterki nie da się wykryć** |
| G4 s-a-0 | `11x` |
| G4 s-a-1 | `0x1`, `10x` |
| G6 s-a-0 | `11x` |
| G6 s-a-1 | `0xx`, `x0x` |
| G7 s-a-0 | `0x1`, `1x0` |
| G7 s-a-1 | `0x0`, `1x1` |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

### `losowy-zbiezny-4.json`

Wejścia w kolejności X1X2X3, wyjścia: G14. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G11 s-a-0 | `11x`, `x11` |
| G11 s-a-1 | **brak – usterki nie da się wykryć** |
| G12 s-a-0 | `11x`, `x11` |
| G12 s-a-1 | `000` |
| G14 s-a-0 | `1xx`, `x1x`, `xx1` |
| G14 s-a-1 | `000` |
| G4 s-a-0 | `10x`, `x01` |
| G4 s-a-1 | `000` |
| G5 s-a-0 | `10x`, `x01` |
| G5 s-a-1 | `000` |
| G7 s-a-0 | `10x`, `x01` |
| G7 s-a-1 | `000` |
| G8 s-a-0 | `010`, `10x`, `x01` |
| G8 s-a-1 | `000` |
| G9 s-a-0 | **brak – usterki nie da się wykryć** |
| G9 s-a-1 | `11x`, `x11` |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

### `losowy-zbiezny-5.json`

Wejścia w kolejności X1X2X3X4, wyjścia: G10, G12. Wzorzec z `x` oznacza wszystkie wektory z dowolną wartością w tym miejscu.

| usterka | wszystkie testy |
|---|---|
| G10 s-a-0 | `0x01`, `0x10`, `1x00`, `1x11` |
| G10 s-a-1 | `0x00`, `0x11`, `1x01`, `1x10` |
| G12 s-a-0 | `0x1x`, `1x0x` |
| G12 s-a-1 | `0x0x`, `1x1x` |
| G5 s-a-0 | `0x0x`, `1x1x` |
| G5 s-a-1 | `0x1x`, `1x0x` |
| G6 s-a-0 | **brak – usterki nie da się wykryć** |
| G6 s-a-1 | **brak – usterki nie da się wykryć** |
| G8 s-a-0 | `0x00`, `0x11`, `1x01`, `1x10` |
| G8 s-a-1 | `0x01`, `0x10`, `1x00`, `1x11` |
| G9 s-a-0 | `x1xx` |
| G9 s-a-1 | `x0xx` |

Aplikacja daje poprawne tabele dla wszystkich usterek tego układu (sprawdzone wszystkie ścieżki decyzji).

## 5. Układy z zajęć (program TESTER)

W `tests/fixtures/tester/` jest 11 układów z TESTER-a w formacie aplikacji – też można je wczytać. Szczególnie ciekawe: `edytor-6` G11 s-a-0 (przykład ze str. 42 – jedyny test 0000 wymaga propagacji dwiema ścieżkami: po G13 i G16 wybierz „Przez G14”, potem G17 i dopiero G18), `tester-rosa` G8 s-a-0 (jedyny test X0..X3 = 0111) i `edytor-x` (bramka G8 z oboma wejściami z węzła W10).
