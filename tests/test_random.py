"""Losowe układy (powtarzalne – wyznaczone ziarnem) sprawdzane niezależną wyrocznią.

Dwie rodziny po 150 układów wielkości jak na zajęciach: bez rekonwergencji i z rekonwergencją
(ścieżki, które rozchodzą się i ponownie spotykają – tam najłatwiej o błędy D-algorytmu).
"""
import pytest

from helpers import check_fault, gate_targets, report
from random_circuits import random_circuit

SEEDS = range(150)
LIMIT = 50000  # maks. liczba przebiegów (kombinacji decyzji) na jedną usterkę – przekroczenie to błąd testu


@pytest.mark.parametrize('reconvergent', [False, True], ids=['bez-rekonwergencji', 'z-rekonwergencja'])
@pytest.mark.parametrize('seed', SEEDS)
def test_random_circuit(seed, reconvergent):
    comps = random_circuit(seed, reconvergent)
    problems = [p for t in gate_targets(comps) for f in ('sa0', 'sa1') for p in check_fault(comps, t, f, LIMIT)]
    assert not problems, report(problems)
