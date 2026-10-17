"""Konwersja układów z programu TESTER (MiDST, Turbo Pascal 1996, pliki *.GAT) do formatu JSON aplikacji.

    python tests/fixtures/tester/konwertuj_gat.py <katalog MiDST>

Format *.GAT (obiekty Turbo Pascala zapisane przez TStream): nagłówek kolekcji bramek
(typ obiektu 151, liczba elementów, limit, delta), a dla każdego elementu: typ obiektu 150,
rodzaj (1 węzeł, 2 wejście, 3 wyjście, 4 NOT, 5 AND, 6 NAND, 7 OR, 8 NOR, 9 XOR, 10 XNOR),
prostokąt na schemacie i numery elementów podłączonych do dwóch wejść (-1 = brak).
Elementy wyjściowe (OUT) nie mają odpowiednika w aplikacji – wyjściem jest linia, której nic nie odczytuje.
"""
import json
import os
import struct
import sys

TYPES = {1: 'NODE', 2: 'IN', 3: 'OUT', 4: 'NOT', 5: 'AND', 6: 'NAND', 7: 'OR', 8: 'NOR', 9: 'XOR', 10: 'XNOR'}
SOURCES = {  # plik w MiDST -> (nazwa danych testowych, opis)
    'TESTER/1.GAT': ('tester-1', 'Układ z zajęć (TESTER 1.GAT).'),
    'TESTER/2.GAT': ('tester-2', 'Układ z zajęć (TESTER 2.GAT) – cztery wyjścia.'),
    'TESTER/3.GAT': ('tester-3', 'Układ z zajęć (TESTER 3.GAT) – multiplekser z rozgałęzieniem wejścia.'),
    'TESTER/4.GAT': ('tester-4', 'Układ z zajęć (TESTER 4.GAT) – łańcuch bramek wszystkich typów.'),
    'TESTER/5.GAT': ('tester-5', 'Układ z zajęć (TESTER 5.GAT) – dwa wyjścia, rozgałęzienia.'),
    'TESTER/a1.gat': ('tester-a1', 'Układ z zajęć (TESTER a1.gat).'),
    'TESTER/fff.gat': ('tester-fff', 'Układ z zajęć (TESTER fff.gat).'),
    'TESTER/rosa.gat': ('tester-rosa', 'Układ z zajęć (TESTER rosa.gat) – wiele rozgałęzień i ścieżek zbieżnych.'),
    'EDYTOR/6.GAT': ('edytor-6', 'Przykład z materiałów (str. 42): błąd 6/0 ma tylko jeden test (0,0,0,0) '
                                 'i wymaga propagacji dwiema ścieżkami jednocześnie.'),
    'EDYTOR/X.GAT': ('edytor-x', 'Układ z zajęć (EDYTOR X.GAT) – bramka AND z oboma wejściami z tego samego węzła.'),
    'EDYTOR/qaz.gat': ('edytor-qaz', 'Układ z zajęć (EDYTOR qaz.gat).'),
}


def parse(path):
    data = open(path, 'rb').read()
    obj, count = struct.unpack_from('<Hh', data, 0)
    assert obj == 151, f'{path}: nieznany nagłówek {obj}'
    gates = []
    for n in range(count):
        obj, typ, left, top, _, _, in0, in1 = struct.unpack_from('<Hhhhhhhh', data, 8 + 16 * n)
        assert obj == 150, f'{path}: nieznany element {obj}'
        gates.append((TYPES[typ], left, top, [in0, in1]))
    return gates


def to_app(gates, source, description):
    prefix = {'IN': 'X', 'NODE': 'W', 'OUT': 'Y'}
    ids = [prefix.get(t, 'G') + str(i) for i, (t, *_) in enumerate(gates)]
    comps = {}
    for i, (typ, left, top, ins) in enumerate(gates):
        if typ == 'OUT': continue
        ins = [ids[j] if j >= 0 else None for j in ins]
        if typ == 'IN': ins = [None, None]
        if typ in ('NOT', 'NODE'): ins = [ins[0], None]
        comps[ids[i]] = {'id': ids[i], 'type': typ, 'x': round(left * 1.6), 'y': round(top * 1.6), 'inputs': ins, 'waypoints': [[], []]}
    return {'opis': description, 'zrodlo': f'MiDST/{source}', 'components': comps, 'counter': len(gates)}


if __name__ == '__main__':
    midst, out_dir = sys.argv[1], os.path.dirname(os.path.abspath(__file__))
    for source, (name, description) in SOURCES.items():
        data = to_app(parse(os.path.join(midst, source)), source, description)
        with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'{source} -> {name}.json ({len(data["components"])} elementów)')
