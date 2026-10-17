"""Losowe układy (powtarzalne – wyznaczone ziarnem) sprawdzane niezależną wyrocznią.

Układy bez rekonwergencji muszą spełniać wszystkie zasady. W układach z rekonwergencją obecny silnik
ma znane błędy (D na obu wejściach, brak D-algebry w badaniu zgodności, propagacja jedną ścieżką),
dlatego zasady budowy tabeli sprawdzamy osobno dla każdego układu, a pełną poprawność – zbiorczo
jako oczekiwaną porażkę, która zgłosi się, gdy błędy zostaną naprawione.
"""
from functools import lru_cache

import pytest

from helpers import OPTIONS, STRUCTURE, check_fault, gate_targets, known_bug, report
from random_circuits import random_circuit

SEEDS = range(150)
LIMIT = 20000  # maks. liczba przebiegów (kombinacji decyzji) na jedną usterkę – przekroczenie to błąd testu


@lru_cache(maxsize=None)
def problems_for(seed, reconvergent):
    comps = random_circuit(seed, reconvergent)
    return [p for t in gate_targets(comps) for f in ('sa0', 'sa1') for p in check_fault(comps, t, f, LIMIT)]


@pytest.mark.parametrize('seed', SEEDS)
def test_without_reconvergence(seed):
    problems = problems_for(seed, False)
    assert not problems, report(problems)


@pytest.mark.parametrize('seed', SEEDS)
def test_with_reconvergence_table_structure(seed):
    problems = [p for p in problems_for(seed, True) if p[0] == STRUCTURE]
    assert not problems, report(problems)


@known_bug('zbiezne_d', 'brak_d_algebry', 'jedna_sciezka')
def test_with_reconvergence_fully_correct():
    failing = {}
    for seed in SEEDS:
        problems = problems_for(seed, True)
        if problems: failing[seed] = problems
    summary = {cat: sum(1 for ps in failing.values() for c, _ in ps if c == cat) for cat in ('test', 'sprzecznosc', 'kompletnosc', OPTIONS)}
    assert not failing, f'{len(failing)}/{len(SEEDS)} układów z naruszeniami {summary}\n' + report(next(iter(failing.values())))
