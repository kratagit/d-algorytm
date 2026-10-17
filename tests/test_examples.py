"""Przykłady wbudowane w aplikację oraz układy z zajęć (program TESTER, tests/fixtures/tester).

Dla każdej bramki, obu typów usterki i każdej ścieżki w drzewie decyzji sprawdzamy niezależną wyrocznią,
że tabela jest zgodna z prawdą: test wykrywa usterkę, wartości linii zgadzają się z symulacją,
każda sprzeczność jest prawdziwa, a każda testowalna usterka ma ścieżkę prowadzącą do testu.
"""
import itertools
import os
import re

import pytest

import buduj_przyklady
from helpers import ROOT, app_examples, check_fault, fixtures, gate_targets, known_bug, load_circuit, report
from oracle import Oracle, gate_inputs, primary_inputs, primary_outputs

MANUAL = fixtures('do-sprawdzenia')
CIRCUITS = {**app_examples(), **fixtures('tester'), 'materialy-str41': MANUAL['materialy-str41']}

KNOWN = {  # (układ, linia, usterka) -> znane błędy silnika
    ('edytor-6', 'G11', 'sa0'): ('jedna_sciezka',),
    ('tester-rosa', 'G8', 'sa0'): ('jedna_sciezka',),
    ('edytor-x', 'G8', 'sa1'): ('to_samo_zrodlo',),
    **{('edytor-x', g, f): ('zbiezne_d', 'jedna_sciezka') for g in ('G0', 'G4', 'G5', 'G6') for f in ('sa0', 'sa1')},
}


def _cases():
    for name, path in CIRCUITS.items():
        comps = load_circuit(path)['components']
        for target in gate_targets(comps):
            for fault in ('sa0', 'sa1'):
                bugs = KNOWN.get((name, target, fault))
                yield pytest.param(name, target, fault, id=f'{name}-{target}-{fault}', marks=[known_bug(*bugs)] if bugs else [])


def test_circuits_exist():
    assert app_examples(), 'brak przykładowych układów [NUMER].json'
    assert len(fixtures('tester')) == 11


@pytest.mark.parametrize('name,target,fault', list(_cases()))
def test_tables_are_true(name, target, fault):
    problems = check_fault(load_circuit(CIRCUITS[name])['components'], target, fault)
    assert not problems, report(problems)


def test_examples_js_is_up_to_date():
    with open(os.path.join(ROOT, 'web', 'examples.js'), encoding='utf-8') as f:
        current = f.read()
    assert current == buduj_przyklady.generuj_examples_js(ROOT), \
        'web/examples.js jest nieaktualny - uruchom: python buduj_przyklady.py'


def _structure(comps):
    """Wyrażenia opisujące wyjścia układu niezależnie od nazw elementów i kolejności wejść bramek."""
    memo = {}

    def expr(cid):
        if cid not in memo:
            c = comps[cid]
            ins = sorted(expr(i) for i in gate_inputs(c))
            memo[cid] = 'IN' if c['type'] == 'IN' else ins[0] if c['type'] == 'NODE' else f"{c['type']}({','.join(ins)})"
        return memo[cid]

    return sorted(expr(o) for o in primary_outputs(comps))


@pytest.mark.parametrize('n', ['1', '2', '4', '5'])
def test_tester_conversion_matches_app_examples(n):
    """Przykłady 1, 2, 4, 5 odtworzono kiedyś w aplikacji ręcznie z TESTER-a – konwerter .GAT musi dać ten sam układ."""
    app = load_circuit(CIRCUITS[f'przyklad-{n}'])['components']
    converted = load_circuit(CIRCUITS[f'tester-{n}'])['components']
    assert _structure(app) == _structure(converted)


def test_manual_answer_key_is_true():
    """Klucz odpowiedzi w tests/fixtures/do-sprawdzenia/README.md zgadza się z wyrocznią (rozwinięte wzorce = wszystkie testy)."""
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'do-sprawdzenia', 'README.md'), encoding='utf-8') as f:
        sections = re.split(r'\n### `', f.read())[1:]
    rows = 0
    for section in sections:
        comps = load_circuit(MANUAL[section.split('.json')[0]])['components']
        pis = primary_inputs(comps)
        for target, stuck, cell in re.findall(r'^\| (\S+) s-a-([01]) \| (.*) \|$', section, re.M):
            listed = {''.join(bits) for pattern in re.findall(r'`([01x]+)`', cell)
                      for bits in itertools.product(*[('0', '1') if ch == 'x' else (ch,) for ch in pattern])}
            truth = {''.join(str(v[p]) for p in pis) for v in Oracle(comps, target, int(stuck)).tests()}
            assert listed == truth, (section.split('.json')[0], target, stuck)
            rows += 1
    assert rows > 100
