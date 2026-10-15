"""Testy na przykładowych układach z repozytorium (1.json, 2.json, ...).

Dla każdej bramki, każdego typu usterki i każdej ścieżki w drzewie decyzji
sprawdzamy niezależnym symulatorem, że wygenerowany wektor faktycznie wykrywa usterkę.
"""
import os

import pytest

import buduj_przyklady
from conftest import (detects, example_files, explore, fill_dont_cares, final_state,
                      is_testable, load_example)

CASES = []
for _f in example_files():
    _comps = load_example(_f)['components']
    for _t in sorted(c for c, v in _comps.items() if v['type'] not in ('IN', 'NODE')):
        for _ft in ('sa0', 'sa1'):
            CASES.append(pytest.param(_f, _t, _ft, id=f"{_f[:-5]}-{_t}-{_ft}"))


def test_examples_exist():
    assert example_files(), "brak przykładowych układów *.json"


@pytest.mark.parametrize('fname,target,fault', CASES)
def test_every_generated_test_detects_fault(fname, target, fault):
    comps = load_example(fname)['components']
    stuck = 0 if fault == 'sa0' else 1
    runs = explore(comps, target, fault)
    for choices, res in runs:
        s = final_state(res)
        if s is None:
            assert any('ERR' in st['delta'].values() or st['msg'].startswith('BŁĄD')
                       for st in res['steps']), f"zakończono bez testu i bez sprzeczności: {choices}"
            continue
        assert s[target] == ('D' if fault == 'sa0' else '~D')
        for vec in fill_dont_cares(comps, s):
            assert detects(comps, vec, target, stuck), f"wektor {vec} nie wykrywa {target} {fault} (wybory {choices})"


@pytest.mark.parametrize('fname,target,fault', CASES)
def test_testable_faults_are_found_on_some_path(fname, target, fault):
    comps = load_example(fname)['components']
    stuck = 0 if fault == 'sa0' else 1
    if not is_testable(comps, target, stuck):
        pytest.skip("usterka nietestowalna (redundantna)")
    runs = explore(comps, target, fault)
    assert any(final_state(res) is not None for _, res in runs), "żadna ścieżka decyzji nie daje testu"


def test_examples_js_is_up_to_date(root_dir):
    with open(os.path.join(root_dir, 'web', 'examples.js'), encoding='utf-8') as f:
        current = f.read()
    assert current == buduj_przyklady.generuj_examples_js(root_dir), \
        "web/examples.js jest nieaktualny - uruchom: python buduj_przyklady.py"
