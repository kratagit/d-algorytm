import itertools
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import DAlgorithmEngine  # noqa: E402

GATES = ['AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR']


def circuit(**spec):
    """Buduje słownik komponentów w formacie frontendu.

    circuit(X1='IN', W1=('NODE', 'X1'), G1=('AND', 'X1', 'X2'), G2=('NOT', 'G1'))
    """
    comps = {}
    for cid, s in spec.items():
        if isinstance(s, str): s = (s,)
        ctype, *ins = s
        ins = (list(ins) + [None, None])[:2]
        comps[cid] = {'id': cid, 'type': ctype, 'x': 0, 'y': 0, 'inputs': ins, 'waypoints': [[], []]}
    return comps


def run_engine(components, target, fault_type, choices=None):
    return DAlgorithmEngine(components, target, fault_type, choices or {}).run()


def final_state(result):
    """Stan z wiersza 'TEST' albo None, gdy algorytm zakończył się sprzecznością."""
    last = result['steps'][-1] if result['steps'] else None
    if last and last['msg'].startswith('TEST'):
        return last['s']
    return None


# --- Niezależny symulator logiczny (nie korzysta z kodu silnika) ---

_LOGIC = {
    'AND': lambda a, b: a & b, 'OR': lambda a, b: a | b,
    'NAND': lambda a, b: 1 - (a & b), 'NOR': lambda a, b: 1 - (a | b),
    'XOR': lambda a, b: a ^ b, 'XNOR': lambda a, b: 1 - (a ^ b),
}


def simulate(components, pi_values, fault=None):
    """Zwraca wartości (0/1) wszystkich komponentów. fault = (id, 0|1) wymusza stan wyjścia."""
    memo = {}

    def val(cid):
        if cid in memo: return memo[cid]
        if fault and cid == fault[0]:
            memo[cid] = fault[1]
            return fault[1]
        c = components[cid]
        t = c['type']
        if t == 'IN': v = pi_values[cid]
        elif t == 'NODE': v = val(c['inputs'][0])
        elif t == 'NOT': v = 1 - val(c['inputs'][0])
        else: v = _LOGIC[t](val(c['inputs'][0]), val(c['inputs'][1]))
        memo[cid] = v
        return v

    return {cid: val(cid) for cid in components}


def primary_inputs(components):
    return sorted(c for c in components if components[c]['type'] == 'IN')


def primary_outputs(components):
    used = {i for c in components.values() for i in c['inputs'] if i}
    return sorted(c for c in components if c not in used and components[c]['type'] != 'IN')


def detects(components, pi_values, target, stuck):
    good = simulate(components, pi_values)
    bad = simulate(components, pi_values, fault=(target, stuck))
    return any(good[o] != bad[o] for o in primary_outputs(components))


def fill_dont_cares(components, state):
    """Wszystkie wektory wejściowe zgodne ze stanem (wejścia 'x' przyjmują 0 i 1)."""
    pis = primary_inputs(components)
    fixed = {p: int(state[p]) for p in pis if state.get(p) in ('0', '1')}
    free = [p for p in pis if p not in fixed]
    for bits in itertools.product([0, 1], repeat=len(free)):
        yield {**fixed, **dict(zip(free, bits))}


def is_testable(components, target, stuck):
    pis = primary_inputs(components)
    return any(detects(components, dict(zip(pis, bits)), target, stuck)
               for bits in itertools.product([0, 1], repeat=len(pis)))


def explore(components, target, fault_type, limit=2000):
    """Przechodzi całe drzewo decyzji silnika. Zwraca listę (choices, result)."""
    seen, out, stack = set(), [], [{}]
    while stack and len(out) < limit:
        choices = stack.pop()
        key = frozenset(choices.items())
        if key in seen: continue
        seen.add(key)
        res = run_engine(components, target, fault_type, dict(choices))
        out.append((choices, res))
        for d in res['decision_log']:
            if d['id'] in choices: continue
            for i in range(len(d['options'])):
                stack.append({**choices, d['id']: i})
    return out


# --- Przykłady z repozytorium ---

def example_files():
    return sorted((f for f in os.listdir(ROOT) if f[:-5].isdigit() and f.endswith('.json')),
                  key=lambda f: int(f[:-5]))


def load_example(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def root_dir():
    return ROOT
