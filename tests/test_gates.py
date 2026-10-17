import itertools

import pytest

from helpers import circuit
from oracle import LOGIC, d_gate
from engine import DAlgorithmEngine

GATES = ['AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR']
VALUES = ['0', '1', 'D', '~D', 'x']


@pytest.fixture
def eng():
    return DAlgorithmEngine({}, None, 'sa0', {})


def prepared(comps, target, fault='sa0'):
    eng = DAlgorithmEngine(comps, target, fault, {})
    eng.prepare()
    return eng


@pytest.mark.parametrize('gate', GATES)
def test_eval_truth_table(eng, gate):
    for a, b in itertools.product([0, 1], repeat=2):
        assert eng.eval_values(gate, [str(a), str(b)]) == str(LOGIC[gate]([a, b]))


@pytest.mark.parametrize('gate', GATES + ['NOT'])
def test_eval_matches_d_algebra(eng, gate):
    """Wartości w D-algebrze (z x) zgodne z niezależną wyrocznią dla wszystkich kombinacji wejść."""
    for ins in itertools.product(VALUES, repeat=1 if gate == 'NOT' else 2):
        assert eng.eval_values(gate, list(ins)) == d_gate(gate, *ins), ins


def test_eval_not_and_passthrough(eng):
    assert eng.eval_values('NOT', ['0']) == '1'
    assert eng.eval_values('NOT', ['x']) == 'x'
    assert eng.eval_values('NODE', ['1']) == '1'
    assert eng.eval_values('IN', ['0']) == '0'


@pytest.mark.parametrize('gate,ctrl,out', [
    ('AND', '0', '0'), ('NAND', '0', '1'), ('OR', '1', '1'), ('NOR', '1', '0'),
])
def test_eval_controlling_value_beats_x(eng, gate, ctrl, out):
    assert eng.eval_values(gate, [ctrl, 'x']) == out
    assert eng.eval_values(gate, ['x', ctrl]) == out


@pytest.mark.parametrize('gate', GATES)
@pytest.mark.parametrize('val', ['0', '1'])
def test_requirement_options_sound_and_complete(gate, val):
    """Każda opcja daje 'val' niezależnie od pozostałych 'x', a każde wejście dające 'val' jest pokryte."""
    eng = prepared(circuit(X1='IN', X2='IN', G1=(gate, 'X1', 'X2')), 'G1')
    options = eng.requirement_options('G1', val)
    assert options
    covers = lambda o, a, b: o.get('X1', str(a)) == str(a) and o.get('X2', str(b)) == str(b)
    for o in options:
        for a, b in itertools.product([0, 1], repeat=2):
            if covers(o, a, b): assert str(LOGIC[gate]([a, b])) == val, (o, a, b)
    for a, b in itertools.product([0, 1], repeat=2):
        if str(LOGIC[gate]([a, b])) == val: assert any(covers(o, a, b) for o in options), (a, b)


def test_requirement_options_not():
    eng = prepared(circuit(X1='IN', G1=('NOT', 'X1')), 'G1')
    assert eng.requirement_options('G1', '1') == [{'X1': '0'}]
    assert eng.requirement_options('G1', '0') == [{'X1': '1'}]


def test_requirement_options_use_d_values_only_where_error_can_reach():
    # G3 = XOR(W1, G2) z W1 = D: wartość 1 daje G2 = ~D (G2 = NOT(W1) leży w zasięgu błędu)
    comps = circuit(X1='IN', X2='IN', G1=('AND', 'X1', 'X2'), W1=('NODE', 'G1'), G2=('NOT', 'W1'),
                    G3=('XOR', 'W1', 'G2'), G4=('XOR', 'W1', 'X2'))
    eng = prepared(comps, 'G1')
    eng.assign_state('G1', 'D', {})
    assert eng.requirement_options('G3', '1') == [{'G2': '~D'}]
    assert eng.requirement_options('G4', '1') == []  # X2 nie może mieć wartości D


def test_requirement_options_merge_pins_from_same_line():
    eng = prepared(circuit(X1='IN', X2='IN', G1=('OR', 'X1', 'X2'), W1=('NODE', 'G1'), G2=('AND', 'W1', 'W1')), 'G2')
    assert eng.requirement_options('G2', '0') == [{'G1': '0'}]
    assert eng.requirement_options('G2', '1') == [{'G1': '1'}]


def test_resolve_name_follows_node_chain():
    comps = circuit(X1='IN', W1=('NODE', 'X1'), W2=('NODE', 'W1'), G1=('NOT', 'W2'))
    eng = DAlgorithmEngine(comps, 'G1', 'sa0', {})
    assert eng.resolve_name('W2') == 'X1'
    assert eng.resolve_name('W1') == 'X1'
    assert eng.resolve_name('G1') == 'G1'


def test_assign_state_propagates_through_nodes_and_detects_conflict():
    comps = circuit(X1='IN', W1=('NODE', 'X1'), W2=('NODE', 'W1'), G1=('NOT', 'W2'))
    eng = DAlgorithmEngine(comps, 'G1', 'sa0', {})
    eng.algo_state = {c: 'x' for c in comps}
    delta = {}
    assert eng.assign_state('W1', '1', delta) is False
    assert eng.algo_state['X1'] == eng.algo_state['W1'] == eng.algo_state['W2'] == '1'
    assert delta == {'W1': '1', 'X1': '1', 'W2': '1'}
    assert eng.assign_state('W2', '1', {}) is False   # ta sama wartość - brak zmian
    assert eng.assign_state('X1', '0', {}) is True    # sprzeczność
