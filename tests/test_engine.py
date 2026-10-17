from helpers import check_fault, circuit, final_state, fixtures, load_circuit, report, run_engine
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
    [branch] = res['decision_log']
    assert branch['id'] == 'branch_G2_G3' and branch['title'] == 'Propagacja błędu. Wybierz drogę:'
    assert [o['label'] for o in branch['options']] == ['Przez G2 (OR)', 'Przez G3 (AND)']
    assert final_state(res)['G2'] == 'D'

    s = final_state(run_engine(comps, 'G1', 'sa0', {'branch_G2_G3': 1}))
    assert (s['G3'], s['X4'], s['W1'], s['G2']) == ('D', '1', 'D', 'x')


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


# --- Minimalne układy błędów wersji 1.1.0 (tests/fixtures/do-sprawdzenia/blad-*.json, opisane w README.md tamże) ---

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


def test_reconvergent_d_on_both_inputs():
    problems = bug_case('blad-1-zbiezne-galezie')
    assert not problems, report(problems)


def test_gate_with_both_inputs_from_same_signal():
    problems = bug_case('blad-2-to-samo-zrodlo')
    assert not problems, report(problems)


def test_redundant_fault_gets_no_test():
    problems = bug_case('blad-3-falszywy-test')
    assert not problems, report(problems)


def test_requirement_satisfied_by_d_values():
    problems = bug_case('blad-4-falszywa-sprzecznosc')
    assert not problems, report(problems)


def test_no_summary_after_propagation_conflict():
    data = BLEDY['blad-5-wiersz-po-sprzecznosci']
    steps = run_engine(data['components'], data['target'], data['fault_type'])['steps']
    conflict = next(n for n, s in enumerate(steps) if 'ERR' in s['delta'].values())
    assert conflict == len(steps) - 1, [s['msg'] for s in steps[conflict:]]


# --- Przykład z materiałów (str. 41) w wersji z bramkami 2-wejściowymi ---

MATERIALY = load_circuit(fixtures('do-sprawdzenia')['materialy-str41'])['components']


def msgs(res):
    return [s['msg'] for s in res['steps']]


def test_material_example_table_rows():
    res = run_engine(MATERIALY, 'G2', 'sa1')
    assert msgs(res) == [
        'Stan początkowy układu',
        'Pobudzenie błędu: G2. Wymagane: X4=1',
        'Wybór ścieżki propagacji (G3, G5, G10, G7)',
        'Propagacja błędu przez G3 (NOR). Wymagane: G1=0',
        'Propagacja błędu przez G5 (AND). Wymagane: X3=1',
        'Propagacja błędu przez G10 (OR). Wymagane: G4=0',
        'Propagacja błędu przez G7 (OR). Wymagane: G6=0',
        'Stan po propagacji (Podsumowanie)',
        'Badanie zgodności stanu na G4=0. Wymagane: G1=0',
        'Badanie zgodności stanu na G1=0. Wymagane: X2=1',
        'Badanie zgodności stanu na G6=0. Wymagane: X5=0',
        'TEST (Stan końcowy układu)',
    ]
    steps = res['steps']
    assert steps[2]['delta'] == {} and steps[2]['s'] == steps[1]['s']
    assert steps[5]['delta'] == {'G4': '0', 'G10': 'D'}
    assert steps[8]['delta'] == {'X1': 'x', 'G1': '0', 'G4': '0'}
    assert steps[10]['delta'] == {'G2': '~D', 'X5': '0', 'G6': '0'}  # wiersz pokazuje wszystkie wejścia bramki
    branches = [d for d in res['decision_log'] if d['id'].startswith('branch_')]
    assert [[o['label'] for o in d['options']] for d in branches] == [
        ['Przez G3 (NOR)', 'Przez G6 (AND)', 'Przez G8 (AND)'], ['Przez G5 (AND)', 'Przez G6 (AND)', 'Przez G8 (AND)'],
        ['Przez G10 (OR)', 'Przez G6 (AND)', 'Przez G8 (AND)'], ['Przez G7 (OR)', 'Przez G6 (AND)', 'Przez G8 (AND)']]


def test_material_example_other_path():
    # droga przez G6 daje test 0,x,0,1,1,x – ten sam, który materiały podają na str. 50
    res = run_engine(MATERIALY, 'G2', 'sa1', {'branch_G3_G6_G8': 1})
    assert msgs(res)[2] == 'Wybór ścieżki propagacji (G6, G7)'
    s = final_state(res)
    assert [s[x] for x in ('X1', 'X2', 'X3', 'X4', 'X5', 'X6')] == ['0', 'x', '0', '1', '1', 'x']


def test_material_example_paths_that_cancel():
    # do G7 dociera D (przez G10) i ~D (przez G6), OR(D, ~D) = 1
    res = run_engine(MATERIALY, 'G2', 'sa1', {'branch_G10_G6_G8': 1, 'branch_G7_G10_G8': 1})
    assert msgs(res)[2] == 'Wybór ścieżki propagacji (G3, G5, G6, G10, G7)'
    assert msgs(res)[-1] == 'SPRZECZNOŚĆ (Blokada propagacji) na G7! Błąd nie przechodzi (D i ~D znoszą się).'


def test_no_path_row_when_fault_is_on_output():
    steps = run_engine(circuit(X1='IN', X2='IN', G1=('AND', 'X1', 'X2')), 'G1', 'sa0')['steps']
    assert not any(s['msg'].startswith('Wybór ścieżki') for s in steps)
