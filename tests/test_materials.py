"""Zgodność z materiałami do zajęć (Materiały.pdf) – tabele D-algebry, D-sześcianów i przykłady z rozwiązaniami.

Część testów sprawdza silnik, a część samą wyrocznię testów i przepisane dane (połączenia układu z przykładu),
porównując je z kilkoma niezależnymi wynikami z materiałów.
"""
import itertools
import re

import pytest

from engine import DAlgorithmEngine
from helpers import circuit, explore, fixtures, known_bug, load_circuit
from oracle import Oracle, d_gate, d_simulate

EXAMPLE = load_circuit(fixtures('materialy')['uklad-g1-g9'])
COMPS = EXAMPLE['components']
GATES = ['AND', 'OR', 'NAND', 'NOR', 'XOR']
N = '~D'

# Tabela 2 (str. 35) dokładnie tak, jak jest wydrukowana: x1, x2, f_AND, f_OR, f_NAND, f_NOR, f_XOR
TABELA_2 = [
    ('0', '0', '0', '0', '1', '1', '0'), ('0', '1', '1', '0', '1', '0', '1'), ('0', 'D', 'D', '0', '1', N, 'D'),
    ('0', N, N, '0', '1', 'D', N), ('1', '0', '1', '0', '1', '0', '1'), ('1', '1', '1', '1', '0', '0', '0'),
    ('1', 'D', '1', 'D', N, '0', N), ('1', N, '1', N, 'D', '0', 'D'), ('D', '0', 'D', '0', '1', N, 'D'),
    ('D', '1', '1', 'D', N, '0', N), ('D', 'D', 'D', 'D', N, N, '0'), ('D', N, '1', '0', '1', '0', '1'),
    (N, '0', N, '0', '1', 'D', N), (N, '1', '1', N, 'D', '0', 'D'), (N, 'D', '1', '0', '1', '0', '1'),
    (N, N, 'D', N, 'D', 'D', '0'),
]

# Tabela 3 (str. 38) – pierwotne D-sześciany: wejścia wymuszające D / ~D na wyjściu bramki
TABELA_3 = {
    'AND': {('0', 'x', N), ('x', '0', N), ('1', '1', 'D')},
    'OR': {('1', 'x', 'D'), ('x', '1', 'D'), ('0', '0', N)},
    'NAND': {('0', 'x', 'D'), ('x', '0', 'D'), ('1', '1', N)},
    'NOR': {('1', 'x', N), ('x', '1', N), ('0', '0', 'D')},
    'XOR': {('0', '0', N), ('1', '1', N), ('0', '1', 'D'), ('1', '0', 'D')},
}

# Tabela 4 (str. 39) – przesyłowe D-sześciany
TABELA_4 = {
    'AND': {('D', '1', 'D'), ('1', 'D', 'D'), (N, '1', N), ('1', N, N)},
    'OR': {('D', '0', 'D'), ('0', 'D', 'D'), (N, '0', N), ('0', N, N)},
    'NAND': {('D', '1', N), ('1', 'D', N), (N, '1', 'D'), ('1', N, 'D')},
    'NOR': {('D', '0', N), ('0', 'D', N), (N, '0', 'D'), ('0', N, 'D')},
    'XOR': {('0', 'D', 'D'), ('D', '0', 'D'), (N, '0', N), ('0', N, N),
            ('1', 'D', N), ('D', '1', N), ('1', N, 'D'), (N, '1', 'D')},
}

# Tabela 5 (str. 40) – pierwotne sześciany
TABELA_5 = {
    'AND': {('0', 'x', '0'), ('x', '0', '0'), ('1', '1', '1')},
    'OR': {('1', 'x', '1'), ('x', '1', '1'), ('0', '0', '0')},
    'NAND': {('0', 'x', '1'), ('x', '0', '1'), ('1', '1', '0')},
    'NOR': {('1', 'x', '0'), ('x', '1', '0'), ('0', '0', '1')},
    'XOR': {('0', '0', '0'), ('1', '1', '0'), ('1', '0', '1'), ('0', '1', '1')},
}


# --- D-algebra (wyrocznia) ---

def test_tabela_2_nand_nor_xor():
    for x1, x2, _, _, f_nand, f_nor, f_xor in TABELA_2:
        assert (d_gate('NAND', x1, x2), d_gate('NOR', x1, x2), d_gate('XOR', x1, x2)) == (f_nand, f_nor, f_xor), (x1, x2)


def test_tabela_2_errata_and_or():
    """W materiałach kolumny f_AND i f_OR są zamienione, a w wierszu (~D, ~D) w kolumnie f_AND jest D zamiast ~D."""
    for x1, x2, f_and, f_or, *_ in TABELA_2:
        assert d_gate('AND', x1, x2) == f_or, (x1, x2)
        if (x1, x2) != (N, N): assert d_gate('OR', x1, x2) == f_and, (x1, x2)
    assert d_gate('OR', N, N) == N  # wydrukowano D


@pytest.mark.parametrize('gate', GATES)
def test_tabela_4_zgodna_z_d_algebra(gate):
    assert {(a, b, d_gate(gate, a, b)) for a, b, _ in TABELA_4[gate]} == TABELA_4[gate]


# --- Silnik a tabele D-sześcianów ---

@pytest.mark.parametrize('gate', GATES)
@pytest.mark.parametrize('value', ['0', '1'])
def test_tabela_5_pierwotne_szesciany(gate, value):
    """Badanie zgodności dla bramki z nieustalonymi wejściami proponuje dokładnie pierwotne sześciany z materiałów."""
    eng = DAlgorithmEngine(circuit(X1='IN', X2='IN', G1=(gate, 'X1', 'X2')), 'G1', 'sa0', {})
    eng.prepare()
    cubes = {(o.get('X1', 'x'), o.get('X2', 'x'), value) for o in eng.requirement_options('G1', value)}
    assert cubes == {row for row in TABELA_5[gate] if row[2] == value}


@pytest.mark.parametrize('gate', GATES)
def test_tabela_3_pobudzenie(gate):
    """Pobudzenie błędu na wyjściu bramki wybiera dokładnie pierwotne D-sześciany z materiałów."""
    comps = circuit(X1='IN', X2='IN', G1=(gate, 'X1', 'X2'))
    found = set()
    for fault, out in (('sa0', 'D'), ('sa1', N)):
        for _, res in explore(comps, 'G1', fault)[0]:
            step = next(s for s in res['steps'] if s['msg'].startswith('Pobudzenie'))
            found.add((step['s']['X1'], step['s']['X2'], out))
    assert found == TABELA_3[gate]


@pytest.mark.parametrize('gate', GATES)
def test_tabela_4_propagacja(gate):
    """Propagacja przez bramkę ustawia drugie wejście i wyjście zgodnie z przesyłowymi D-sześcianami."""
    found = set()
    for pin in (0, 1):
        ins = ('F', 'XB') if pin == 0 else ('XB', 'F')
        comps = circuit(XA='IN', XB='IN', F=('NOT', 'XA'), G=(gate, *ins))
        for fault in ('sa0', 'sa1'):
            for _, res in explore(comps, 'F', fault)[0]:
                step = next(s for s in res['steps'] if s['msg'].startswith('Propagacja błędu przez G'))
                found.add((step['s'][ins[0]], step['s'][ins[1]], step['s']['G']))
    assert found == TABELA_4[gate]


# --- Układ G1–G9 z materiałów: sprawdzenie przepisanych połączeń wynikami ze str. 33 i 41 ---

def test_symulacja_str33():
    sim = EXAMPLE['symulacja_str33']
    values = d_simulate(COMPS, sim['wejscia'], tuple(sim['usterka']))
    assert {k: values[k] for k in sim['wartosci']} == sim['wartosci']


def _all_fills(test):
    free = [k for k, v in test.items() if v == 'x']
    for bits in itertools.product([0, 1], repeat=len(free)):
        yield {**{k: int(v) for k, v in test.items() if v != 'x'}, **dict(zip(free, bits))}


def test_test_ze_str41_wykrywa_usterke():
    """Test z tabeli na str. 41 (x,1,1,1,0,x) wykrywa usterkę G2 s-a-1 dla każdego uzupełnienia x."""
    test = {k: v for k, v in EXAMPLE['dalgorytm_str41']['tabela'][-1]['wartosci'].items() if k.startswith('X')}
    oracle = Oracle(COMPS, 'G2', 1)
    for vec in _all_fills(test):
        values = oracle.matching({k: str(v) for k, v in vec.items()})[0][1]
        assert any(values[o] in ('D', N) for o in oracle.outputs), vec


def test_tabela_str41_zgodna_z_symulacja():
    """Wiersze „Stan końcowy” i „Test” z materiałów zgadzają się z symulacją dla każdego uzupełnienia x."""
    data = EXAMPLE['dalgorytm_str41']
    oracle = Oracle(COMPS, 'G2', 1)
    for row in data['tabela']:
        if row['etap'] not in ('stan_koncowy', 'test'): continue
        assert oracle.matching(row['wartosci']), row['etap']
        pis = {k: v for k, v in row['wartosci'].items() if k.startswith('X') and v != 'x'}
        for vec, values in oracle.matching(pis):
            if row['etap'] == 'test':
                assert all(values[k] == v for k, v in row['wartosci'].items() if v != 'x'), vec


def test_przyklad_str42_jeden_test():
    """Błąd 6/0 z przykładu na str. 42 (edytor-6, linia G11) ma tylko jeden test (0,0,0,0)."""
    comps = load_circuit(fixtures('tester')['edytor-6'])['components']
    assert Oracle(comps, 'G11', 0).tests() == [{'X0': 0, 'X1': 0, 'X2': 0, 'X3': 0}]


# --- Tabela D-algorytmu z materiałów (str. 41) jako wzorzec dla silnika ---

STAGES = [('Stan początkowy', 'start'), ('Pobudzenie', 'pobudzenie'), ('Wybór ścieżki', 'wybor_sciezki'), ('Propagacja', 'propagacja'),
          ('Stan po propagacji', 'stan_koncowy'), ('Badanie zgodności', 'zgodnosc'), ('TEST', 'test')]


def _normalize(step, columns):
    stage = next((name for prefix, name in STAGES if step['msg'].startswith(prefix)), None)
    values = step['s'] if step['full'] else step['delta']
    row = {'etap': stage, 'wartosci': {k: values[k] for k in columns if k in values}}
    gate = re.search(r'(?:przez|na) (\w+)', step['msg'])
    if stage in ('propagacja', 'zgodnosc') and gate: row['bramka'] = gate.group(1)
    return row


@known_bug('format_tabeli')
def test_tabela_dalgorytmu_str41():
    data = EXAMPLE['dalgorytm_str41']
    expected = [{k: v for k, v in row.items() if k != 'sciezka'} for row in data['tabela']]
    tables = [[_normalize(s, data['kolumny']) for s in res['steps']] for _, res in explore(COMPS, 'G2', 'sa1')[0]]
    assert expected in tables
