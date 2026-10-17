from helpers import check_fault, circuit, final_state, fixtures, known_bug, load_circuit, report, run_engine
from oracle import is_testable


def test_missing_target_returns_empty_result():
    res = run_engine(circuit(X1='IN'), 'G99', 'sa0')
    assert res == {'cols': [], 'steps': [], 'decision_log': []}


def test_columns_order_inputs_gates_nodes():
    comps = circuit(G10=('NOT', 'X2'), W3=('NODE', 'X1'), X2='IN', G2=('AND', 'W3', 'X2'), X1='IN')
    res = run_engine(comps, 'G2', 'sa0')
    assert res['cols'] == ['X1', 'X2', 'G2', 'G10', 'W3']


def test_single_and_sa0():
    res = run_engine(circuit(X1='IN', X2='IN', G1=('AND', 'X1', 'X2')), 'G1', 'sa0')
    s = final_state(res)
    assert s == {'X1': '1', 'X2': '1', 'G1': 'D'}
    assert res['decision_log'] == []  # jedyna możliwość pobudzenia
    assert res['steps'][0]['full'] and res['steps'][-1]['full']


def test_single_and_sa1_offers_excitation_alternatives():
    comps = circuit(X1='IN', X2='IN', G1=('AND', 'X1', 'X2'))
    res = run_engine(comps, 'G1', 'sa1')
    assert final_state(res) == {'X1': '0', 'X2': 'x', 'G1': '~D'}
    [dec] = res['decision_log']
    assert dec['id'] == 'excite_G1' and dec['selected'] == 0
    assert [o['label'] for o in dec['options']] == ['X1=0', 'X2=0']

    res2 = run_engine(comps, 'G1', 'sa1', {'excite_G1': 1})
    assert final_state(res2) == {'X1': 'x', 'X2': '0', 'G1': '~D'}
    assert res2['decision_log'][0]['selected'] == 1


def test_propagation_sets_non_controlling_side_input():
    comps = circuit(X1='IN', X2='IN', X3='IN', G1=('AND', 'X1', 'X2'), G2=('OR', 'G1', 'X3'))
    s = final_state(run_engine(comps, 'G1', 'sa0'))
    assert s == {'X1': '1', 'X2': '1', 'X3': '0', 'G1': 'D', 'G2': 'D'}


def test_inverting_gates_flip_d():
    comps = circuit(X1='IN', X2='IN', X3='IN', G1=('AND', 'X1', 'X2'), G2=('NOT', 'G1'), G3=('NAND', 'G2', 'X3'))
    s = final_state(run_engine(comps, 'G1', 'sa0'))
    assert (s['G1'], s['G2'], s['G3'], s['X3']) == ('D', '~D', 'D', '1')


def test_fanout_through_node_creates_branch_decision():
    comps = circuit(X1='IN', X2='IN', X3='IN', X4='IN',
                    G1=('AND', 'X1', 'X2'), W1=('NODE', 'G1'),
                    G2=('OR', 'W1', 'X3'), G3=('AND', 'W1', 'X4'))
    res = run_engine(comps, 'G1', 'sa0')
    branch = next(d for d in res['decision_log'] if d['id'] == 'branch_G1')
    assert [o['label'] for o in branch['options']] == ['Przez G2 (OR)', 'Przez G3 (AND)']
    assert final_state(res)['G2'] == 'D'

    s = final_state(run_engine(comps, 'G1', 'sa0', {'branch_G1': 1}))
    assert (s['G3'], s['X4'], s['W1']) == ('D', '1', 'D')


def test_justification_reaches_primary_inputs():
    # Boczne wejście G3 pochodzi z bramki - musi zostać uzasadnione wstecz
    comps = circuit(X1='IN', X2='IN', X3='IN', X4='IN',
                    G1=('AND', 'X1', 'X2'), G2=('NOR', 'X3', 'X4'), G3=('AND', 'G1', 'G2'))
    s = final_state(run_engine(comps, 'G1', 'sa0'))
    assert (s['G3'], s['G2'], s['X3'], s['X4']) == ('D', '1', '0', '0')


def test_reconvergent_conflict_is_reported():
    # Pobudzenie G1 sa0 wymaga X1=1, a propagacja przez G3 wymaga G2=NOT(X1)=1 -> X1=0
    comps = circuit(X1='IN', X2='IN', W1=('NODE', 'X1'),
                    G1=('AND', 'W1', 'X2'), G2=('NOT', 'W1'), G3=('AND', 'G1', 'G2'))
    res = run_engine(comps, 'G1', 'sa0')
    assert final_state(res) is None
    last = res['steps'][-1]
    assert 'SPRZECZNOŚĆ' in last['msg']
    assert 'ERR' in last['delta'].values()


def test_impossible_excitation_reports_error():
    # G1 = AND(X1, -) z niepodłączonym wejściem nie da się wysterować na 1
    comps = circuit(X1='IN', G1=('AND', 'X1', None))
    res = run_engine(comps, 'G1', 'sa0')
    assert final_state(res) is None
    assert res['steps'][-1]['msg'].startswith('BŁĄD')


def test_steps_have_consistent_shape():
    comps = circuit(X1='IN', X2='IN', X3='IN', G1=('XOR', 'X1', 'X2'), G2=('XNOR', 'G1', 'X3'))
    res = run_engine(comps, 'G1', 'sa1')
    for step in res['steps']:
        assert set(step) == {'s', 'delta', 'msg', 'full'}
        assert set(step['s']) == set(res['cols'])
        assert set(step['delta']) <= set(res['cols'])


# --- Minimalne układy znanych błędów (tests/fixtures/do-sprawdzenia/blad-*.json, opisane w README.md tamże) ---

BLEDY = {name: load_circuit(path) for name, path in fixtures('do-sprawdzenia').items() if name.startswith('blad-')}


def bug_case(name):
    data = BLEDY[name]
    return check_fault(data['components'], data['target'], data['fault_type'])


def test_minimal_circuits_facts():
    """Fakty o minimalnych układach według wyroczni – przesłanki testów poniżej."""
    comps = {name: data['components'] for name, data in BLEDY.items()}
    assert is_testable(comps['blad-1-zbiezne-galezie'], 'G1', 0)
    assert is_testable(comps['blad-2-to-samo-zrodlo'], 'G2', 1)
    assert not is_testable(comps['blad-3-falszywy-test'], 'G1', 0)
    assert not is_testable(comps['blad-3-falszywy-test'], 'G1', 1)
    assert is_testable(comps['blad-4-falszywa-sprzecznosc'], 'G1', 0)
    assert not is_testable(comps['blad-5-wiersz-po-sprzecznosci'], 'G1', 0)


@known_bug('zbiezne_d')
def test_reconvergent_d_on_both_inputs():
    problems = bug_case('blad-1-zbiezne-galezie')
    assert not problems, report(problems)


@known_bug('to_samo_zrodlo')
def test_gate_with_both_inputs_from_same_signal():
    problems = bug_case('blad-2-to-samo-zrodlo')
    assert not problems, report(problems)


@known_bug('brak_d_algebry')
def test_redundant_fault_gets_no_test():
    problems = bug_case('blad-3-falszywy-test')
    assert not problems, report(problems)


@known_bug('brak_d_algebry')
def test_requirement_satisfied_by_d_values():
    problems = bug_case('blad-4-falszywa-sprzecznosc')
    assert not problems, report(problems)


@known_bug('podsumowanie_po_sprzecznosci')
def test_no_summary_after_propagation_conflict():
    data = BLEDY['blad-5-wiersz-po-sprzecznosci']
    steps = run_engine(data['components'], data['target'], data['fault_type'])['steps']
    conflict = next(n for n, s in enumerate(steps) if 'ERR' in s['delta'].values())
    assert conflict == len(steps) - 1, [s['msg'] for s in steps[conflict:]]
