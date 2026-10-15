import itertools

import pytest

from conftest import GATES, _LOGIC, circuit
from engine import DAlgorithmEngine


@pytest.fixture
def eng():
    return DAlgorithmEngine({}, None, 'sa0', {})


@pytest.mark.parametrize('gate', GATES)
def test_eval_gate_truth_table(eng, gate):
    for a, b in itertools.product([0, 1], repeat=2):
        assert eng.eval_gate(gate, str(a), str(b)) == str(_LOGIC[gate](a, b))


def test_eval_gate_not_and_passthrough(eng):
    assert eng.eval_gate('NOT', '0', None) == '1'
    assert eng.eval_gate('NOT', '1', None) == '0'
    assert eng.eval_gate('NOT', 'x', None) == 'x'
    assert eng.eval_gate('NODE', '1', None) == '1'
    assert eng.eval_gate('IN', '0', None) == '0'


@pytest.mark.parametrize('gate,ctrl,out', [
    ('AND', '0', '0'), ('NAND', '0', '1'), ('OR', '1', '1'), ('NOR', '1', '0'),
])
def test_eval_gate_controlling_value_beats_x(eng, gate, ctrl, out):
    assert eng.eval_gate(gate, ctrl, 'x') == out
    assert eng.eval_gate(gate, 'x', ctrl) == out


@pytest.mark.parametrize('gate', GATES)
def test_eval_gate_unknown_without_controlling_value(eng, gate):
    nc = {'AND': '1', 'NAND': '1', 'OR': '0', 'NOR': '0'}.get(gate, '0')
    assert eng.eval_gate(gate, nc, 'x') == 'x'
    assert eng.eval_gate(gate, 'x', 'x') == 'x'


@pytest.mark.parametrize('gate', GATES)
@pytest.mark.parametrize('val', ['0', '1'])
def test_justifications_are_sound_and_complete(eng, gate, val):
    """Każda kombinacja z get_justifications daje 'val' niezależnie od 'x',
    a każde wejście dające 'val' jest pokryte przez którąś kombinację."""
    cands = eng.get_justifications(gate, val)
    assert cands
    for cand in cands:
        for a, b in itertools.product([0, 1], repeat=2):
            if cand[0] in ('x', str(a)) and cand[1] in ('x', str(b)):
                assert str(_LOGIC[gate](a, b)) == val, (cand, a, b)
    for a, b in itertools.product([0, 1], repeat=2):
        if str(_LOGIC[gate](a, b)) == val:
            assert any(c[0] in ('x', str(a)) and c[1] in ('x', str(b)) for c in cands), (a, b)


def test_justifications_not(eng):
    assert eng.get_justifications('NOT', '1') == [{0: '0'}]
    assert eng.get_justifications('NOT', '0') == [{0: '1'}]


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
