"""Uruchamianie silnika w testach i sprawdzanie wygenerowanych tabel.

`check_run` zwraca naruszenia zasad, które musi spełniać każda tabela – niezależnie od tego,
jakie decyzje wybrał użytkownik. Prawdę ustala niezależna wyrocznia (oracle.py).
Każde naruszenie ma kategorię, żeby testy mogły odróżnić znane ograniczenia silnika od regresji.
"""
import json
import os

from engine import DAlgorithmEngine
from oracle import Oracle, fault_cone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')
D_VALUES = ('D', '~D')
VALUES = ('0', '1', 'D', '~D', 'x')

# Kategorie naruszeń
STRUCTURE = 'struktura'        # budowa tabeli: stan początkowy, kolumny, wartości, zmiany już ustalonych linii
TEST = 'test'                  # wiersz TEST niezgodny z symulacją albo wektor nie wykrywa usterki
CONFLICT = 'sprzecznosc'       # zgłoszona sprzeczność/blokada/błąd pobudzenia, której w rzeczywistości nie ma
COMPLETENESS = 'kompletnosc'   # usterka testowalna, a żadna ścieżka decyzji nie daje testu
OPTIONS = 'opcje'              # wadliwa lista decyzji (powtórzone opcje, wybór poza zakresem)

def circuit(**spec):
    """Buduje słownik komponentów w formacie aplikacji.

    circuit(X1='IN', W1=('NODE', 'X1'), G1=('AND', 'X1', 'X2'), G2=('NOT', 'G1'))
    """
    comps = {}
    for cid, s in spec.items():
        if isinstance(s, str): s = (s,)
        ctype, *ins = s
        ins = (list(ins) + [None, None])[:max(2, len(ins))]
        comps[cid] = {'id': cid, 'type': ctype, 'x': 0, 'y': 0, 'inputs': ins, 'waypoints': [[], []]}
    return comps


def run_engine(components, target, fault_type, choices=None):
    return DAlgorithmEngine(components, target, fault_type, choices or {}).run()


def final_state(result):
    """Stan z wiersza 'TEST' albo None, gdy algorytm nie wyznaczył testu."""
    last = result['steps'][-1] if result['steps'] else None
    return last['s'] if last and last['msg'].startswith('TEST') else None


def explore(components, target, fault_type, limit=20000):
    """Przechodzi drzewo decyzji silnika (każdą kombinację wyborów z list rozwijanych).

    Zwraca listę (wybory, wynik) i informację, czy drzewo zostało przejrzane w całości.
    Każdy przebieg (ciąg decyzji, które naprawdę wystąpiły) jest uruchamiany raz: dla przebiegu z ustalonymi
    pierwszymi `fixed` decyzjami rozwijane są tylko alternatywy dalszych decyzji.
    """
    out, stack = [], [({}, 0)]
    while stack and len(out) < limit:
        choices, fixed = stack.pop()
        res = run_engine(components, target, fault_type, choices)
        log = res['decision_log']
        out.append(({d['id']: d['selected'] for d in log}, res))
        for k in range(fixed, len(log)):
            prefix = {d['id']: d['selected'] for d in log[:k]}
            stack.extend(({**prefix, log[k]['id']: i}, k + 1) for i in range(len(log[k]['options'])) if i != log[k]['selected'])
    return out, not stack


def gate_targets(comps):
    return sorted(c for c, v in comps.items() if v['type'] not in ('IN', 'NODE'))


def load_circuit(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def app_examples():
    """Przykłady wbudowane w aplikację ([NUMER].json w katalogu głównym)."""
    files = sorted((f for f in os.listdir(ROOT) if f[:-5].isdigit() and f.endswith('.json')), key=lambda f: int(f[:-5]))
    return {f'przyklad-{f[:-5]}': os.path.join(ROOT, f) for f in files}


def fixtures(group):
    folder = os.path.join(FIXTURES, group)
    return {f[:-5]: os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith('.json')}


def check_run(comps, target, fault_type, result, oracle):
    """Naruszenia zasad poprawnej tabeli D-algorytmu dla jednego przebiegu silnika: lista (kategoria, opis)."""
    problems = []
    steps, cols = result['steps'], result['cols']
    if not steps: return [(STRUCTURE, 'brak kroków')]
    if not (steps[0]['full'] and set(steps[0]['s'].values()) == {'x'}):
        problems.append((STRUCTURE, 'pierwszy wiersz nie jest stanem początkowym (same x)'))

    cone, prev = fault_cone(comps, target), {}
    for n, st in enumerate(steps, 1):
        s, delta = st['s'], st['delta']
        if set(s) != set(cols): problems.append((STRUCTURE, f'krok {n}: stan nie obejmuje wszystkich kolumn'))
        if any(v not in VALUES for v in s.values()) or any(v not in VALUES + ('ERR',) for v in delta.values()):
            problems.append((STRUCTURE, f'krok {n}: niedozwolona wartość'))
        for k, v in prev.items():
            if v != 'x' and s.get(k) != v:
                problems.append((STRUCTURE, f'krok {n}: linia {k} zmieniła wartość {v} -> {s.get(k)}'))
        for k, v in delta.items():
            if v in ('0', '1') + D_VALUES and s.get(k) != v:
                problems.append((STRUCTURE, f'krok {n}: wiersz pokazuje {k}={v}, a stan ma {k}={s.get(k)}'))
        for k, v in s.items():
            if v in D_VALUES and k not in cone:
                problems.append((STRUCTURE, f'krok {n}: {k}={v} poza zasięgiem błędu'))
        if 'ERR' in delta.values():
            problems += _check_conflict(n, st, oracle)
        if st['msg'].startswith('BŁĄD'):
            required = 'D' if fault_type == 'sa0' else '~D'
            if oracle.realizable({}, lambda d: d[target] == required):
                problems.append((CONFLICT, f'krok {n}: fałszywy błąd pobudzenia – {target} da się wysterować'))
        prev = s

    state = final_state(result)
    if state is not None:
        pis = {k: v for k, v in state.items() if comps[k]['type'] == 'IN' and v != 'x'}
        for vec, d in oracle.matching(pis):
            if not any(d[o] in D_VALUES for o in oracle.outputs):
                problems.append((TEST, f'TEST: wektor {vec} nie wykrywa usterki')); break
            wrong = {k: f'{v} (naprawdę {d[k]})' for k, v in state.items() if v != 'x' and d[k] != v}
            if wrong:
                problems.append((TEST, f'TEST: dla wejść {vec} tabela podaje nieprawdziwe wartości {wrong}')); break
    elif not any('ERR' in st['delta'].values() or st['msg'].startswith('BŁĄD') for st in steps):
        problems.append((STRUCTURE, 'brak testu i brak wiersza wyjaśniającego (sprzeczność / błąd)'))

    for d in result['decision_log']:
        labels = [o['label'] for o in d['options']]
        if len(labels) != len(set(labels)): problems.append((OPTIONS, f'decyzja {d["id"]}: powtórzone opcje {labels}'))
        if not 0 <= d['selected'] < len(labels): problems.append((OPTIONS, f'decyzja {d["id"]}: wybór poza zakresem'))
    return problems


def _check_conflict(n, step, oracle):
    """Sprzeczność jest prawdziwa, jeśli dotychczasowych przypisań nie da się zrealizować żadnym wektorem."""
    s = step['s']
    gate = next(k for k, v in step['delta'].items() if v == 'ERR')
    if 'D-granica' in step['msg']:
        if oracle.realizable(s, lambda d: any(d[o] in D_VALUES for o in oracle.outputs)):
            return [(CONFLICT, f'krok {n}: fałszywa pusta D-granica – przy obecnych przypisaniach błąd może dotrzeć do wyjścia')]
    elif 'Blokada propagacji' in step['msg']:
        if oracle.realizable(s, lambda d: d[gate] in D_VALUES):
            return [(CONFLICT, f'krok {n}: fałszywa blokada na {gate} – przy obecnych przypisaniach błąd może przez nią przejść')]
    elif oracle.realizable(s):
        return [(CONFLICT, f'krok {n}: fałszywa sprzeczność na {gate} – przypisania da się zrealizować')]
    return []


def check_fault(comps, target, fault_type, limit=20000):
    """Wszystkie przebiegi dla jednej usterki: lista (kategoria, opis) ze wskazaniem wyborów użytkownika."""
    oracle = Oracle(comps, target, 0 if fault_type == 'sa0' else 1)
    runs, complete = explore(comps, target, fault_type, limit)
    problems = [] if complete else [(STRUCTURE, f'{target}/{fault_type}: drzewo decyzji ma ponad {limit} przebiegów '
                                                '– nie wszystko zostało sprawdzone, zwiększ limit')]
    for choices, res in runs:
        where = f'{target}/{fault_type} {choices or "domyślne wybory"}'
        problems += [(cat, f'{where}: {msg}') for cat, msg in check_run(comps, target, fault_type, res, oracle)]
    if complete and oracle.tests() and not any(final_state(r) is not None for _, r in runs):
        problems.append((COMPLETENESS, f'{target}/{fault_type}: usterka jest testowalna (np. {oracle.tests()[0]}), '
                                       'a żadna ścieżka decyzji nie daje testu'))
    return problems


def report(problems, limit=8):
    """Czytelny opis naruszeń do komunikatu asercji."""
    lines = [f'[{cat}] {msg}' for cat, msg in problems[:limit]]
    if len(problems) > limit: lines.append(f'... i {len(problems) - limit} więcej')
    return '\n'.join(lines)
